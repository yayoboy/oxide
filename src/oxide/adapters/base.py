"""
Base adapter interface for LLM services.

All adapters (CLI-based and HTTP-based) must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional, Dict, Any

from ..utils.logging import logger


class BaseAdapter(ABC):
    """
    Abstract base class for LLM service adapters.

    Adapters provide a uniform interface for interacting with different LLM services,
    whether they are CLI tools (Gemini, Qwen) or HTTP APIs (Ollama, LM Studio).
    """

    def __init__(self, service_name: str, config: Dict[str, Any]):
        """
        Initialize the adapter.

        Args:
            service_name: Name of the service (e.g., 'gemini', 'ollama_local')
            config: Service configuration dictionary
        """
        self.service_name = service_name
        self.config = config
        self.logger = logger.getChild(f"adapter.{service_name}")

    @abstractmethod
    async def execute(
        self,
        prompt: str,
        files: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Execute a task and stream results.

        Args:
            prompt: The task prompt/query
            files: Optional list of file paths to include as context
            **kwargs: Additional adapter-specific parameters

        Yields:
            str: Chunks of the response text as they become available

        Raises:
            AdapterError: If execution fails
            ServiceUnavailableError: If service is not reachable
            TimeoutError: If execution times out
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the service is available and healthy.

        Returns:
            bool: True if service is available, False otherwise
        """
        pass

    async def get_models(self) -> List[str]:
        """
        Get list of available models for this service.

        Returns:
            List of model names/identifiers

        Note:
            Optional method - adapters can override if they support model listing.
            Default implementation returns empty list.
        """
        return []

    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about this service.

        Returns:
            Dictionary with service metadata
        """
        return {
            "name": self.service_name,
            "type": self.config.get("type"),
            "enabled": self.config.get("enabled", True),
            "adapter_class": self.__class__.__name__,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(service='{self.service_name}')"
