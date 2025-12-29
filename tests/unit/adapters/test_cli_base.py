"""
Unit tests for CLIAdapter base class.

Tests subprocess management, command building, output streaming.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from oxide.adapters.cli_adapter import CLIAdapter
from oxide.utils.exceptions import CLIAdapterError, TimeoutError, ServiceUnavailableError


@pytest.fixture
def cli_config():
    """Sample CLI adapter configuration."""
    return {
        "enabled": True,
        "type": "cli",
        "executable": "test-cli"
    }


@pytest.fixture
def cli_adapter(cli_config):
    """Create a CLIAdapter instance."""
    return CLIAdapter("test_service", cli_config)


class TestCLIAdapterInit:
    """Test CLIAdapter initialization."""

    def test_init_with_executable(self, cli_config):
        """Test initialization with valid executable."""
        adapter = CLIAdapter("test", cli_config)
        assert adapter.service_name == "test"
        assert adapter.executable == "test-cli"

    def test_init_without_executable(self):
        """Test initialization fails without executable."""
        config = {"enabled": True, "type": "cli"}
        with pytest.raises(CLIAdapterError, match="No executable"):
            CLIAdapter("test", config)

    def test_init_has_logger(self, cli_adapter):
        """Test that adapter has logger."""
        assert hasattr(cli_adapter, 'logger')


class TestCommandBuilding:
    """Test command construction."""

    @pytest.mark.asyncio
    async def test_build_command_prompt_only(self, cli_adapter):
        """Test building command with prompt only."""
        cmd = await cli_adapter._build_command("Test prompt", None)

        assert isinstance(cmd, list)
        assert cli_adapter.executable in cmd
        assert "Test prompt" in " ".join(cmd)

    @pytest.mark.asyncio
    async def test_build_command_with_files(self, cli_adapter):
        """Test building command with files."""
        files = ["file1.py", "file2.py"]
        cmd = await cli_adapter._build_command("Test", files)

        # Should include files
        cmd_str = " ".join(cmd)
        assert "file1.py" in cmd_str or "@file1.py" in cmd_str

    @pytest.mark.asyncio
    async def test_build_command_escapes_special_chars(self, cli_adapter):
        """Test that special characters are properly escaped."""
        prompt = "Test with 'quotes' and \"double quotes\""
        cmd = await cli_adapter._build_command(prompt, None)

        # Command should be properly constructed
        assert isinstance(cmd, list)
        assert len(cmd) > 0


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_executable_exists(self, cli_adapter):
        """Test health check when executable exists."""
        with patch('shutil.which', return_value='/usr/bin/test-cli'):
            result = await cli_adapter.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_executable_not_found(self, cli_adapter):
        """Test health check when executable not found."""
        with patch('shutil.which', return_value=None):
            result = await cli_adapter.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_with_version_command(self, cli_adapter):
        """Test health check by running version command."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"v1.0", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('shutil.which', return_value='/usr/bin/test-cli'):
                result = await cli_adapter.health_check()
                assert result is True


class TestOutputStreaming:
    """Test output streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_output_success(self, cli_adapter):
        """Test successful output streaming."""
        mock_process = MagicMock()
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[
            b"Line 1\n",
            b"Line 2\n",
            b""  # EOF
        ])
        mock_process.stdout = mock_stdout

        chunks = []
        async for chunk in cli_adapter._stream_output(mock_process, timeout=None):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert "Line 1" in chunks[0]
        assert "Line 2" in chunks[1]

    @pytest.mark.asyncio
    async def test_stream_output_with_timeout(self, cli_adapter):
        """Test streaming with timeout."""
        mock_process = MagicMock()
        mock_stdout = AsyncMock()

        async def slow_read():
            await asyncio.sleep(10)  # Simulate slow read
            return b""

        mock_stdout.readline = slow_read
        mock_process.stdout = mock_stdout

        with pytest.raises(asyncio.TimeoutError):
            async for _ in cli_adapter._stream_output(mock_process, timeout=1):
                pass

    @pytest.mark.asyncio
    async def test_stream_output_empty(self, cli_adapter):
        """Test streaming with no output."""
        mock_process = MagicMock()
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(return_value=b"")
        mock_process.stdout = mock_stdout

        chunks = []
        async for chunk in cli_adapter._stream_output(mock_process, timeout=None):
            chunks.append(chunk)

        assert len(chunks) == 0


class TestExecute:
    """Test execute method."""

    @pytest.mark.asyncio
    async def test_execute_success(self, cli_adapter):
        """Test successful execution."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"Response\n", b""])
        mock_process.stdout = mock_stdout
        mock_process.wait = AsyncMock()

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('oxide.utils.process_manager.get_process_manager'):
                chunks = []
                async for chunk in cli_adapter.execute("Test prompt"):
                    chunks.append(chunk)

                assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_execute_file_not_found(self, cli_adapter):
        """Test execution when executable not found."""
        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError):
            with patch('oxide.utils.process_manager.get_process_manager'):
                with pytest.raises(ServiceUnavailableError):
                    async for _ in cli_adapter.execute("Test"):
                        pass

    @pytest.mark.asyncio
    async def test_execute_command_failure(self, cli_adapter):
        """Test execution when command fails."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_stderr = AsyncMock()
        mock_stderr.read = AsyncMock(return_value=b"Error occurred")
        mock_process.stderr = mock_stderr
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(return_value=b"")
        mock_process.stdout = mock_stdout
        mock_process.wait = AsyncMock()

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('oxide.utils.process_manager.get_process_manager'):
                with pytest.raises(CLIAdapterError, match="exit code 1"):
                    async for _ in cli_adapter.execute("Test"):
                        pass

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, cli_adapter):
        """Test execution with timeout."""
        mock_process = MagicMock()
        mock_process.kill = Mock()
        mock_process.wait = AsyncMock()
        mock_stdout = AsyncMock()

        async def slow_read():
            await asyncio.sleep(10)
            return b""

        mock_stdout.readline = slow_read
        mock_process.stdout = mock_stdout

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('oxide.utils.process_manager.get_process_manager'):
                with pytest.raises(TimeoutError):
                    async for _ in cli_adapter.execute("Test", timeout=1):
                        pass

    @pytest.mark.asyncio
    async def test_execute_with_files(self, cli_adapter):
        """Test execution with file context."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_stdout = AsyncMock()
        mock_stdout.readline = AsyncMock(side_effect=[b"Response\n", b""])
        mock_process.stdout = mock_stdout
        mock_process.wait = AsyncMock()

        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            with patch('oxide.utils.process_manager.get_process_manager'):
                files = ["file1.py", "file2.py"]
                async for _ in cli_adapter.execute("Test", files=files):
                    pass

                # Verify command was built with files
                mock_exec.assert_called_once()


class TestGetInfo:
    """Test get_info method."""

    @pytest.mark.asyncio
    async def test_get_info_returns_dict(self, cli_adapter):
        """Test that get_info returns expected structure."""
        info = await cli_adapter.get_info()

        assert isinstance(info, dict)
        assert "type" in info
        assert "executable" in info
        assert info["type"] == "cli"
        assert info["executable"] == "test-cli"

    @pytest.mark.asyncio
    async def test_get_info_includes_service_name(self, cli_adapter):
        """Test that get_info includes service name."""
        info = await cli_adapter.get_info()

        assert "service" in info or "name" in info
