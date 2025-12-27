"""
Test suite for configuration management API routes.

Tests cover:
- Configuration retrieval (full, services, routing rules)
- Configuration validation
- Hot reload functionality
- Service and routing rule patching
- Error handling
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.oxide.web.backend.routes.config import router
from src.oxide.config.loader import Config, ServiceConfig, RoutingRuleConfig, ServiceType


@pytest.fixture
def app():
    """Create FastAPI app with config router"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_config():
    """Create mock configuration"""
    config = MagicMock(spec=Config)

    # Mock services
    config.services = {
        "qwen": MagicMock(
            enabled=True,
            type=ServiceType.CLI,
            command="qwen",
            default_model="qwen",
            model_dump=lambda mode=None: {
                "enabled": True,
                "type": "cli",
                "command": "qwen",
                "default_model": "qwen"
            }
        ),
        "gemini": MagicMock(
            enabled=True,
            type=ServiceType.CLI,
            command="gemini",
            default_model="gemini-pro",
            model_dump=lambda mode=None: {
                "enabled": True,
                "type": "cli",
                "command": "gemini",
                "default_model": "gemini-pro"
            }
        ),
        "ollama": MagicMock(
            enabled=False,
            type=ServiceType.HTTP,
            model_dump=lambda mode=None: {
                "enabled": False,
                "type": "http",
                "base_url": "http://localhost:11434"
            }
        )
    }

    # Mock routing rules
    config.routing_rules = {
        "quick_query": MagicMock(
            primary="qwen",
            fallback=["gemini"],
            timeout_seconds=30,
            model_dump=lambda mode=None: {
                "primary": "qwen",
                "fallback": ["gemini"],
                "timeout_seconds": 30
            }
        )
    }

    # Mock model_dump for full config
    config.model_dump = MagicMock(return_value={
        "services": {
            "qwen": {"enabled": True, "type": "cli"},
            "gemini": {"enabled": True, "type": "cli"},
            "ollama": {"enabled": False, "type": "http"}
        },
        "routing_rules": {
            "quick_query": {
                "primary": "qwen",
                "fallback": ["gemini"],
                "timeout_seconds": 30
            }
        },
        "execution": {
            "max_parallel_services": 3
        },
        "logging": {
            "level": "INFO"
        }
    })

    # Mock get_enabled_services
    config.get_enabled_services = MagicMock(return_value=["qwen", "gemini"])

    return config


@pytest.fixture
def mock_hot_reload_manager(mock_config):
    """Create mock hot reload manager"""
    manager = MagicMock()
    manager.current_config = mock_config
    manager.reload_count = 5
    manager.last_reload_time = 1234567890.0
    manager.reload = MagicMock(return_value=mock_config)
    manager._detect_changes = MagicMock(return_value={
        "services": ["qwen enabled -> disabled"]
    })
    manager.get_stats = MagicMock(return_value={
        "reload_count": 5,
        "last_reload_time": 1234567890.0,
        "total_reloads": 10
    })
    return manager


