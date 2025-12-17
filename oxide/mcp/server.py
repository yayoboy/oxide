"""
MCP Server for Oxide.

Exposes Oxide functionality via Model Context Protocol for Claude Code integration.
"""
import sys

from mcp.server import Server
from mcp.types import TextContent

from ..utils.logging import logger
from .context import OxideServerContext


# Create MCP server
app = Server("oxide")


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
    context = OxideServerContext.get_instance()
    chunks = []
    async for content in context.tools.route_task(prompt, files, preferences):
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
    context = OxideServerContext.get_instance()
    chunks = []
    async for content in context.tools.analyze_parallel(directory, prompt, num_workers):
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
    context = OxideServerContext.get_instance()
    chunks = []
    async for content in context.tools.list_services():
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

    context = None

    try:
        # Initialize Oxide context
        context = OxideServerContext.initialize()

        # Run MCP server (blocks)
        app.run()

    except KeyboardInterrupt:
        logger.info("Oxide MCP Server shutdown requested")
        if context:
            context.cleanup()
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if context:
            context.cleanup()
        sys.exit(1)

    finally:
        # Ensure cleanup
        if context:
            context.cleanup()


if __name__ == "__main__":
    main()
