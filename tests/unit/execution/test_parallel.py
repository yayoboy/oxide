"""
Unit tests for ParallelExecutor.

Tests parallel execution logic, file splitting, result aggregation.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from oxide.execution.parallel import ParallelExecutor, ParallelResult


@pytest.fixture
def parallel_executor():
    """Create a ParallelExecutor instance."""
    return ParallelExecutor(max_workers=3)


@pytest.fixture
def mock_adapter():
    """Create a mock LLM adapter."""
    adapter = Mock()
    adapter.execute = AsyncMock(return_value="Mock response")
    return adapter


@pytest.fixture
def sample_files():
    """Sample file list for testing."""
    return ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py", "file6.py"]


class TestParallelExecutorInit:
    """Test ParallelExecutor initialization."""

    def test_init_default_workers(self):
        """Test initialization with default max_workers."""
        executor = ParallelExecutor()
        assert executor.max_workers == 3

    def test_init_custom_workers(self):
        """Test initialization with custom max_workers."""
        executor = ParallelExecutor(max_workers=5)
        assert executor.max_workers == 5

    def test_init_has_logger(self):
        """Test that logger is initialized."""
        executor = ParallelExecutor()
        assert hasattr(executor, 'logger')


class TestFileSplitting:
    """Test file splitting logic."""

    def test_split_files_equal_distribution(self, parallel_executor):
        """Test splitting files equally among workers."""
        files = ["f1", "f2", "f3", "f4", "f5", "f6"]
        chunks = parallel_executor._split_files(files, num_chunks=3)

        assert len(chunks) == 3
        # Each chunk should have 2 files
        for chunk in chunks:
            assert len(chunk) == 2

    def test_split_files_uneven_distribution(self, parallel_executor):
        """Test splitting files with uneven distribution."""
        files = ["f1", "f2", "f3", "f4", "f5"]
        chunks = parallel_executor._split_files(files, num_chunks=3)

        assert len(chunks) == 3
        total_files = sum(len(chunk) for chunk in chunks)
        assert total_files == 5

    def test_split_files_more_chunks_than_files(self, parallel_executor):
        """Test splitting with more chunks than files."""
        files = ["f1", "f2"]
        chunks = parallel_executor._split_files(files, num_chunks=5)

        # Should create chunks for all files (some empty)
        assert len(chunks) == 5
        non_empty = [c for c in chunks if c]
        assert len(non_empty) == 2

    def test_split_files_single_chunk(self, parallel_executor):
        """Test splitting into single chunk."""
        files = ["f1", "f2", "f3"]
        chunks = parallel_executor._split_files(files, num_chunks=1)

        assert len(chunks) == 1
        assert len(chunks[0]) == 3

    def test_split_files_empty_list(self, parallel_executor):
        """Test splitting empty file list."""
        chunks = parallel_executor._split_files([], num_chunks=3)

        assert len(chunks) == 3
        for chunk in chunks:
            assert len(chunk) == 0


class TestExecuteOnService:
    """Test execution on individual service."""

    @pytest.mark.asyncio
    async def test_execute_on_service_success(self, parallel_executor, mock_adapter):
        """Test successful execution on a service."""
        result = await parallel_executor._execute_on_service(
            "test_service",
            mock_adapter,
            "Test prompt",
            ["file1.py", "file2.py"]
        )

        assert result["service"] == "test_service"
        assert result["success"] is True
        assert "response" in result
        assert result["file_count"] == 2
        mock_adapter.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_on_service_empty_files(self, parallel_executor, mock_adapter):
        """Test execution with empty file list."""
        result = await parallel_executor._execute_on_service(
            "test_service",
            mock_adapter,
            "Test prompt",
            []
        )

        assert result["service"] == "test_service"
        assert result["file_count"] == 0
        mock_adapter.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_on_service_adapter_failure(self, parallel_executor):
        """Test handling of adapter execution failure."""
        failing_adapter = Mock()
        failing_adapter.execute = AsyncMock(side_effect=Exception("Adapter error"))

        result = await parallel_executor._execute_on_service(
            "failing_service",
            failing_adapter,
            "Test prompt",
            ["file1.py"]
        )

        assert result["service"] == "failing_service"
        assert result["success"] is False
        assert "error" in result


class TestSplitStrategy:
    """Test split execution strategy."""

    @pytest.mark.asyncio
    async def test_split_strategy_basic(self, parallel_executor, sample_files):
        """Test basic split strategy execution."""
        mock_adapters = {
            "service1": Mock(execute=AsyncMock(return_value="Response 1")),
            "service2": Mock(execute=AsyncMock(return_value="Response 2")),
            "service3": Mock(execute=AsyncMock(return_value="Response 3"))
        }

        result = await parallel_executor._execute_split_strategy(
            "Analyze files",
            sample_files,
            ["service1", "service2", "service3"],
            mock_adapters
        )

        assert isinstance(result, ParallelResult)
        assert result.successful_tasks == 3
        assert result.failed_tasks == 0
        assert len(result.individual_results) == 3

    @pytest.mark.asyncio
    async def test_split_strategy_limits_workers(self, parallel_executor):
        """Test that split strategy limits number of workers."""
        many_services = ["s1", "s2", "s3", "s4", "s5"]  # 5 services
        mock_adapters = {s: Mock(execute=AsyncMock(return_value=f"Response {s}"))
                        for s in many_services}

        result = await parallel_executor._execute_split_strategy(
            "Test prompt",
            ["f1", "f2", "f3"],
            many_services,
            mock_adapters
        )

        # Should only use max_workers (3) services
        assert len(result.individual_results) <= parallel_executor.max_workers

    @pytest.mark.asyncio
    async def test_split_strategy_partial_failure(self, parallel_executor):
        """Test split strategy with some services failing."""
        mock_adapters = {
            "service1": Mock(execute=AsyncMock(return_value="Success")),
            "service2": Mock(execute=AsyncMock(side_effect=Exception("Failed"))),
            "service3": Mock(execute=AsyncMock(return_value="Success"))
        }

        result = await parallel_executor._execute_split_strategy(
            "Test prompt",
            ["f1", "f2", "f3"],
            ["service1", "service2", "service3"],
            mock_adapters
        )

        assert result.successful_tasks == 2
        assert result.failed_tasks == 1


class TestDuplicateStrategy:
    """Test duplicate execution strategy."""

    @pytest.mark.asyncio
    async def test_duplicate_strategy_basic(self, parallel_executor):
        """Test basic duplicate strategy execution."""
        mock_adapters = {
            "service1": Mock(execute=AsyncMock(return_value="Response 1")),
            "service2": Mock(execute=AsyncMock(return_value="Response 2"))
        }

        result = await parallel_executor._execute_duplicate_strategy(
            "Test prompt",
            ["file1.py"],
            ["service1", "service2"],
            mock_adapters
        )

        assert isinstance(result, ParallelResult)
        assert result.successful_tasks + result.failed_tasks == 2

    @pytest.mark.asyncio
    async def test_duplicate_strategy_all_files_to_each_service(self, parallel_executor):
        """Test that duplicate strategy sends all files to each service."""
        mock_adapters = {
            "service1": Mock(execute=AsyncMock(return_value="R1")),
            "service2": Mock(execute=AsyncMock(return_value="R2"))
        }

        files = ["f1", "f2", "f3"]
        await parallel_executor._execute_duplicate_strategy(
            "Test",
            files,
            ["service1", "service2"],
            mock_adapters
        )

        # Each adapter should receive all files
        for adapter in mock_adapters.values():
            assert adapter.execute.called


class TestExecuteParallel:
    """Test main execute_parallel method."""

    @pytest.mark.asyncio
    async def test_execute_parallel_split_strategy(self, parallel_executor):
        """Test execute_parallel with split strategy."""
        mock_adapters = {
            "service1": Mock(execute=AsyncMock(return_value="Response 1")),
            "service2": Mock(execute=AsyncMock(return_value="Response 2"))
        }

        result = await parallel_executor.execute_parallel(
            "Test prompt",
            ["f1", "f2", "f3", "f4"],
            ["service1", "service2"],
            mock_adapters,
            strategy="split"
        )

        assert isinstance(result, ParallelResult)
        assert result.total_duration_seconds > 0
        assert result.services_used == ["service1", "service2"]

    @pytest.mark.asyncio
    async def test_execute_parallel_duplicate_strategy(self, parallel_executor):
        """Test execute_parallel with duplicate strategy."""
        mock_adapters = {
            "service1": Mock(execute=AsyncMock(return_value="R1"))
        }

        result = await parallel_executor.execute_parallel(
            "Test",
            ["f1"],
            ["service1"],
            mock_adapters,
            strategy="duplicate"
        )

        assert isinstance(result, ParallelResult)
        assert result.total_duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_execute_parallel_invalid_strategy(self, parallel_executor):
        """Test execute_parallel with invalid strategy."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            await parallel_executor.execute_parallel(
                "Test",
                ["f1"],
                ["service1"],
                {},
                strategy="invalid_strategy"
            )

    @pytest.mark.asyncio
    async def test_execute_parallel_measures_duration(self, parallel_executor):
        """Test that execution duration is measured."""
        mock_adapters = {
            "service1": Mock(execute=AsyncMock(return_value="Response"))
        }

        result = await parallel_executor.execute_parallel(
            "Test",
            ["f1"],
            ["service1"],
            mock_adapters,
            strategy="split"
        )

        assert result.total_duration_seconds >= 0
        assert isinstance(result.total_duration_seconds, float)