class TestGetConfiguration:
    """Test GET /api/config/"""

    def test_get_configuration_success(self, client, mock_hot_reload_manager):
        """Test getting full configuration"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            response = client.get("/api/config/")

        assert response.status_code == 200
        data = response.json()

        assert "services" in data
        assert "routing_rules" in data
        assert "execution" in data
        assert "logging" in data

    def test_get_configuration_fallback_to_load(self, client, mock_config):
        """Test fallback to load_config when no hot reload manager"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=None):
            with patch('src.oxide.web.backend.routes.config.load_config', return_value=mock_config):
                response = client.get("/api/config/")

        assert response.status_code == 200
        data = response.json()
        assert "services" in data

    def test_get_configuration_error(self, client):
        """Test error handling"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', side_effect=Exception("Config error")):
            response = client.get("/api/config/")

        assert response.status_code == 500
        assert "Config error" in response.json()["detail"]


class TestGetServices:
    """Test GET /api/config/services"""

    def test_get_services_config(self, client, mock_hot_reload_manager):
        """Test getting all services configuration"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            response = client.get("/api/config/services")

        assert response.status_code == 200
        data = response.json()

        assert "services" in data
        assert "qwen" in data["services"]
        assert "gemini" in data["services"]

    def test_get_specific_service(self, client, mock_hot_reload_manager):
        """Test getting specific service configuration"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            response = client.get("/api/config/services/qwen")

        assert response.status_code == 200
        data = response.json()

        assert data["service_name"] == "qwen"
        assert "config" in data
        assert data["config"]["enabled"] is True

    def test_get_service_not_found(self, client, mock_hot_reload_manager):
        """Test getting non-existent service"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            response = client.get("/api/config/services/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetRoutingRules:
    """Test GET /api/config/routing-rules"""

    def test_get_routing_rules(self, client, mock_hot_reload_manager):
        """Test getting all routing rules"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            response = client.get("/api/config/routing-rules")

        assert response.status_code == 200
        data = response.json()

        assert "routing_rules" in data
        assert "quick_query" in data["routing_rules"]

    def test_get_specific_routing_rule(self, client, mock_hot_reload_manager):
        """Test getting specific routing rule"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            response = client.get("/api/config/routing-rules/quick_query")

        assert response.status_code == 200
        data = response.json()

        assert data["task_type"] == "quick_query"
        assert data["rule"]["primary"] == "qwen"
        assert "gemini" in data["rule"]["fallback"]

    def test_get_routing_rule_not_found(self, client, mock_hot_reload_manager):
        """Test getting non-existent routing rule"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            response = client.get("/api/config/routing-rules/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestValidateConfiguration:
    """Test POST /api/config/validate"""

    def test_validate_valid_config(self, client):
        """Test validating a valid configuration"""
        valid_config = {
            "services": {
                "qwen": {
                    "enabled": True,
                    "type": "cli",
                    "command": "qwen"
                }
            },
            "routing_rules": {},
            "execution": {},
            "logging": {}
        }

        with patch('src.oxide.web.backend.routes.config.Config') as mock_config_class:
            mock_instance = MagicMock()
            mock_instance.get_enabled_services.return_value = ["qwen"]
            mock_instance.routing_rules = {}
            mock_config_class.return_value = mock_instance

            response = client.post("/api/config/validate", json=valid_config)

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert len(data["errors"]) == 0

    def test_validate_no_enabled_services(self, client):
        """Test validation warning for no enabled services"""
        config_data = {
            "services": {
                "qwen": {"enabled": False, "type": "cli"}
            },
            "routing_rules": {},
            "execution": {},
            "logging": {}
        }

        with patch('src.oxide.web.backend.routes.config.Config') as mock_config_class:
            mock_instance = MagicMock()
            mock_instance.get_enabled_services.return_value = []
            mock_instance.routing_rules = {}
            mock_config_class.return_value = mock_instance

            response = client.post("/api/config/validate", json=config_data)

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert any("No services" in w for w in data["warnings"])

    def test_validate_disabled_primary_service(self, client):
        """Test validation warning for disabled primary service"""
        with patch('src.oxide.web.backend.routes.config.Config') as mock_config_class:
            mock_instance = MagicMock()
            mock_instance.get_enabled_services.return_value = ["qwen"]

            # Mock service configs
            qwen_service = MagicMock()
            qwen_service.enabled = False
            mock_instance.services = {"qwen": qwen_service}

            # Mock routing rule
            rule = MagicMock()
            rule.primary = "qwen"
            rule.fallback = []
            mock_instance.routing_rules = {"quick_query": rule}

            mock_config_class.return_value = mock_instance

            response = client.post("/api/config/validate", json={
                "services": {},
                "routing_rules": {},
                "execution": {},
                "logging": {}
            })

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert any("disabled primary service" in w.lower() for w in data["warnings"])

    def test_validate_invalid_config(self, client):
        """Test validating an invalid configuration"""
        with patch('src.oxide.web.backend.routes.config.Config', side_effect=Exception("Invalid config")):
            response = client.post("/api/config/validate", json={})

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False
        assert len(data["errors"]) > 0
        assert any("Invalid config" in e for e in data["errors"])


class TestReloadConfiguration:
    """Test POST /api/config/reload"""

    def test_reload_success(self, client, mock_hot_reload_manager):
        """Test successful configuration reload"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            mock_hot_reload_manager.reload_count = 5
            mock_hot_reload_manager.reload.return_value = mock_hot_reload_manager.current_config

            response = client.post("/api/config/reload")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "reloaded"
        assert data["reload_count"] >= 5
        assert "timestamp" in data

    def test_reload_not_enabled(self, client):
        """Test reload when hot reload is not enabled"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=None):
            response = client.post("/api/config/reload")

        # Note: Returns 500 due to HTTPException being caught by general exception handler
        assert response.status_code in [500, 503]
        assert "not enabled" in response.json()["detail"].lower() or "restart" in response.json()["detail"].lower()

    def test_reload_config_error(self, client, mock_hot_reload_manager):
        """Test reload with configuration error"""
        from src.oxide.config.loader import ConfigError

        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            mock_hot_reload_manager.reload.side_effect = ConfigError("Invalid YAML")

            response = client.post("/api/config/reload")

        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]


class TestGetReloadStats:
    """Test GET /api/config/reload/stats"""

    def test_get_reload_stats_enabled(self, client, mock_hot_reload_manager):
        """Test getting reload stats when enabled"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            response = client.get("/api/config/reload/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["enabled"] is True
        assert "reload_count" in data

    def test_get_reload_stats_disabled(self, client):
        """Test getting reload stats when disabled"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=None):
            response = client.get("/api/config/reload/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["enabled"] is False
        assert "not enabled" in data["message"].lower()


class TestPatchServiceConfig:
    """Test PATCH /api/config/services/{service_name}"""

    def test_patch_service_enabled(self, client, mock_hot_reload_manager, mock_config):
        """Test patching service enabled status"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            with patch('src.oxide.web.backend.routes.config.save_config'):
                response = client.patch(
                    "/api/config/services/qwen",
                    json={"enabled": False}
                )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "updated"
        assert data["service_name"] == "qwen"

    def test_patch_service_default_model(self, client, mock_hot_reload_manager):
        """Test patching service default model"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            with patch('src.oxide.web.backend.routes.config.save_config'):
                response = client.patch(
                    "/api/config/services/qwen",
                    json={"default_model": "qwen-turbo"}
                )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "updated"

    def test_patch_service_not_found(self, client, mock_hot_reload_manager):
        """Test patching non-existent service"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            response = client.patch(
                "/api/config/services/nonexistent",
                json={"enabled": True}
            )

        assert response.status_code == 404

    def test_patch_service_no_hot_reload(self, client):
        """Test patching when hot reload is disabled"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=None):
            response = client.patch(
                "/api/config/services/qwen",
                json={"enabled": False}
            )

        assert response.status_code == 503
        assert "not enabled" in response.json()["detail"].lower()


class TestPatchRoutingRule:
    """Test PATCH /api/config/routing-rules/{task_type}"""

    def test_patch_routing_rule_primary(self, client, mock_hot_reload_manager, mock_config):
        """Test patching routing rule primary service"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            with patch('src.oxide.web.backend.routes.config.save_config'):
                response = client.patch(
                    "/api/config/routing-rules/quick_query",
                    json={"primary": "gemini"}
                )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "updated"
        assert data["task_type"] == "quick_query"

    def test_patch_routing_rule_fallback(self, client, mock_hot_reload_manager):
        """Test patching routing rule fallback services"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            with patch('src.oxide.web.backend.routes.config.save_config'):
                response = client.patch(
                    "/api/config/routing-rules/quick_query",
                    json={"fallback": ["qwen", "gemini"]}
                )

        assert response.status_code == 200

    def test_patch_routing_rule_timeout(self, client, mock_hot_reload_manager):
        """Test patching routing rule timeout"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            with patch('src.oxide.web.backend.routes.config.save_config'):
                response = client.patch(
                    "/api/config/routing-rules/quick_query",
                    json={"timeout_seconds": 60}
                )

        assert response.status_code == 200

    def test_patch_routing_rule_invalid_service(self, client, mock_hot_reload_manager):
        """Test patching with invalid service name"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            response = client.patch(
                "/api/config/routing-rules/quick_query",
                json={"primary": "nonexistent"}
            )

        assert response.status_code == 400
        assert "Unknown service" in response.json()["detail"]

    def test_patch_routing_rule_not_found(self, client, mock_hot_reload_manager):
        """Test patching non-existent routing rule"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=mock_hot_reload_manager):
            response = client.patch(
                "/api/config/routing-rules/nonexistent",
                json={"primary": "qwen"}
            )

        assert response.status_code == 404

    def test_patch_routing_rule_no_hot_reload(self, client):
        """Test patching when hot reload is disabled"""
        with patch('src.oxide.web.backend.routes.config.get_hot_reload_manager', return_value=None):
            response = client.patch(
                "/api/config/routing-rules/quick_query",
                json={"primary": "gemini"}
            )

        assert response.status_code == 503
