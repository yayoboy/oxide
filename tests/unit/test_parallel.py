"""
Unit tests for Parallel Execution.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import Dict, Any

from oxide.execution.parallel import ParallelExecutor, ParallelResult


class TestParallelExecutor:
    """Test suite for ParallelExecutor."""

    @pytest.fixture
    def executor(self):
        """Create a ParallelExecutor instance."""
        return ParallelExecutor(max_workers=3)

    @pytest.fixture
    def mock_adapters(self):
        """Create mock adapters."""
        adapters = {}

        for service in ["gemini", "qwen", "ollama_local"]:
            adapter = MagicMock()

            async def mock_execute(*args, **kwargs):
                yield f"Response from {service}"

            adapter.execute = mock_execute
            adapters[service] = adapter

        return adapters

    def test_executor_initialization(self):
        """Test executor initialization."""
        executor = ParallelExecutor(max_workers=5)

        assert executor.max_workers == 5
        assert executor.logger is not None

    def test_split_files_equal_distribution(self, executor):
        """Test splitting files into equal chunks."""
        files = ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py", "file6.py"]

        chunks = executor._split_files(files, 3)

        assert len(chunks) == 3
        assert chunks[0] == ["file1.py", "file2.py"]
        assert chunks[1] == ["file3.py", "file4.py"]
        assert chunks[2] == ["file5.py", "file6.py"]

    def test_split_files_unequal_distribution(self, executor):
        """Test splitting files with remainder."""
        files = ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]

        chunks = executor._split_files(files, 3)

        assert len(chunks) == 3
        # First chunk should have extra file (2 files)
        assert len(chunks[0]) == 2
        # Second chunk should have extra file (2 files)
        assert len(chunks[1]) == 2
        # Third chunk has remainder (1 file)
        assert len(chunks[2]) == 1

    def test_split_files_single_chunk(self, executor):
        """Test splitting into single chunk."""
        files = ["file1.py", "file2.py", "file3.py"]

        chunks = executor._split_files(files, 1)

        assert len(chunks) == 1
        assert chunks[0] == files

    def test_split_files_more_chunks_than_files(self, executor):
        """Test splitting with more chunks than files."""
        files = ["file1.py", "file2.py"]

        chunks = executor._split_files(files, 5)

        # Should create chunks for available files
        assert len(chunks) == 5
        assert chunks[0] == ["file1.py"]
        assert chunks[1] == ["file2.py"]
        assert chunks[2] == []
        assert chunks[3] == []
        assert chunks[4] == []

    def test_split_files_zero_chunks(self, executor):
        """Test splitting with zero chunks."""
        files = ["file1.py"]

        chunks = executor._split_files(files, 0)

        assert chunks == []

    def test_aggregate_results_split_strategy(self, executor):
        """Test aggregating results from split strategy."""
        individual_results = [
            {
                "service": "gemini",
                "success": True,
                "output": "Analysis from gemini"
            },
            {
                "service": "qwen",
                "success": True,
                "output": "Analysis from qwen"
            }
        ]

        aggregated = executor._aggregate_results(individual_results)

        assert "gemini" in aggregated
        assert "qwen" in aggregated
        assert "Analysis from gemini" in aggregated
        assert "Analysis from qwen" in aggregated

    def test_aggregate_results_with_failures(self, executor):
        """Test aggregating results when some tasks fail."""
        individual_results = [
            {
                "service": "gemini",
                "success": True,
                "output": "Success"
            },
            {
                "service": "qwen",
                "success": False,
                "error": "Failed"
            }
        ]

        aggregated = executor._aggregate_results(individual_results)

        # Should only include successful results
        assert "gemini" in aggregated
        assert "Success" in aggregated
        assert "qwen" not in aggregated
        assert "Failed" not in aggregated

    def test_aggregate_results_all_failed(self, executor):
        """Test aggregating when all tasks failed."""
        individual_results = [
            {
                "service": "gemini",
                "success": False,
                "error": "Error 1"
            },
            {
                "service": "qwen",
                "success": False,
                "error": "Error 2"
            }
        ]

        aggregated = executor._aggregate_results(individual_results)

        assert "All parallel tasks failed" in aggregated

    def test_aggregate_duplicate_results(self, executor):
        """Test aggregating results from duplicate strategy."""
        individual_results = [
            {
                "service": "gemini",
                "success": True,
                "output": "Output from gemini"
            },
            {
                "service": "qwen",
                "success": True,
                "output": "Output from qwen"
            }
        ]

        aggregated = executor._aggregate_duplicate_results(individual_results)

        assert "Comparison of Results" in aggregated
        assert "gemini" in aggregated
        assert "qwen" in aggregated
        assert "Output from gemini" in aggregated
        assert "Output from qwen" in aggregated

    def test_aggregate_duplicate_results_with_error(self, executor):
        """Test aggregating duplicate results with errors."""
        individual_results = [
            {
                "service": "gemini",
                "success": True,
                "output": "Success"
            },
            {
                "service": "qwen",
                "success": False,
                "error": "Service failed"
            }
        ]

        aggregated = executor._aggregate_duplicate_results(individual_results)

        assert "gemini" in aggregated
        assert "qwen" in aggregated
        assert "Success" in aggregated
        assert "Error:" in aggregated
        assert "Service failed" in aggregated

    @pytest.mark.asyncio
    async def test_execute_on_service_success(self, executor):
        """Test executing on a single service successfully."""
        adapter = MagicMock()

        async def mock_execute(*args, **kwargs):
            yield "Hello "
            yield "World"

        adapter.execute = mock_execute

        result = await executor._execute_on_service(
            "test_service",
            adapter,
            "test prompt",
            ["file.py"]
        )

        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_execute_on_service_failure(self, executor):
        """Test executing on service that raises exception."""
        adapter = MagicMock()

        async def mock_execute(*args, **kwargs):
            raise Exception("Service error")
            yield  # Make it a generator

        adapter.execute = mock_execute

        with pytest.raises(Exception, match="Service error"):
            await executor._execute_on_service(
                "test_service",
                adapter,
                "test prompt",
                ["file.py"]
            )

    @pytest.mark.asyncio
    async def test_execute_parallel_split_strategy_success(self, executor, mock_adapters):
        """Test parallel execution with split strategy."""
        files = ["file1.py", "file2.py", "file3.py"]
        services = ["gemini", "qwen", "ollama_local"]

        result = await executor.execute_parallel(
            "Analyze these files",
            files,
            services,
            mock_adapters,
            strategy="split"
        )

        assert isinstance(result, ParallelResult)
        assert result.successful_tasks >= 0
        assert result.failed_tasks >= 0
        assert len(result.services_used) <= 3
        assert result.total_duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_execute_parallel_duplicate_strategy(self, executor, mock_adapters):
        """Test parallel execution with duplicate strategy."""
        files = ["file1.py", "file2.py"]
        services = ["gemini", "qwen"]

        result = await executor.execute_parallel(
            "Analyze",
            files,
            services,
            mock_adapters,
            strategy="duplicate"
        )

        assert isinstance(result, ParallelResult)
        assert result.successful_tasks >= 0
        assert len(result.individual_results) >= 0

    @pytest.mark.asyncio
    async def test_execute_parallel_unknown_strategy(self, executor, mock_adapters):
        """Test that unknown strategy raises error."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            await executor.execute_parallel(
                "Test",
                ["file.py"],
                ["gemini"],
                mock_adapters,
                strategy="unknown"
            )

    @pytest.mark.asyncio
    async def test_execute_split_with_missing_adapter(self, executor):
        """Test split strategy with missing adapter."""
        files = ["file1.py", "file2.py"]
        services = ["gemini", "nonexistent"]
        adapters = {}

        result = await executor._execute_split_strategy(
            "Test",
            files,
            services,
            adapters
        )

        # Should handle missing adapters gracefully
        assert result.successful_tasks == 0
        assert result.failed_tasks == 0  # No tasks were created

    @pytest.mark.asyncio
    async def test_execute_parallel_limits_workers(self, executor, mock_adapters):
        """Test that parallel execution respects max_workers limit."""
        executor.max_workers = 2
        files = ["file1.py", "file2.py", "file3.py"]
        services = ["gemini", "qwen", "ollama_local"]  # 3 services

        result = await executor.execute_parallel(
            "Analyze",
            files,
            services,
            mock_adapters,
            strategy="split"
        )

        # Should only use max_workers services
        assert len(result.services_used) == 2

    @pytest.mark.asyncio
    async def test_execute_parallel_handles_service_failure(self, executor):
        """Test parallel execution when some services fail."""
        # Create adapters where one fails
        adapters = {}

        async def success_execute(*args, **kwargs):
            yield "Success"

        async def failing_execute(*args, **kwargs):
            raise Exception("Service failed")
            yield

        success_adapter = MagicMock()
        success_adapter.execute = success_execute

        failing_adapter = MagicMock()
        failing_adapter.execute = failing_execute

        adapters["gemini"] = success_adapter
        adapters["qwen"] = failing_adapter

        result = await executor.execute_parallel(
            "Test",
            ["file.py"],
            ["gemini", "qwen"],
            adapters,
            strategy="duplicate"
        )

        assert result.successful_tasks >= 1
        assert result.failed_tasks >= 1

    @pytest.mark.asyncio
    async def test_parallel_result_structure(self, executor, mock_adapters):
        """Test that ParallelResult has correct structure."""
        result = await executor.execute_parallel(
            "Test",
            ["file.py"],
            ["gemini"],
            mock_adapters,
            strategy="split"
        )

        # Verify all fields are present
        assert hasattr(result, "aggregated_text")
        assert hasattr(result, "individual_results")
        assert hasattr(result, "services_used")
        assert hasattr(result, "total_duration_seconds")
        assert hasattr(result, "successful_tasks")
        assert hasattr(result, "failed_tasks")

        # Verify types
        assert isinstance(result.aggregated_text, str)
        assert isinstance(result.individual_results, list)
        assert isinstance(result.services_used, list)
        assert isinstance(result.total_duration_seconds, float)
        assert isinstance(result.successful_tasks, int)
        assert isinstance(result.failed_tasks, int)
