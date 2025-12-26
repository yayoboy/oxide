"""
Comprehensive test suite for Orchestrator component.

Tests cover:
- Basic task execution flow
- Retry and fallback logic
- Memory integration
- Cost tracking
- Health checks
- Preferences override
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import AsyncIterator, List, Optional

from oxide.core.orchestrator import Orchestrator
from oxide.core.classifier import TaskInfo, TaskType
from oxide.core.router import RouterDecision
from oxide.utils.exceptions import (
    ServiceUnavailableError,
    ExecutionError,
    NoServiceAvailableError
)


# Helper function for async generators
async def async_gen(items: List[str]) -> AsyncIterator[str]:
    """Create async generator from list of items"""
    for item in items:
        yield item


@pytest.fixture
def mock_classifier():
    """Mock TaskClassifier"""
    classifier = MagicMock()
    classifier.classify = MagicMock(return_value=TaskInfo(
        task_type=TaskType.QUICK_QUERY,
        file_count=0,
        total_size_bytes=0,
        complexity_score=0.1,
        recommended_services=['gemini', 'qwen'],
        use_parallel=False,
        estimated_latency='low'
    ))
    return classifier


@pytest.fixture
def mock_router():
    """Mock TaskRouter"""
    router = AsyncMock()
    router.route = AsyncMock(return_value=RouterDecision(
        primary_service='gemini',
        fallback_services=['qwen', 'ollama_local'],
        execution_mode='single',
        timeout_seconds=120
    ))
    return router


@pytest.fixture
def mock_memory():
    """Mock ContextMemory"""
    memory = MagicMock()
    memory.add_context = MagicMock(return_value='msg_123')
    memory.get_context_for_task = MagicMock(return_value=[])
    return memory


@pytest.fixture
def mock_cost_tracker():
    """Mock CostTracker"""
    cost_tracker = MagicMock()
    cost_tracker.record_cost = MagicMock(return_value={
        'task_id': 'test',
        'service': 'gemini',
        'total_cost_usd': 0.001
    })
    return cost_tracker


@pytest.fixture
def mock_adapter_success():
    """Mock adapter with successful execution"""
    adapter = AsyncMock()
    adapter.execute = AsyncMock(return_value=async_gen(['Hello', ' ', 'World']))
    adapter.health_check = AsyncMock(return_value=True)
    adapter.get_service_info = MagicMock(return_value={'type': 'cli', 'model': 'gemini-pro'})
    return adapter


@pytest.fixture
def mock_adapter_fail():
    """Mock adapter that fails"""
    adapter = AsyncMock()
    adapter.execute = AsyncMock(side_effect=Exception("Connection timeout"))
    adapter.health_check = AsyncMock(return_value=False)
    adapter.get_service_info = MagicMock(return_value={'type': 'cli'})
    return adapter


@pytest.fixture
def mock_adapter_unavailable():
    """Mock adapter that's unavailable"""
    adapter = AsyncMock()
    adapter.execute = AsyncMock(
        side_effect=ServiceUnavailableError('gemini', 'Service is down')
    )
    adapter.health_check = AsyncMock(return_value=False)
    return adapter


@pytest.fixture
def orchestrator_with_mocks(
    mock_config,
    mock_classifier,
    mock_router,
    mock_memory,
    mock_cost_tracker,
    mock_adapter_success,
    monkeypatch
):
    """Create Orchestrator with all mocked dependencies"""
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.config = mock_config
    orchestrator.classifier = mock_classifier
    orchestrator.router = mock_router
    orchestrator.memory = mock_memory
    orchestrator.cost_tracker = mock_cost_tracker
    orchestrator.adapters = {
        'gemini': mock_adapter_success,
        'qwen': mock_adapter_success,
        'ollama_local': mock_adapter_success,
    }

    # Mock logger
    orchestrator.logger = MagicMock()

    return orchestrator


