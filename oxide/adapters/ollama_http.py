"""
HTTP adapter for Ollama and LM Studio.

Supports both Ollama API and OpenAI-compatible APIs.
"""
import json
from typing import AsyncIterator, List, Optional, Dict, Any

import aiohttp

from .base import BaseAdapter
from ..utils.exceptions import HTTPAdapterError, ServiceUnavailableError, TimeoutError


class OllamaHTTPAdapter(BaseAdapter):
    """
    Adapter for HTTP-based LLM services (Ollama, LM Studio).

    Supports:
    - Ollama API (/api/generate, /api/chat)
    - OpenAI-compatible API (/v1/chat/completions) for LM Studio
    """

    def __init__(self, service_name: str, config: Dict[str, Any]):
        super().__init__(service_name, config)

        self.base_url = config.get("base_url")
        if not self.base_url:
            raise HTTPAdapterError(f"No base_url specified for '{service_name}'")

        # Remove trailing slash
        self.base_url = self.base_url.rstrip("/")

        self.api_type = config.get("api_type", "ollama")
        self.default_model = config.get("default_model")

        self.logger.info(
            f"Initialized {service_name} adapter (base_url={self.base_url}, api_type={self.api_type})"
        )

    async def execute(
        self,
        prompt: str,
        files: Optional[List[str]] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Execute task via HTTP API and stream results.

        Args:
            prompt: Task prompt
            files: Optional files (converted to text context)
            model: Model to use (defaults to configured default_model)
            timeout: Request timeout in seconds
            **kwargs: Additional API-specific parameters

        Yields:
            Response chunks

        Raises:
            HTTPAdapterError: If API request fails
            ServiceUnavailableError: If service is unreachable
        """
        # Build full prompt with file contents if provided
        full_prompt = await self._build_prompt_with_files(prompt, files)

        # Select model
        model_to_use = model or self.default_model
        if not model_to_use:
            raise HTTPAdapterError(
                f"No model specified for {self.service_name} and no default_model configured"
            )

        # Route to appropriate API
        if self.api_type == "ollama":
            async for chunk in self._execute_ollama(full_prompt, model_to_use, timeout):
                yield chunk
        elif self.api_type == "openai_compatible":
            async for chunk in self._execute_openai_compatible(full_prompt, model_to_use, timeout):
                yield chunk
        else:
            raise HTTPAdapterError(f"Unknown api_type: {self.api_type}")

    async def _build_prompt_with_files(
        self,
        prompt: str,
        files: Optional[List[str]] = None
    ) -> str:
        """
        Build prompt with file contents included.

        Note: Unlike CLI tools, HTTP APIs don't support @ syntax,
        so we need to read and include file contents directly.
        """
        if not files:
            return prompt

        from pathlib import Path

        full_prompt = ""

        for file_path in files:
            path = Path(file_path).expanduser().resolve()
            if not path.exists():
                self.logger.warning(f"File not found: {file_path}")
                continue

            try:
                # Read file content (with size limit to avoid OOM)
                MAX_FILE_SIZE = 1024 * 1024  # 1MB per file
                if path.stat().st_size > MAX_FILE_SIZE:
                    self.logger.warning(f"File too large, skipping: {file_path}")
                    continue

                content = path.read_text(encoding="utf-8", errors="replace")
                full_prompt += f"\n\n# File: {file_path}\n```\n{content}\n```\n\n"

            except (OSError, PermissionError, UnicodeDecodeError) as e:
                # Expected file system/encoding errors
                self.logger.debug(f"Cannot read file {file_path}: {e}")
            except Exception as e:
                # Unexpected error
                self.logger.warning(f"Unexpected error reading file {file_path}: {e}")

        full_prompt += f"\n\n{prompt}"
        return full_prompt

    async def _execute_ollama(
        self,
        prompt: str,
        model: str,
        timeout: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        Execute via Ollama API (/api/generate).
        """
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout) if timeout else None

            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPAdapterError(
                            f"Ollama API error (status {response.status}): {error_text}"
                        )

                    # Stream newline-delimited JSON responses
                    async for line_bytes in response.content:
                        line = line_bytes.decode("utf-8").strip()
                        if not line:
                            continue

                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]

                            # Check if done
                            if data.get("done", False):
                                break

                        except json.JSONDecodeError as e:
                            self.logger.warning(f"Invalid JSON from Ollama: {line[:100]}")

        except aiohttp.ClientConnectionError as e:
            raise ServiceUnavailableError(
                self.service_name,
                f"Cannot connect to {self.base_url}: {e}"
            )
        except asyncio.TimeoutError:
            raise TimeoutError(self.service_name, timeout or 0)
        except (aiohttp.ClientError, ConnectionError) as e:
            # Expected HTTP/network errors
            raise HTTPAdapterError(f"HTTP request error: {e}") from e
        except Exception as e:
            # Re-raise known exceptions, wrap unexpected ones
            if not isinstance(e, (HTTPAdapterError, ServiceUnavailableError, TimeoutError)):
                raise HTTPAdapterError(f"Unexpected error: {e}") from e
            raise

    async def _execute_openai_compatible(
        self,
        prompt: str,
        model: str,
        timeout: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        Execute via OpenAI-compatible API (/v1/chat/completions).
        Used for LM Studio and similar services.
        """
        url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": True
        }

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout) if timeout else None

            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPAdapterError(
                            f"OpenAI API error (status {response.status}): {error_text}"
                        )

                    # Stream SSE (Server-Sent Events) format
                    async for line_bytes in response.content:
                        line = line_bytes.decode("utf-8").strip()

                        # SSE format: data: {...}
                        if line.startswith("data: "):
                            json_str = line[6:]  # Remove "data: " prefix

                            if json_str == "[DONE]":
                                break

                            try:
                                data = json.loads(json_str)
                                # Extract content delta
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content")
                                    if content:
                                        yield content

                            except json.JSONDecodeError:
                                self.logger.warning(f"Invalid JSON in SSE: {json_str[:100]}")

        except aiohttp.ClientConnectionError as e:
            raise ServiceUnavailableError(
                self.service_name,
                f"Cannot connect to {self.base_url}: {e}"
            )
        except asyncio.TimeoutError:
            raise TimeoutError(self.service_name, timeout or 0)
        except (aiohttp.ClientError, ConnectionError) as e:
            # Expected HTTP/network errors
            raise HTTPAdapterError(f"HTTP request error: {e}") from e
        except Exception as e:
            # Re-raise known exceptions, wrap unexpected ones
            if not isinstance(e, (HTTPAdapterError, ServiceUnavailableError, TimeoutError)):
                raise HTTPAdapterError(f"Unexpected error: {e}") from e
            raise

    async def health_check(self) -> bool:
        """
        Check if HTTP service is available.
        """
        try:
            # Try appropriate health check endpoint
            if self.api_type == "ollama":
                url = f"{self.base_url}/api/tags"
            else:  # openai_compatible
                url = f"{self.base_url}/v1/models"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200

        except (aiohttp.ClientError, ConnectionError, asyncio.TimeoutError) as e:
            # Expected network/timeout errors
            self.logger.debug(f"Health check failed (expected): {e}")
            return False
        except Exception as e:
            # Unexpected error
            self.logger.warning(f"Health check failed unexpectedly: {e}")
            return False

    async def get_models(self) -> List[str]:
        """
        Get list of available models.
        """
        try:
            if self.api_type == "ollama":
                url = f"{self.base_url}/api/tags"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            data = await response.json()
                            return [model["name"] for model in data.get("models", [])]

            elif self.api_type == "openai_compatible":
                url = f"{self.base_url}/v1/models"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            data = await response.json()
                            return [model["id"] for model in data.get("data", [])]

        except (aiohttp.ClientError, ConnectionError, asyncio.TimeoutError) as e:
            # Expected network/timeout errors
            self.logger.debug(f"Failed to get models (network error): {e}")
        except (json.JSONDecodeError, KeyError) as e:
            # Expected JSON parsing errors
            self.logger.warning(f"Failed to parse models response: {e}")
        except Exception as e:
            # Unexpected error
            self.logger.warning(f"Unexpected error getting models: {e}")

        return []

    def get_service_info(self) -> Dict[str, Any]:
        info = super().get_service_info()
        info.update({
            "base_url": self.base_url,
            "api_type": self.api_type,
            "default_model": self.default_model,
        })
        return info


# Import asyncio for type annotations
import asyncio
