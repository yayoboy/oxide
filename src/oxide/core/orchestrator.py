"""
Core orchestration system for Oxide.

Coordinates task classification, routing, and execution across LLM services.
"""
from typing import AsyncIterator, List, Optional, Dict, Any
import time
import hashlib

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
from ..utils.task_storage import get_task_storage
from ..memory.context_memory import get_context_memory
from ..analytics import get_cost_tracker
from .classifier import TaskClassifier, TaskInfo
from .router import TaskRouter, RouterDecision
from ..execution.parallel import ParallelExecutor


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

        # Initialize parallel executor
        max_workers = getattr(self.config.execution, "max_parallel_workers", 3)
        self.parallel_executor = ParallelExecutor(max_workers=max_workers)
        self.logger.info(f"Parallel executor initialized with {max_workers} workers")

        # Initialize task storage
        self.task_storage = get_task_storage()
        self.logger.info("Task storage initialized")

        # Initialize context memory
        self.memory = get_context_memory()
        self.logger.info("Context memory initialized")

        # Initialize cost tracker
        self.cost_tracker = get_cost_tracker()
        self.logger.info("Cost tracker initialized")

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

            except Exception as e:
                self.logger.error(f"Failed to initialize adapter '{service_name}': {e}")

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
            preferences: Optional routing preferences:
                - preferred_service: Force specific service (e.g., "ollama_remote")
                - task_type: Override task classification (e.g., "code_generation")
                - timeout: Override timeout in seconds
                - conversation_id: Optional conversation ID for context continuity
                - use_memory: Enable/disable memory (default: True)

        Yields:
            Response chunks as they become available

        Raises:
            NoServiceAvailableError: If no service can handle the task
            ExecutionError: If task execution fails
        """
        self.logger.info(f"Executing task with {len(files) if files else 0} files")
        preferences = preferences or {}

        # Generate conversation ID for memory tracking
        conversation_id = preferences.get("conversation_id") or self._generate_conversation_id(prompt)
        use_memory = preferences.get("use_memory", True)

        # Generate unique task ID
        task_id = preferences.get("task_id") or f"task_{int(time.time() * 1000)}"

        # Create initial task record in storage
        self.task_storage.add_task(
            task_id=task_id,
            prompt=prompt,
            files=files,
            preferences=preferences
        )

        try:
            # Mark task as running
            self.task_storage.update_task(task_id, status="running")
            # Store user prompt in memory
            if use_memory:
                self.memory.add_context(
                    conversation_id=conversation_id,
                    role="user",
                    content=prompt,
                    metadata={
                        "files": files,
                        "preferences": {k: v for k, v in preferences.items() if k not in ["conversation_id", "use_memory"]}
                    }
                )

            # Check for preference overrides
            preferred_service = preferences.get("preferred_service")
            timeout_override = preferences.get("timeout")

            # 1. Classify task (always needed for TaskInfo)
            task_info = self.classifier.classify(prompt, files)

            # Update task with classification
            self.task_storage.update_task(
                task_id,
                task_type=task_info.task_type.value
            )

            # Retrieve relevant context from memory and enhance prompt
            enhanced_prompt = prompt
            if use_memory:
                relevant_context = self.memory.get_context_for_task(
                    task_type=task_info.task_type.value,
                    prompt=prompt,
                    max_messages=5,
                    max_age_hours=24
                )
                if relevant_context:
                    self.logger.debug(f"Retrieved {len(relevant_context)} relevant context messages")

                    # Format context for injection into prompt
                    context_str = self._format_context_for_prompt(relevant_context)
                    enhanced_prompt = f"{context_str}\n\n{prompt}"
                    self.logger.info(f"Enhanced prompt with {len(relevant_context)} context messages")

            if preferred_service:
                # Direct routing to preferred service
                self.logger.info(f"Using preferred service: {preferred_service}")

                # Verify service exists and is available
                if preferred_service not in self.adapters:
                    raise NoServiceAvailableError(f"Service '{preferred_service}' not found")

                if not await self._check_service_health(preferred_service):
                    self.logger.warning(f"Preferred service '{preferred_service}' is unhealthy, but attempting anyway")

                # Create decision for preferred service
                decision = RouterDecision(
                    primary_service=preferred_service,
                    fallback_services=[],
                    execution_mode="single",
                    timeout_seconds=timeout_override or self.config.execution.timeout_seconds
                )

                # Update task with preferred service
                self.task_storage.update_task(
                    task_id,
                    service=preferred_service
                )
            else:
                # Allow task_type override
                if "task_type" in preferences:
                    from .classifier import TaskType
                    task_info.task_type = TaskType(preferences["task_type"])
                    self.logger.info(f"Task type overridden to: {task_info.task_type}")

                # 2. Route to service
                decision = await self.router.route(task_info)

                # Apply timeout override if provided
                if timeout_override:
                    decision.timeout_seconds = timeout_override

                # Update task with routing decision
                self.task_storage.update_task(
                    task_id,
                    service=decision.primary_service
                )

            # 3. Execute based on execution mode
            response_chunks = []

            if decision.execution_mode == "parallel" and files and len(files) > 1:
                # Use parallel execution for large file sets
                self.logger.info(
                    f"Using parallel execution: {len(files)} files across "
                    f"{len([decision.primary_service] + decision.fallback_services)} services"
                )

                # Get available services (primary + fallbacks)
                services = [decision.primary_service] + decision.fallback_services

                # Execute in parallel
                parallel_result = await self.parallel_executor.execute_parallel(
                    prompt=enhanced_prompt,
                    files=files,
                    services=services,
                    adapters=self.adapters,
                    strategy="split"  # Split files among services
                )

                # Yield the aggregated result
                yield parallel_result.aggregated_text
                response_chunks.append(parallel_result.aggregated_text)

            else:
                # Use standard serial execution with retries
                async for chunk in self._execute_with_retry(
                    decision,
                    enhanced_prompt,
                    files,
                    task_info
                ):
                    response_chunks.append(chunk)
                    yield chunk

            # Store assistant response in memory and track cost
            response = "".join(response_chunks)

            if use_memory:
                self.memory.add_context(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response,
                    metadata={
                        "service": decision.primary_service,
                        "task_type": task_info.task_type.value,
                        "execution_time": time.time()
                    }
                )

            # Track cost (uses estimates for token counts)
            try:
                self.cost_tracker.record_cost(
                    task_id=conversation_id,
                    service=decision.primary_service,
                    prompt=prompt,
                    response=response
                )
            except Exception as e:
                self.logger.warning(f"Failed to record cost: {e}")

            # Mark task as completed with result
            self.task_storage.update_task(
                task_id,
                status="completed",
                result=response[:500] + "..." if len(response) > 500 else response  # Store truncated result
            )

            self.logger.info(f"Task {task_id} completed successfully on {decision.primary_service}")

        except NoServiceAvailableError as e:
            self.logger.error(f"No service available: {e}")
            # Mark task as failed
            self.task_storage.update_task(
                task_id,
                status="failed",
                error=str(e)
            )
            raise

        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            # Mark task as failed
            self.task_storage.update_task(
                task_id,
                status="failed",
                error=str(e)
            )
            raise ExecutionError(f"Failed to execute task: {e}")

    def _format_context_for_prompt(self, context_messages: List[Dict[str, Any]]) -> str:
        """
        Format context messages for injection into prompt.

        Args:
            context_messages: List of context messages from memory

        Returns:
            Formatted context string
        """
        if not context_messages:
            return ""

        context_parts = ["Previous relevant conversation history:"]

        for msg in context_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Format role name
            role_display = {
                "user": "User",
                "assistant": "Assistant",
                "system": "System"
            }.get(role, role.capitalize())

            context_parts.append(f"\n{role_display}: {content}")

        context_parts.append("\n---\nCurrent task:")

        return "\n".join(context_parts)

    def _generate_conversation_id(self, prompt: str) -> str:
        """
        Generate a unique conversation ID based on prompt and timestamp.

        Args:
            prompt: Task prompt

        Returns:
            Conversation ID string
        """
        # Create hash from prompt + timestamp (truncated to hour for grouping similar tasks)
        timestamp_hour = int(time.time() / 3600) * 3600
        hash_input = f"{prompt[:100]}_{timestamp_hour}".encode()
        conv_hash = hashlib.md5(hash_input).hexdigest()[:12]
        return f"conv_{conv_hash}"

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
        except Exception as e:
            self.logger.debug(f"Health check failed for {service_name}: {e}")
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

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
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
