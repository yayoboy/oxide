"""
HTTP adapter for Ollama and LM Studio.

Supports both Ollama API and OpenAI-compatible APIs.
Enhanced with auto-start, auto-model-detection, and smart retry.
"""
import asyncio
import json
from typing import AsyncIterator, List, Optional, Dict, Any

import aiohttp

from .base import BaseAdapter
from ..utils.exceptions import HTTPAdapterError, ServiceUnavailableError, TimeoutError
from ..utils.service_manager import get_service_manager


class OllamaHTTPAdapter(BaseAdapter):
    """
    Adapter for HTTP-based LLM services (Ollama, LM Studio).

    Supports:
    - Ollama API (/api/generate, /api/chat)
    - OpenAI-compatible API (/v1/chat/completions) for LM Studio

    Features:
    - Auto-start Ollama if not running (configurable)
    - Auto-detect best available model if not configured
    - Smart retry on temporary failures
    - Health monitoring and recovery
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

        # Enhanced features configuration
        self.auto_start = config.get("auto_start", True)  # Auto-start service if down
        self.auto_detect_model = config.get("auto_detect_model", True)  # Auto-detect model
        self.max_retries = config.get("max_retries", 2)  # Retry attempts
        self.retry_delay = config.get("retry_delay", 2)  # Delay between retries (seconds)

        # Service manager for auto-start and monitoring
        self.service_manager = get_service_manager()

        # Model cache (will be populated on first use)
        self._detected_model = None
        self._service_initialized = False

        self.logger.info(
            f"Initialized {service_name} adapter (base_url={self.base_url}, "
            f"api_type={self.api_type}, auto_start={self.auto_start}, "
            f"auto_detect={self.auto_detect_model})"
        )

    async def _ensure_service_ready(self) -> bool:
        """
        Ensure service is ready (running and has models).
        Called lazily on first execute.

        Returns:
            True if service is ready
        """
        if self._service_initialized:
            return True

        try:
            # Use service manager to ensure service is healthy
            health = await self.service_manager.ensure_service_healthy(
                service_name=self.service_name,
                base_url=self.base_url,
                api_type=self.api_type,
                auto_start=self.auto_start,
                auto_detect_model=self.auto_detect_model
            )

            if not health["healthy"]:
                error_msg = health.get("error", "Unknown error")
                self.logger.error(f"Service {self.service_name} not healthy: {error_msg}")
                return False

            # Cache detected model if auto-detection is enabled
            if self.auto_detect_model and not self.default_model:
                self._detected_model = health.get("recommended_model")
                if self._detected_model:
                    self.logger.info(f"Auto-detected model for {self.service_name}: {self._detected_model}")
                else:
                    self.logger.warning(f"No model could be auto-detected for {self.service_name}")

            self._service_initialized = True
            return True

        except Exception as e:
            self.logger.error(f"Failed to ensure service ready: {e}")
            return False

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

        Features:
        - Auto-starts service if configured
        - Auto-detects model if not specified
        - Retries on temporary failures

        Args:
            prompt: Task prompt
            files: Optional files (converted to text context)
            model: Model to use (defaults to configured/auto-detected model)
            timeout: Request timeout in seconds
            **kwargs: Additional API-specific parameters

        Yields:
            Response chunks

        Raises:
            HTTPAdapterError: If API request fails
            ServiceUnavailableError: If service is unreachable
        """
        # Ensure service is ready (auto-start, model detection, etc.)
        if not await self._ensure_service_ready():
            raise ServiceUnavailableError(
                self.service_name,
                "Service could not be started or initialized"
            )

        # Build full prompt with file contents if provided
        full_prompt = await self._build_prompt_with_files(prompt, files)

        # Select model (priority: explicit > default > auto-detected)
        model_to_use = model or self.default_model or self._detected_model
        if not model_to_use:
            raise HTTPAdapterError(
                f"No model available for {self.service_name}. "
                f"Please configure default_model or enable auto_detect_model."
            )

        # Execute with retry logic
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                # Route to appropriate API
                if self.api_type == "ollama":
                    async for chunk in self._execute_ollama(full_prompt, model_to_use, timeout):
                        yield chunk
                elif self.api_type == "openai_compatible":
                    async for chunk in self._execute_openai_compatible(full_prompt, model_to_use, timeout):
                        yield chunk
                else:
                    raise HTTPAdapterError(f"Unknown api_type: {self.api_type}")

                # Success - exit retry loop
                return

            except ServiceUnavailableError as e:
                last_error = e
                if attempt < self.max_retries:
                    self.logger.warning(
                        f"Service unavailable (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"retrying in {self.retry_delay}s..."
                    )
                    await asyncio.sleep(self.retry_delay)

                    # Try to restart service if auto_start is enabled
                    if self.auto_start and self.api_type == "ollama":
                        self.logger.info("Attempting to restart Ollama...")
                        await self.service_manager.ensure_ollama_running(self.base_url)
                else:
                    # Final attempt failed
                    raise

            except Exception as e:
                # Non-recoverable error
                raise

        # If we get here, all retries failed
        if last_error:
            raise last_error

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

            except Exception as e:
                self.logger.warning(f"Error reading file {file_path}: {e}")

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
        except Exception as e:
            if not isinstance(e, (HTTPAdapterError, ServiceUnavailableError, TimeoutError)):
                raise HTTPAdapterError(f"Unexpected error: {e}")
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
        except Exception as e:
            if not isinstance(e, (HTTPAdapterError, ServiceUnavailableError, TimeoutError)):
                raise HTTPAdapterError(f"Unexpected error: {e}")
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

        except Exception as e:
            self.logger.debug(f"Health check failed: {e}")
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

        except Exception as e:
            self.logger.warning(f"Failed to get models: {e}")

        return []

    def get_service_info(self) -> Dict[str, Any]:
        info = super().get_service_info()
        info.update({
            "base_url": self.base_url,
            "api_type": self.api_type,
            "default_model": self.default_model,
        })
        return info
