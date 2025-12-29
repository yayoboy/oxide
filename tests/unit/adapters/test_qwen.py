"""
Unit tests for QwenAdapter.

Tests Qwen-specific configuration, service metadata, and CLI adapter inheritance.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from oxide.adapters.qwen import QwenAdapter


@pytest.fixture
def qwen_config():
    """Sample Qwen adapter configuration."""
    return {
        "enabled": True,
        "type": "cli",
        "executable": "qwen"
    }


@pytest.fixture
def qwen_adapter(qwen_config):
    """Create a QwenAdapter instance."""
    return QwenAdapter(qwen_config)


class TestQwenAdapterInit:
    """Test QwenAdapter initialization."""

    def test_init_with_config(self, qwen_config):
        """Test initialization with valid configuration."""
        adapter = QwenAdapter(qwen_config)

        assert adapter.service_name == "qwen"
        assert adapter.executable == "qwen"
        assert hasattr(adapter, 'logger')

    def test_init_sets_service_name(self, qwen_config):
        """Test that service name is correctly set to 'qwen'."""
        adapter = QwenAdapter(qwen_config)

        # Verify service name is passed to parent CLIAdapter
        assert adapter.service_name == "qwen"

    def test_init_with_custom_executable(self):
        """Test initialization with custom executable path."""
        config = {
            "enabled": True,
            "type": "cli",
            "executable": "/usr/local/bin/qwen"
        }
        adapter = QwenAdapter(config)

        assert adapter.executable == "/usr/local/bin/qwen"
        assert adapter.service_name == "qwen"

    def test_init_without_executable(self):
        """Test that initialization fails without executable."""
        config = {"enabled": True, "type": "cli"}

        with pytest.raises(Exception):  # CLIAdapterError from parent
            QwenAdapter(config)

    def test_init_logs_initialization(self, qwen_config, caplog):
        """Test that initialization is logged."""
        QwenAdapter(qwen_config)

        # Check that Qwen-specific log message was created
        assert any("Initialized Qwen adapter" in record.message
                   for record in caplog.records)


class TestGetServiceInfo:
    """Test get_service_info method."""

    def test_get_service_info_returns_dict(self, qwen_adapter):
        """Test that get_service_info returns a dictionary."""
        info = qwen_adapter.get_service_info()

        assert isinstance(info, dict)

    def test_get_service_info_includes_base_info(self, qwen_adapter):
        """Test that base CLIAdapter info is included."""
        info = qwen_adapter.get_service_info()

        # Base CLIAdapter should provide these
        assert "type" in info
        assert "executable" in info
        assert info["type"] == "cli"

    def test_get_service_info_includes_description(self, qwen_adapter):
        """Test that Qwen-specific description is included."""
        info = qwen_adapter.get_service_info()

        assert "description" in info
        assert "Qwen Code" in info["description"]
        assert "code tasks" in info["description"]

    def test_get_service_info_includes_max_context(self, qwen_adapter):
        """Test that max context tokens are specified."""
        info = qwen_adapter.get_service_info()

        assert "max_context_tokens" in info
        assert info["max_context_tokens"] == 32000

    def test_get_service_info_includes_optimal_tasks(self, qwen_adapter):
        """Test that optimal task types are specified."""
        info = qwen_adapter.get_service_info()

        assert "optimal_for" in info
        assert isinstance(info["optimal_for"], list)

        # Verify all expected task types
        expected_tasks = [
            "code_review",
            "code_generation",
            "debugging",
            "refactoring"
        ]
        for task in expected_tasks:
            assert task in info["optimal_for"]

    def test_get_service_info_optimal_tasks_order(self, qwen_adapter):
        """Test that optimal tasks are in expected order."""
        info = qwen_adapter.get_service_info()

        optimal_for = info["optimal_for"]
        assert optimal_for[0] == "code_review"
        assert optimal_for[1] == "code_generation"
        assert optimal_for[2] == "debugging"
        assert optimal_for[3] == "refactoring"

    def test_get_service_info_all_code_related(self, qwen_adapter):
        """Test that all optimal tasks are code-related."""
        info = qwen_adapter.get_service_info()

        # All tasks should contain "code" or be "debugging"/"refactoring"
        for task in info["optimal_for"]:
            assert "code" in task or task in ["debugging", "refactoring"]


class TestInheritance:
    """Test CLIAdapter inheritance."""

    def test_inherits_from_cli_adapter(self, qwen_adapter):
        """Test that QwenAdapter inherits from CLIAdapter."""
        from oxide.adapters.cli_adapter import CLIAdapter

        assert isinstance(qwen_adapter, CLIAdapter)

    def test_has_execute_method(self, qwen_adapter):
        """Test that execute method is inherited."""
        assert hasattr(qwen_adapter, 'execute')
        assert callable(qwen_adapter.execute)

    def test_has_health_check_method(self, qwen_adapter):
        """Test that health_check method is inherited."""
        assert hasattr(qwen_adapter, 'health_check')
        assert callable(qwen_adapter.health_check)

    def test_has_build_command_method(self, qwen_adapter):
        """Test that _build_command method is inherited."""
        assert hasattr(qwen_adapter, '_build_command')
        assert callable(qwen_adapter._build_command)

    def test_has_stream_output_method(self, qwen_adapter):
        """Test that _stream_output method is inherited."""
        assert hasattr(qwen_adapter, '_stream_output')
        assert callable(qwen_adapter._stream_output)


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_uses_qwen_executable(self, qwen_adapter):
        """Test that health check looks for qwen executable."""
        with patch('shutil.which', return_value='/usr/bin/qwen') as mock_which:
            result = await qwen_adapter.health_check()

            assert result is True
            mock_which.assert_called_with('qwen')

    @pytest.mark.asyncio
    async def test_health_check_qwen_not_found(self, qwen_adapter):
        """Test health check when qwen is not installed."""
        with patch('shutil.which', return_value=None):
            result = await qwen_adapter.health_check()

            assert result is False


class TestCommandBuilding:
    """Test command building for Qwen."""

    @pytest.mark.asyncio
    async def test_build_command_includes_qwen(self, qwen_adapter):
        """Test that built commands include qwen executable."""
        cmd = await qwen_adapter._build_command("Test prompt", None)

        assert isinstance(cmd, list)
        assert any('qwen' in str(part) for part in cmd)

    @pytest.mark.asyncio
    async def test_build_command_with_prompt(self, qwen_adapter):
        """Test command building with prompt."""
        prompt = "Review this code for bugs"
        cmd = await qwen_adapter._build_command(prompt, None)

        cmd_str = " ".join(cmd)
        assert "Review this code for bugs" in cmd_str or prompt in cmd

    @pytest.mark.asyncio
    async def test_build_command_with_files(self, qwen_adapter):
        """Test command building with file context."""
        files = ["test.py", "main.py"]
        cmd = await qwen_adapter._build_command("Analyze", files)

        # Should include files in some form
        cmd_str = " ".join(cmd)
        assert "test.py" in cmd_str or any("test.py" in str(part) for part in cmd)


class TestExecution:
    """Test execution functionality."""

    @pytest.mark.asyncio
    async def test_execute_with_code_review_prompt(self, qwen_adapter):
        """Test executing a code review task."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[
            b"The code looks good\n",
            b""
        ])
        mock_process.stdout = mock_stdout
        mock_process.wait = AsyncMock()

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('oxide.utils.process_manager.get_process_manager'):
                chunks = []
                async for chunk in qwen_adapter.execute("Review this code"):
                    chunks.append(chunk)

                assert len(chunks) > 0
                assert any("code" in chunk.lower() for chunk in chunks)

    @pytest.mark.asyncio
    async def test_execute_with_files(self, qwen_adapter):
        """Test executing with file context."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"Analysis\n", b""])
        mock_process.stdout = mock_stdout
        mock_process.wait = AsyncMock()

        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            with patch('oxide.utils.process_manager.get_process_manager'):
                files = ["src/main.py"]
                async for _ in qwen_adapter.execute("Analyze", files=files):
                    pass

                # Verify execution was called
                mock_exec.assert_called_once()


class TestCodeSpecialization:
    """Test Qwen's code specialization."""

    def test_optimal_for_code_tasks(self, qwen_adapter):
        """Test that Qwen is optimized for code-related tasks."""
        info = qwen_adapter.get_service_info()

        code_tasks = ["code_review", "code_generation", "debugging", "refactoring"]

        # All specified optimal tasks should be code-related
        for task in info["optimal_for"]:
            assert task in code_tasks

    def test_not_optimal_for_non_code_tasks(self, qwen_adapter):
        """Test that non-code tasks are not in optimal_for."""
        info = qwen_adapter.get_service_info()

        # These should NOT be in Qwen's optimal tasks
        non_code_tasks = [
            "summarization",
            "translation",
            "creative_writing",
            "question_answer"
        ]

        for task in non_code_tasks:
            assert task not in info["optimal_for"]

    def test_max_context_appropriate_for_code(self, qwen_adapter):
        """Test that context size is appropriate for code files."""
        info = qwen_adapter.get_service_info()

        # 32K tokens is appropriate for multiple code files
        assert info["max_context_tokens"] >= 30000
        assert info["max_context_tokens"] <= 100000


