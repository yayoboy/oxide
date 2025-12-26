"""
Shared pytest fixtures and configuration for Oxide tests.

This module provides common fixtures used across all test suites including:
- Mock configuration objects
- Mock adapters and services
- Temporary file systems
- Mock HTTP sessions
- FastAPI test clients
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, AsyncIterator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

# Configuration Fixtures


@pytest.fixture
def mock_config_dict() -> Dict[str, Any]:
    """Provide a complete mock configuration dictionary."""
    return {
        "logging": {
            "level": "INFO",
            "file": None,
            "console": True
        },
        "execution": {
            "timeout_seconds": 120,
            "max_retries": 2,
            "retry_on_failure": True
        },
        "services": {
            "gemini": {
                "type": "cli",
                "executable": "gemini",
                "enabled": True
            },
            "qwen": {
                "type": "cli",
                "executable": "qwen",
                "enabled": True
            },
            "ollama_local": {
                "type": "http",
                "base_url": "http://localhost:11434",
                "api_type": "ollama",
                "default_model": "qwen2.5-coder:7b",
                "enabled": True,
                "auto_start": True,
                "auto_detect_model": True,
                "preferred_models": ["qwen2.5-coder", "codellama"]
            },
            "ollama_remote": {
                "type": "http",
                "base_url": "http://remote.example.com:11434",
                "api_type": "ollama",
                "default_model": "llama3",
                "enabled": False
            }
        },
        "routing_rules": {
            "codebase_analysis": {
                "primary": "gemini",
                "fallback": ["qwen"],
                "parallel_threshold_files": 20,
                "timeout_seconds": 300
            },
            "code_review": {
                "primary": "qwen",
                "fallback": ["ollama_local"],
                "parallel_threshold_files": None,
                "timeout_seconds": 120
            },
            "quick_query": {
                "primary": "ollama_local",
                "fallback": ["ollama_remote", "qwen"],
                "parallel_threshold_files": None,
                "timeout_seconds": 30
            }
        }
    }


@pytest.fixture
def mock_config(mock_config_dict):
    """Provide a mock Config object."""
    from oxide.config.loader import Config, ServiceConfig, RoutingRuleConfig, LoggingConfig, ExecutionConfig

    # Create config objects from dict
    logging_config = LoggingConfig(**mock_config_dict["logging"])
    execution_config = ExecutionConfig(**mock_config_dict["execution"])

    services = {
        name: ServiceConfig(**svc_data)
        for name, svc_data in mock_config_dict["services"].items()
    }

    routing_rules = {
        name: RoutingRuleConfig(**rule_data)
        for name, rule_data in mock_config_dict["routing_rules"].items()
    }

    return Config(
        logging=logging_config,
        execution=execution_config,
        services=services,
        routing_rules=routing_rules
    )


# Task and Classification Fixtures


@pytest.fixture
def sample_prompts() -> Dict[str, str]:
    """Provide sample prompts for different task types."""
    return {
        "quick_query": "What is 2 + 2?",
        "code_review": "Review this code for potential bugs and improvements",
        "code_generation": "Write a Python function to sort a list",
        "debugging": "Fix the bug in this function that causes infinite loop",
        "refactoring": "Refactor this code to improve readability",
        "documentation": "Document this API endpoint with examples",
        "architecture": "Design a microservices architecture for an e-commerce platform",
        "codebase_analysis": "Analyze this entire codebase and provide architectural insights"
    }


@pytest.fixture
def sample_task_files(tmp_path: Path) -> List[str]:
    """Create sample files for testing."""
    files = []

    # Create a few sample code files
    for i in range(3):
        file_path = tmp_path / f"sample_{i}.py"
        file_path.write_text(f"""
def function_{i}():
    '''Sample function {i}'''
    return {i} * 2
