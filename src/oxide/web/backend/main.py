"""
Oxide Web Dashboard - FastAPI Backend

Provides REST API and WebSocket endpoints for the Oxide dashboard.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ...core.orchestrator import Orchestrator
from ...config.loader import load_config
from ...utils.logging import logger, setup_logging
from .routes import services, tasks, monitoring
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

    logger.info("Oxide Web Backend started successfully")

    yield

    # Cleanup
    logger.info("Shutting down Oxide Web Backend")


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


# Include routers
app.include_router(services.router, prefix="/api/services", tags=["services"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["monitoring"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Oxide LLM Orchestrator API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
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
