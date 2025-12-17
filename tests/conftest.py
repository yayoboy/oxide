"""
Pytest configuration and shared fixtures.
"""
import pytest
from pathlib import Path
from typing import Dict, Any

from oxide.config.loader import Config, ServiceConfig, RoutingRuleConfig, ExecutionConfig, LoggingConfig


@pytest.fixture
def mock_config() -> Config:
    """Create a mock configuration for testing."""
    return Config(
        services={
            "gemini": ServiceConfig(
                type="cli",
                enabled=True,
                executable="gemini",
                max_context_tokens=2000000
            ),
            "qwen": ServiceConfig(
                type="cli",
                enabled=True,
                executable="qwen"
            ),
            "ollama_local": ServiceConfig(
                type="http",
                enabled=True,
                base_url="http://localhost:11434",
                api_type="ollama",
                default_model="qwen2.5-coder:7b"
            )
        },
        routing_rules={
            "codebase_analysis": RoutingRuleConfig(
                primary="gemini",
                fallback=["qwen"],
                parallel_threshold_files=20,
                timeout_seconds=300
            ),
            "code_review": RoutingRuleConfig(
                primary="qwen",
                fallback=["ollama_local"],
                timeout_seconds=120
            ),
            "quick_query": RoutingRuleConfig(
                primary="ollama_local",
                fallback=["qwen"],
                timeout_seconds=30
            )
        },
        execution=ExecutionConfig(
            max_parallel_workers=3,
            timeout_seconds=120,
            streaming=True,
            retry_on_failure=True,
            max_retries=2
        ),
        logging=LoggingConfig(
            level="ERROR",  # Reduce noise in tests
            console=False
        )
    )


@pytest.fixture
def temp_test_files(tmp_path: Path) -> Dict[str, Path]:
    """Create temporary test files."""
    files = {}

    # Small Python file
    small_file = tmp_path / "small.py"
    small_file.write_text("def hello(): return 'world'")
    files["small"] = small_file

    # Medium Python file
    medium_file = tmp_path / "medium.py"
    medium_file.write_text("# " + "x" * 1000 + "\ndef test(): pass")
    files["medium"] = medium_file

    # Large file
    large_file = tmp_path / "large.py"
    large_file.write_text("# " + "x" * 100000)
    files["large"] = large_file

    return files


@pytest.fixture
def sample_prompts() -> Dict[str, str]:
    """Sample prompts for different task types."""
    return {
        "review": "Review this code for potential bugs and security issues",
        "generate": "Generate a new API endpoint for user authentication",
        "analyze": "Analyze this codebase and explain the architecture",
        "quick": "What is a closure?",
        "debug": "Debug this TypeError in the authentication module",
        "refactor": "Refactor this code to improve performance"
    }
