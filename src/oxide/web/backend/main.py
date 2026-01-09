"""
Oxide Web Dashboard - FastAPI Backend

Provides REST API and WebSocket endpoints for the Oxide dashboard.
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from ...core.orchestrator import Orchestrator
from ...config.loader import load_config
from ...config.hot_reload import init_hot_reload, get_hot_reload_manager
from ...utils.logging import logger, setup_logging
from ...utils.metrics_cache import get_metrics_cache
from ...cluster import init_cluster_coordinator, get_cluster_coordinator
from .routes import services, tasks, monitoring, routing, machines, memory, cluster, costs, config, auth, api_keys
from .auth import initialize_default_user
from .websocket import WebSocketManager
from .middleware import limiter, optional_auth_middleware, get_auth_enabled


# Application state container (eliminates global variables)
class AppState:
    """Container for application-wide state with dependency injection support."""

    def __init__(self):
        self.orchestrator: Optional[Orchestrator] = None
        self.ws_manager: Optional[WebSocketManager] = None
        self.metrics_cache = get_metrics_cache(ttl=2.0)
        self.hot_reload_manager = None
        self.cluster_coordinator = None


async def broadcast_periodic_updates(state: AppState):
    """
    Background task to broadcast periodic updates to WebSocket clients.

    Uses async monitoring and caching to prevent blocking the event loop.

    Args:
        state: Application state container
    """
    import psutil

    while True:
        try:
            # Only broadcast if there are connected clients
            if (state.ws_manager and
                state.ws_manager.get_connection_count() > 0 and
                state.orchestrator):

                # Get cached or compute metrics asynchronously
                metrics_cache = state.metrics_cache

                # CPU monitoring (blocking call - run in executor with cache)
                cpu_percent = await metrics_cache.get_or_compute_async(
                    "cpu_percent",
                    lambda: psutil.cpu_percent(interval=0.1),
                    use_executor=True
                )

                # Memory monitoring (fast, but cache anyway)
                memory = await metrics_cache.get_or_compute_async(
                    "memory",
                    lambda: psutil.virtual_memory(),
                    use_executor=False
                )

                # Service status (async, cache to reduce load)
                service_status = await metrics_cache.get_or_compute_async(
                    "service_status",
                    lambda: state.orchestrator.get_service_status(),
                    use_executor=False
                )

                # Broadcast service status
                await state.ws_manager.broadcast_service_status("all", service_status)

                # Task stats (fast, minimal caching)
                from ...utils.task_storage import get_task_storage
                task_storage = get_task_storage()
                stats = task_storage.get_stats()

                # Count services
                total_services = len(service_status)
                enabled_services = sum(1 for s in service_status.values() if s.get("enabled"))
                healthy_services = sum(1 for s in service_status.values() if s.get("healthy"))

                # Task stats
                total_tasks = stats["total"]
                running_tasks = stats["by_status"].get("running", 0)
                completed_tasks = stats["by_status"].get("completed", 0)
                failed_tasks = stats["by_status"].get("failed", 0)

                metrics = {
                    "services": {
                        "total": total_services,
                        "enabled": enabled_services,
                        "healthy": healthy_services,
                        "unhealthy": enabled_services - healthy_services
                    },
                    "tasks": {
                        "total": total_tasks,
                        "running": running_tasks,
                        "completed": completed_tasks,
                        "failed": failed_tasks,
                        "queued": max(0, total_tasks - running_tasks - completed_tasks - failed_tasks)
                    },
                    "system": {
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory.percent,
                        "memory_used_mb": round(memory.used / (1024 * 1024), 2),
                        "memory_total_mb": round(memory.total / (1024 * 1024), 2)
                    },
                    "websocket": {
                        "connections": state.ws_manager.get_connection_count()
                    }
                }

                await state.ws_manager.broadcast_metrics(metrics)

            await asyncio.sleep(2)  # Broadcast every 2 seconds

        except Exception as e:
            logger.error(f"Error in periodic broadcast: {e}")
            await asyncio.sleep(5)  # Wait longer on error


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown with dependency injection."""
    logger.info("Starting Oxide Web Backend")

    # Create application state container
    state = AppState()

    # Initialize default admin user if needed
    initialize_default_user()

    # Initialize hot reload manager
    from pathlib import Path
    config_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "default.yaml"
    state.hot_reload_manager = init_hot_reload(
        config_path=config_path,
        auto_reload=True  # Enable auto-reload by default
    )
    state.hot_reload_manager.start()

    # Load configuration
    cfg = state.hot_reload_manager.current_config
    setup_logging(
        level=cfg.logging.level,
        log_file=cfg.logging.file,
        console=cfg.logging.console
    )

    # Initialize path validator with configured allowed directories
    from ...utils.path_validator import init_path_validator
    if cfg.security.path_validation_enabled:
        init_path_validator(allowed_dirs=cfg.security.allowed_directories)
        logger.info("✓ Path validator initialized with security whitelist")
    else:
        logger.warning("⚠️ Path validation DISABLED - use only for testing!")

    # Initialize orchestrator
    state.orchestrator = Orchestrator(cfg)

    # Add hot reload callback to update orchestrator on config change
    def on_config_reload(event):
        """Handle configuration reload."""
        logger.info("Configuration reloaded, updating orchestrator...")

        try:
            # Re-initialize path validator with new security config
            if event.new_config.security.path_validation_enabled:
                init_path_validator(allowed_dirs=event.new_config.security.allowed_directories)
                logger.info("✓ Path validator reloaded with updated whitelist")

            # Re-initialize orchestrator with new config
            # Note: This is a simplified reload. Full reload would require
            # stopping old adapters and starting new ones.
            state.orchestrator = Orchestrator(event.new_config)
            logger.info("✅ Orchestrator updated with new configuration")

        except Exception as e:
            logger.error(f"❌ Failed to update orchestrator: {e}")

    state.hot_reload_manager.add_reload_callback(on_config_reload)

    # Initialize WebSocket manager
    state.ws_manager = WebSocketManager()

    # Store state in app for dependency injection
    app.state.oxide = state

    # Start background task for periodic WebSocket broadcasts
    broadcast_task = asyncio.create_task(broadcast_periodic_updates(state))
    logger.info("Started periodic WebSocket broadcast task")

    # Initialize cluster coordinator if enabled
    cluster_cfg = getattr(cfg, 'cluster', None)
    if cluster_cfg and getattr(cluster_cfg, 'enabled', False):
        import socket
        node_id = f"{socket.gethostname()}_{cfg.cluster.api_port}"

        state.cluster_coordinator = init_cluster_coordinator(
            node_id=node_id,
            broadcast_port=cfg.cluster.broadcast_port,
            api_port=cfg.cluster.api_port
        )
        await state.cluster_coordinator.start(state.orchestrator)
        logger.info("Cluster coordinator started")
    else:
        logger.info("Cluster coordination disabled")

    logger.info("Oxide Web Backend started successfully")

    yield

    # Cleanup
    logger.info("Shutting down Oxide Web Backend")

    # Stop broadcast task
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        logger.info("Periodic broadcast task stopped")

    # Stop hot reload manager
    if state.hot_reload_manager:
        state.hot_reload_manager.stop()
        logger.info("Hot reload manager stopped")

    # Stop cluster coordinator
    if state.cluster_coordinator:
        await state.cluster_coordinator.stop()
        logger.info("Cluster coordinator stopped")


