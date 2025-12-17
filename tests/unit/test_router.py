"""
Unit tests for TaskRouter.
"""
import pytest
from unittest.mock import AsyncMock

from oxide.core.router import TaskRouter, RouterDecision
from oxide.core.classifier import TaskInfo, TaskType
from oxide.utils.exceptions import NoServiceAvailableError


class TestTaskRouter:
    """Test suite for TaskRouter."""

    @pytest.fixture
    def router(self, mock_config):
        """Create a TaskRouter instance."""
        return TaskRouter(mock_config)

    @pytest.fixture
    def router_with_health_checker(self, mock_config):
        """Create a TaskRouter with a mock health checker."""
        health_checker = AsyncMock(return_value=True)
        return TaskRouter(mock_config, service_health_checker=health_checker), health_checker

    @pytest.fixture
    def sample_task_info(self):
        """Create sample TaskInfo."""
        return TaskInfo(
            task_type=TaskType.CODE_REVIEW,
            file_count=5,
            total_size_bytes=50000,
            complexity_score=0.3,
            recommended_services=["qwen", "ollama_local"],
            use_parallel=False,
            estimated_latency="medium"
        )

    @pytest.mark.asyncio
    async def test_route_to_primary_service(self, router, sample_task_info):
        """Test routing to primary service."""
        decision = await router.route(sample_task_info)

        assert decision.primary_service == "qwen"
        assert "ollama_local" in decision.fallback_services
        assert decision.execution_mode == "single"
        assert decision.timeout_seconds == 120

    @pytest.mark.asyncio
    async def test_route_parallel_execution(self, router):
        """Test routing with parallel execution."""
        task_info = TaskInfo(
            task_type=TaskType.CODEBASE_ANALYSIS,
            file_count=30,
            total_size_bytes=500000,
            complexity_score=0.8,
            recommended_services=["gemini", "qwen"],
            use_parallel=True,
            estimated_latency="high"
        )

        decision = await router.route(task_info)

        assert decision.primary_service == "gemini"
        assert decision.execution_mode == "parallel"
        assert decision.timeout_seconds == 300

    @pytest.mark.asyncio
    async def test_route_quick_query(self, router):
        """Test routing of quick queries."""
        task_info = TaskInfo(
            task_type=TaskType.QUICK_QUERY,
            file_count=0,
            total_size_bytes=0,
            complexity_score=0.1,
            recommended_services=["ollama_local", "qwen"],
            use_parallel=False,
            estimated_latency="low"
        )

        decision = await router.route(task_info)

        assert decision.primary_service == "ollama_local"
        assert decision.timeout_seconds == 30

    @pytest.mark.asyncio
    async def test_fallback_when_primary_unhealthy(self, mock_config):
        """Test fallback to secondary service when primary is unhealthy."""
        # Mock health checker that marks primary as unhealthy
        async def health_checker(service_name: str) -> bool:
            return service_name != "qwen"  # qwen is unhealthy

        router = TaskRouter(mock_config, service_health_checker=health_checker)

        task_info = TaskInfo(
            task_type=TaskType.CODE_REVIEW,
            file_count=5,
            total_size_bytes=50000,
            complexity_score=0.3,
            recommended_services=["qwen", "ollama_local"],
            use_parallel=False,
            estimated_latency="medium"
        )

        decision = await router.route(task_info)

        # Should fallback to ollama_local
        assert decision.primary_service == "ollama_local"

    @pytest.mark.asyncio
    async def test_no_service_available_error(self, mock_config):
        """Test error when no service is available."""
        # Mock health checker that marks all services as unhealthy
        async def health_checker(service_name: str) -> bool:
            return False

        router = TaskRouter(mock_config, service_health_checker=health_checker)

        task_info = TaskInfo(
            task_type=TaskType.CODE_REVIEW,
            file_count=5,
            total_size_bytes=50000,
            complexity_score=0.3,
            recommended_services=["qwen", "ollama_local"],
            use_parallel=False,
            estimated_latency="medium"
        )

        with pytest.raises(NoServiceAvailableError):
            await router.route(task_info)

    @pytest.mark.asyncio
    async def test_route_from_recommendations_no_rule(self, mock_config):
        """Test routing when no explicit rule exists."""
        router = TaskRouter(mock_config)

        # Task type not in routing rules
        task_info = TaskInfo(
            task_type=TaskType.DEBUGGING,  # Not in default rules
            file_count=3,
            total_size_bytes=10000,
            complexity_score=0.2,
            recommended_services=["qwen", "ollama_local"],
            use_parallel=False,
            estimated_latency="medium"
        )

        decision = await router.route(task_info)

        # Should use recommendations
        assert decision.primary_service in ["qwen", "ollama_local"]

    @pytest.mark.asyncio
    async def test_is_service_available_disabled(self, router):
        """Test that disabled services are marked as unavailable."""
        is_available = await router._is_service_available("disabled_service")

        assert is_available is False

    @pytest.mark.asyncio
    async def test_is_service_available_unknown(self, router):
        """Test that unknown services are marked as unavailable."""
        is_available = await router._is_service_available("unknown_service")

        assert is_available is False

    @pytest.mark.asyncio
    async def test_is_service_available_enabled(self, router):
        """Test that enabled services without health checker are available."""
        is_available = await router._is_service_available("gemini")

        assert is_available is True

    @pytest.mark.asyncio
    async def test_select_available_service(self, router_with_health_checker):
        """Test selection of available service."""
        router, health_checker = router_with_health_checker

        service = await router._select_available_service("gemini", ["qwen", "ollama_local"])

        assert service == "gemini"
        health_checker.assert_called()

    @pytest.mark.asyncio
    async def test_select_available_service_fallback(self, mock_config):
        """Test fallback selection when primary is unavailable."""
        # Primary fails, first fallback succeeds
        async def health_checker(service_name: str) -> bool:
            return service_name != "gemini"

        router = TaskRouter(mock_config, service_health_checker=health_checker)

        service = await router._select_available_service("gemini", ["qwen", "ollama_local"])

        assert service == "qwen"

    def test_get_routing_rules_summary(self, router):
        """Test getting routing rules summary."""
        summary = router.get_routing_rules_summary()

        assert "codebase_analysis" in summary
        assert summary["codebase_analysis"]["primary"] == "gemini"
        assert "qwen" in summary["codebase_analysis"]["fallback"]
        assert summary["code_review"]["timeout"] == 120

    @pytest.mark.asyncio
    async def test_timeout_override(self, router):
        """Test that rule-specific timeout overrides default."""
        task_info = TaskInfo(
            task_type=TaskType.CODEBASE_ANALYSIS,
            file_count=30,
            total_size_bytes=500000,
            complexity_score=0.8,
            recommended_services=["gemini", "qwen"],
            use_parallel=True,
            estimated_latency="high"
        )

        decision = await router.route(task_info)

        # Should use rule-specific timeout (300) not default (120)
        assert decision.timeout_seconds == 300