class TestResultAggregation:
    """Test result aggregation logic."""

    def test_aggregate_results_combines_responses(self, parallel_executor):
        """Test that responses are combined properly."""
        individual_results = [
            {"service": "s1", "success": True, "response": "Part 1"},
            {"service": "s2", "success": True, "response": "Part 2"},
            {"service": "s3", "success": True, "response": "Part 3"}
        ]

        aggregated = parallel_executor._aggregate_results(individual_results)

        assert "Part 1" in aggregated
        assert "Part 2" in aggregated
        assert "Part 3" in aggregated

    def test_aggregate_results_handles_failures(self, parallel_executor):
        """Test aggregation with some failed results."""
        individual_results = [
            {"service": "s1", "success": True, "response": "Success"},
            {"service": "s2", "success": False, "error": "Failed"},
            {"service": "s3", "success": True, "response": "Also success"}
        ]

        aggregated = parallel_executor._aggregate_results(individual_results)

        # Should only include successful responses
        assert "Success" in aggregated
        assert "Also success" in aggregated
        assert "Failed" not in aggregated

    def test_aggregate_results_empty_list(self, parallel_executor):
        """Test aggregation with empty results."""
        aggregated = parallel_executor._aggregate_results([])

        assert aggregated == ""

    def test_aggregate_results_all_failures(self, parallel_executor):
        """Test aggregation when all tasks failed."""
        individual_results = [
            {"service": "s1", "success": False, "error": "Error 1"},
            {"service": "s2", "success": False, "error": "Error 2"}
        ]

        aggregated = parallel_executor._aggregate_results(individual_results)

        # Should return error summary
        assert "error" in aggregated.lower() or aggregated == ""
