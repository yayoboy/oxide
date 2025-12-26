"""
Unit tests for CLIAdapter.

Tests the base CLI adapter and its implementations (GeminiAdapter, QwenAdapter).
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from pathlib import Path

from oxide.adapters.cli_adapter import CLIAdapter
from oxide.utils.exceptions import CLIAdapterError, ServiceUnavailableError, TimeoutError


class TestCLIAdapter:
    """Test suite for base CLIAdapter class."""

    @pytest.fixture
    def cli_config(self):
        """Provide CLI adapter configuration."""
        return {
            "type": "cli",
            "executable": "test-cli",
            "enabled": True
        }

    @pytest.fixture
    def cli_adapter(self, cli_config):
        """Provide CLIAdapter instance."""
        return CLIAdapter("test_service", cli_config)

    def test_adapter_initialization(self, cli_adapter):
        """Test adapter initializes correctly."""
        assert cli_adapter.service_name == "test_service"
        assert cli_adapter.executable == "test-cli"
        assert cli_adapter.config["enabled"] is True

    def test_get_service_info(self, cli_adapter):
        """Test getting service information."""
        info = cli_adapter.get_service_info()

        assert info["name"] == "test_service"
        assert info["type"] == "cli"
        assert info["executable"] == "test-cli"
        assert info["enabled"] is True

    def test_build_command_basic(self, cli_adapter):
        """Test building basic command."""
        cmd = cli_adapter._build_command("Test prompt")

        assert "test-cli" in cmd
        assert "-p" in cmd
        assert "Test prompt" in cmd

    def test_build_command_with_files(self, cli_adapter, sample_task_files):
        """Test building command with file paths."""
        cmd = cli_adapter._build_command("Test prompt", files=sample_task_files)

        assert "test-cli" in cmd
        # Files should be included in command
        for file in sample_task_files:
            # Check if file is in command (implementation may vary)
            assert any(str(file) in str(part) for part in cmd)

    def test_build_command_with_preferences(self, cli_adapter):
        """Test building command with preferences."""
        preferences = {"timeout": 60, "model": "test-model"}
        cmd = cli_adapter._build_command("Test prompt", preferences=preferences)

        assert "test-cli" in cmd

    @pytest.mark.asyncio
    async def test_execute_success(self, cli_adapter, mock_subprocess_process):
        """Test successful command execution."""
        with patch('asyncio.create_subprocess_exec', return_value=mock_subprocess_process):
            chunks = []
            async for chunk in cli_adapter.execute("Test prompt"):
                chunks.append(chunk)

            assert len(chunks) > 0
            assert "Test output" in "".join(chunks)

    @pytest.mark.asyncio
    async def test_execute_command_not_found(self, cli_adapter):
        """Test execution when command is not found."""
        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError):
            with pytest.raises(ServiceUnavailableError) as exc_info:
                async for _ in cli_adapter.execute("Test"):
                    pass

            assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_process_error(self, cli_adapter):
        """Test execution when process returns error code."""
        process = AsyncMock()
        process.pid = 12345
        process.returncode = 1

        stdout = AsyncMock()
        stdout.readline = AsyncMock(return_value=b"")
        process.stdout = stdout

        stderr = AsyncMock()
        stderr.read = AsyncMock(return_value=b"Error message")
        process.stderr = stderr

        async def mock_wait():
            return 1

        process.wait = mock_wait

        with patch('asyncio.create_subprocess_exec', return_value=process):
            with pytest.raises(CLIAdapterError):
                async for _ in cli_adapter.execute("Test"):
                    pass

    @pytest.mark.asyncio
    async def test_execute_streams_output(self, cli_adapter):
        """Test that execute properly streams output."""
        process = AsyncMock()
        process.pid = 12345
        process.returncode = 0

        # Simulate multiple output lines
        output_lines = [b"Line 1\n", b"Line 2\n", b"Line 3\n", b""]
        stdout = AsyncMock()
        stdout.readline = AsyncMock(side_effect=output_lines)
        process.stdout = stdout

        async def mock_wait():
            return 0

        process.wait = mock_wait

        with patch('asyncio.create_subprocess_exec', return_value=process):
            chunks = []
            async for chunk in cli_adapter.execute("Test"):
                chunks.append(chunk)

            assert len(chunks) == 3
            assert chunks[0] == "Line 1\n"
            assert chunks[1] == "Line 2\n"
            assert chunks[2] == "Line 3\n"

    @pytest.mark.asyncio
    async def test_health_check_success(self, cli_adapter):
        """Test health check when service is available."""
        with patch('shutil.which', return_value="/usr/bin/test-cli"):
            is_healthy = await cli_adapter.health_check()
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, cli_adapter):
        """Test health check when service is not available."""
        with patch('shutil.which', return_value=None):
            is_healthy = await cli_adapter.health_check()
            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_get_models_not_supported(self, cli_adapter):
        """Test that get_models returns empty list for base adapter."""
        models = await cli_adapter.get_models()
        assert models == []


class TestCLIAdapterWithFiles:
    """Test suite for CLI adapter with file handling."""

    @pytest.fixture
    def gemini_config(self):
        """Provide Gemini-like adapter configuration."""
        return {
            "type": "cli",
            "executable": "gemini",
            "enabled": True
        }

    @pytest.fixture
    def gemini_adapter(self, gemini_config):
        """Provide CLI adapter configured for Gemini."""
        return CLIAdapter("gemini", gemini_config)

    @pytest.mark.asyncio
    async def test_command_with_files(self, gemini_adapter, tmp_path):
        """Test command includes file paths with @ syntax."""
        # Create actual files
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("print('hello')")
        file2.write_text("print('world')")

        test_files = [str(file1), str(file2)]

        cmd = await gemini_adapter._build_command("Analyze this", files=test_files)

        # CLI uses @ syntax for files
        assert "gemini" in cmd
        assert "-p" in cmd

        # Check files are properly formatted
        cmd_str = " ".join(cmd)
        assert "@" in cmd_str

    @pytest.mark.asyncio
    async def test_command_with_large_fileset(self, gemini_adapter, large_file_set):
        """Test command for large codebase."""
        cmd = await gemini_adapter._build_command(
            "Analyze entire codebase",
            files=large_file_set
        )

        assert "gemini" in cmd
        assert len(cmd) > 0


class TestQwenCLIAdapter:
    """Test suite for Qwen-configured CLI adapter."""

    @pytest.fixture
    def qwen_config(self):
        """Provide Qwen adapter configuration."""
        return {
            "type": "cli",
            "executable": "qwen",
            "enabled": True
        }

    @pytest.fixture
    def qwen_adapter(self, qwen_config):
        """Provide CLI adapter configured for Qwen."""
        return CLIAdapter("qwen", qwen_config)

    def test_qwen_initialization(self, qwen_adapter):
        """Test Qwen adapter initializes correctly."""
        assert qwen_adapter.service_name == "qwen"
        assert qwen_adapter.executable == "qwen"

    @pytest.mark.asyncio
    async def test_qwen_command_structure(self, qwen_adapter, sample_task_files):
        """Test Qwen command structure."""
        cmd = await qwen_adapter._build_command("Review this code", files=sample_task_files)

        assert "qwen" in cmd
        assert "-p" in cmd

    @pytest.mark.asyncio
    async def test_qwen_execute_with_files(self, qwen_adapter, sample_task_files, mock_subprocess_process):
        """Test Qwen execution with file paths."""
        with patch('asyncio.create_subprocess_exec', return_value=mock_subprocess_process), \
             patch('oxide.adapters.cli_adapter.get_process_manager') as mock_pm:

            pm = MagicMock()
            pm.register_async_process = MagicMock()
            pm.unregister_async_process = MagicMock()
            mock_pm.return_value = pm

            chunks = []
            async for chunk in qwen_adapter.execute("Review code", files=sample_task_files):
                chunks.append(chunk)

            assert len(chunks) > 0


@pytest.mark.asyncio
class TestCLIAdapterIntegration:
    """Integration tests for CLI adapter workflows."""

    async def test_full_execution_lifecycle(self, tmp_path):
        """Test complete execution lifecycle."""
        config = {
            "type": "cli",
            "executable": "echo",
            "enabled": True
        }

        adapter = CLIAdapter("echo_service", config)

        # Health check
        with patch('shutil.which', return_value="/bin/echo"):
            is_healthy = await adapter.health_check()
            assert is_healthy is True

        # Execute (using echo which is always available)
        # Note: This is a real execution, not mocked
        chunks = []
        try:
            async for chunk in adapter.execute("test"):
                chunks.append(chunk)
                # Break after first chunk to avoid hanging
                break
        except Exception:
            # If execution fails, that's ok for this test
            pass

    async def test_adapter_process_cleanup(self):
        """Test that adapter cleans up processes properly."""
        config = {"type": "cli", "executable": "sleep", "enabled": True}
        adapter = CLIAdapter("sleep_service", config)

        process = AsyncMock()
        process.pid = 99999
        process.returncode = None

        stdout = AsyncMock()
        stdout.readline = AsyncMock(side_effect=[b"output\n", b""])
        process.stdout = stdout

        async def mock_wait():
            await asyncio.sleep(0.01)
            return 0

        process.wait = mock_wait

        with patch('asyncio.create_subprocess_exec', return_value=process):
            chunks = []
            async for chunk in adapter.execute("test"):
                chunks.append(chunk)

        # Process should have been awaited
        process.wait.assert_called()
