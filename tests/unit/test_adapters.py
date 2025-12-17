"""
Unit tests for Adapters.
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from oxide.adapters.base import BaseAdapter
from oxide.adapters.cli_adapter import CLIAdapter
from oxide.adapters.gemini import GeminiAdapter
from oxide.adapters.qwen import QwenAdapter
from oxide.utils.exceptions import CLIAdapterError, ServiceUnavailableError


class TestCLIAdapter:
    """Test suite for CLIAdapter."""

    @pytest.fixture
    def cli_config(self):
        """Create CLI adapter configuration."""
        return {
            "type": "cli",
            "enabled": True,
            "executable": "test-cli"
        }

    def test_cli_adapter_initialization(self, cli_config):
        """Test CLI adapter initialization."""
        adapter = CLIAdapter("test_service", cli_config)

        assert adapter.service_name == "test_service"
        assert adapter.executable == "test-cli"

    def test_cli_adapter_missing_executable(self):
        """Test that missing executable raises error."""
        config = {"type": "cli", "enabled": True}

        with pytest.raises(CLIAdapterError, match="No executable specified"):
            CLIAdapter("test_service", config)

    @pytest.mark.asyncio
    async def test_build_command_no_files(self, cli_config):
        """Test command building without files."""
        adapter = CLIAdapter("test_service", cli_config)

        cmd = await adapter._build_command("test prompt")

        assert cmd == ["test-cli", "-p", "test prompt"]

    @pytest.mark.asyncio
    async def test_build_command_with_files(self, cli_config, tmp_path):
        """Test command building with files."""
        adapter = CLIAdapter("test_service", cli_config)

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        cmd = await adapter._build_command("analyze", files=[str(test_file)])

        assert cmd[0] == "test-cli"
        assert cmd[1] == "-p"
        assert f"@{test_file}" in cmd[2]
        assert "analyze" in cmd[2]

    @pytest.mark.asyncio
    async def test_build_command_skips_nonexistent_files(self, cli_config):
        """Test that nonexistent files are skipped."""
        adapter = CLIAdapter("test_service", cli_config)

        cmd = await adapter._build_command("test", files=["/nonexistent/file.py"])

        # Should not include the nonexistent file
        assert "@/nonexistent/file.py" not in cmd[2]

    @pytest.mark.asyncio
    async def test_health_check_success(self, cli_config):
        """Test successful health check."""
        adapter = CLIAdapter("test_service", cli_config)

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            # Mock successful process
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process

            result = await adapter.health_check()

            assert result is True
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_executable_not_found(self, cli_config):
        """Test health check when executable is not found."""
        adapter = CLIAdapter("test_service", cli_config)

        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError):
            result = await adapter.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_execute_file_not_found(self, cli_config):
        """Test execute raises ServiceUnavailableError when executable not found."""
        adapter = CLIAdapter("test_service", cli_config)

        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError):
            with pytest.raises(ServiceUnavailableError, match="not found in PATH"):
                async for _ in adapter.execute("test prompt"):
                    pass


class TestGeminiAdapter:
    """Test suite for GeminiAdapter."""

    @pytest.fixture
    def gemini_config(self):
        """Create Gemini adapter configuration."""
        return {
            "type": "cli",
            "enabled": True,
            "executable": "gemini"
        }

    def test_gemini_adapter_initialization(self, gemini_config):
        """Test Gemini adapter initialization."""
        adapter = GeminiAdapter(gemini_config)

        assert adapter.service_name == "gemini"
        assert adapter.executable == "gemini"

    def test_gemini_service_info(self, gemini_config):
        """Test Gemini service info."""
        adapter = GeminiAdapter(gemini_config)

        info = adapter.get_service_info()

        assert info["name"] == "gemini"
        assert info["max_context_tokens"] == 2000000
        assert "codebase_analysis" in info["optimal_for"]


class TestQwenAdapter:
    """Test suite for QwenAdapter."""

    @pytest.fixture
    def qwen_config(self):
        """Create Qwen adapter configuration."""
        return {
            "type": "cli",
            "enabled": True,
            "executable": "qwen"
        }

    def test_qwen_adapter_initialization(self, qwen_config):
        """Test Qwen adapter initialization."""
        adapter = QwenAdapter(qwen_config)

        assert adapter.service_name == "qwen"
        assert adapter.executable == "qwen"

    def test_qwen_service_info(self, qwen_config):
        """Test Qwen service info."""
        adapter = QwenAdapter(qwen_config)

        info = adapter.get_service_info()

        assert info["name"] == "qwen"
        assert "code_review" in info["optimal_for"]


class TestBaseAdapter:
    """Test suite for BaseAdapter interface."""

    def test_base_adapter_initialization(self):
        """Test that BaseAdapter cannot be instantiated directly."""
        # BaseAdapter is abstract, need concrete implementation
        class ConcreteAdapter(BaseAdapter):
            async def execute(self, prompt, files=None, **kwargs):
                yield "test"

            async def health_check(self):
                return True

        config = {"type": "test", "enabled": True}
        adapter = ConcreteAdapter("test_service", config)

        assert adapter.service_name == "test_service"
        assert adapter.config == config

    def test_get_service_info(self):
        """Test get_service_info method."""
        class ConcreteAdapter(BaseAdapter):
            async def execute(self, prompt, files=None, **kwargs):
                yield "test"

            async def health_check(self):
                return True

        config = {"type": "test", "enabled": True}
        adapter = ConcreteAdapter("test_service", config)

        info = adapter.get_service_info()

        assert info["name"] == "test_service"
        assert info["type"] == "test"
        assert info["enabled"] is True
        assert info["adapter_class"] == "ConcreteAdapter"

    @pytest.mark.asyncio
    async def test_get_models_default(self):
        """Test default get_models returns empty list."""
        class ConcreteAdapter(BaseAdapter):
            async def execute(self, prompt, files=None, **kwargs):
                yield "test"

            async def health_check(self):
                return True

        config = {"type": "test", "enabled": True}
        adapter = ConcreteAdapter("test_service", config)

        models = await adapter.get_models()

        assert models == []

    def test_adapter_repr(self):
        """Test adapter string representation."""
        class ConcreteAdapter(BaseAdapter):
            async def execute(self, prompt, files=None, **kwargs):
                yield "test"

            async def health_check(self):
                return True

        config = {"type": "test", "enabled": True}
        adapter = ConcreteAdapter("test_service", config)

        assert repr(adapter) == "ConcreteAdapter(service='test_service')"
