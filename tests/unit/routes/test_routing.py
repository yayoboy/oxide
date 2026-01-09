"""
Test suite for routing rules API routes.

Tests cover:
- CRUD operations for routing rules
- Task type listing
- Error handling
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from oxide.web.backend.routes.routing import router


@pytest.fixture
def app():
    """Create FastAPI app with routing router"""
    app = FastAPI()
    app.include_router(router, prefix="/api/routing")
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_routing_manager():
    """Create mock routing rules manager"""
    manager = MagicMock()

    # Mock export_rules
    manager.export_rules.return_value = [
        {"task_type": "coding", "service": "qwen"},
        {"task_type": "review", "service": "gemini"}
    ]

    # Mock get_stats
    manager.get_stats.return_value = {
        "total_rules": 2,
        "rules_by_service": {"qwen": 1, "gemini": 1},
        "task_types": ["coding", "review"]
    }

    # Mock get_rule
    manager.get_rule.return_value = "qwen"

    # Mock add_rule
    manager.add_rule.return_value = {
        "task_type": "coding",
        "service": "qwen",
        "action": "created"
    }

    # Mock delete_rule
    manager.delete_rule.return_value = True

    # Mock clear_all_rules
    manager.clear_all_rules.return_value = 2

    return manager


class TestListRoutingRules:
    """Test GET /api/routing/rules"""

    def test_list_rules_success(self, client, mock_routing_manager):
        """Test listing all routing rules"""
        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', return_value=mock_routing_manager):
            response = client.get("/api/routing/rules")

        assert response.status_code == 200
        data = response.json()

        assert "rules" in data
        assert "stats" in data
        assert len(data["rules"]) == 2
        assert data["stats"]["total_rules"] == 2

    def test_list_rules_error(self, client):
        """Test error handling"""
        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', side_effect=Exception("Manager error")):
            response = client.get("/api/routing/rules")

        assert response.status_code == 500
        assert "Manager error" in response.json()["detail"]


class TestGetRoutingRule:
    """Test GET /api/routing/rules/{task_type}"""

    def test_get_rule_success(self, client, mock_routing_manager):
        """Test getting specific routing rule"""
        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', return_value=mock_routing_manager):
            response = client.get("/api/routing/rules/coding")

        assert response.status_code == 200
        data = response.json()

        assert data["task_type"] == "coding"
        assert data["service"] == "qwen"

    def test_get_rule_not_found(self, client, mock_routing_manager):
        """Test getting non-existent routing rule"""
        mock_routing_manager.get_rule.return_value = None

        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', return_value=mock_routing_manager):
            response = client.get("/api/routing/rules/nonexistent")

        assert response.status_code == 404
        assert "no routing rule found" in response.json()["detail"].lower()


class TestCreateRoutingRule:
    """Test POST /api/routing/rules"""

    def test_create_rule_success(self, client, mock_routing_manager):
        """Test creating a new routing rule"""
        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', return_value=mock_routing_manager):
            response = client.post(
                "/api/routing/rules",
                json={"task_type": "coding", "service": "qwen"}
            )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert data["rule"]["task_type"] == "coding"
        assert data["rule"]["service"] == "qwen"

    def test_create_rule_error(self, client):
        """Test error handling"""
        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', side_effect=Exception("Create error")):
            response = client.post(
                "/api/routing/rules",
                json={"task_type": "coding", "service": "qwen"}
            )

        assert response.status_code == 500
        assert "Create error" in response.json()["detail"]


class TestUpdateRoutingRule:
    """Test PUT /api/routing/rules/{task_type}"""

    def test_update_rule_success(self, client, mock_routing_manager):
        """Test updating a routing rule"""
        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', return_value=mock_routing_manager):
            response = client.put(
                "/api/routing/rules/coding",
                json={"task_type": "coding", "service": "gemini"}
            )

        assert response.status_code == 200
        data = response.json()

        assert data["message"] == "Routing rule updated"
        assert data["rule"]["task_type"] == "coding"
        assert data["rule"]["service"] == "gemini"

    def test_update_rule_mismatch(self, client, mock_routing_manager):
        """Test updating with mismatched task types"""
        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', return_value=mock_routing_manager):
            response = client.put(
                "/api/routing/rules/coding",
                json={"task_type": "review", "service": "gemini"}
            )

        assert response.status_code == 400
        assert "must match" in response.json()["detail"].lower()

    def test_update_rule_error(self, client):
        """Test error handling"""
        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', side_effect=Exception("Update error")):
            response = client.put(
                "/api/routing/rules/coding",
                json={"task_type": "coding", "service": "qwen"}
            )

        assert response.status_code == 500
        assert "Update error" in response.json()["detail"]


class TestDeleteRoutingRule:
    """Test DELETE /api/routing/rules/{task_type}"""

    def test_delete_rule_success(self, client, mock_routing_manager):
        """Test deleting a routing rule"""
        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', return_value=mock_routing_manager):
            response = client.delete("/api/routing/rules/coding")

        assert response.status_code == 200
        data = response.json()

        assert "deleted successfully" in data["message"].lower()

    def test_delete_rule_not_found(self, client, mock_routing_manager):
        """Test deleting non-existent rule"""
        mock_routing_manager.delete_rule.return_value = False

        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', return_value=mock_routing_manager):
            response = client.delete("/api/routing/rules/nonexistent")

        assert response.status_code == 404
        assert "no routing rule found" in response.json()["detail"].lower()


class TestClearRoutingRules:
    """Test POST /api/routing/rules/clear"""

    def test_clear_rules_success(self, client, mock_routing_manager):
        """Test clearing all routing rules"""
        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', return_value=mock_routing_manager):
            response = client.post("/api/routing/rules/clear")

        assert response.status_code == 200
        data = response.json()

        assert "Cleared" in data["message"]
        assert data["cleared"] == 2

    def test_clear_rules_error(self, client):
        """Test error handling"""
        with patch('src.oxide.web.backend.routes.routing.get_routing_rules_manager', side_effect=Exception("Clear error")):
            response = client.post("/api/routing/rules/clear")

        assert response.status_code == 500
        assert "Clear error" in response.json()["detail"]


class TestGetAvailableTaskTypes:
    """Test GET /api/routing/task-types"""

    def test_get_task_types(self, client):
        """Test getting available task types"""
        response = client.get("/api/routing/task-types")

        assert response.status_code == 200
        data = response.json()

        assert "task_types" in data
        assert len(data["task_types"]) > 0

        # Check first task type has required fields
        task_type = data["task_types"][0]
        assert "name" in task_type
        assert "label" in task_type
        assert "description" in task_type
        assert "recommended_services" in task_type

    def test_task_types_includes_coding(self, client):
        """Test that coding task type is included"""
        response = client.get("/api/routing/task-types")
        data = response.json()

        task_names = [t["name"] for t in data["task_types"]]
        assert "coding" in task_names
        assert "code_review" in task_names
        assert "quick_query" in task_names