class TestOrchestratorBasicExecution:
    """Test basic task execution flow"""

    @pytest.mark.asyncio
    async def test_execute_task_simple_prompt(self, orchestrator_with_mocks):
        """Test simple prompt execution with default settings"""
        orchestrator = orchestrator_with_mocks

        # Execute
        chunks = []
        async for chunk in orchestrator.execute_task("What is Python?"):
            chunks.append(chunk)

        # Assertions
        assert len(chunks) == 3
        assert ''.join(chunks) == 'Hello World'

        # Verify classifier was called
        orchestrator.classifier.classify.assert_called_once_with(
            "What is Python?",
            None
        )

        # Verify router was called
        orchestrator.router.route.assert_called_once()

        # Verify adapter execute was called
        orchestrator.adapters['gemini'].execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_task_with_files(self, orchestrator_with_mocks, tmp_files):
        """Test execution with file context"""
        orchestrator = orchestrator_with_mocks
        files = tmp_files(3)

        # Execute
        chunks = []
        async for chunk in orchestrator.execute_task("Review this code", files=files):
            chunks.append(chunk)

        # Verify files passed to classifier
        orchestrator.classifier.classify.assert_called_once_with(
            "Review this code",
            files
        )

        # Verify files passed to adapter
        call_args = orchestrator.adapters['gemini'].execute.call_args
        assert call_args[1]['files'] == files

    @pytest.mark.asyncio
    async def test_execute_task_stores_memory(self, orchestrator_with_mocks):
        """Test that prompt and response are stored in memory"""
        orchestrator = orchestrator_with_mocks

        # Execute
        chunks = []
        async for chunk in orchestrator.execute_task("Test prompt"):
            chunks.append(chunk)

        # Verify memory.add_context called twice (user + assistant)
        assert orchestrator.memory.add_context.call_count == 2

        # Check user message
        user_call = orchestrator.memory.add_context.call_args_list[0]
        assert user_call[1]['role'] == 'user'
        assert user_call[1]['content'] == 'Test prompt'

        # Check assistant message
        assistant_call = orchestrator.memory.add_context.call_args_list[1]
        assert assistant_call[1]['role'] == 'assistant'
        assert assistant_call[1]['content'] == 'Hello World'

    @pytest.mark.asyncio
    async def test_execute_task_records_cost(self, orchestrator_with_mocks):
        """Test that cost is recorded on successful execution"""
        orchestrator = orchestrator_with_mocks

        # Execute
        chunks = []
        async for chunk in orchestrator.execute_task("Test"):
            chunks.append(chunk)

        # Verify cost_tracker.record_cost was called
        orchestrator.cost_tracker.record_cost.assert_called_once()
        call_args = orchestrator.cost_tracker.record_cost.call_args
        assert call_args[1]['service'] == 'gemini'
        assert call_args[1]['prompt'] == 'Test'
        assert call_args[1]['response'] == 'Hello World'


class TestOrchestratorRetryFallback:
    """Test retry and fallback logic"""

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(
        self,
        orchestrator_with_mocks,
        mock_adapter_success,
        monkeypatch
    ):
        """Test retry logic for transient failures"""
        orchestrator = orchestrator_with_mocks

        # Mock adapter to fail once, then succeed
        call_count = {'count': 0}

        async def mock_execute(*args, **kwargs):
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise Exception("Temporary failure")
            else:
                async for chunk in async_gen(['Success']):
                    yield chunk

        orchestrator.adapters['gemini'].execute = mock_execute

        # Execute
        chunks = []
        async for chunk in orchestrator.execute_task("Test"):
            chunks.append(chunk)

        # Verify retry occurred
        assert call_count['count'] == 2
        assert chunks == ['Success']

    @pytest.mark.asyncio
    async def test_no_retry_on_service_unavailable(self, orchestrator_with_mocks):
        """Test that ServiceUnavailableError triggers immediate fallback"""
        orchestrator = orchestrator_with_mocks

        # Mock primary to raise ServiceUnavailableError, fallback succeeds
        orchestrator.adapters['gemini'].execute = AsyncMock(
            side_effect=ServiceUnavailableError('gemini', 'Service down')
        )
        orchestrator.adapters['qwen'].execute = AsyncMock(
            return_value=async_gen(['Fallback response'])
        )

        # Execute
        chunks = []
        async for chunk in orchestrator.execute_task("Test"):
            chunks.append(chunk)

        # Verify primary was called once (no retry)
        assert orchestrator.adapters['gemini'].execute.call_count == 1

        # Verify fallback was called
        orchestrator.adapters['qwen'].execute.assert_called_once()
        assert chunks == ['Fallback response']

    @pytest.mark.asyncio
    async def test_fallback_to_secondary_service(self, orchestrator_with_mocks):
        """Test fallback when primary service fails"""
        orchestrator = orchestrator_with_mocks

        # Primary fails with max retries, fallback succeeds
        orchestrator.adapters['gemini'].execute = AsyncMock(
            side_effect=Exception("Always fails")
        )
        orchestrator.adapters['qwen'].execute = AsyncMock(
            return_value=async_gen(['Qwen response'])
        )

        # Execute
        chunks = []
        async for chunk in orchestrator.execute_task("Test"):
            chunks.append(chunk)

        # Verify fallback was used
        assert chunks == ['Qwen response']
        orchestrator.adapters['qwen'].execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_services_exhausted_raises_error(self, orchestrator_with_mocks):
        """Test ExecutionError when all services fail"""
        orchestrator = orchestrator_with_mocks

        # All adapters fail
        for adapter in orchestrator.adapters.values():
            adapter.execute = AsyncMock(side_effect=Exception("Failed"))

        # Execute and expect error
        with pytest.raises(ExecutionError) as exc_info:
            chunks = []
            async for chunk in orchestrator.execute_task("Test"):
                chunks.append(chunk)

        assert "All services failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_service_available_error(
        self,
        orchestrator_with_mocks,
        mock_classifier
    ):
        """Test NoServiceAvailableError when no services recommended"""
        orchestrator = orchestrator_with_mocks

        # Classifier returns no recommended services
        mock_classifier.classify.return_value = TaskInfo(
            task_type=TaskType.QUICK_QUERY,
            file_count=0,
            total_size_bytes=0,
            complexity_score=0.1,
            recommended_services=[],  # Empty!
            use_parallel=False,
            estimated_latency='low'
        )

        # Router returns no services
        orchestrator.router.route.return_value = RouterDecision(
            primary_service=None,
            fallback_services=[],
            execution_mode='single',
            timeout_seconds=120
        )

        # Execute and expect error
        with pytest.raises(NoServiceAvailableError):
            async for chunk in orchestrator.execute_task("Test"):
                pass