""")
        files.append(str(file_path))

    return files


@pytest.fixture
def large_file_set(tmp_path: Path) -> List[str]:
    """Create a large set of files for codebase analysis tests."""
    files = []

    # Create 25 files to trigger large codebase detection
    for i in range(25):
        file_path = tmp_path / f"module_{i}.py"
        content = f"# Module {i}\n" + ("def func(): pass\n" * 50)
        file_path.write_text(content)
        files.append(str(file_path))

    return files


# Adapter Fixtures


@pytest.fixture
def mock_base_adapter():
    """Provide a mock BaseAdapter."""
    from oxide.adapters.base import BaseAdapter

    adapter = MagicMock(spec=BaseAdapter)
    adapter.service_name = "mock_adapter"
    adapter.config = {"type": "mock", "enabled": True}

    # Mock async methods
    async def mock_execute(prompt, files=None, **kwargs):
        yield "Mock response"

    async def mock_health_check():
        return True

    async def mock_get_models():
        return ["mock-model-1", "mock-model-2"]

    adapter.execute = mock_execute
    adapter.health_check = mock_health_check
    adapter.get_models = mock_get_models
    adapter.get_service_info = MagicMock(return_value={
        "name": "mock_adapter",
        "type": "mock",
        "enabled": True
    })

    return adapter


@pytest.fixture
def mock_subprocess_process():
    """Provide a mock subprocess process for CLI adapter tests."""
    process = AsyncMock()
    process.pid = 12345
    process.returncode = 0

    # Mock stdout
    stdout = AsyncMock()
    stdout.readline = AsyncMock(side_effect=[b"Test output\n", b""])
    process.stdout = stdout

    # Mock stderr
    stderr = AsyncMock()
    process.stderr = stderr

    async def mock_wait():
        return 0

    process.wait = mock_wait

    return process


@pytest.fixture
def mock_aiohttp_response():
    """Provide a mock aiohttp response."""
    response = AsyncMock()
    response.status = 200

    async def mock_json():
        return {"models": [{"name": "test-model"}]}

    async def mock_text():
        return "Mock response text"

    response.json = mock_json
    response.text = mock_text

    return response


# Service Manager Fixtures


@pytest.fixture
def mock_service_manager():
    """Provide a mock ServiceManager."""
    from oxide.utils.service_manager import ServiceManager

    manager = MagicMock(spec=ServiceManager)

    async def mock_ensure_ollama_running(base_url="http://localhost:11434", **kwargs):
        return True

    async def mock_get_available_models(base_url, api_type="ollama"):
        return ["qwen2.5-coder:7b", "codellama:7b"]

    async def mock_auto_detect_model(base_url, api_type="ollama", preferred_models=None):
        return "qwen2.5-coder:7b"

    async def mock_ensure_service_healthy(service_name, base_url, **kwargs):
        return {
            "service": service_name,
            "healthy": True,
            "models": ["qwen2.5-coder:7b"],
            "recommended_model": "qwen2.5-coder:7b"
        }

    manager.ensure_ollama_running = mock_ensure_ollama_running
    manager.get_available_models = mock_get_available_models
    manager.auto_detect_model = mock_auto_detect_model
    manager.ensure_service_healthy = mock_ensure_service_healthy

    return manager


# Task Storage Fixtures


@pytest.fixture
def temp_task_storage(tmp_path: Path):
    """Provide an isolated TaskStorage instance for testing."""
    from oxide.utils.task_storage import TaskStorage

    storage_file = tmp_path / "test_tasks.json"
    return TaskStorage(storage_path=storage_file)


@pytest.fixture
def populated_task_storage(temp_task_storage):
    """Provide a TaskStorage with sample tasks."""
    storage = temp_task_storage

    # Add various tasks
    storage.add_task(
        task_id="task-1",
        prompt="Test prompt 1",
        files=[],
        service="qwen",
        task_type="quick_query"
    )
    storage.update_task("task-1", status="completed", result="Test result 1")

    storage.add_task(
        task_id="task-2",
        prompt="Test prompt 2",
        files=["file1.py"],
        service="gemini",
        task_type="code_review"
    )
    storage.update_task("task-2", status="running")

    storage.add_task(
        task_id="task-3",
        prompt="Test prompt 3",
        files=[],
        service="ollama_local",
        task_type="code_generation"
    )
    storage.update_task("task-3", status="failed", error="Service unavailable")

    return storage


# Orchestrator Fixtures


@pytest.fixture
def mock_orchestrator(mock_config, mock_base_adapter):
    """Provide a mock Orchestrator."""
    from oxide.core.orchestrator import Orchestrator

    with patch('oxide.core.orchestrator.TaskClassifier'), \
         patch('oxide.core.orchestrator.TaskRouter'), \
         patch('oxide.core.orchestrator.get_context_memory'), \
         patch('oxide.core.orchestrator.get_cost_tracker'):

        orchestrator = Orchestrator(mock_config)

        # Replace adapters with mocks
        orchestrator.adapters = {
            "mock_adapter": mock_base_adapter
        }

        return orchestrator


# FastAPI Test Client Fixtures


@pytest.fixture
def api_client(mock_orchestrator, temp_task_storage):
    """Provide FastAPI TestClient with mocked dependencies."""
    from oxide.web.backend.main import app, set_orchestrator

    # Inject mocked orchestrator
    set_orchestrator(mock_orchestrator)

    # Create test client
    client = TestClient(app)

    return client


# Memory and Analytics Fixtures


@pytest.fixture
def mock_context_memory():
    """Provide a mock ContextMemory."""
    from oxide.memory.context_memory import ContextMemory

    memory = MagicMock(spec=ContextMemory)

    memory.add_context = MagicMock(return_value=None)
    memory.get_context_for_task = MagicMock(return_value=[])
    memory.clear_conversation = MagicMock(return_value=None)

    return memory


@pytest.fixture
def mock_cost_tracker():
    """Provide a mock CostTracker."""
    from oxide.analytics.cost_tracker import CostTracker

    tracker = MagicMock(spec=CostTracker)

    tracker.record_cost = MagicMock(return_value=None)
    tracker.get_total_cost = MagicMock(return_value=0.0)
    tracker.get_cost_by_service = MagicMock(return_value={})

    return tracker


# Utility Fixtures


@pytest.fixture
def mock_logger():
    """Provide a mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset task storage singleton
    import oxide.utils.task_storage as task_storage_module
    task_storage_module._task_storage = None

    # Reset service manager singleton
    import oxide.utils.service_manager as service_manager_module
    service_manager_module._service_manager = None

    # Reset cost tracker singleton
    try:
        import oxide.analytics.cost_tracker as cost_tracker_module
        cost_tracker_module._cost_tracker = None
    except AttributeError:
        pass

    # Reset context memory singleton
    try:
        import oxide.memory.context_memory as context_memory_module
        context_memory_module._context_memory = None
    except AttributeError:
        pass

    yield


