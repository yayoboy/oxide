"""
OpenRouter HTTP adapter for Oxide.

Provides access to 200+ AI models through OpenRouter's unified API with:
- Automatic fallback between models
- Free model support
- Usage cost tracking
- OpenAI-compatible API format
"""
import asyncio
import json
import os
from typing import AsyncIterator, List, Optional, Dict, Any
from decimal import Decimal

import aiohttp

from .base import BaseAdapter
from ..utils.exceptions import HTTPAdapterError, ServiceUnavailableError, TimeoutError


class OpenRouterAdapter(BaseAdapter):
    """
    Adapter for OpenRouter API (https://openrouter.ai).

    Features:
    - Access to 200+ models from various providers
    - Automatic model fallback
    - Free model filtering
    - Usage cost tracking
    - OpenAI-compatible format
    """

    # OpenRouter API base URL
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, service_name: str, config: Dict[str, Any]):
        super().__init__(service_name, config)

        # Set base_url for consistency with other adapters
        self.base_url = self.BASE_URL

        # API key can be from config or environment variable
        self.api_key = config.get("api_key") or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            self.logger.warning(
                f"No API key configured for {service_name}. "
                "Set 'api_key' in config or OPENROUTER_API_KEY environment variable."
            )

        self.default_model = config.get("default_model", "openrouter/auto")
        self.preferred_models = config.get("preferred_models", [])
        self.fallback_models = config.get("fallback_models", [])

        # Free models filter
        self.use_free_only = config.get("use_free_only", False)

        # Retry configuration
        self.max_retries = config.get("max_retries", 2)
        self.retry_delay = config.get("retry_delay", 2)

        # App attribution (optional, for OpenRouter rankings)
        self.site_url = config.get("site_url", "https://github.com/oxide-ai/oxide")
        self.site_name = config.get("site_name", "Oxide LLM Orchestrator")

        # Cached models list
        self._models_cache: Optional[List[Dict[str, Any]]] = None
        self._free_models_cache: Optional[List[str]] = None

        self.logger.info(
            f"Initialized {service_name} adapter "
            f"(model={self.default_model}, free_only={self.use_free_only})"
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
        Execute task via OpenRouter API and stream results.

        Args:
            prompt: Task prompt
            files: Optional files (converted to text context)
            model: Model to use (defaults to configured model)
            timeout: Request timeout in seconds
            **kwargs: Additional OpenRouter-specific parameters

        Yields:
            Response chunks

        Raises:
            HTTPAdapterError: If API request fails
            ServiceUnavailableError: If API is unreachable
        """
        if not self.api_key:
            raise HTTPAdapterError(
                f"{self.service_name}: No API key configured. "
                "Please set api_key in configuration or OPENROUTER_API_KEY env var."
            )

        # Build full prompt with file contents
        full_prompt = await self._build_prompt_with_files(prompt, files)

        # Select model (priority: explicit > default)
        model_to_use = model or self.default_model

        # If free_only is enabled, ensure we use a free model
        if self.use_free_only and model_to_use:
            free_models = await self.get_free_models()
            if model_to_use not in free_models:
                self.logger.warning(
                    f"Model '{model_to_use}' is not free. "
                    f"Switching to first available free model."
                )
                if free_models:
                    model_to_use = free_models[0]
                    self.logger.info(f"Using free model: {model_to_use}")
                else:
                    raise HTTPAdapterError("No free models available")

        # Execute with retry and fallback logic
        models_to_try = [model_to_use]
        if self.fallback_models:
            models_to_try.extend(self.fallback_models)

        last_error = None
        for model_attempt in models_to_try:
            for retry_attempt in range(self.max_retries + 1):
                try:
                    async for chunk in self._execute_request(
                        full_prompt, model_attempt, timeout, **kwargs
                    ):
                        yield chunk

                    # Success - exit both loops
                    return

                except ServiceUnavailableError as e:
                    last_error = e
                    if retry_attempt < self.max_retries:
                        self.logger.warning(
                            f"Service unavailable for {model_attempt} "
                            f"(retry {retry_attempt + 1}/{self.max_retries + 1}), "
                            f"retrying in {self.retry_delay}s..."
                        )
                        await asyncio.sleep(self.retry_delay)
                    else:
                        # Max retries reached for this model, try next model
                        self.logger.warning(
                            f"Model {model_attempt} failed after {self.max_retries + 1} attempts. "
                            f"Trying next fallback model..."
                        )
                        break

                except HTTPAdapterError as e:
                    # Non-retryable error (e.g., invalid API key, bad request)
                    raise

                except Exception as e:
                    last_error = e
                    raise HTTPAdapterError(f"Unexpected error: {e}")

        # All models and retries failed
        if last_error:
            raise last_error
        raise HTTPAdapterError("All models and retries exhausted")

    async def _execute_request(
        self,
        prompt: str,
        model: str,
        timeout: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Execute single request to OpenRouter API."""
        url = f"{self.BASE_URL}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Optional app attribution headers (for OpenRouter rankings)
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.site_name:
            headers["X-Title"] = self.site_name

        # Build request payload (OpenAI-compatible format)
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": True,
        }

        # Add optional parameters
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]

        # Enable fallback if fallback_models are configured
        if self.fallback_models:
            payload["route"] = "fallback"
            payload["models"] = [model] + self.fallback_models

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout) if timeout else None

            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()

                        # Parse error details if available
                        try:
                            error_data = json.loads(error_text)
                            error_msg = error_data.get("error", {}).get("message", error_text)
                        except:
                            error_msg = error_text

                        if response.status == 401:
                            raise HTTPAdapterError(
                                f"Authentication failed: Invalid API key. "
                                f"Please check your OPENROUTER_API_KEY."
                            )
                        elif response.status == 402:
                            raise HTTPAdapterError(
                                f"Payment required: Insufficient credits. "
                                f"Please add credits at https://openrouter.ai/credits"
                            )
                        elif response.status == 429:
                            raise ServiceUnavailableError(
                                self.service_name,
                                f"Rate limit exceeded. Please wait and try again."
                            )
                        elif response.status == 503:
                            raise ServiceUnavailableError(
                                self.service_name,
                                f"Model temporarily unavailable: {error_msg}"
                            )
                        else:
                            raise HTTPAdapterError(
                                f"OpenRouter API error (status {response.status}): {error_msg}"
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

                                # Log detailed usage info if available (final chunk)
                                usage = data.get("usage")
                                if usage:
                                    model_used = data.get("model", "unknown")
                                    prompt_tokens = usage.get("prompt_tokens", 0)
                                    completion_tokens = usage.get("completion_tokens", 0)
                                    total_tokens = usage.get("total_tokens", 0)

                                    self.logger.info(
                                        f"OpenRouter metrics - "
                                        f"model: {model_used}, "
                                        f"tokens: {total_tokens} "
                                        f"(prompt: {prompt_tokens}, completion: {completion_tokens})"
                                    )

                                    # Log cost estimate if model pricing is available
                                    if self._models_cache:
                                        for model_info in self._models_cache:
                                            if model_info["id"] == model_used:
                                                pricing = model_info.get("pricing", {})
                                                prompt_cost_str = pricing.get("prompt", "0")
                                                completion_cost_str = pricing.get("completion", "0")

                                                try:
                                                    from decimal import Decimal
                                                    prompt_cost = Decimal(prompt_cost_str) * prompt_tokens
                                                    completion_cost = Decimal(completion_cost_str) * completion_tokens
                                                    total_cost = prompt_cost + completion_cost

                                                    self.logger.info(
                                                        f"OpenRouter cost estimate: ${float(total_cost):.6f} USD"
                                                    )
                                                except Exception as e:
                                                    self.logger.debug(f"Failed to calculate cost: {e}")
                                                break

                            except json.JSONDecodeError:
                                self.logger.warning(f"Invalid JSON in SSE: {json_str[:100]}")

        except aiohttp.ClientConnectionError as e:
            raise ServiceUnavailableError(
                self.service_name,
                f"Cannot connect to OpenRouter API: {e}"
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                self.service_name,
                timeout or 0,
                f"Request timed out after {timeout}s"
            )
        except Exception as e:
            if not isinstance(e, (HTTPAdapterError, ServiceUnavailableError, TimeoutError)):
                raise HTTPAdapterError(f"Unexpected error: {e}")
            raise

    async def _build_prompt_with_files(
        self,
        prompt: str,
        files: Optional[List[str]] = None
    ) -> str:
        """Build prompt with file contents included."""
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

    async def health_check(self) -> bool:
        """Check if OpenRouter API is available."""
        if not self.api_key:
            return False

        try:
            url = f"{self.BASE_URL}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200

        except Exception as e:
            self.logger.debug(f"Health check failed: {e}")
            return False

    async def get_models(self) -> List[str]:
        """
        Get list of available models from OpenRouter.

        Returns model IDs (e.g., "openai/gpt-4", "anthropic/claude-3-sonnet").
        """
        if self._models_cache:
            return [m["id"] for m in self._models_cache]

        if not self.api_key:
            self.logger.warning("Cannot fetch models: No API key configured")
            return []

        try:
            url = f"{self.BASE_URL}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._models_cache = data.get("data", [])
                        return [model["id"] for model in self._models_cache]
                    else:
                        self.logger.warning(f"Failed to fetch models: HTTP {response.status}")
                        return []

        except Exception as e:
            self.logger.warning(f"Failed to get models: {e}")
            return []

    async def get_free_models(self) -> List[str]:
        """
        Get list of free models from OpenRouter.

        Free models are those with pricing.prompt = "0" or very low cost.
        """
        if self._free_models_cache:
            return self._free_models_cache

        # Ensure models are loaded
        await self.get_models()

        if not self._models_cache:
            return []

        free_models = []
        for model in self._models_cache:
            pricing = model.get("pricing", {})

            # Check if prompt cost is zero or near-zero
            prompt_cost_str = pricing.get("prompt", "0")
            try:
                prompt_cost = Decimal(prompt_cost_str)
                # Consider free if cost is 0 or less than $0.0001 per token
                if prompt_cost <= Decimal("0.0001"):
                    free_models.append(model["id"])
            except (ValueError, TypeError):
                continue

        self._free_models_cache = free_models
        self.logger.info(f"Found {len(free_models)} free models on OpenRouter")

        return free_models

    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model."""
        # Ensure models are loaded
        await self.get_models()

        if not self._models_cache:
            return None

        for model in self._models_cache:
            if model["id"] == model_id:
                return model

        return None

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information."""
        info = super().get_service_info()
        info.update({
            "base_url": self.BASE_URL,
            "default_model": self.default_model,
            "use_free_only": self.use_free_only,
            "has_api_key": bool(self.api_key),
            "fallback_models": self.fallback_models,
        })
        return info