class TestOrchestratorPreferences:
    """Test preferences override behavior"""

    @pytest.mark.asyncio
    async def test_preferred_service_override(self, orchestrator_with_mocks):
        """Test preferred_service bypasses routing"""
        orchestrator = orchestrator_with_mocks

        # Execute with preferred service
        chunks = []
        preferences = {'preferred_service': 'qwen'}
        async for chunk in orchestrator.execute_task("Test", preferences=preferences):
            chunks.append(chunk)

        # Verify qwen adapter was used directly
        orchestrator.adapters['qwen'].execute.assert_called_once()

        # Router should still be called for decision structure
        orchestrator.router.route.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_override(self, orchestrator_with_mocks):
        """Test timeout preference overrides default"""
        orchestrator = orchestrator_with_mocks

        # Execute with custom timeout
        preferences = {'timeout': 60}
        chunks = []
        async for chunk in orchestrator.execute_task("Test", preferences=preferences):
            chunks.append(chunk)

        # Verify adapter called with custom timeout
        call_args = orchestrator.adapters['gemini'].execute.call_args
        assert call_args[1]['timeout'] == 60

    @pytest.mark.asyncio
    async def test_use_memory_false(self, orchestrator_with_mocks):
        """Test disabling memory tracking"""
        orchestrator = orchestrator_with_mocks

        # Execute with memory disabled
        preferences = {'use_memory': False}
        chunks = []
        async for chunk in orchestrator.execute_task("Test", preferences=preferences):
            chunks.append(chunk)

        # Verify memory methods NOT called
        orchestrator.memory.add_context.assert_not_called()
        orchestrator.memory.get_context_for_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_conversation_id_preference(self, orchestrator_with_mocks):
        """Test explicit conversation_id for memory continuity"""
        orchestrator = orchestrator_with_mocks

        # Execute with explicit conversation ID
        preferences = {'conversation_id': 'conv_123'}
        chunks = []
        async for chunk in orchestrator.execute_task("Test", preferences=preferences):
            chunks.append(chunk)

        # Verify memory used the conversation ID
        user_call = orchestrator.memory.add_context.call_args_list[0]
        assert user_call[1]['conversation_id'] == 'conv_123'


class TestOrchestratorHealthChecks:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_check_service_health_success(self, orchestrator_with_mocks):
        """Test successful health check"""
        orchestrator = orchestrator_with_mocks

        # Check health
        result = await orchestrator._check_service_health('gemini')

        # Verify
        assert result is True
        orchestrator.adapters['gemini'].health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_service_health_failure(self, orchestrator_with_mocks):
        """Test health check returns False on failure"""
        orchestrator = orchestrator_with_mocks
        orchestrator.adapters['gemini'].health_check = AsyncMock(return_value=False)

        # Check health
        result = await orchestrator._check_service_health('gemini')

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self, orchestrator_with_mocks):
        """Test graceful handling of health check exceptions"""
        orchestrator = orchestrator_with_mocks
        orchestrator.adapters['gemini'].health_check = AsyncMock(
            side_effect=Exception("Network error")
        )

        # Check health
        result = await orchestrator._check_service_health('gemini')

        # Verify returns False instead of raising
        assert result is False


