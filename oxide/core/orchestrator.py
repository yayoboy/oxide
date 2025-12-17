"""
Core orchestration system for Oxide.

Coordinates task classification, routing, and execution across LLM services.
"""
from typing import AsyncIterator, List, Optional, Dict, Any

from ..adapters.base import BaseAdapter
from ..adapters.gemini import GeminiAdapter
from ..adapters.qwen import QwenAdapter
from ..adapters.ollama_http import OllamaHTTPAdapter
from ..config.loader import Config, load_config
from ..utils.exceptions import (
    BaseOxideError,
    NoServiceAvailableError,
    ServiceUnavailableError,
    ExecutionError
)
from ..utils.logging import logger, setup_logging
from .classifier import TaskClassifier, TaskInfo
from .router import TaskRouter, RouterDecision


class Orchestrator:
    """
    Main orchestration system for Oxide.

    Coordinates all components to execute tasks on appropriate LLM services.
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize orchestrator.

        Args:
            config: Optional Config object (loads default if not provided)
        """
        # Load configuration
        self.config = config or load_config()

        # Setup logging
        setup_logging(
            level=self.config.logging.level,
            log_file=self.config.logging.file,
            console=self.config.logging.console
        )

        self.logger = logger.getChild("orchestrator")
        self.logger.info("Initializing Oxide Orchestrator")

        # Initialize components
        self.classifier = TaskClassifier()
        self.router = TaskRouter(self.config, service_health_checker=self._check_service_health)

        # Initialize adapters registry
        self.adapters: Dict[str, BaseAdapter] = {}
        self._initialize_adapters()

        self.logger.info(f"Initialized with {len(self.adapters)} adapters")

    def _initialize_adapters(self):
        """Initialize adapters for all configured services."""
        for service_name, service_config in self.config.services.items():
            if not service_config.enabled:
                self.logger.debug(f"Skipping disabled service: {service_name}")
                continue

            try:
                adapter = self._create_adapter(service_name, service_config.model_dump())
                self.adapters[service_name] = adapter
                self.logger.info(f"Initialized adapter: {service_name}")

            except (ValueError, ImportError, AttributeError) as e:
                # Expected errors during adapter initialization
                self.logger.error(f"Failed to initialize adapter '{service_name}': {e}")
            except Exception as e:
                # Unexpected error - log with more detail for debugging
                self.logger.exception(f"Unexpected error initializing adapter '{service_name}': {e}")

    def _create_adapter(self, service_name: str, config: Dict[str, Any]) -> BaseAdapter:
        """
        Create appropriate adapter based on service configuration.

        Args:
            service_name: Name of service
            config: Service configuration

        Returns:
            Initialized adapter instance

        Raises:
            ValueError: If service type is unknown
        """
        service_type = config.get("type")

        if service_type == "cli":
            # Determine which CLI adapter to use
            if "gemini" in service_name.lower():
                return GeminiAdapter(config)
            elif "qwen" in service_name.lower():
                return QwenAdapter(config)
            else:
                # Generic CLI adapter (you could make this more flexible)
                raise ValueError(f"Unknown CLI service: {service_name}")

        elif service_type == "http":
            return OllamaHTTPAdapter(service_name, config)

        else:
            raise ValueError(f"Unknown service type: {service_type}")

    async def execute_task(
        self,
        prompt: str,
        files: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Execute a task with intelligent routing.

        Args:
            prompt: Task prompt/query
            files: Optional list of file paths
            preferences: Optional routing preferences (e.g., prefer_local=True)

        Yields:
            Response chunks as they become available

        Raises:
            NoServiceAvailableError: If no service can handle the task
            ExecutionError: If task execution fails
        """
        self.logger.info(f"Executing task with {len(files) if files else 0} files")

        try:
            # 1. Classify task
            task_info = self.classifier.classify(prompt, files)

            # 2. Route to service
            decision = await self.router.route(task_info)

            # 3. Execute with retries
            async for chunk in self._execute_with_retry(
                decision,
                prompt,
                files,
                task_info
            ):
                yield chunk

            self.logger.info(f"Task completed successfully on {decision.primary_service}")

        except NoServiceAvailableError:
            # No service available - re-raise as-is
            self.logger.error("No service available for task")
            raise

        except (ServiceUnavailableError, ExecutionError) as e:
            # Service or execution errors - re-raise as ExecutionError
            self.logger.error(f"Task execution failed: {e}")
            raise ExecutionError(f"Failed to execute task: {e}") from e

        except Exception as e:
            # Unexpected error - log with full traceback and wrap
            self.logger.exception(f"Unexpected error during task execution: {e}")
            raise ExecutionError(f"Unexpected failure executing task: {e}") from e

    async def _execute_with_retry(
        self,
        decision: RouterDecision,
        prompt: str,
        files: Optional[List[str]],
        task_info: TaskInfo
    ) -> AsyncIterator[str]:
        """
        Execute task with retry and fallback logic.

        Args:
            decision: Routing decision
            prompt: Task prompt
            files: Optional file paths
            task_info: Task classification info

        Yields:
            Response chunks
        """
        services_to_try = [decision.primary_service] + decision.fallback_services
        max_retries = self.config.execution.max_retries if self.config.execution.retry_on_failure else 1

        last_error = None

        for service_name in services_to_try:
            for attempt in range(max_retries):
                try:
                    self.logger.debug(
                        f"Attempting {service_name} (attempt {attempt + 1}/{max_retries})"
                    )

                    adapter = self.adapters.get(service_name)
                    if not adapter:
                        self.logger.warning(f"Adapter not found: {service_name}")
                        continue

                    # Execute
                    async for chunk in adapter.execute(
                        prompt=prompt,
                        files=files,
                        timeout=decision.timeout_seconds
                    ):
                        yield chunk

                    # Success - return
                    return

                except ServiceUnavailableError as e:
                    self.logger.warning(f"Service unavailable: {e}")
                    last_error = e
                    # Don't retry on unavailable service, try next service
                    break

                except Exception as e:
                    self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    last_error = e

                    # If max retries reached, try next service
                    if attempt >= max_retries - 1:
                        break

                    # Otherwise retry

        # All services and retries exhausted
        if last_error:
            raise ExecutionError(f"All services failed. Last error: {last_error}")
        else:
            raise NoServiceAvailableError(task_info.task_type.value)

    async def _check_service_health(self, service_name: str) -> bool:
        """
        Check health of a specific service.

        Args:
            service_name: Name of service to check

        Returns:
            True if service is healthy
        """
        adapter = self.adapters.get(service_name)
        if not adapter:
            return False

        try:
            return await adapter.health_check()
        except (ServiceUnavailableError, TimeoutError, ConnectionError) as e:
            # Expected health check failures
            self.logger.debug(f"Health check failed for {service_name}: {e}")
            return False
        except Exception as e:
            # Unexpected error during health check
            self.logger.warning(f"Unexpected error in health check for {service_name}: {e}")
            return False

    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get status of all services.

        Returns:
            Dictionary with service status information
        """
        status = {}

        for service_name, adapter in self.adapters.items():
            is_healthy = await self._check_service_health(service_name)

            status[service_name] = {
                "enabled": True,  # Only enabled adapters are initialized
                "healthy": is_healthy,
                "info": adapter.get_service_info()
            }

        return status

    async def test_service(self, service_name: str, test_prompt: str = "Hello") -> Dict[str, Any]:
        """
        Test a specific service with a simple prompt.

        Args:
            service_name: Name of service to test
            test_prompt: Test prompt to send

        Returns:
            Test results dictionary
        """
        adapter = self.adapters.get(service_name)
        if not adapter:
            return {
                "success": False,
                "error": f"Service '{service_name}' not found"
            }

        try:
            # Try health check first
            is_healthy = await adapter.health_check()
            if not is_healthy:
                return {
                    "success": False,
                    "error": "Service failed health check"
                }

            # Try simple execution
            response_chunks = []
            async for chunk in adapter.execute(test_prompt, timeout=10):
                response_chunks.append(chunk)

            response = "".join(response_chunks)

            return {
                "success": True,
                "response": response[:200],  # First 200 chars
                "response_length": len(response)
            }

        except (ServiceUnavailableError, TimeoutError, ExecutionError) as e:
            # Expected service test failures
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            # Unexpected error during test
            self.logger.warning(f"Unexpected error testing {service_name}: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    def get_adapters_info(self) -> Dict[str, Any]:
        """Get information about all initialized adapters."""
        return {
            name: adapter.get_service_info()
            for name, adapter in self.adapters.items()
        }

    def get_routing_rules(self) -> Dict[str, Any]:
        """Get summary of routing rules."""
        return self.router.get_routing_rules_summary()
