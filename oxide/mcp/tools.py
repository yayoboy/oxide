"""
MCP tool definitions for Oxide.

Exposes Oxide functionality as tools that Claude can invoke.
"""
from typing import List, Optional, Dict, Any
from pathlib import Path

from mcp.types import TextContent

from ..core.orchestrator import Orchestrator
from ..execution.parallel import ParallelExecutor
from ..utils.logging import logger


class OxideTools:
    """
    MCP tools for Oxide LLM orchestration.

    Provides tools that Claude can use to route tasks intelligently
    across multiple LLM services.
    """

    def __init__(self, orchestrator: Orchestrator):
        """
        Initialize tools with orchestrator instance.

        Args:
            orchestrator: Oxide orchestrator instance
        """
        self.orchestrator = orchestrator
        self.parallel_executor = ParallelExecutor(
            max_workers=orchestrator.config.execution.max_parallel_workers
        )
        self.logger = logger.getChild("tools")

    async def route_task(
        self,
        prompt: str,
        files: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[TextContent]:
        """
        Intelligently route a task to the best LLM.

        This tool analyzes the task and automatically selects the most
        appropriate LLM service based on task characteristics.

        Args:
            prompt: Task description or query
            files: Optional list of file paths to include as context
            preferences: Optional routing preferences (e.g., prefer_local=true)

        Returns:
            List of TextContent chunks with the response
        """
        self.logger.info(f"route_task called with {len(files) if files else 0} files")

        try:
            # Validate files exist
            if files:
                validated_files = []
                for file_path in files:
                    path = Path(file_path).expanduser().resolve()
                    if path.exists():
                        validated_files.append(str(path))
                    else:
                        yield TextContent(
                            type="text",
                            text=f"⚠️ Warning: File not found: {file_path}\n\n"
                        )
                files = validated_files

            # Stream results
            buffer = ""
            async for chunk in self.orchestrator.execute_task(prompt, files, preferences):
                buffer += chunk
                # Yield chunks as they arrive
                yield TextContent(type="text", text=chunk)

            self.logger.info(f"route_task completed: {len(buffer)} chars")

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}\n"
            self.logger.error(f"route_task failed: {e}")
            yield TextContent(type="text", text=error_msg)

    async def analyze_parallel(
        self,
        directory: str,
        prompt: str,
        num_workers: Optional[int] = None
    ) -> List[TextContent]:
        """
        Analyze large codebase in parallel across multiple LLMs.

        Distributes files across multiple LLM services for faster analysis
        of large codebases.

        Args:
            directory: Directory to analyze
            prompt: Analysis prompt/query
            num_workers: Number of parallel workers (default: config max_parallel_workers)

        Returns:
            List of TextContent chunks with aggregated results
        """
        self.logger.info(f"analyze_parallel called for directory: {directory}")

        try:
            # Discover files in directory
            dir_path = Path(directory).expanduser().resolve()
            if not dir_path.exists():
                yield TextContent(
                    type="text",
                    text=f"❌ Error: Directory not found: {directory}\n"
                )
                return

            if not dir_path.is_dir():
                yield TextContent(
                    type="text",
                    text=f"❌ Error: Not a directory: {directory}\n"
                )
                return

            # Find files (exclude common non-source files)
            files = self._discover_files(dir_path)

            if not files:
                yield TextContent(
                    type="text",
                    text=f"⚠️ No files found in {directory}\n"
                )
                return

            yield TextContent(
                type="text",
                text=f"📁 Found {len(files)} files in {directory}\n\n"
            )

            # Determine services to use
            num_workers = num_workers or self.orchestrator.config.execution.max_parallel_workers
            enabled_services = self.orchestrator.config.get_enabled_services()
            services_to_use = enabled_services[:num_workers]

            yield TextContent(
                type="text",
                text=f"🔄 Using {len(services_to_use)} services: {', '.join(services_to_use)}\n\n"
            )

            # Execute in parallel
            result = await self.parallel_executor.execute_parallel(
                prompt=prompt,
                files=files,
                services=services_to_use,
                adapters=self.orchestrator.adapters,
                strategy="split"
            )

            # Yield results
            yield TextContent(
                type="text",
                text=f"✅ Parallel execution completed in {result.total_duration_seconds:.2f}s\n"
                f"   Successful: {result.successful_tasks}, Failed: {result.failed_tasks}\n\n"
            )

            yield TextContent(
                type="text",
                text=result.aggregated_text
            )

        except Exception as e:
            error_msg = f"❌ Error during parallel analysis: {str(e)}\n"
            self.logger.error(f"analyze_parallel failed: {e}")
            yield TextContent(type="text", text=error_msg)

    async def list_services(self) -> List[TextContent]:
        """
        Check health and availability of all configured LLM services.

        Returns status information for all services including health checks.

        Returns:
            List of TextContent with service status
        """
        self.logger.info("list_services called")

        try:
            yield TextContent(
                type="text",
                text="🔍 Checking Oxide LLM services...\n\n"
            )

            # Get service status
            status = await self.orchestrator.get_service_status()

            # Format output
            output = "## Oxide Service Status\n\n"

            for service_name, service_info in status.items():
                enabled = service_info.get("enabled", False)
                healthy = service_info.get("healthy", False)
                info = service_info.get("info", {})

                # Status indicator
                if enabled and healthy:
                    indicator = "✅"
                elif enabled:
                    indicator = "⚠️"
                else:
                    indicator = "❌"

                output += f"{indicator} **{service_name}**"
                output += f" ({info.get('type', 'unknown')})\n"

                if "description" in info:
                    output += f"   {info['description']}\n"

                if "base_url" in info:
                    output += f"   URL: {info['base_url']}\n"

                output += f"   Status: {'Healthy' if healthy else 'Unavailable'}\n"
                output += "\n"

            # Add routing rules summary
            output += "## Routing Rules\n\n"
            rules = self.orchestrator.get_routing_rules()

            for task_type, rule in rules.items():
                output += f"**{task_type}**: {rule['primary']}"
                if rule['fallback']:
                    output += f" (fallback: {', '.join(rule['fallback'])})"
                output += "\n"

            yield TextContent(type="text", text=output)

        except Exception as e:
            error_msg = f"❌ Error listing services: {str(e)}\n"
            self.logger.error(f"list_services failed: {e}")
            yield TextContent(type="text", text=error_msg)

    def _discover_files(self, directory: Path, max_files: int = 1000) -> List[str]:
        """
        Discover source files in directory.

        Args:
            directory: Directory to search
            max_files: Maximum files to return

        Returns:
            List of file paths
        """
        # Common source file extensions
        extensions = {
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".java", ".cpp", ".c", ".h", ".hpp",
            ".go", ".rs", ".rb", ".php",
            ".swift", ".kt", ".scala",
            ".sql", ".yaml", ".yml", ".json",
            ".md", ".txt"
        }

        # Directories to skip
        skip_dirs = {
            ".git", ".svn", "__pycache__", "node_modules",
            ".venv", "venv", "build", "dist",
            ".next", ".cache", "target"
        }

        files = []

        try:
            for item in directory.rglob("*"):
                # Skip directories in skip list
                if any(skip in item.parts for skip in skip_dirs):
                    continue

                # Check if file has valid extension
                if item.is_file() and item.suffix in extensions:
                    files.append(str(item))

                    if len(files) >= max_files:
                        break

        except Exception as e:
            self.logger.warning(f"Error discovering files: {e}")

        return files