# OpenAPI tags for documentation organization
tags_metadata = [
    {
        "name": "authentication",
        "description": "User authentication and authorization endpoints. Includes login, logout, and token management.",
    },
    {
        "name": "services",
        "description": "LLM service management. List, configure, and monitor configured LLM providers (Ollama, OpenRouter, Gemini, etc.).",
    },
    {
        "name": "tasks",
        "description": "Task execution and history. Submit tasks for execution, track progress, and retrieve results.",
    },
    {
        "name": "monitoring",
        "description": "System monitoring and metrics. Real-time metrics for services, tasks, and system resources.",
    },
    {
        "name": "routing",
        "description": "Task routing rules. Configure custom routing rules to assign tasks to specific services based on task type.",
    },
    {
        "name": "machines",
        "description": "Machine and node management. Monitor distributed Oxide instances in a cluster.",
    },
    {
        "name": "memory",
        "description": "Context memory management. Store and retrieve conversation context for improved LLM responses.",
    },
    {
        "name": "cluster",
        "description": "Cluster coordination. Manage multi-node Oxide deployments with automatic failover and load balancing.",
    },
    {
        "name": "costs",
        "description": "Cost tracking and budgeting. Monitor API usage costs across all LLM providers.",
    },
    {
        "name": "config",
        "description": "Configuration management. Retrieve and update Oxide configuration with hot-reload support.",
    },
    {
        "name": "api-keys",
        "description": "API key management. Store and validate API keys for external LLM services.",
    },
]

