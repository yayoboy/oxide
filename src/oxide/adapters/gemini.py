"""
Gemini CLI adapter.
"""
from .cli_adapter import CLIAdapter


class GeminiAdapter(CLIAdapter):
    """
    Adapter for Gemini CLI tool.

    Gemini is optimized for large context windows and multi-file analysis.
    Ideal for codebase analysis and architectural understanding.
    """

    def __init__(self, config: dict):
        super().__init__("gemini", config)
        self.logger.info("Initialized Gemini adapter")

    def get_service_info(self) -> dict:
        info = super().get_service_info()
        info.update({
            "description": "Google Gemini - Large context window (2M+ tokens)",
            "max_context_tokens": 2000000,
            "optimal_for": [
                "codebase_analysis",
                "architecture_design",
                "multi_file_context"
            ]
        })
        return info
