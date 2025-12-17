"""
Unit tests for Orchestrator.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from oxide.core.orchestrator import Orchestrator
from oxide.core.classifier import TaskType
from oxide.utils.exceptions import (
    NoServiceAvailableError,
    ServiceUnavailableError,
    ExecutionError
)
from oxide.config.loader import Config, ServiceConfig, RoutingRuleConfig, ExecutionConfig


class TestOrchestrator:
    """Test suite for Orchestrator."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return Config(
            services={
                "gemini": ServiceConfig(
                    type="cli",
                    enabled=True,
                    executable="gemini"
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
                max_retries=2,
                retry_on_failure=True,
                timeout_seconds=120
            )
        )

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create an Orchestrator instance with mocked adapters."""
        with patch('oxide.core.orchestrator.GeminiAdapter'), \
             patch('oxide.core.orchestrator.QwenAdapter'), \
             patch('oxide.core.orchestrator.OllamaHTTPAdapter'):

            orch = Orchestrator(config=mock_config)

            # Mock adapters
            for service_name in orch.adapters:
                adapter = orch.adapters[service_name]
                # Create async mock that returns async iterator
                adapter.execute = MagicMock()
                adapter.health_check = AsyncMock(return_value=True)
                adapter.get_service_info = MagicMock(return_value={
                    "name": service_name,
                    "type": "mock"
                })

            return orch

    def test_orchestrator_initialization(self, mock_config):
        """Test orchestrator initialization."""
        with patch('oxide.core.orchestrator.GeminiAdapter'), \
             patch('oxide.core.orchestrator.QwenAdapter'), \
             patch('oxide.core.orchestrator.OllamaHTTPAdapter'):

            orch = Orchestrator(config=mock_config)

            assert orch.config == mock_config
            assert orch.classifier is not None
            assert orch.router is not None
            assert len(orch.adapters) == 3

    def test_create_adapter_gemini(self, orchestrator):
        """Test creating Gemini adapter."""
        config = {"type": "cli", "executable": "gemini", "enabled": True}

        with patch('oxide.core.orchestrator.GeminiAdapter') as MockAdapter:
            adapter = orchestrator._create_adapter("gemini", config)
            MockAdapter.assert_called_once_with(config)

    def test_create_adapter_qwen(self, orchestrator):
        """Test creating Qwen adapter."""
        config = {"type": "cli", "executable": "qwen", "enabled": True}

        with patch('oxide.core.orchestrator.QwenAdapter') as MockAdapter:
            adapter = orchestrator._create_adapter("qwen", config)
            MockAdapter.assert_called_once_with(config)

    def test_create_adapter_ollama(self, orchestrator):
        """Test creating Ollama adapter."""
        config = {
            "type": "http",
            "base_url": "http://localhost:11434",
            "enabled": True
        }

        with patch('oxide.core.orchestrator.OllamaHTTPAdapter') as MockAdapter:
            adapter = orchestrator._create_adapter("ollama_local", config)
            MockAdapter.assert_called_once_with("ollama_local", config)

    def test_create_adapter_unknown_type(self, orchestrator):
        """Test creating adapter with unknown type raises error."""
        config = {"type": "unknown", "enabled": True}

        with pytest.raises(ValueError, match="Unknown service type"):
            orchestrator._create_adapter("test", config)

    def test_create_adapter_unknown_cli_service(self, orchestrator):
        """Test creating unknown CLI service raises error."""
        config = {"type": "cli", "executable": "unknown", "enabled": True}

        with pytest.raises(ValueError, match="Unknown CLI service"):
            orchestrator._create_adapter("unknown_cli", config)

    @pytest.mark.asyncio
    async def test_execute_task_success(self, orchestrator):
        """Test successful task execution."""
        # Mock adapter to return chunks
        mock_adapter = orchestrator.adapters["qwen"]

        async def mock_execute(*args, **kwargs):
            for chunk in ["Hello", " ", "World"]:
                yield chunk

        mock_adapter.execute = mock_execute

        chunks = []
        async for chunk in orchestrator.execute_task("Review this code", files=["test.py"]):
            chunks.append(chunk)

        assert chunks == ["Hello", " ", "World"]

    @pytest.mark.asyncio
    async def test_execute_task_with_fallback(self, orchestrator):
        """Test task execution with fallback when primary fails."""
        # Primary service fails
        async def primary_execute(*args, **kwargs):
            raise ServiceUnavailableError("qwen", "Service down")
            yield  # Make it a generator

        orchestrator.adapters["qwen"].execute = primary_execute

        # Fallback succeeds
        async def fallback_execute(*args, **kwargs):
            yield "Fallback response"

        orchestrator.adapters["ollama_local"].execute = fallback_execute

        chunks = []
        async for chunk in orchestrator.execute_task("Review code", files=["test.py"]):
            chunks.append(chunk)

        assert chunks == ["Fallback response"]

    @pytest.mark.asyncio
    async def test_execute_task_retry_logic(self, orchestrator):
        """Test retry logic on transient failures."""
        mock_adapter = orchestrator.adapters["qwen"]

        # Fail first attempt, succeed second
        call_count = 0
        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Transient error")
            else:
                for chunk in ["Success"]:
                    yield chunk

        mock_adapter.execute.side_effect = mock_execute

        chunks = []
        async for chunk in orchestrator.execute_task("Review code", files=["test.py"]):
            chunks.append(chunk)

        assert chunks == ["Success"]
        assert call_count == 2  # Retried once

    @pytest.mark.asyncio
    async def test_execute_task_all_services_fail(self, orchestrator):
        """Test that ExecutionError is raised when all services fail."""
        # All services fail
        async def failing_execute(*args, **kwargs):
            raise Exception("Service error")
            yield  # Make it a generator

        for adapter in orchestrator.adapters.values():
            adapter.execute = failing_execute

        with pytest.raises(ExecutionError, match="All services failed"):
            async for _ in orchestrator.execute_task("Test"):
                pass

    @pytest.mark.asyncio
    async def test_execute_task_no_service_available(self, orchestrator):
        """Test NoServiceAvailableError when no service can handle task."""
        # Make all adapters return None (not found)
        orchestrator.adapters.clear()

        with pytest.raises((NoServiceAvailableError, ExecutionError)):
            async for _ in orchestrator.execute_task("Test"):
                pass

    @pytest.mark.asyncio
    async def test_check_service_health_healthy(self, orchestrator):
        """Test health check for healthy service."""
        orchestrator.adapters["qwen"].health_check.return_value = True

        result = await orchestrator._check_service_health("qwen")

        assert result is True

    @pytest.mark.asyncio
    async def test_check_service_health_unhealthy(self, orchestrator):
        """Test health check for unhealthy service."""
        orchestrator.adapters["qwen"].health_check.return_value = False

        result = await orchestrator._check_service_health("qwen")

        assert result is False

    @pytest.mark.asyncio
    async def test_check_service_health_nonexistent(self, orchestrator):
        """Test health check for non-existent service."""
        result = await orchestrator._check_service_health("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_check_service_health_exception(self, orchestrator):
        """Test health check when adapter raises exception."""
        orchestrator.adapters["qwen"].health_check.side_effect = Exception("Health check error")

        result = await orchestrator._check_service_health("qwen")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_service_status(self, orchestrator):
        """Test getting service status for all services."""
        status = await orchestrator.get_service_status()

        assert "qwen" in status
        assert "gemini" in status
        assert "ollama_local" in status

        assert status["qwen"]["enabled"] is True
        assert status["qwen"]["healthy"] is True
        assert "info" in status["qwen"]

    @pytest.mark.asyncio
    async def test_test_service_success(self, orchestrator):
        """Test testing a service successfully."""
        orchestrator.adapters["qwen"].health_check = AsyncMock(return_value=True)

        async def mock_execute(*args, **kwargs):
            yield "Test response"

        orchestrator.adapters["qwen"].execute = mock_execute

        result = await orchestrator.test_service("qwen", "Hello")

        assert result["success"] is True
        assert "response" in result
        assert result["response_length"] > 0

    @pytest.mark.asyncio
    async def test_test_service_not_found(self, orchestrator):
        """Test testing a non-existent service."""
        result = await orchestrator.test_service("nonexistent", "Hello")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_test_service_unhealthy(self, orchestrator):
        """Test testing an unhealthy service."""
        orchestrator.adapters["qwen"].health_check.return_value = False

        result = await orchestrator.test_service("qwen", "Hello")

        assert result["success"] is False
        assert "health check" in result["error"]

    @pytest.mark.asyncio
    async def test_test_service_execution_error(self, orchestrator):
        """Test testing a service that fails during execution."""
        orchestrator.adapters["qwen"].health_check = AsyncMock(return_value=True)

        async def mock_execute(*args, **kwargs):
            raise Exception("Execution failed")
            yield  # Make it a generator

        orchestrator.adapters["qwen"].execute = mock_execute

        result = await orchestrator.test_service("qwen", "Hello")

        assert result["success"] is False
        assert "Execution failed" in result["error"]

    def test_get_adapters_info(self, orchestrator):
        """Test getting adapter information."""
        info = orchestrator.get_adapters_info()

        assert "qwen" in info
        assert "gemini" in info
        assert "ollama_local" in info

        assert info["qwen"]["name"] == "qwen"
        assert info["qwen"]["type"] == "mock"

    def test_get_routing_rules(self, orchestrator):
        """Test getting routing rules summary."""
        rules = orchestrator.get_routing_rules()

        assert "code_review" in rules
        assert rules["code_review"]["primary"] == "qwen"
        assert "ollama_local" in rules["code_review"]["fallback"]

    @pytest.mark.asyncio
    async def test_execute_with_retry_max_retries_exhausted(self, orchestrator):
        """Test that retries are exhausted correctly."""
        from oxide.core.router import RouterDecision
        from oxide.core.classifier import TaskInfo, TaskType

        decision = RouterDecision(
            primary_service="qwen",
            fallback_services=[],
            execution_mode="single",
            timeout_seconds=120
        )

        task_info = TaskInfo(
            task_type=TaskType.CODE_REVIEW,
            file_count=1,
            total_size_bytes=1000,
            complexity_score=0.3,
            recommended_services=["qwen"],
            use_parallel=False
        )

        # Fail all retry attempts
        async def failing_execute(*args, **kwargs):
            raise Exception("Persistent error")
            yield

        orchestrator.adapters["qwen"].execute = failing_execute

        with pytest.raises(ExecutionError, match="All services failed"):
            async for _ in orchestrator._execute_with_retry(
                decision, "test", None, task_info
            ):
                pass

    def test_initialize_adapters_skips_disabled(self, mock_config):
        """Test that disabled services are skipped during initialization."""
        mock_config.services["gemini"].enabled = False

        with patch('oxide.core.orchestrator.QwenAdapter'), \
             patch('oxide.core.orchestrator.OllamaHTTPAdapter'):

            orch = Orchestrator(config=mock_config)

            assert "gemini" not in orch.adapters
            assert "qwen" in orch.adapters
            assert "ollama_local" in orch.adapters

    # Helper method for async iteration
    @staticmethod
    async def _async_iter(items):
        """Helper to create async iterator from list."""
        for item in items:
            yield item