class TestConfiguration:
    """Test various configuration scenarios."""

    def test_minimal_config(self):
        """Test with minimal configuration."""
        config = {"enabled": True, "type": "cli", "executable": "qwen"}
        adapter = QwenAdapter(config)

        assert adapter.service_name == "qwen"
        assert adapter.executable == "qwen"

    def test_config_with_additional_options(self):
        """Test configuration with additional options."""
        config = {
            "enabled": True,
            "type": "cli",
            "executable": "qwen",
            "timeout": 300,
            "max_retries": 3
        }
        adapter = QwenAdapter(config)

        # Should initialize successfully
        assert adapter.service_name == "qwen"

    def test_different_executable_paths(self):
        """Test with various executable paths."""
        paths = [
            "qwen",
            "/usr/bin/qwen",
            "/usr/local/bin/qwen",
            "./qwen",
            "~/.local/bin/qwen"
        ]

        for path in paths:
            config = {"enabled": True, "type": "cli", "executable": path}
            adapter = QwenAdapter(config)
            assert adapter.executable == path


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_service_info_immutable(self, qwen_adapter):
        """Test that modifying returned service info doesn't affect adapter."""
        info1 = qwen_adapter.get_service_info()
        info1["description"] = "Modified"

        # Get info again - should be unchanged
        info2 = qwen_adapter.get_service_info()
        assert info2["description"] != "Modified"
        assert "Qwen Code" in info2["description"]

    def test_multiple_instances(self, qwen_config):
        """Test creating multiple QwenAdapter instances."""
        adapter1 = QwenAdapter(qwen_config)
        adapter2 = QwenAdapter(qwen_config)

        # Should be separate instances
        assert adapter1 is not adapter2

        # But have same configuration
        assert adapter1.service_name == adapter2.service_name
        assert adapter1.executable == adapter2.executable

    def test_get_service_info_called_multiple_times(self, qwen_adapter):
        """Test that get_service_info can be called multiple times."""
        info1 = qwen_adapter.get_service_info()
        info2 = qwen_adapter.get_service_info()
        info3 = qwen_adapter.get_service_info()

        # All should have same content
        assert info1 == info2 == info3
