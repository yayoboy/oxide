"""
Qwen CLI adapter.
"""
from .cli_adapter import CLIAdapter


class QwenAdapter(CLIAdapter):
    """
    Adapter for Qwen CLI tool.

    Qwen is code-specialized and optimized for code review,
    generation, and debugging tasks.
    """

    def __init__(self, config: dict):
        super().__init__("qwen", config)
        self.logger.info("Initialized Qwen adapter")

    def get_service_info(self) -> dict:
        info = super().get_service_info()
        info.update({
            "description": "Qwen Code - Specialized for code tasks",
            "max_context_tokens": 32000,
            "optimal_for": [
                "code_review",
                "code_generation",
                "debugging",
                "refactoring"
            ]
        })
        return info
