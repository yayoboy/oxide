"""
Unit tests for TaskRouter.

Tests routing logic, service selection, fallback mechanisms,
and health checking integration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from oxide.core.router import TaskRouter, RouterDecision
from oxide.core.classifier import TaskInfo, TaskType
from oxide.utils.exceptions import NoServiceAvailableError


class TestTaskRouter:
    """Test suite for TaskRouter"""

    @pytest.mark.asyncio
    async def test_init(self, mock_config):
        """Test router initialization"""
        router = TaskRouter(mock_config)

        assert router.config == mock_config
        assert router.routing_rules is not None
        assert router.service_health_checker is None

    @pytest.mark.asyncio
    async def test_init_with_health_checker(self, mock_config):
        """Test router initialization with health checker"""
        health_checker = AsyncMock()
        router = TaskRouter(mock_config, health_checker)

        assert router.service_health_checker == health_checker

    # Basic Routing Tests

    @pytest.mark.asyncio
    async def test_route_quick_query(self, mock_config):
        """Test routing for quick query task"""
        router = TaskRouter(mock_config)

        task_info = TaskInfo(
            task_type=TaskType.QUICK_QUERY,
            file_count=0,
            total_size_bytes=0,
            complexity_score=0.1,
            recommended_services=["ollama_local"],
            use_parallel=False,
            estimated_latency="low"
        )

        decision = await router.route(task_info)

        assert decision.primary_service == "ollama_local"
        assert "ollama_remote" in decision.fallback_services
        assert decision.execution_mode == "single"
        assert decision.timeout_seconds is not None

    @pytest.mark.asyncio
    async def test_route_code_review(self, mock_config):
        """Test routing for code review task"""
        router = TaskRouter(mock_config)

        task_info = TaskInfo(
            task_type=TaskType.CODE_REVIEW,
            file_count=3,
            total_size_bytes=5000,
            complexity_score=0.4,
            recommended_services=["qwen"],
            use_parallel=False
        )

        decision = await router.route(task_info)

        assert decision.primary_service == "qwen"
        assert "ollama_local" in decision.fallback_services
        assert decision.execution_mode == "single"

    @pytest.mark.asyncio
    async def test_route_codebase_analysis(self, mock_config):
        """Test routing for codebase analysis"""
        router = TaskRouter(mock_config)

        task_info = TaskInfo(
            task_type=TaskType.CODEBASE_ANALYSIS,
            file_count=25,
            total_size_bytes=1000000,
            complexity_score=0.8,
            recommended_services=["gemini"],
            use_parallel=True,
            estimated_latency="high"
        )

        decision = await router.route(task_info)

        assert decision.primary_service == "gemini"
        assert decision.execution_mode == "parallel"

    # Health Checking Tests

    @pytest.mark.asyncio
    async def test_route_with_healthy_service(self, mock_config):
        """Test routing when primary service is healthy"""
        async def health_checker(service_name):
            return True

        router = TaskRouter(mock_config, health_checker)

        task_info = TaskInfo(
            task_type=TaskType.QUICK_QUERY,
            file_count=0,
            total_size_bytes=0,
            complexity_score=0.1,
            recommended_services=["ollama_local"]
        )

        decision = await router.route(task_info)
        assert decision.primary_service == "ollama_local"

    @pytest.mark.asyncio
    async def test_route_with_unhealthy_primary(self, mock_config):
        """Test routing falls back when primary is unhealthy"""
        async def health_checker(service_name):
            # Primary service (ollama_local) is down
            return service_name != "ollama_local"

        router = TaskRouter(mock_config, health_checker)

        task_info = TaskInfo(
            task_type=TaskType.QUICK_QUERY,
            file_count=0,
            total_size_bytes=0,
            complexity_score=0.1,
            recommended_services=["ollama_local", "qwen"]
        )

        decision = await router.route(task_info)

        # Should fallback to next available service
        assert decision.primary_service != "ollama_local"
        assert decision.primary_service in ["ollama_remote", "qwen"]

    @pytest.mark.asyncio
    async def test_route_all_services_unhealthy(self, mock_config):
        """Test routing when all services are unhealthy"""
        async def health_checker(service_name):
            return False  # All unhealthy

        router = TaskRouter(mock_config, health_checker)

        task_info = TaskInfo(
            task_type=TaskType.QUICK_QUERY,
            file_count=0,
            total_size_bytes=0,
            complexity_score=0.1,
            recommended_services=["ollama_local"]
        )

        with pytest.raises(NoServiceAvailableError):
            await router.route(task_info)

    # Fallback Logic Tests

    @pytest.mark.asyncio
    async def test_select_available_service_primary_available(self, mock_config):
        """Test service selection when primary is available"""
        async def health_checker(service_name):
            return True

        router = TaskRouter(mock_config, health_checker)

        service = await router._select_available_service(
            "gemini",
            ["qwen", "ollama_local"]
        )

        assert service == "gemini"

    @pytest.mark.asyncio
    async def test_select_available_service_use_fallback(self, mock_config):
        """Test service selection uses fallback when primary unavailable"""
        async def health_checker(service_name):
            return service_name != "gemini"  # Primary down

        router = TaskRouter(mock_config, health_checker)

        service = await router._select_available_service(
            "gemini",
            ["qwen", "ollama_local"]
        )

        assert service == "qwen"

    @pytest.mark.asyncio
    async def test_select_available_service_none_available(self, mock_config):
        """Test service selection when none are available"""
        async def health_checker(service_name):
            return False

        router = TaskRouter(mock_config, health_checker)

        service = await router._select_available_service(
            "gemini",
            ["qwen", "ollama_local"]
        )

        assert service is None

    # Service Availability Checks

    @pytest.mark.asyncio
    async def test_is_service_available_enabled(self, mock_config):
        """Test service availability check for enabled service"""
        router = TaskRouter(mock_config)

        is_available = await router._is_service_available("gemini")
        assert is_available is True

    @pytest.mark.asyncio
    async def test_is_service_available_disabled(self, mock_config):
        """Test service availability check for disabled service"""
        router = TaskRouter(mock_config)

        is_available = await router._is_service_available("ollama_remote")
        assert is_available is False  # Disabled in mock config

    @pytest.mark.asyncio
    async def test_is_service_available_unknown_service(self, mock_config):
        """Test service availability check for unknown service"""
        router = TaskRouter(mock_config)

        is_available = await router._is_service_available("nonexistent")
        assert is_available is False

    @pytest.mark.asyncio
    async def test_is_service_available_with_health_check(self, mock_config):
        """Test service availability with health checker"""
        async def health_checker(service_name):
            return service_name == "gemini"

        router = TaskRouter(mock_config, health_checker)

        assert await router._is_service_available("gemini") is True
        assert await router._is_service_available("qwen") is False

    @pytest.mark.asyncio
    async def test_is_service_available_health_check_error(self, mock_config):
        """Test service availability when health check raises error"""
        async def health_checker(service_name):
            raise Exception("Health check failed")

        router = TaskRouter(mock_config, health_checker)

        is_available = await router._is_service_available("gemini")
        assert is_available is False

    # Routing from Recommendations Tests

    @pytest.mark.asyncio
    async def test_route_from_recommendations(self, mock_config):
        """Test routing from classifier recommendations when no rule exists"""
        router = TaskRouter(mock_config)

        task_info = TaskInfo(
            task_type=TaskType.DEBUGGING,  # No rule for debugging
            file_count=1,
            total_size_bytes=1000,
            complexity_score=0.3,
            recommended_services=["qwen", "ollama_local"]
        )

        decision = await router._route_from_recommendations(task_info)

        assert decision.primary_service == "qwen"
        assert decision.fallback_services == ["ollama_local"]
        assert decision.execution_mode == "single"

    @pytest.mark.asyncio
    async def test_route_from_recommendations_no_services(self, mock_config):
        """Test routing from recommendations with no recommended services"""
        router = TaskRouter(mock_config)

        task_info = TaskInfo(
            task_type=TaskType.DEBUGGING,
            file_count=0,
            total_size_bytes=0,
            complexity_score=0.1,
            recommended_services=[]  # No recommendations
        )

        with pytest.raises(NoServiceAvailableError):
            await router._route_from_recommendations(task_info)

    # Timeout Configuration Tests

    @pytest.mark.asyncio
    async def test_route_uses_rule_timeout(self, mock_config):
        """Test that routing uses rule-specific timeout"""
        router = TaskRouter(mock_config)

        task_info = TaskInfo(
            task_type=TaskType.CODEBASE_ANALYSIS,
            file_count=25,
            total_size_bytes=1000000,
            complexity_score=0.8,
            recommended_services=["gemini"]
        )

        decision = await router.route(task_info)

        # Codebase analysis should have 300s timeout from rules
        assert decision.timeout_seconds == 300

    @pytest.mark.asyncio
    async def test_route_uses_default_timeout(self, mock_config):
        """Test routing uses default timeout when rule doesn't specify"""
        router = TaskRouter(mock_config)

        task_info = TaskInfo(
            task_type=TaskType.DEBUGGING,  # No timeout in rule
            file_count=1,
            total_size_bytes=1000,
            complexity_score=0.3,
            recommended_services=["qwen"]
        )

        decision = await router._route_from_recommendations(task_info)

        # Should use default from execution config (120s)
        assert decision.timeout_seconds == 120

    # Execution Mode Tests

    @pytest.mark.asyncio
    async def test_route_single_execution_mode(self, mock_config):
        """Test single execution mode selection"""
        router = TaskRouter(mock_config)

        task_info = TaskInfo(
            task_type=TaskType.QUICK_QUERY,
            file_count=0,
            total_size_bytes=0,
            complexity_score=0.1,
            recommended_services=["ollama_local"],
            use_parallel=False
        )

        decision = await router.route(task_info)
        assert decision.execution_mode == "single"

    @pytest.mark.asyncio
    async def test_route_parallel_execution_mode(self, mock_config):
        """Test parallel execution mode selection"""
        router = TaskRouter(mock_config)

        task_info = TaskInfo(
            task_type=TaskType.CODEBASE_ANALYSIS,
            file_count=30,
            total_size_bytes=2000000,
            complexity_score=0.9,
            recommended_services=["gemini"],
            use_parallel=True  # Classifier recommends parallel
        )

        decision = await router.route(task_info)
        assert decision.execution_mode == "parallel"

    # Routing Rules Summary Tests

    def test_get_routing_rules_summary(self, mock_config):
        """Test getting routing rules summary"""
        router = TaskRouter(mock_config)

        summary = router.get_routing_rules_summary()

        assert isinstance(summary, dict)
        assert "codebase_analysis" in summary
        assert "code_review" in summary
        assert "quick_query" in summary

        # Check structure
        assert "primary" in summary["quick_query"]
        assert "fallback" in summary["quick_query"]
        assert "parallel_threshold" in summary["quick_query"]
        assert "timeout" in summary["quick_query"]

    def test_get_routing_rules_summary_values(self, mock_config):
        """Test routing rules summary contains correct values"""
        router = TaskRouter(mock_config)

        summary = router.get_routing_rules_summary()

        assert summary["quick_query"]["primary"] == "ollama_local"
        assert summary["code_review"]["primary"] == "qwen"
        assert summary["codebase_analysis"]["primary"] == "gemini"

    # Edge Cases

    @pytest.mark.asyncio
    async def test_route_with_none_task_info(self, mock_config):
        """Test routing with minimal task info"""
        router = TaskRouter(mock_config)

        task_info = TaskInfo(
            task_type=TaskType.QUICK_QUERY,
            file_count=0,
            total_size_bytes=0,
            complexity_score=0.0,
            recommended_services=["ollama_local"]
        )

        decision = await router.route(task_info)
        assert decision is not None

    @pytest.mark.asyncio
    async def test_route_logging(self, mock_config, mock_logger, monkeypatch):
        """Test that routing decisions are logged"""
        router = TaskRouter(mock_config)
        monkeypatch.setattr(router, 'logger', mock_logger)

        task_info = TaskInfo(
            task_type=TaskType.QUICK_QUERY,
            file_count=0,
            total_size_bytes=0,
            complexity_score=0.1,
            recommended_services=["ollama_local"]
        )

        await router.route(task_info)

        # Verify logging occurred
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_route_fallback_logging(self, mock_config, mock_logger, monkeypatch):
        """Test that fallback is logged when primary fails"""
        async def health_checker(service_name):
            return service_name != "ollama_local"

        router = TaskRouter(mock_config, health_checker)
        monkeypatch.setattr(router, 'logger', mock_logger)

        task_info = TaskInfo(
            task_type=TaskType.QUICK_QUERY,
            file_count=0,
            total_size_bytes=0,
            complexity_score=0.1,
            recommended_services=["ollama_local", "qwen"]
        )

        await router.route(task_info)

        # Should log fallback usage
        mock_logger.info.assert_called()
