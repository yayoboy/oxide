"""
Test suite for WebSocket manager.

Tests cover:
- Connection management
- Broadcasting
- Message sending
- Task event broadcasting
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket

from src.oxide.web.backend.websocket import WebSocketManager


@pytest.fixture
def ws_manager():
    """Create WebSocketManager instance"""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket"""
    ws = AsyncMock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


class TestWebSocketManager:
    """Test WebSocketManager basic functionality"""

    @pytest.mark.asyncio
    async def test_connect_websocket(self, ws_manager, mock_websocket):
        """Test connecting a new WebSocket"""
        # Initially no connections
        assert ws_manager.get_connection_count() == 0

        # Connect
        await ws_manager.connect(mock_websocket)

        # Verify
        assert ws_manager.get_connection_count() == 1
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_json.assert_called_once()

        # Verify welcome message
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'connected'
        assert call_args['clients'] == 1

    def test_disconnect_websocket(self, ws_manager, mock_websocket):
        """Test disconnecting a WebSocket"""
        # Add connection
        ws_manager.active_connections.append(mock_websocket)
        assert ws_manager.get_connection_count() == 1

        # Disconnect
        ws_manager.disconnect(mock_websocket)

        # Verify
        assert ws_manager.get_connection_count() == 0
        assert mock_websocket not in ws_manager.active_connections

    def test_disconnect_non_existent(self, ws_manager, mock_websocket):
        """Test disconnecting a non-existent WebSocket"""
        # Should not raise error
        ws_manager.disconnect(mock_websocket)
        assert ws_manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_send_personal_message(self, ws_manager, mock_websocket):
        """Test sending personal message to specific client"""
        message = {"type": "test", "data": "hello"}

        await ws_manager.send_personal(message, mock_websocket)

        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self, ws_manager):
        """Test broadcasting to multiple connected clients"""
        # Create multiple mock websockets
        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)
        ws3 = AsyncMock(spec=WebSocket)

        ws_manager.active_connections = [ws1, ws2, ws3]

        message = {"type": "broadcast", "data": "test"}
        await ws_manager.broadcast(message)

        # Verify all received message
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)
        ws3.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed_connections(self, ws_manager):
        """Test that failed connections are removed during broadcast"""
        # Create mock websockets, one that fails
        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)
        ws2.send_json = AsyncMock(side_effect=Exception("Connection closed"))
        ws3 = AsyncMock(spec=WebSocket)

        ws_manager.active_connections = [ws1, ws2, ws3]

        message = {"type": "test"}
        await ws_manager.broadcast(message)

        # ws2 should be removed
        assert ws_manager.get_connection_count() == 2
        assert ws2 not in ws_manager.active_connections
        assert ws1 in ws_manager.active_connections
        assert ws3 in ws_manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_task_start(self, ws_manager, mock_websocket):
        """Test broadcasting task start event"""
        ws_manager.active_connections = [mock_websocket]

        await ws_manager.broadcast_task_start(
            task_id="task-123",
            task_type="code_review",
            service="gemini"
        )

        # Verify message structure
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'task_start'
        assert call_args['task_id'] == 'task-123'
        assert call_args['task_type'] == 'code_review'
        assert call_args['service'] == 'gemini'
        assert 'timestamp' in call_args

    @pytest.mark.asyncio
    async def test_broadcast_task_progress(self, ws_manager, mock_websocket):
        """Test broadcasting task progress event"""
        ws_manager.active_connections = [mock_websocket]

        await ws_manager.broadcast_task_progress(
            task_id="task-123",
            chunk="Processing...",
            progress_percent=50.0
        )

        # Verify message structure
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'task_progress'
        assert call_args['task_id'] == 'task-123'
        assert call_args['chunk'] == 'Processing...'
        assert call_args['progress'] == 50.0

    @pytest.mark.asyncio
    async def test_broadcast_task_complete(self, ws_manager, mock_websocket):
        """Test broadcasting task complete event"""
        ws_manager.active_connections = [mock_websocket]

        await ws_manager.broadcast_task_complete(
            task_id="task-123",
            success=True,
            duration_seconds=2.5
        )

        # Verify message structure
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'task_complete'
        assert call_args['task_id'] == 'task-123'
        assert call_args['success'] is True
        assert call_args['duration'] == 2.5
        assert 'timestamp' in call_args

    @pytest.mark.asyncio
    async def test_broadcast_task_complete_with_error(self, ws_manager, mock_websocket):
        """Test broadcasting task complete event with error"""
        ws_manager.active_connections = [mock_websocket]

        await ws_manager.broadcast_task_complete(
            task_id="task-123",
            success=False,
            error="Service unavailable"
        )

        # Verify message structure
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'task_complete'
        assert call_args['success'] is False
        assert call_args['error'] == 'Service unavailable'

    @pytest.mark.asyncio
    async def test_broadcast_service_status(self, ws_manager, mock_websocket):
        """Test broadcasting service status"""
        ws_manager.active_connections = [mock_websocket]

        status = {
            "healthy": True,
            "enabled": True,
            "info": {"model": "gemini-pro"}
        }

        await ws_manager.broadcast_service_status("gemini", status)

        # Verify message structure
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'service_status'
        assert call_args['service'] == 'gemini'
        assert call_args['status'] == status
        assert 'timestamp' in call_args

    @pytest.mark.asyncio
    async def test_broadcast_metrics(self, ws_manager, mock_websocket):
        """Test broadcasting system metrics"""
        ws_manager.active_connections = [mock_websocket]

        metrics = {
            "services": {"total": 3, "healthy": 2},
            "tasks": {"running": 1, "completed": 10},
            "system": {"cpu_percent": 45.5}
        }

        await ws_manager.broadcast_metrics(metrics)

        # Verify message structure
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'metrics'
        assert call_args['data'] == metrics
        assert 'timestamp' in call_args

    def test_get_connection_count(self, ws_manager):
        """Test getting connection count"""
        assert ws_manager.get_connection_count() == 0

        # Add connections
        ws_manager.active_connections = [MagicMock() for _ in range(5)]
        assert ws_manager.get_connection_count() == 5

    @pytest.mark.asyncio
    async def test_send_personal_handles_error(self, ws_manager):
        """Test send_personal handles errors gracefully"""
        ws = AsyncMock(spec=WebSocket)
        ws.send_json = AsyncMock(side_effect=Exception("Connection error"))

        # Should not raise
        await ws_manager.send_personal({"test": "data"}, ws)
