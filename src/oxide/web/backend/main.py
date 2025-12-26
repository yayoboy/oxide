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

from ...core.orchestrator import Orchestrator
from ...config.loader import load_config
from ...utils.logging import logger, setup_logging
from ...cluster import init_cluster_coordinator, get_cluster_coordinator
from .routes import services, tasks, monitoring, routing, machines, memory, cluster, costs
from .websocket import WebSocketManager


# Global instances
orchestrator: Optional[Orchestrator] = None
ws_manager: Optional[WebSocketManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global orchestrator, ws_manager

    logger.info("Starting Oxide Web Backend")

    # Load configuration
    config = load_config()
    setup_logging(
        level=config.logging.level,
        log_file=config.logging.file,
        console=config.logging.console
    )

    # Initialize orchestrator
    orchestrator = Orchestrator(config)

    # Initialize WebSocket manager
    ws_manager = WebSocketManager()

    # Initialize cluster coordinator if enabled
    cluster_config = getattr(config, 'cluster', None)
    if cluster_config and getattr(cluster_config, 'enabled', False):
        import socket
        node_id = f"{socket.gethostname()}_{config.cluster.api_port}"

        coordinator = init_cluster_coordinator(
            node_id=node_id,
            broadcast_port=config.cluster.broadcast_port,
            api_port=config.cluster.api_port
        )
        await coordinator.start(orchestrator)
        logger.info("Cluster coordinator started")
    else:
        logger.info("Cluster coordination disabled")

    logger.info("Oxide Web Backend started successfully")

    yield

    # Cleanup
    logger.info("Shutting down Oxide Web Backend")

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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers (these take precedence over static files)
app.include_router(services.router, prefix="/api/services", tags=["services"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["monitoring"])
app.include_router(routing.router, prefix="/api/routing", tags=["routing"])
app.include_router(machines.router, prefix="/api/machines", tags=["machines"])
app.include_router(memory.router)  # Memory router already has prefix="/api/memory"
app.include_router(cluster.router)  # Cluster router already has prefix="/api/cluster"
app.include_router(costs.router)  # Costs router already has prefix="/api/costs"


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
