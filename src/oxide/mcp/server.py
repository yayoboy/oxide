"""
MCP Server for Oxide.

Exposes Oxide functionality via Model Context Protocol for Claude Code integration.
"""
import asyncio
import sys
import os
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..core.orchestrator import Orchestrator
from ..config.loader import load_config
from ..utils.logging import logger, setup_logging
from ..utils.process_manager import get_process_manager
from .tools import OxideTools


# Create MCP server
mcp = FastMCP("oxide")


# Global orchestrator and tools instances
orchestrator: Orchestrator = None
oxide_tools: OxideTools = None
web_process: subprocess.Popen = None


def start_web_ui():
    """Start Web UI backend if enabled via environment variable."""
    global web_process

    # Check if auto-start is enabled
    if os.environ.get("OXIDE_AUTO_START_WEB", "").lower() in ("true", "1", "yes"):
        logger.info("Auto-starting Web UI backend...")

        try:
            # Start web backend as subprocess
            web_process = subprocess.Popen(
                [
                    sys.executable, "-m", "uvicorn",
                    "oxide.web.backend.main:app",
                    "--host", "0.0.0.0",
                    "--port", "8000",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Register process for automatic cleanup
            process_manager = get_process_manager()
            process_manager.register_sync_process(web_process)

            logger.info(f"Web UI backend started (PID: {web_process.pid})")
            logger.info("🌐 Web UI started at http://localhost:8000")

        except Exception as e:
            logger.error(f"Failed to start Web UI: {e}")


def stop_web_ui():
    """Stop Web UI backend if running."""
    global web_process

    if web_process and web_process.poll() is None:
        logger.info("Stopping Web UI backend...")

        # Unregister from process manager (we're handling it manually here)
        process_manager = get_process_manager()
        process_manager.unregister_sync_process(web_process)

        # Clean up manually
        web_process.terminate()
        try:
            web_process.wait(timeout=5)
            logger.info("Web UI backend stopped")
        except subprocess.TimeoutExpired:
            web_process.kill()
            logger.warning("Web UI backend force killed")


def initialize():
    """Initialize Oxide orchestrator and tools."""
    global orchestrator, oxide_tools

    logger.info("Initializing Oxide MCP Server")

    try:
        # Initialize process manager (sets up signal handlers)
        process_manager = get_process_manager()
        logger.info("✓ Process manager initialized (signal handlers active)")

        # Load configuration
        config = load_config()

        # Setup logging
        setup_logging(
            level=config.logging.level,
            log_file=config.logging.file,
            console=config.logging.console
        )

        # Initialize path validator with configured allowed directories
        from ..utils.path_validator import init_path_validator
        if config.security.path_validation_enabled:
            init_path_validator(allowed_dirs=config.security.allowed_directories)
            logger.info("✓ Path validator initialized with security whitelist")
        else:
            logger.warning("⚠️ Path validation DISABLED - use only for testing!")

        # Initialize orchestrator
        orchestrator = Orchestrator(config)

        # Initialize tools
        oxide_tools = OxideTools(orchestrator)

        logger.info("Oxide MCP Server initialized successfully")

        # Auto-start Web UI if enabled
        start_web_ui()

    except Exception as e:
        logger.error(f"Failed to initialize Oxide: {e}")
        sys.exit(1)


# Define MCP tools
@mcp.tool()
async def route_task(
    prompt: str,
    files: list[str] | None = None,
    preferences: dict | None = None
) -> str:
    """
    Intelligently route a task to the best LLM.

    Analyzes the task characteristics and automatically selects the most
    appropriate LLM service (Gemini for large codebases, Qwen for code review, etc.).

    Args:
        prompt: Task description or query
        files: Optional list of file paths to include as context
        preferences: Optional routing preferences
    """
    result_parts = []
    async for content in oxide_tools.route_task(prompt, files, preferences):
        result_parts.append(content.text)
    return "".join(result_parts)


@mcp.tool()
async def analyze_parallel(
    directory: str,
    prompt: str,
    num_workers: int | None = None
) -> str:
    """
    Analyze large codebase in parallel across multiple LLMs.

    Distributes files across multiple LLM services for faster analysis.
    Ideal for analyzing large codebases with 20+ files.

    Args:
        directory: Directory path to analyze
        prompt: Analysis prompt/query
        num_workers: Number of parallel workers (default: 3)
    """
    result_parts = []
    async for content in oxide_tools.analyze_parallel(directory, prompt, num_workers):
        result_parts.append(content.text)
    return "".join(result_parts)


@mcp.tool()
async def list_services() -> str:
    """
    Check health and availability of all configured LLM services.

    Returns status information for all services including:
    - Service health (available/unavailable)
    - Service type (CLI/HTTP)
    - Routing rules configuration
    """
    result_parts = []
    async for content in oxide_tools.list_services():
        result_parts.append(content.text)
    return "".join(result_parts)


def main():
    """
    Main entry point for Oxide MCP server.

    This function is called when running: uv run oxide-mcp
    """
    # Initialize Oxide before running the server
    logger.info("🔬 Oxide LLM Orchestrator")
    logger.info("Starting MCP server...")

    try:
        # Initialize Oxide
        initialize()

        # Run MCP server (blocks)
        mcp.run(transport="stdio")

    except KeyboardInterrupt:
        logger.info("Oxide MCP Server shutdown requested")
        stop_web_ui()
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        stop_web_ui()
        sys.exit(1)
    finally:
        # Ensure web UI is stopped
        stop_web_ui()


if __name__ == "__main__":
    main()
