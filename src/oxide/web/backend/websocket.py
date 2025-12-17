"""
WebSocket manager for real-time updates.

Handles WebSocket connections and broadcasts events to connected clients.
"""
import asyncio
from typing import List, Dict, Any
from fastapi import WebSocket
import json

from ...utils.logging import logger


class WebSocketManager:
    """
    Manages WebSocket connections and broadcasts.

    Supports:
    - Multiple simultaneous connections
    - Broadcast to all clients
    - Send to specific client
    - Task execution streaming
    """

    def __init__(self):
        """Initialize WebSocket manager."""
        self.active_connections: List[WebSocket] = []
        self.logger = logger.getChild("websocket")

    async def connect(self, websocket: WebSocket):
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection to register
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")

        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Oxide WebSocket",
            "clients": len(self.active_connections)
        })

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def send_personal(self, message: Dict[str, Any], websocket: WebSocket):
        """
        Send message to a specific client.

        Args:
            message: Message to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            self.logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast message to all connected clients.

        Args:
            message: Message to broadcast
        """
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                self.logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_task_start(self, task_id: str, task_type: str, service: str):
        """
        Broadcast task start event.

        Args:
            task_id: Task identifier
            task_type: Type of task
            service: Service handling the task
        """
        await self.broadcast({
            "type": "task_start",
            "task_id": task_id,
            "task_type": task_type,
            "service": service,
            "timestamp": asyncio.get_event_loop().time()
        })

    async def broadcast_task_progress(
        self,
        task_id: str,
        chunk: str,
        progress_percent: float = None
    ):
        """
        Broadcast task progress/streaming chunk.

        Args:
            task_id: Task identifier
            chunk: Response chunk
            progress_percent: Optional progress percentage
        """
        message = {
            "type": "task_progress",
            "task_id": task_id,
            "chunk": chunk
        }

        if progress_percent is not None:
            message["progress"] = progress_percent

        await self.broadcast(message)

    async def broadcast_task_complete(
        self,
        task_id: str,
        success: bool,
        duration_seconds: float = None,
        error: str = None
    ):
        """
        Broadcast task completion event.

        Args:
            task_id: Task identifier
            success: Whether task completed successfully
            duration_seconds: Task execution duration
            error: Error message if failed
        """
        message = {
            "type": "task_complete",
            "task_id": task_id,
            "success": success,
            "timestamp": asyncio.get_event_loop().time()
        }

        if duration_seconds is not None:
            message["duration"] = duration_seconds

        if error:
            message["error"] = error

        await self.broadcast(message)

    async def broadcast_service_status(self, service_name: str, status: Dict[str, Any]):
        """
        Broadcast service status change.

        Args:
            service_name: Service identifier
            status: Service status information
        """
        await self.broadcast({
            "type": "service_status",
            "service": service_name,
            "status": status,
            "timestamp": asyncio.get_event_loop().time()
        })

    async def broadcast_metrics(self, metrics: Dict[str, Any]):
        """
        Broadcast system metrics.

        Args:
            metrics: System metrics data
        """
        await self.broadcast({
            "type": "metrics",
            "data": metrics,
            "timestamp": asyncio.get_event_loop().time()
        })

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)
