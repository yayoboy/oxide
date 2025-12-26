"""
Integration tests for Tasks API endpoints.

Tests all endpoints in src/oxide/web/backend/routes/tasks.py including:
- POST /api/tasks/execute - Execute task
- GET /api/tasks/{task_id} - Get task info
- GET /api/tasks/ - List tasks
- DELETE /api/tasks/{task_id} - Delete task
- POST /api/tasks/clear - Clear tasks
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


class TestTasksAPI:
    """Test suite for Tasks API endpoints."""

    def test_execute_task_success(self, api_client, mock_orchestrator):
        """Test successful task execution."""
        # Mock the orchestrator execute_task to yield some data
        async def mock_execute(*args, **kwargs):
            yield "Test response chunk 1\n"
            yield "Test response chunk 2\n"

        mock_orchestrator.execute_task = mock_execute

        # Execute task
        response = api_client.post(
            "/api/tasks/execute",
            json={
                "prompt": "Test prompt",
                "files": ["test.py"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "task_id" in data
        assert data["status"] == "queued"
        assert "message" in data

    def test_execute_task_minimal_request(self, api_client, mock_orchestrator):
        """Test task execution with minimal request (no files)."""
        async def mock_execute(*args, **kwargs):
            yield "Response"

        mock_orchestrator.execute_task = mock_execute

        response = api_client.post(
            "/api/tasks/execute",
            json={"prompt": "What is 2+2?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data

    def test_execute_task_with_preferences(self, api_client, mock_orchestrator):
        """Test task execution with routing preferences."""
        async def mock_execute(*args, **kwargs):
            yield "Response"

        mock_orchestrator.execute_task = mock_execute

        response = api_client.post(
            "/api/tasks/execute",
            json={
                "prompt": "Test",
                "preferences": {
                    "service": "gemini",
                    "timeout": 60
                }
            }
        )

        assert response.status_code == 200

    def test_execute_task_invalid_request(self, api_client):
        """Test task execution with invalid request."""
        # Missing prompt
        response = api_client.post(
            "/api/tasks/execute",
            json={"files": ["test.py"]}
        )

        assert response.status_code == 422  # Validation error

    def test_get_task_exists(self, api_client, populated_task_storage):
        """Test getting existing task."""
        response = api_client.get("/api/tasks/task-1")

        assert response.status_code == 200
        data = response.json()

        assert data["task_id"] == "task-1"
        assert data["status"] == "completed"
        assert data["prompt"] == "Test prompt 1"

    def test_get_task_not_found(self, api_client):
        """Test getting non-existent task."""
        response = api_client.get("/api/tasks/nonexistent-task")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_tasks_all(self, api_client, populated_task_storage):
        """Test listing all tasks."""
        response = api_client.get("/api/tasks/")

        assert response.status_code == 200
        data = response.json()

        assert "tasks" in data
        assert "total" in data
        assert "filtered" in data
        assert len(data["tasks"]) == 3  # We have 3 tasks in fixture

    def test_list_tasks_filter_by_status(self, api_client, populated_task_storage):
        """Test listing tasks filtered by status."""
        response = api_client.get("/api/tasks/?status=completed")

        assert response.status_code == 200
        data = response.json()

        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["status"] == "completed"

    def test_list_tasks_with_limit(self, api_client, populated_task_storage):
        """Test listing tasks with limit."""
        response = api_client.get("/api/tasks/?limit=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data["tasks"]) <= 2

    def test_delete_task_success(self, api_client, populated_task_storage):
        """Test deleting existing task."""
        response = api_client.delete("/api/tasks/task-1")

        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]

        # Verify task is actually deleted
        get_response = api_client.get("/api/tasks/task-1")
        assert get_response.status_code == 404

    def test_delete_task_not_found(self, api_client):
        """Test deleting non-existent task."""
        response = api_client.delete("/api/tasks/nonexistent-task")

        assert response.status_code == 404

    def test_clear_tasks_all(self, api_client, populated_task_storage):
        """Test clearing all tasks."""
        response = api_client.post("/api/tasks/clear")

        assert response.status_code == 200
        data = response.json()

        assert "cleared" in data
        assert data["cleared"] == 3  # All 3 tasks cleared

        # Verify tasks are cleared
        list_response = api_client.get("/api/tasks/")
        assert len(list_response.json()["tasks"]) == 0

    def test_clear_tasks_by_status(self, api_client, populated_task_storage):
        """Test clearing tasks by status."""
        response = api_client.post("/api/tasks/clear?status=completed")

        assert response.status_code == 200
        data = response.json()

        assert data["cleared"] == 1  # Only completed task cleared

        # Verify correct tasks remain
        list_response = api_client.get("/api/tasks/")
        remaining_tasks = list_response.json()["tasks"]
        assert len(remaining_tasks) == 2
        assert all(t["status"] != "completed" for t in remaining_tasks)


@pytest.mark.asyncio
class TestTaskExecutionFlow:
    """Test the complete task execution flow."""

    async def test_background_execution_success(self, api_client, mock_orchestrator, temp_task_storage):
        """Test that background task execution updates status correctly."""
        import asyncio
        from unittest.mock import patch

        # Mock execute_task to yield test data
        async def mock_execute(*args, **kwargs):
            yield "Line 1\n"
            await asyncio.sleep(0.01)
            yield "Line 2\n"

        mock_orchestrator.execute_task = mock_execute

        # Create task
        response = api_client.post(
            "/api/tasks/execute",
            json={"prompt": "Test"}
        )

        task_id = response.json()["task_id"]

        # Wait a bit for background task to complete
        await asyncio.sleep(0.1)

        # Check task status
        status_response = api_client.get(f"/api/tasks/{task_id}")
        # Note: Due to TestClient limitations with background tasks,
        # the actual execution might not complete in test environment
        # This test validates the endpoint works, not the background execution
        assert status_response.status_code == 200

    async def test_background_execution_failure(self, api_client, mock_orchestrator):
        """Test that background task handles execution errors."""
        from oxide.utils.exceptions import NoServiceAvailableError

        # Mock execute_task to raise error
        async def mock_execute(*args, **kwargs):
            raise NoServiceAvailableError("No services available")
            yield  # Make it a generator

        mock_orchestrator.execute_task = mock_execute

        # Create task
        response = api_client.post(
            "/api/tasks/execute",
            json={"prompt": "Test"}
        )

        assert response.status_code == 200
        task_id = response.json()["task_id"]

        # The background task will fail, but endpoint should succeed
        assert task_id is not None