# Platform-specific Fixtures


@pytest.fixture
def mock_platform(monkeypatch):
    """Mock platform.system() for platform-specific tests."""
    def _mock_platform(system_name: str):
        monkeypatch.setattr('platform.system', lambda: system_name)

    return _mock_platform


# Async Helper Fixtures


@pytest.fixture
def event_loop():
    """Provide a fresh event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# HTTP Mocking Fixtures (for integration tests)


@pytest.fixture
def mock_ollama_api(respx_mock):
    """Mock Ollama API endpoints."""
    # Mock health check
    respx_mock.get("http://localhost:11434/api/tags").mock(
        return_value={"models": [{"name": "qwen2.5-coder:7b"}]}
    )

    # Mock generate endpoint
    respx_mock.post("http://localhost:11434/api/generate").mock(
        return_value={"response": "Mock response", "done": True}
    )

    return respx_mock


# File System Fixtures


@pytest.fixture
def mock_file_system(fs):
    """Provide a fake filesystem using pyfakefs."""
    # Create some standard directories
    fs.create_dir("/tmp")
    fs.create_dir("/home/user/.oxide")

    return fs


# Test Data Fixtures


@pytest.fixture
def sample_config_yaml(tmp_path: Path) -> Path:
    """Create a sample config YAML file."""
    config_file = tmp_path / "config.yaml"
    config_content = """
logging:
  level: INFO
  console: true

execution:
  timeout_seconds: 120
  max_retries: 2

services:
  gemini:
    type: cli
    executable: gemini
    enabled: true

routing_rules:
  quick_query:
    primary: ollama_local
    fallback: []
"""
    config_file.write_text(config_content)
    return config_file


# WebSocket Fixtures


@pytest.fixture
def mock_websocket_manager():
    """Provide a mock WebSocketManager."""
    manager = MagicMock()

    async def mock_broadcast(*args, **kwargs):
        pass

    manager.broadcast_task_start = mock_broadcast
    manager.broadcast_task_progress = mock_broadcast
    manager.broadcast_task_complete = mock_broadcast

    return manager
