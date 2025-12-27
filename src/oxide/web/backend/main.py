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
from ...cluster import init_cluster_coordinator, get_cluster_coordinator
from .routes import services, tasks, monitoring, routing, machines, memory, cluster, costs, config, auth
from .auth import initialize_default_user
from .websocket import WebSocketManager
from .middleware import limiter, optional_auth_middleware, get_auth_enabled


# Global instances
orchestrator: Optional[Orchestrator] = None
ws_manager: Optional[WebSocketManager] = None


async def broadcast_periodic_updates():
    """Background task to broadcast periodic updates to WebSocket clients."""
    import psutil

    while True:
        try:
            # Only broadcast if there are connected clients
            if ws_manager and ws_manager.get_connection_count() > 0 and orchestrator:
                # Broadcast service status
                service_status = await orchestrator.get_service_status()
                await ws_manager.broadcast_service_status("all", service_status)

                # Broadcast metrics
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

                # System resources
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()

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
                        "queued": total_tasks - running_tasks - completed_tasks - failed_tasks
                    },
                    "system": {
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory.percent,
                        "memory_used_mb": round(memory.used / (1024 * 1024), 2),
                        "memory_total_mb": round(memory.total / (1024 * 1024), 2)
                    },
                    "websocket": {
                        "connections": ws_manager.get_connection_count()
                    }
                }

                await ws_manager.broadcast_metrics(metrics)

            await asyncio.sleep(2)  # Broadcast every 2 seconds

        except Exception as e:
            logger.error(f"Error in periodic broadcast: {e}")
            await asyncio.sleep(5)  # Wait longer on error


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global orchestrator, ws_manager

    logger.info("Starting Oxide Web Backend")

    # Initialize default admin user if needed
    initialize_default_user()

    # Initialize hot reload manager
    from pathlib import Path
    config_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "default.yaml"
    hot_reload_manager = init_hot_reload(
        config_path=config_path,
        auto_reload=True  # Enable auto-reload by default
    )
    hot_reload_manager.start()

    # Load configuration
    cfg = hot_reload_manager.current_config
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
    orchestrator = Orchestrator(cfg)

    # Add hot reload callback to update orchestrator on config change
    def on_config_reload(event):
        """Handle configuration reload."""
        global orchestrator

        logger.info("Configuration reloaded, updating orchestrator...")

        try:
            # Re-initialize path validator with new security config
            if event.new_config.security.path_validation_enabled:
                init_path_validator(allowed_dirs=event.new_config.security.allowed_directories)
                logger.info("✓ Path validator reloaded with updated whitelist")

            # Re-initialize orchestrator with new config
            # Note: This is a simplified reload. Full reload would require
            # stopping old adapters and starting new ones.
            orchestrator = Orchestrator(event.new_config)
            logger.info("✅ Orchestrator updated with new configuration")

        except Exception as e:
            logger.error(f"❌ Failed to update orchestrator: {e}")

    hot_reload_manager.add_reload_callback(on_config_reload)

    # Initialize WebSocket manager
    ws_manager = WebSocketManager()

    # Start background task for periodic WebSocket broadcasts
    broadcast_task = asyncio.create_task(broadcast_periodic_updates())
    logger.info("Started periodic WebSocket broadcast task")

    # Initialize cluster coordinator if enabled
    cluster_cfg = getattr(cfg, 'cluster', None)
    if cluster_cfg and getattr(cluster_cfg, 'enabled', False):
        import socket
        node_id = f"{socket.gethostname()}_{cfg.cluster.api_port}"

        coordinator = init_cluster_coordinator(
            node_id=node_id,
            broadcast_port=cfg.cluster.broadcast_port,
            api_port=cfg.cluster.api_port
        )
        await coordinator.start(orchestrator)
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
    hot_reload_mgr = get_hot_reload_manager()
    if hot_reload_mgr:
        hot_reload_mgr.stop()
        logger.info("Hot reload manager stopped")

    # Stop cluster coordinator
    coordinator = get_cluster_coordinator()
    if coordinator:
        await coordinator.stop()
        logger.info("Cluster coordinator stopped")


# Create FastAPI app
app = FastAPI(
    title="Oxide LLM Orchestrator API",
    description="REST API and WebSocket interface for Oxide intelligent LLM routing",
    version="0.1.0",
    lifespan=lifespan
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "orchestrator": orchestrator is not None,
        "services": len(orchestrator.adapters) if orchestrator else 0
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Streams:
    - Task execution progress
    - Service status changes
    - System metrics
    """
    await ws_manager.connect(websocket)

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()

            # Echo or handle commands
            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
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


def get_orchestrator() -> Orchestrator:
    """Get the global orchestrator instance."""
    if orchestrator is None:
        raise RuntimeError("Orchestrator not initialized")
    return orchestrator


def set_orchestrator(orch: Orchestrator) -> None:
    """Set the global orchestrator instance (for testing)."""
    global orchestrator
    orchestrator = orch


def get_ws_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    if ws_manager is None:
        raise RuntimeError("WebSocket manager not initialized")
    return ws_manager


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
