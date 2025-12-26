"""
Service Manager for Local LLM Services

Handles auto-start, health monitoring, and recovery for:
- Ollama (local inference server)
- LM Studio (OpenAI-compatible API)
- Other local HTTP-based LLM services
"""
import asyncio
import subprocess
import shutil
import platform
from typing import Optional, Dict, Any, List
from pathlib import Path
import aiohttp

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ServiceManager:
    """Manages lifecycle of local LLM services"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._ollama_process = None
        self._health_check_tasks = {}

    async def ensure_ollama_running(
        self,
        base_url: str = "http://localhost:11434",
        auto_start: bool = True,
        timeout: int = 30
    ) -> bool:
        """
        Ensure Ollama is running, auto-start if needed.

        Args:
            base_url: Ollama API base URL
            auto_start: Whether to auto-start if not running
            timeout: Max seconds to wait for startup

        Returns:
            True if Ollama is running, False otherwise
        """
        # Check if already running
        if await self._check_ollama_health(base_url):
            self.logger.info("Ollama is already running")
            return True

        if not auto_start:
            self.logger.warning("Ollama not running and auto_start=False")
            return False

        # Try to start Ollama
        self.logger.info("Ollama not running, attempting to start...")

        if not await self._start_ollama():
            return False

        # Wait for Ollama to be ready
        for i in range(timeout):
            await asyncio.sleep(1)
            if await self._check_ollama_health(base_url):
                self.logger.info(f"Ollama started successfully (took {i+1}s)")
                return True

            if i % 5 == 0 and i > 0:
                self.logger.debug(f"Waiting for Ollama to start... ({i}s/{timeout}s)")

        self.logger.error(f"Ollama failed to start within {timeout}s")
        return False

    async def _check_ollama_health(self, base_url: str) -> bool:
        """Quick health check for Ollama"""
        try:
            url = f"{base_url.rstrip('/')}/api/tags"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as response:
                    return response.status == 200
        except Exception:
            return False

    async def _start_ollama(self) -> bool:
        """
        Start Ollama service using system-appropriate method.

        Returns:
            True if startup initiated successfully
        """
        # Check if ollama is installed
        ollama_path = shutil.which("ollama")
        if not ollama_path:
            self.logger.error("Ollama executable not found in PATH")
            return False

        system = platform.system()

        try:
            if system == "Darwin":  # macOS
                # Check if Ollama.app is running
                result = subprocess.run(
                    ["pgrep", "-f", "Ollama.app"],
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    # Try to start Ollama.app
                    ollama_app = "/Applications/Ollama.app"
                    if Path(ollama_app).exists():
                        subprocess.Popen(["open", "-a", "Ollama"])
                        self.logger.info("Started Ollama.app")
                        return True

                # Fallback: start ollama serve as background process
                self._ollama_process = subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
                self.logger.info("Started ollama serve in background")
                return True

            elif system == "Linux":
                # Try systemd first
                try:
                    subprocess.run(
                        ["systemctl", "--user", "start", "ollama"],
                        check=True,
                        capture_output=True
                    )
                    self.logger.info("Started Ollama via systemd")
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass

                # Fallback: start as background process
                self._ollama_process = subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
                self.logger.info("Started ollama serve in background")
                return True

            elif system == "Windows":
                # Try to start Ollama service
                subprocess.Popen(
                    ["ollama", "serve"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.logger.info("Started Ollama on Windows")
                return True

            else:
                self.logger.error(f"Unsupported platform: {system}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to start Ollama: {e}")
            return False

    async def get_available_models(
        self,
        base_url: str,
        api_type: str = "ollama"
    ) -> List[str]:
        """
        Get list of available models from service.

        Args:
            base_url: Service API base URL
            api_type: "ollama" or "openai_compatible"

        Returns:
            List of model names
        """
        try:
            if api_type == "ollama":
                url = f"{base_url.rstrip('/')}/api/tags"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            data = await response.json()
                            models = [model["name"] for model in data.get("models", [])]
                            self.logger.info(f"Found {len(models)} Ollama models: {models}")
                            return models

            elif api_type == "openai_compatible":
                url = f"{base_url.rstrip('/')}/models"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            data = await response.json()
                            models = [model["id"] for model in data.get("data", [])]
                            self.logger.info(f"Found {len(models)} models in {base_url}: {models}")
                            return models

        except Exception as e:
            self.logger.warning(f"Failed to get models from {base_url}: {e}")

        return []

    async def auto_detect_model(
        self,
        base_url: str,
        api_type: str = "ollama",
        preferred_models: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Auto-detect best available model.

        Args:
            base_url: Service API base URL
            api_type: "ollama" or "openai_compatible"
            preferred_models: List of preferred model names (priority order)

        Returns:
            Model name or None if no models available
        """
        available = await self.get_available_models(base_url, api_type)

        if not available:
            self.logger.warning(f"No models available in {base_url}")
            return None

        # If preferred models specified, try to find them in order
        if preferred_models:
            for preferred in preferred_models:
                # Check exact match
                if preferred in available:
                    self.logger.info(f"Selected preferred model: {preferred}")
                    return preferred

                # Check partial match (e.g., "qwen" matches "qwen2.5-coder:7b")
                for model in available:
                    if preferred.lower() in model.lower():
                        self.logger.info(f"Selected model by partial match: {model} (preferred: {preferred})")
                        return model

        # No preferred model found, return first available
        selected = available[0]
        self.logger.info(f"Selected first available model: {selected}")
        return selected

    async def ensure_service_healthy(
        self,
        service_name: str,
        base_url: str,
        api_type: str = "ollama",
        auto_start: bool = True,
        auto_detect_model: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive service health check with auto-recovery.

        Args:
            service_name: Service identifier
            base_url: Service API base URL
            api_type: "ollama" or "openai_compatible"
            auto_start: Auto-start service if down
            auto_detect_model: Auto-detect model if not configured

        Returns:
            Dict with status, healthy, models, recommended_model
        """
        result = {
            "service": service_name,
            "healthy": False,
            "base_url": base_url,
            "api_type": api_type,
            "models": [],
            "recommended_model": None,
            "error": None
        }

        try:
            # For Ollama, ensure it's running
            if api_type == "ollama" and auto_start:
                is_running = await self.ensure_ollama_running(base_url)
                if not is_running:
                    result["error"] = "Failed to start Ollama"
                    return result

            # Get available models
            models = await self.get_available_models(base_url, api_type)
            result["models"] = models

            if not models:
                result["error"] = "No models available"
                return result

            # Auto-detect recommended model
            if auto_detect_model:
                # Preferred models for different service types
                if api_type == "ollama":
                    preferred = ["qwen2.5-coder", "codellama", "llama3", "mistral"]
                else:  # openai_compatible (LM Studio)
                    preferred = ["qwen", "coder", "code", "llama"]

                recommended = await self.auto_detect_model(base_url, api_type, preferred)
                result["recommended_model"] = recommended

            result["healthy"] = True
            return result

        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"Service health check failed for {service_name}: {e}")
            return result

    async def start_health_monitoring(
        self,
        service_name: str,
        base_url: str,
        api_type: str = "ollama",
        interval: int = 60,
        auto_recovery: bool = True
    ):
        """
        Start background health monitoring for a service.

        Args:
            service_name: Service identifier
            base_url: Service API base URL
            api_type: "ollama" or "openai_compatible"
            interval: Check interval in seconds
            auto_recovery: Attempt auto-recovery on failure
        """
        async def monitor():
            while True:
                try:
                    health = await self.ensure_service_healthy(
                        service_name,
                        base_url,
                        api_type,
                        auto_start=auto_recovery
                    )

                    if not health["healthy"]:
                        self.logger.warning(
                            f"Service {service_name} unhealthy: {health.get('error')}"
                        )

                    await asyncio.sleep(interval)

                except asyncio.CancelledError:
                    self.logger.info(f"Health monitoring stopped for {service_name}")
                    break
                except Exception as e:
                    self.logger.error(f"Health monitoring error for {service_name}: {e}")
                    await asyncio.sleep(interval)

        # Cancel existing monitoring task if any
        if service_name in self._health_check_tasks:
            self._health_check_tasks[service_name].cancel()

        # Start new monitoring task
        task = asyncio.create_task(monitor())
        self._health_check_tasks[service_name] = task
        self.logger.info(f"Started health monitoring for {service_name} (interval: {interval}s)")

    def stop_health_monitoring(self, service_name: str):
        """Stop health monitoring for a service"""
        if service_name in self._health_check_tasks:
            self._health_check_tasks[service_name].cancel()
            del self._health_check_tasks[service_name]
            self.logger.info(f"Stopped health monitoring for {service_name}")

    def cleanup(self):
        """Cleanup resources and stop monitoring"""
        # Stop all health monitoring tasks
        for task in self._health_check_tasks.values():
            task.cancel()
        self._health_check_tasks.clear()

        # Stop Ollama process if we started it
        if self._ollama_process:
            try:
                self._ollama_process.terminate()
                self._ollama_process.wait(timeout=5)
            except Exception as e:
                self.logger.warning(f"Error stopping Ollama process: {e}")
            finally:
                self._ollama_process = None


# Global service manager instance
_service_manager = None


def get_service_manager() -> ServiceManager:
    """Get global service manager instance"""
    global _service_manager
    if _service_manager is None:
        _service_manager = ServiceManager()
    return _service_manager
