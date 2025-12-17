"""
MCP Server for Oxide.

Exposes Oxide functionality via Model Context Protocol for Claude Code integration.
"""
import asyncio
import sys
import os
import subprocess
from pathlib import Path

from mcp.server import Server
from mcp.types import Tool, TextContent

from ..core.orchestrator import Orchestrator
from ..config.loader import load_config
from ..utils.logging import logger, setup_logging
from .tools import OxideTools


# Create MCP server
app = Server("oxide")


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

            logger.info(f"Web UI backend started (PID: {web_process.pid})")
            print("🌐 Web UI started at http://localhost:8000", file=sys.stderr)

        except Exception as e:
            logger.error(f"Failed to start Web UI: {e}")


def stop_web_ui():
    """Stop Web UI backend if running."""
    global web_process

    if web_process and web_process.poll() is None:
        logger.info("Stopping Web UI backend...")
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
        # Load configuration
        config = load_config()

        # Setup logging
        setup_logging(
            level=config.logging.level,
            log_file=config.logging.file,
            console=config.logging.console
        )

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
@app.tool()
async def route_task(
    prompt: str,
    files: list[str] | None = None,
    preferences: dict | None = None
) -> list[TextContent]:
    """
    Intelligently route a task to the best LLM.

    Analyzes the task characteristics and automatically selects the most
    appropriate LLM service (Gemini for large codebases, Qwen for code review, etc.).

    Args:
        prompt: Task description or query
        files: Optional list of file paths to include as context
        preferences: Optional routing preferences

    Example:
        route_task("Review this code for bugs", files=["src/main.py", "src/utils.py"])
    """
    chunks = []
    async for content in oxide_tools.route_task(prompt, files, preferences):
        chunks.append(content)
    return chunks


@app.tool()
async def analyze_parallel(
    directory: str,
    prompt: str,
    num_workers: int | None = None
) -> list[TextContent]:
    """
    Analyze large codebase in parallel across multiple LLMs.

    Distributes files across multiple LLM services for faster analysis.
    Ideal for analyzing large codebases with 20+ files.

    Args:
        directory: Directory path to analyze
        prompt: Analysis prompt/query
        num_workers: Number of parallel workers (default: 3)

    Example:
        analyze_parallel("./src", "Identify all API endpoints and their authentication")
    """
    chunks = []
    async for content in oxide_tools.analyze_parallel(directory, prompt, num_workers):
        chunks.append(content)
    return chunks


@app.tool()
async def list_services() -> list[TextContent]:
    """
    Check health and availability of all configured LLM services.

    Returns status information for all services including:
    - Service health (available/unavailable)
    - Service type (CLI/HTTP)
    - Routing rules configuration

    Example:
        list_services()
    """
    chunks = []
    async for content in oxide_tools.list_services():
        chunks.append(content)
    return chunks


def main():
    """
    Main entry point for Oxide MCP server.

    This function is called when running: uv run oxide-mcp
    """
    # Print startup banner
    print("🔬 Oxide LLM Orchestrator", file=sys.stderr)
    print("Starting MCP server...", file=sys.stderr)

    try:
        # Initialize Oxide
        initialize()

        # Run MCP server (blocks)
        app.run()

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