# Create FastAPI app with enhanced OpenAPI documentation
app = FastAPI(
    title="Oxide LLM Orchestrator API",
    description="""
# Oxide LLM Orchestrator

**Intelligent multi-provider LLM routing and orchestration system**

Oxide provides a unified interface for managing and routing tasks across multiple LLM providers:
- **Local Services**: Ollama, LM Studio
- **Remote APIs**: OpenRouter, OpenAI, Anthropic, Google Gemini, Groq
- **CLI Tools**: aichat, fabric, llm

## Features

- 🎯 **Smart Routing**: Automatically route tasks to the best available service
- 📊 **Real-time Monitoring**: WebSocket-based live metrics and status updates
- 💰 **Cost Tracking**: Monitor API usage and costs across all providers
- 🔐 **Secure**: Optional authentication, rate limiting, and API key management
- 🌐 **Distributed**: Multi-node cluster support with automatic failover
- 🧠 **Context Memory**: Persistent conversation context for improved responses
- ⚡ **High Performance**: Async I/O, connection pooling, and intelligent caching

## Quick Start

1. **List Services**: `GET /api/services/`
2. **Execute Task**: `POST /api/tasks/execute/`
3. **Monitor Metrics**: WebSocket connection to `/ws`

## Authentication

By default, authentication is **disabled** for ease of development. To enable:

```bash
export OXIDE_AUTH_ENABLED=true
```

Then use the `/auth/login` endpoint to obtain a JWT token and include it in the `Authorization` header:

```
Authorization: Bearer <your-token>
```

## WebSocket API

Connect to `/ws` for real-time updates:
- Task execution progress
- Service health status changes
- System metrics (CPU, memory, task queue)

## Rate Limiting

API endpoints are rate-limited to prevent abuse:
- **Default**: 100 requests per minute per IP
- **Authenticated**: 1000 requests per minute

## Support

- 📖 **Documentation**: `/docs` (Swagger UI) or `/redoc` (ReDoc)
- 🐛 **Issues**: Report bugs and feature requests on GitHub
- 💬 **Community**: Join our Discord for help and discussions
    """,
    version="0.1.0",
    contact={
        "name": "Oxide Project",
        "url": "https://github.com/yayoboy/oxide",
        "email": "esoglobine@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - configured for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    expose_headers=["Content-Length", "X-Request-ID"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Optional authentication middleware (enabled via OXIDE_AUTH_ENABLED=true)
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Authentication middleware wrapper."""
    return await optional_auth_middleware(request, call_next)


# Include API routers (these take precedence over static files)
# Authentication routes (no auth required)
app.include_router(auth.router, tags=["authentication"])

# Protected API routes (require authentication)
# TODO: Add authentication dependencies to protect these routes
app.include_router(services.router, prefix="/api/services", tags=["services"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["monitoring"])
app.include_router(routing.router, prefix="/api/routing", tags=["routing"])
app.include_router(machines.router, prefix="/api/machines", tags=["machines"])
app.include_router(memory.router)  # Memory router already has prefix="/api/memory"
app.include_router(cluster.router)  # Cluster router already has prefix="/api/cluster"
app.include_router(costs.router)  # Costs router already has prefix="/api/costs"
app.include_router(config.router)  # Config router with prefix="/api/config"
app.include_router(api_keys.router)  # API keys router with prefix="/api/api-keys"


# Serve static files from the frontend build
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
    logger.info(f"Serving frontend static files from: {frontend_dist}")
else:
    logger.warning(f"Frontend dist directory not found: {frontend_dist}")
    logger.warning("Run 'npm run build' in src/oxide/web/frontend to build the frontend")


@app.get("/")
async def root():
    """Serve the frontend index.html."""
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        # Fallback to JSON if frontend not built
        return {
            "name": "Oxide LLM Orchestrator API",
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs",
            "warning": "Frontend not built. Run 'npm run build' in src/oxide/web/frontend"
        }


@app.get("/debug")
async def debug_info(request: Request):
    """Debug endpoint with comprehensive system info."""
    state: AppState = request.app.state.oxide
    service_status = await state.orchestrator.get_service_status()

    # Categorize services
    categories = {"cli": [], "local": [], "remote": []}
    for name, status in service_status.items():
        info = status.get("info", {})
        service_type = info.get("type")

        if service_type == "cli":
            categories["cli"].append(name)
        elif service_type == "http":
            base_url = info.get("base_url", "")
            if "localhost" in base_url or "127.0.0.1" in base_url:
                categories["local"].append(name)
            else:
                categories["remote"].append(name)

    return {
        "status": "ok",
        "services": {
            "total": len(service_status),
            "enabled": sum(1 for s in service_status.values() if s.get("enabled")),
            "healthy": sum(1 for s in service_status.values() if s.get("healthy")),
            "categorized": categories,
            "details": service_status
        },
        "frontend": {
            "dist_exists": frontend_dist.exists(),
            "index_exists": (frontend_dist / "index.html").exists() if frontend_dist.exists() else False,
            "assets_exist": (frontend_dist / "assets").exists() if frontend_dist.exists() else False
        },
        "cache": state.metrics_cache.get_stats()
    }


@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint."""
    state: AppState = request.app.state.oxide
    return {
        "status": "healthy",
        "orchestrator": state.orchestrator is not None,
        "services": len(state.orchestrator.adapters) if state.orchestrator else 0,
        "websocket_connections": state.ws_manager.get_connection_count() if state.ws_manager else 0
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, request: Request):
    """
    WebSocket endpoint for real-time updates.

    Streams:
    - Task execution progress
    - Service status changes
    - System metrics
    """
    state: AppState = request.app.state.oxide
    await state.ws_manager.connect(websocket)

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()

            # Echo or handle commands
            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        state.ws_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# SPA catch-all route removed - client-side routing handles navigation
# Frontend is served from root "/" and static assets from "/assets"


# Dependency injection functions for routes
def get_orchestrator(request: Request) -> Orchestrator:
    """
    Dependency injection for Orchestrator.

    Args:
        request: FastAPI request object

    Returns:
        Orchestrator instance from app state

    Raises:
        RuntimeError: If orchestrator not initialized
    """
    state: AppState = request.app.state.oxide
    if state.orchestrator is None:
        raise RuntimeError("Orchestrator not initialized")
    return state.orchestrator


def get_ws_manager(request: Request) -> WebSocketManager:
    """
    Dependency injection for WebSocket manager.

    Args:
        request: FastAPI request object

    Returns:
        WebSocketManager instance from app state

    Raises:
        RuntimeError: If WebSocket manager not initialized
    """
    state: AppState = request.app.state.oxide
    if state.ws_manager is None:
        raise RuntimeError("WebSocket manager not initialized")
    return state.ws_manager


def get_metrics_cache_instance(request: Request):
    """
    Dependency injection for MetricsCache.

    Args:
        request: FastAPI request object

    Returns:
        MetricsCache instance from app state
    """
    state: AppState = request.app.state.oxide
    return state.metrics_cache


def set_orchestrator(app: FastAPI, orch: Orchestrator) -> None:
    """
    Set orchestrator instance (for testing).

    Args:
        app: FastAPI app instance
        orch: Orchestrator instance
    """
    if not hasattr(app.state, 'oxide'):
        app.state.oxide = AppState()
    app.state.oxide.orchestrator = orch


def main():
    """Main entry point for Oxide Web Server."""
    import uvicorn

    uvicorn.run(
        "oxide.web.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
