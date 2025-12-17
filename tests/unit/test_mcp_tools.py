"""
Unit tests for MCP Tools.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from mcp.types import TextContent

from oxide.mcp.tools import OxideTools
from oxide.execution.parallel import ParallelResult


class TestOxideTools:
    """Test suite for OxideTools."""

    @pytest.fixture
    def mock_orchestrator(self, mock_config):
        """Create a mock orchestrator."""
        orch = MagicMock()
        orch.config = mock_config
        orch.adapters = {}
        orch.execute_task = AsyncMock()
        orch.get_service_status = AsyncMock()
        orch.get_routing_rules = MagicMock()
        return orch

    @pytest.fixture
    def tools(self, mock_orchestrator):
        """Create an OxideTools instance."""
        return OxideTools(mock_orchestrator)

    def test_tools_initialization(self, mock_orchestrator):
        """Test tools initialization."""
        tools = OxideTools(mock_orchestrator)

        assert tools.orchestrator == mock_orchestrator
        assert tools.parallel_executor is not None
        assert tools.logger is not None

    @pytest.mark.asyncio
    async def test_route_task_success(self, tools, mock_orchestrator):
        """Test successful route_task execution."""
        # Mock orchestrator to yield chunks
        async def mock_execute(*args, **kwargs):
            yield "Hello "
            yield "World"

        mock_orchestrator.execute_task = mock_execute

        results = []
        async for result in tools.route_task("Test prompt"):
            results.append(result)

        # Should yield TextContent chunks
        assert len(results) == 2
        assert all(isinstance(r, TextContent) for r in results)
        assert results[0].text == "Hello "
        assert results[1].text == "World"

    @pytest.mark.asyncio
    async def test_route_task_with_files(self, tools, mock_orchestrator, tmp_path):
        """Test route_task with file validation."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        async def mock_execute(*args, **kwargs):
            yield "Response"

        mock_orchestrator.execute_task = mock_execute

        results = []
        async for result in tools.route_task("Test", files=[str(test_file)]):
            results.append(result)

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_route_task_with_nonexistent_file(self, tools, mock_orchestrator):
        """Test route_task with nonexistent file shows warning."""
        async def mock_execute(*args, **kwargs):
            yield "Response"

        mock_orchestrator.execute_task = mock_execute

        results = []
        async for result in tools.route_task("Test", files=["/nonexistent/file.py"]):
            results.append(result)

        # Should yield warning about missing file
        warnings = [r for r in results if "Warning" in r.text or "⚠️" in r.text]
        assert len(warnings) > 0

    @pytest.mark.asyncio
    async def test_route_task_handles_error(self, tools, mock_orchestrator):
        """Test route_task handles execution errors."""
        async def mock_execute(*args, **kwargs):
            raise Exception("Execution failed")
            yield

        mock_orchestrator.execute_task = mock_execute

        results = []
        async for result in tools.route_task("Test"):
            results.append(result)

        # Should yield error message
        assert len(results) > 0
        error_texts = [r.text for r in results]
        assert any("Error" in text or "❌" in text for text in error_texts)

    @pytest.mark.asyncio
    async def test_analyze_parallel_success(self, tools, mock_orchestrator, tmp_path):
        """Test successful parallel analysis."""
        # Create test directory with files
        (tmp_path / "file1.py").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")

        # Mock config to have get_enabled_services method
        mock_config = MagicMock()
        mock_config.get_enabled_services.return_value = ["gemini", "qwen"]
        mock_config.execution = MagicMock()
        mock_config.execution.max_parallel_workers = 3
        mock_orchestrator.config = mock_config

        # Mock parallel execution result
        with patch.object(tools.parallel_executor, 'execute_parallel') as mock_exec:
            mock_exec.return_value = ParallelResult(
                aggregated_text="Parallel results",
                individual_results=[],
                services_used=["gemini", "qwen"],
                total_duration_seconds=1.5,
                successful_tasks=2,
                failed_tasks=0
            )

            results = []
            async for result in tools.analyze_parallel(str(tmp_path), "Analyze"):
                results.append(result)

            # Should yield multiple messages
            assert len(results) > 0
            text_combined = "".join(r.text for r in results)

            assert "Found" in text_combined  # File discovery message
            assert "Using" in text_combined  # Services message
            assert "completed" in text_combined  # Completion message

    @pytest.mark.asyncio
    async def test_analyze_parallel_directory_not_found(self, tools):
        """Test analyze_parallel with nonexistent directory."""
        results = []
        async for result in tools.analyze_parallel("/nonexistent/dir", "Analyze"):
            results.append(result)

        # Should yield error about directory not found
        assert len(results) > 0
        assert any("not found" in r.text for r in results)

    @pytest.mark.asyncio
    async def test_analyze_parallel_not_a_directory(self, tools, tmp_path):
        """Test analyze_parallel with file instead of directory."""
        test_file = tmp_path / "not_a_dir.txt"
        test_file.write_text("content")

        results = []
        async for result in tools.analyze_parallel(str(test_file), "Analyze"):
            results.append(result)

        # Should yield error about not being a directory
        assert len(results) > 0
        assert any("Not a directory" in r.text for r in results)

    @pytest.mark.asyncio
    async def test_analyze_parallel_no_files_found(self, tools, tmp_path):
        """Test analyze_parallel when no files found."""
        # Create empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        results = []
        async for result in tools.analyze_parallel(str(empty_dir), "Analyze"):
            results.append(result)

        # Should yield warning about no files
        assert len(results) > 0
        assert any("No files found" in r.text for r in results)

    @pytest.mark.asyncio
    async def test_analyze_parallel_handles_error(self, tools, mock_orchestrator, tmp_path):
        """Test analyze_parallel handles errors gracefully."""
        (tmp_path / "file.py").write_text("content")

        # Mock config to have get_enabled_services method
        mock_config = MagicMock()
        mock_config.get_enabled_services.return_value = ["gemini"]
        mock_config.execution = MagicMock()
        mock_config.execution.max_parallel_workers = 3
        mock_orchestrator.config = mock_config

        # Mock parallel executor to raise error
        with patch.object(tools.parallel_executor, 'execute_parallel') as mock_exec:
            mock_exec.side_effect = Exception("Parallel execution failed")

            results = []
            async for result in tools.analyze_parallel(str(tmp_path), "Analyze"):
                results.append(result)

            # Should yield error message
            error_texts = [r.text for r in results]
            assert any("Error" in text for text in error_texts)

    @pytest.mark.asyncio
    async def test_list_services_success(self, tools, mock_orchestrator):
        """Test successful list_services call."""
        # Mock service status
        mock_orchestrator.get_service_status.return_value = {
            "gemini": {
                "enabled": True,
                "healthy": True,
                "info": {
                    "type": "cli",
                    "description": "Google Gemini"
                }
            },
            "qwen": {
                "enabled": True,
                "healthy": False,
                "info": {
                    "type": "cli"
                }
            }
        }

        # Mock routing rules
        mock_orchestrator.get_routing_rules.return_value = {
            "code_review": {
                "primary": "qwen",
                "fallback": ["gemini"]
            }
        }

        results = []
        async for result in tools.list_services():
            results.append(result)

        # Should yield service information
        assert len(results) > 0
        text_combined = "".join(r.text for r in results)

        assert "gemini" in text_combined
        assert "qwen" in text_combined
        assert "Routing Rules" in text_combined

    @pytest.mark.asyncio
    async def test_list_services_handles_error(self, tools, mock_orchestrator):
        """Test list_services handles errors."""
        mock_orchestrator.get_service_status.side_effect = Exception("Status error")

        results = []
        async for result in tools.list_services():
            results.append(result)

        # Should yield error message
        assert len(results) > 0
        assert any("Error" in r.text for r in results)

    def test_discover_files_finds_source_files(self, tools, tmp_path):
        """Test file discovery finds source files."""
        # Create various files
        (tmp_path / "file1.py").write_text("python")
        (tmp_path / "file2.js").write_text("javascript")
        (tmp_path / "readme.md").write_text("markdown")
        (tmp_path / "binary.exe").write_text("binary")  # Should be skipped

        files = tools._discover_files(tmp_path)

        # Should find .py, .js, .md but not .exe
        assert len(files) == 3
        assert any("file1.py" in f for f in files)
        assert any("file2.js" in f for f in files)
        assert any("readme.md" in f for f in files)
        assert not any(".exe" in f for f in files)

    def test_discover_files_skips_common_dirs(self, tools, tmp_path):
        """Test file discovery skips common non-source directories."""
        # Create files in directories that should be skipped
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.js").write_text("should skip")

        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("should skip")

        # Create file in valid location
        (tmp_path / "valid.py").write_text("should find")

        files = tools._discover_files(tmp_path)

        # Should only find valid.py
        assert len(files) == 1
        assert "valid.py" in files[0]
        assert not any("node_modules" in f for f in files)
        assert not any(".git" in f for f in files)

    def test_discover_files_respects_max_limit(self, tools, tmp_path):
        """Test file discovery respects max_files limit."""
        # Create many files
        for i in range(20):
            (tmp_path / f"file{i}.py").write_text(f"content{i}")

        files = tools._discover_files(tmp_path, max_files=10)

        # Should stop at max_files
        assert len(files) == 10

    def test_discover_files_handles_nested_directories(self, tools, tmp_path):
        """Test file discovery handles nested directories."""
        # Create nested structure
        subdir = tmp_path / "src" / "components"
        subdir.mkdir(parents=True)

        (tmp_path / "root.py").write_text("root")
        (tmp_path / "src" / "main.py").write_text("src")
        (subdir / "component.py").write_text("nested")

        files = tools._discover_files(tmp_path)

        # Should find all nested files
        assert len(files) == 3
        assert any("root.py" in f for f in files)
        assert any("main.py" in f for f in files)
        assert any("component.py" in f for f in files)

    def test_discover_files_handles_error_gracefully(self, tools, mock_orchestrator):
        """Test file discovery handles errors gracefully."""
        # Create a path object that will raise error
        invalid_path = Path("/proc/invalid_path_that_doesnt_exist")

        # Should not crash, just return empty list
        files = tools._discover_files(invalid_path)
        assert isinstance(files, list)

    @pytest.mark.asyncio
    async def test_route_task_with_preferences(self, tools, mock_orchestrator):
        """Test route_task passes preferences to orchestrator."""
        async def mock_execute(prompt, files, preferences):
            assert preferences == {"prefer_local": True}
            yield "Response"

        mock_orchestrator.execute_task = mock_execute

        results = []
        async for result in tools.route_task(
            "Test",
            preferences={"prefer_local": True}
        ):
            results.append(result)

        assert len(results) > 0
