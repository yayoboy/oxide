"""
Custom exceptions for Oxide orchestrator.
"""


class BaseOxideError(Exception):
    """Base exception for all Oxide errors."""
    pass


class ConfigError(BaseOxideError):
    """Configuration-related errors."""
    pass


class AdapterError(BaseOxideError):
    """Base exception for adapter errors."""
    pass


class CLIAdapterError(AdapterError):
    """Errors from CLI-based adapters (Gemini, Qwen)."""
    pass


class HTTPAdapterError(AdapterError):
    """Errors from HTTP-based adapters (Ollama, LM Studio)."""
    pass


class ServiceUnavailableError(AdapterError):
    """Service is not available or unreachable."""

    def __init__(self, service_name: str, reason: str = ""):
        self.service_name = service_name
        self.reason = reason
        message = f"Service '{service_name}' is unavailable"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class RoutingError(BaseOxideError):
    """Base exception for routing errors."""
    pass


class NoServiceAvailableError(RoutingError):
    """No service is available to handle the task."""

    def __init__(self, task_type: str):
        self.task_type = task_type
        super().__init__(f"No service available to handle task type: {task_type}")


class ClassificationError(RoutingError):
    """Error during task classification."""
    pass


class ExecutionError(BaseOxideError):
    """Error during task execution."""
    pass


class TimeoutError(ExecutionError):
    """Task execution timed out."""

    def __init__(self, service_name: str, timeout_seconds: int):
        self.service_name = service_name
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Task execution on '{service_name}' timed out after {timeout_seconds}s"
        )