class TestOrchestratorMemoryIntegration:
    """Test memory integration"""

    @pytest.mark.asyncio
    async def test_memory_context_retrieval(self, orchestrator_with_mocks):
        """Test context memory retrieval for task"""
        orchestrator = orchestrator_with_mocks

        # Setup existing context
        orchestrator.memory.get_context_for_task.return_value = [
            {'role': 'user', 'content': 'Previous question'},
            {'role': 'assistant', 'content': 'Previous answer'}
        ]

        # Execute
        chunks = []
        async for chunk in orchestrator.execute_task("Follow-up question"):
            chunks.append(chunk)

        # Verify context was retrieved
        orchestrator.memory.get_context_for_task.assert_called_once()
        call_args = orchestrator.memory.get_context_for_task.call_args
        assert call_args[1]['task_type'] == 'quick_query'
        assert call_args[1]['prompt'] == 'Follow-up question'

    @pytest.mark.asyncio
    async def test_memory_error_handling(self, orchestrator_with_mocks):
        """Test that memory errors don't fail task execution"""
        orchestrator = orchestrator_with_mocks

        # Mock memory to raise exception
        orchestrator.memory.add_context = MagicMock(
            side_effect=Exception("Memory error")
        )

        # Execute should still succeed
        chunks = []
        async for chunk in orchestrator.execute_task("Test"):
            chunks.append(chunk)

        # Verify task completed
        assert chunks == ['Hello', ' ', 'World']

        # Verify error was logged
        orchestrator.logger.warning.assert_called()


class TestOrchestratorCostTracking:
    """Test cost tracking integration"""

    @pytest.mark.asyncio
    async def test_cost_recorded_on_success(self, orchestrator_with_mocks):
        """Test cost tracker called with correct params"""
        orchestrator = orchestrator_with_mocks

        # Execute
        chunks = []
        async for chunk in orchestrator.execute_task("Test prompt"):
            chunks.append(chunk)

        # Verify cost recorded
        orchestrator.cost_tracker.record_cost.assert_called_once()
        call_args = orchestrator.cost_tracker.record_cost.call_args
        assert call_args[1]['service'] == 'gemini'
        assert call_args[1]['prompt'] == 'Test prompt'
        assert call_args[1]['response'] == 'Hello World'

    @pytest.mark.asyncio
    async def test_cost_tracking_error_handling(self, orchestrator_with_mocks):
        """Test that cost tracking errors don't fail execution"""
        orchestrator = orchestrator_with_mocks

        # Mock cost tracker to raise exception
        orchestrator.cost_tracker.record_cost = MagicMock(
            side_effect=Exception("Database error")
        )

        # Execute should still succeed
        chunks = []
        async for chunk in orchestrator.execute_task("Test"):
            chunks.append(chunk)

        # Verify task completed
        assert chunks == ['Hello', ' ', 'World']

        # Verify warning logged
        orchestrator.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_cost_not_recorded_on_failure(self, orchestrator_with_mocks):
        """Test cost only recorded on successful execution"""
        orchestrator = orchestrator_with_mocks

        # All services fail
        for adapter in orchestrator.adapters.values():
            adapter.execute = AsyncMock(side_effect=Exception("Failed"))

        # Execute and expect error
        with pytest.raises(ExecutionError):
            async for chunk in orchestrator.execute_task("Test"):
                pass

        # Verify cost was NOT recorded
        orchestrator.cost_tracker.record_cost.assert_not_called()


class TestOrchestratorServiceManagement:
    """Test service status and management methods"""

    @pytest.mark.asyncio
    async def test_get_service_status(self, orchestrator_with_mocks):
        """Test get_service_status returns correct format"""
        orchestrator = orchestrator_with_mocks

        # Get status
        status = await orchestrator.get_service_status()

        # Verify structure
        assert 'services' in status
        assert 'gemini' in status['services']
        assert 'qwen' in status['services']

        # Verify health checks were called
        for adapter in orchestrator.adapters.values():
            adapter.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_service(self, orchestrator_with_mocks):
        """Test service testing with custom prompt"""
        orchestrator = orchestrator_with_mocks

        # Test service
        result = await orchestrator.test_service('gemini', 'Hello test')

        # Verify adapter execute was called
        orchestrator.adapters['gemini'].execute.assert_called_once()
        call_args = orchestrator.adapters['gemini'].execute.call_args
        assert call_args[0][0] == 'Hello test'

        # Verify result structure
        assert 'service' in result
        assert 'success' in result
        assert result['service'] == 'gemini'

    def test_get_adapters_info(self, orchestrator_with_mocks):
        """Test get_adapters_info returns adapter information"""
        orchestrator = orchestrator_with_mocks

        # Get info
        info = orchestrator.get_adapters_info()

        # Verify
        assert 'gemini' in info
        assert 'qwen' in info
        assert info['gemini']['type'] == 'cli'

    def test_get_routing_rules(self, orchestrator_with_mocks):
        """Test get_routing_rules returns routing configuration"""
        orchestrator = orchestrator_with_mocks

        # Get rules
        rules = orchestrator.get_routing_rules()

        # Verify structure
        assert isinstance(rules, dict)
