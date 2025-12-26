"""
Integration tests for Services API endpoints.

Tests all endpoints in src/oxide/web/backend/routes/services.py including:
- GET /api/services/ - List services
- GET /api/services/{service_name} - Get service info
- POST /api/services/{service_name}/health - Health check
- POST /api/services/{service_name}/test - Test service
- GET /api/services/{service_name}/models - Get models
- GET /api/services/routing/rules - Get routing rules
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestServicesAPI:
    """Test suite for Services API endpoints."""

    def test_list_services_success(self, api_client, mock_orchestrator):
        """Test listing all services."""
        # Mock get_service_status
        async def mock_status():
            return {
                "gemini": {
                    "enabled": True,
                    "healthy": True,
                    "type": "cli"
                },
                "qwen": {
                    "enabled": True,
                    "healthy": True,
                    "type": "cli"
                },
                "ollama_local": {
                    "enabled": False,
                    "healthy": False,
                    "type": "http"
                }
            }

        mock_orchestrator.get_service_status = mock_status

        response = api_client.get("/api/services/")

        assert response.status_code == 200
        data = response.json()

        assert "services" in data
        assert data["total"] == 3
        assert data["enabled"] == 2
        assert data["healthy"] == 2

    def test_list_services_empty(self, api_client, mock_orchestrator):
        """Test listing services when none are configured."""
        async def mock_status():
            return {}

        mock_orchestrator.get_service_status = mock_status

        response = api_client.get("/api/services/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_get_service_success(self, api_client, mock_orchestrator, mock_base_adapter):
        """Test getting specific service info."""
        # Add adapter to orchestrator
        mock_orchestrator.adapters = {"mock_adapter": mock_base_adapter}

        # Mock health check
        async def mock_health_check(service_name):
            return True

        mock_orchestrator._check_service_health = mock_health_check

        response = api_client.get("/api/services/mock_adapter")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "mock_adapter"
        assert data["healthy"] is True
        assert "info" in data

    def test_get_service_not_found(self, api_client, mock_orchestrator):
        """Test getting non-existent service."""
        mock_orchestrator.adapters = {}

        response = api_client.get("/api/services/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_check_service_health_healthy(self, api_client, mock_orchestrator, mock_base_adapter):
        """Test health check for healthy service."""
        mock_orchestrator.adapters = {"test_service": mock_base_adapter}

        async def mock_health_check(service_name):
            return True

        mock_orchestrator._check_service_health = mock_health_check

        response = api_client.post("/api/services/test_service/health")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "test_service"
        assert data["healthy"] is True

    def test_check_service_health_unhealthy(self, api_client, mock_orchestrator, mock_base_adapter):
        """Test health check for unhealthy service."""
        mock_orchestrator.adapters = {"test_service": mock_base_adapter}

        async def mock_health_check(service_name):
            return False

        mock_orchestrator._check_service_health = mock_health_check

        response = api_client.post("/api/services/test_service/health")

        assert response.status_code == 200
        data = response.json()
        assert data["healthy"] is False

    def test_check_service_health_not_found(self, api_client, mock_orchestrator):
        """Test health check for non-existent service."""
        mock_orchestrator.adapters = {}

        response = api_client.post("/api/services/nonexistent/health")

        assert response.status_code == 404

    def test_test_service_success(self, api_client, mock_orchestrator):
        """Test service with test prompt."""
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()
        mock_orchestrator.adapters = {"test_service": mock_adapter}

        async def mock_test(service_name, prompt):
            return {
                "success": True,
                "response": "Test response",
                "latency_ms": 123
            }

        mock_orchestrator.test_service = mock_test

        response = api_client.post(
            "/api/services/test_service/test",
            params={"test_prompt": "Hello"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "test_service"
        assert data["test_prompt"] == "Hello"
        assert data["success"] is True

    def test_test_service_default_prompt(self, api_client, mock_orchestrator):
        """Test service with default test prompt."""
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()
        mock_orchestrator.adapters = {"test_service": mock_adapter}

        async def mock_test(service_name, prompt):
            return {"success": True, "response": "OK"}

        mock_orchestrator.test_service = mock_test

        response = api_client.post("/api/services/test_service/test")

        assert response.status_code == 200
        # Default prompt is "Hello"
        assert response.json()["test_prompt"] == "Hello"

    def test_get_service_models_success(self, api_client, mock_orchestrator, mock_base_adapter):
        """Test getting available models for a service."""
        mock_orchestrator.adapters = {"test_service": mock_base_adapter}

        response = api_client.get("/api/services/test_service/models")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "test_service"
        assert "models" in data
        assert isinstance(data["models"], list)
        # mock_base_adapter returns ["mock-model-1", "mock-model-2"]
        assert len(data["models"]) == 2

    def test_get_service_models_not_found(self, api_client, mock_orchestrator):
        """Test getting models for non-existent service."""
        mock_orchestrator.adapters = {}

        response = api_client.get("/api/services/nonexistent/models")

        assert response.status_code == 404

    def test_get_routing_rules_success(self, api_client, mock_orchestrator):
        """Test getting routing rules."""
        def mock_get_rules():
            return {
                "code_review": {
                    "primary": "qwen",
                    "fallback": ["gemini"],
                    "timeout": 120
                },
                "codebase_analysis": {
                    "primary": "gemini",
                    "fallback": ["qwen"],
                    "timeout": 300
                }
            }

        mock_orchestrator.get_routing_rules = mock_get_rules

        response = api_client.get("/api/services/routing/rules")

        assert response.status_code == 200
        data = response.json()

        assert "rules" in data
        assert "total" in data
        assert data["total"] == 2
        assert "code_review" in data["rules"]


@pytest.mark.asyncio
class TestServicesIntegration:
    """Integration tests for service-related workflows."""

    async def test_service_lifecycle(self, api_client, mock_orchestrator, mock_base_adapter):
        """Test complete service lifecycle: list, get, health check, test."""
        mock_orchestrator.adapters = {"test_service": mock_base_adapter}

        async def mock_status():
            return {"test_service": {"enabled": True, "healthy": True}}

        async def mock_health(service_name):
            return True

        async def mock_test(service_name, prompt):
            return {"success": True}

        mock_orchestrator.get_service_status = mock_status
        mock_orchestrator._check_service_health = mock_health
        mock_orchestrator.test_service = mock_test

        # 1. List services
        list_resp = api_client.get("/api/services/")
        assert list_resp.status_code == 200

        # 2. Get specific service
        get_resp = api_client.get("/api/services/test_service")
        assert get_resp.status_code == 200

        # 3. Health check
        health_resp = api_client.post("/api/services/test_service/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["healthy"] is True

        # 4. Test service
        test_resp = api_client.post("/api/services/test_service/test")
        assert test_resp.status_code == 200
        assert test_resp.json()["success"] is True

        # 5. Get models
        models_resp = api_client.get("/api/services/test_service/models")
        assert models_resp.status_code == 200
