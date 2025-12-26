"""
Integration tests for Monitoring API endpoints.

Tests all endpoints in src/oxide/web/backend/routes/monitoring.py including:
- GET /api/monitoring/metrics - Get system metrics
- GET /api/monitoring/stats - Get detailed statistics
- GET /api/monitoring/health - System health check
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMonitoringAPI:
    """Test suite for Monitoring API endpoints."""

    def test_get_metrics_success(self, api_client, mock_orchestrator, populated_task_storage):
        """Test getting system metrics."""
        # Mock service status
        async def mock_status():
            return {
                "gemini": {"enabled": True, "healthy": True},
                "qwen": {"enabled": True, "healthy": False},
                "ollama": {"enabled": False, "healthy": False}
            }

        mock_orchestrator.get_service_status = mock_status

        # Mock WebSocket manager
        with patch('oxide.web.backend.routes.monitoring.get_ws_manager') as mock_ws:
            ws_manager = MagicMock()
            ws_manager.get_connection_count.return_value = 5
            mock_ws.return_value = ws_manager

            response = api_client.get("/api/monitoring/metrics")

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "services" in data
        assert "tasks" in data
        assert "system" in data
        assert "websocket" in data
        assert "timestamp" in data

        # Check services metrics
        assert data["services"]["total"] == 3
        assert data["services"]["enabled"] == 2
        assert data["services"]["healthy"] == 1
        assert data["services"]["unhealthy"] == 1

        # Check tasks metrics
        assert data["tasks"]["total"] == 3  # From populated_task_storage
        assert "completed" in data["tasks"]
        assert "failed" in data["tasks"]
        assert "running" in data["tasks"]

        # Check system metrics
        assert "cpu_percent" in data["system"]
        assert "memory_percent" in data["system"]
        assert "memory_used_mb" in data["system"]
        assert "memory_total_mb" in data["system"]

        # Check WebSocket metrics
        assert data["websocket"]["connections"] == 5

    def test_get_metrics_error_handling(self, api_client, mock_orchestrator):
        """Test metrics endpoint error handling."""
        # Make get_service_status raise an error
        async def mock_status():
            raise Exception("Service error")

        mock_orchestrator.get_service_status = mock_status

        response = api_client.get("/api/monitoring/metrics")

        # Should return 200 with error in response
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_get_stats_with_tasks(self, api_client, populated_task_storage):
        """Test getting statistics with existing tasks."""
        response = api_client.get("/api/monitoring/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_tasks"] == 3
        assert "avg_duration" in data
        assert "success_rate" in data
        assert "tasks_by_status" in data
        assert "completed" in data
        assert "failed" in data

        # Check tasks by status
        assert data["tasks_by_status"]["completed"] == 1
        assert data["tasks_by_status"]["running"] == 1
        assert data["tasks_by_status"]["failed"] == 1

    def test_get_stats_no_tasks(self, api_client, temp_task_storage):
        """Test getting statistics with no tasks."""
        response = api_client.get("/api/monitoring/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_tasks"] == 0
        assert data["avg_duration"] == 0
        assert data["success_rate"] == 0
        assert data["tasks_by_status"] == {}

    def test_get_stats_success_rate_calculation(self, api_client, temp_task_storage):
        """Test that success rate is calculated correctly."""
        storage = temp_task_storage

        # Add 7 completed and 3 failed tasks
        for i in range(7):
            storage.add_task(f"task-{i}", "test", [], "gemini", "quick_query")
            storage.update_task(f"task-{i}", status="completed")

        for i in range(7, 10):
            storage.add_task(f"task-{i}", "test", [], "gemini", "quick_query")
            storage.update_task(f"task-{i}", status="failed")

        response = api_client.get("/api/monitoring/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_tasks"] == 10
        assert data["completed"] == 7
        assert data["failed"] == 3
        assert data["success_rate"] == 70.0

    def test_health_check_healthy(self, api_client):
        """Test health check when system is healthy."""
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory:

            # Mock memory with safe values
            memory = MagicMock()
            memory.percent = 60.0
            mock_memory.return_value = memory

            response = api_client.get("/api/monitoring/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["healthy"] is True
        assert data["issues"] == []
        assert "cpu_percent" in data
        assert "memory_percent" in data

    def test_health_check_high_cpu(self, api_client):
        """Test health check with high CPU usage."""
        with patch('psutil.cpu_percent', return_value=95.0), \
             patch('psutil.virtual_memory') as mock_memory:

            memory = MagicMock()
            memory.percent = 50.0
            mock_memory.return_value = memory

            response = api_client.get("/api/monitoring/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "degraded"
        assert data["healthy"] is False
        assert "High CPU usage" in data["issues"]

    def test_health_check_high_memory(self, api_client):
        """Test health check with high memory usage."""
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory:

            memory = MagicMock()
            memory.percent = 95.0
            mock_memory.return_value = memory

            response = api_client.get("/api/monitoring/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "degraded"
        assert data["healthy"] is False
        assert "High memory usage" in data["issues"]

    def test_health_check_multiple_issues(self, api_client):
        """Test health check with multiple issues."""
        with patch('psutil.cpu_percent', return_value=95.0), \
             patch('psutil.virtual_memory') as mock_memory:

            memory = MagicMock()
            memory.percent = 95.0
            mock_memory.return_value = memory

            response = api_client.get("/api/monitoring/health")

        assert response.status_code == 200
        data = response.json()

        assert data["healthy"] is False
        assert len(data["issues"]) == 2

    def test_health_check_error_handling(self, api_client):
        """Test health check error handling."""
        with patch('psutil.cpu_percent', side_effect=Exception("psutil error")):
            response = api_client.get("/api/monitoring/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert data["healthy"] is False
        assert len(data["issues"]) > 0


@pytest.mark.asyncio
class TestMonitoringIntegration:
    """Integration tests for monitoring workflows."""

    async def test_full_monitoring_workflow(self, api_client, mock_orchestrator, populated_task_storage):
        """Test complete monitoring workflow."""
        async def mock_status():
            return {"gemini": {"enabled": True, "healthy": True}}

        mock_orchestrator.get_service_status = mock_status

        with patch('oxide.web.backend.routes.monitoring.get_ws_manager') as mock_ws:
            ws_manager = MagicMock()
            ws_manager.get_connection_count.return_value = 2
            mock_ws.return_value = ws_manager

            # 1. Get metrics
            metrics_resp = api_client.get("/api/monitoring/metrics")
            assert metrics_resp.status_code == 200
            metrics = metrics_resp.json()

            # 2. Get stats
            stats_resp = api_client.get("/api/monitoring/stats")
            assert stats_resp.status_code == 200
            stats = stats_resp.json()

            # 3. Health check
            health_resp = api_client.get("/api/monitoring/health")
            assert health_resp.status_code == 200
            health = health_resp.json()

            # Verify data consistency
            assert metrics["tasks"]["total"] == stats["total_tasks"]
            assert health["healthy"] in [True, False]

    async def test_metrics_reflect_task_changes(self, api_client, mock_orchestrator, temp_task_storage):
        """Test that metrics update when tasks change."""
        async def mock_status():
            return {}

        mock_orchestrator.get_service_status = mock_status

        with patch('oxide.web.backend.routes.monitoring.get_ws_manager') as mock_ws:
            ws_manager = MagicMock()
            ws_manager.get_connection_count.return_value = 0
            mock_ws.return_value = ws_manager

            # Initial metrics
            resp1 = api_client.get("/api/monitoring/metrics")
            metrics1 = resp1.json()
            assert metrics1["tasks"]["total"] == 0

            # Add a task
            temp_task_storage.add_task("new-task", "test", [], "gemini", "quick_query")

            # Metrics should update
            resp2 = api_client.get("/api/monitoring/metrics")
            metrics2 = resp2.json()
            assert metrics2["tasks"]["total"] == 1
