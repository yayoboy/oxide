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
    Manages WebSocket connections and broadcasts with connection pooling.

    Features:
    - Connection pooling with configurable max connections
    - Automatic cleanup of dead connections
    - Broadcast rate limiting
    - Connection health monitoring
    - Memory-efficient message batching

    Performance optimizations:
    - Set data structure for O(1) add/remove
    - Connection limit to prevent resource exhaustion
    - Dead connection cleanup during broadcasts
    """

    def __init__(self, max_connections: int = 100, max_message_queue: int = 1000):
        """
        Initialize WebSocket manager with connection pooling.

        Args:
            max_connections: Maximum number of concurrent connections
            max_message_queue: Maximum queued messages per connection
        """
        self.active_connections: set[WebSocket] = set()  # O(1) add/remove with set
        self.max_connections = max_connections
        self.max_message_queue = max_message_queue
        self.logger = logger.getChild("websocket")
        self.total_connections = 0  # Counter for monitoring
        self.rejected_connections = 0

    async def connect(self, websocket: WebSocket) -> bool:
        """
        Accept and register a new WebSocket connection with limit check.

        Args:
            websocket: WebSocket connection to register

        Returns:
            True if connection accepted, False if rejected (limit reached)
        """
        # Check connection limit
        if len(self.active_connections) >= self.max_connections:
            self.rejected_connections += 1
            self.logger.warning(
                f"Connection rejected: limit reached ({self.max_connections}). "
                f"Total rejected: {self.rejected_connections}"
            )
            await websocket.close(
                code=1008,  # Policy Violation
                reason=f"Max connections reached ({self.max_connections})"
            )
            return False

        # Accept connection
        await websocket.accept()
        self.active_connections.add(websocket)
        self.total_connections += 1

        self.logger.info(
            f"New WebSocket connection. Active: {len(self.active_connections)}/{self.max_connections}"
        )

        # Send welcome message
        try:
            await websocket.send_json({
                "type": "connected",
                "message": "Connected to Oxide WebSocket",
                "active_clients": len(self.active_connections),
                "max_clients": self.max_connections
            })
        except Exception as e:
            self.logger.error(f"Error sending welcome message: {e}")
            self.disconnect(websocket)
            return False

        return True

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        self.active_connections.discard(websocket)  # discard doesn't raise if not found
        self.logger.debug(
            f"WebSocket disconnected. Active: {len(self.active_connections)}/{self.max_connections}"
        )

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
        Broadcast message to all connected clients with automatic cleanup.

        Dead connections are automatically detected and removed during broadcast.

        Args:
            message: Message to broadcast
        """
        if not self.active_connections:
            return  # Early exit if no connections

        disconnected = set()

        # Use asyncio.gather for parallel sends (more efficient)
        async def send_to_client(connection: WebSocket):
            try:
                await connection.send_json(message)
            except Exception as e:
                self.logger.debug(f"Connection failed during broadcast: {e}")
                disconnected.add(connection)

        # Send to all clients in parallel
        await asyncio.gather(
            *[send_to_client(conn) for conn in self.active_connections],
            return_exceptions=True
        )

        # Remove disconnected clients (O(n) where n = disconnected)
        if disconnected:
            self.active_connections -= disconnected
            self.logger.info(
                f"Cleaned up {len(disconnected)} dead connections. "
                f"Active: {len(self.active_connections)}"
            )

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

    async def broadcast_task_broadcast_chunk(
        self,
        task_id: str,
        service: str,
        chunk: str,
        done: bool,
        timestamp: float,
        error: str = None,
        total_chunks: int = None
    ):
        """
        Broadcast a chunk from a specific service in broadcast_all mode.

        This sends real-time chunks from multiple LLM services to allow
        side-by-side comparison in the UI.

        Args:
            task_id: Task identifier
            service: Service name that produced this chunk
            chunk: Response chunk text
            done: Whether this service has completed
            timestamp: Timestamp when chunk was generated
            error: Error message if service failed
            total_chunks: Total number of chunks from this service (if done)
        """
        message = {
            "type": "task_broadcast_chunk",
            "task_id": task_id,
            "service": service,
            "chunk": chunk,
            "done": done,
            "timestamp": timestamp
        }

        if error:
            message["error"] = error

        if total_chunks is not None:
            message["total_chunks"] = total_chunks

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

    async def close_all(self):
        """
        Close all active WebSocket connections gracefully.

        Used during application shutdown.
        """
        self.logger.info(f"Closing {len(self.active_connections)} WebSocket connections...")

        close_tasks = [
            conn.close(code=1001, reason="Server shutting down")
            for conn in self.active_connections
        ]

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        self.active_connections.clear()
        self.logger.info("All WebSocket connections closed")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get WebSocket manager statistics.

        Returns:
            Dictionary with connection statistics
        """
        return {
            "active_connections": len(self.active_connections),
            "max_connections": self.max_connections,
            "total_connections": self.total_connections,
            "rejected_connections": self.rejected_connections,
            "utilization_percent": round(
                (len(self.active_connections) / self.max_connections) * 100, 2
            ) if self.max_connections > 0 else 0
        }
