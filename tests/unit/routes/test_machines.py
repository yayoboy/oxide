"""
Test suite for machine monitoring API routes.

Tests cover:
- Machine listing with local and remote machines
- Service discovery and grouping
- System metrics collection
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from oxide.web.backend.routes.machines import router


@pytest.fixture
def app():
    """Create FastAPI app with machines router"""
    app = FastAPI()
    app.include_router(router, prefix="/api/machines")
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_orchestrator():
    """Create mock orchestrator"""
    orchestrator = MagicMock()
    orchestrator.get_service_status = AsyncMock()
    return orchestrator


@pytest.fixture
def mock_psutil():
    """Mock psutil metrics"""
    with patch('oxide.web.backend.routes.machines.psutil') as mock:
        # Mock CPU
        mock.cpu_percent.return_value = 45.5

        # Mock memory
        mock_memory = MagicMock()
        mock_memory.percent = 62.3
        mock_memory.used = 8192 * 1024 * 1024  # 8192 MB
        mock_memory.total = 16384 * 1024 * 1024  # 16384 MB
        mock.virtual_memory.return_value = mock_memory

        # Mock disk
        mock_disk = MagicMock()
        mock_disk.percent = 75.0
        mock_disk.used = 250 * 1024 * 1024 * 1024  # 250 GB
        mock_disk.total = 500 * 1024 * 1024 * 1024  # 500 GB
        mock.disk_usage.return_value = mock_disk

        yield mock


def override_get_orchestrator(mock_orch):
    """Override dependency"""
    from oxide.web.backend.routes.machines import get_orchestrator

    def _override():
        return mock_orch

    return _override


class TestListMachines:
    """Test GET /api/machines/"""

    def test_list_machines_local_only(self, client, mock_orchestrator, mock_psutil, app):
        """Test listing machines with only local services"""
        mock_orchestrator.get_service_status.return_value = {
            "qwen": {
                "enabled": True,
                "healthy": True,
                "info": {"type": "cli", "command": "qwen"}
            }
        }

        # Override dependency
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/")

        assert response.status_code == 200
        data = response.json()

        assert "machines" in data
        assert data["total"] == 1
        assert data["online"] == 1

        # Check local machine
        local = next(m for m in data["machines"] if m["id"] == "local")
        assert local["name"] == "Local Machine"
        assert local["status"] == "online"
        assert local["metrics"]["cpu_percent"] == 45.5
        assert local["metrics"]["memory_percent"] == 62.3

    def test_list_machines_with_local_http_service(self, client, mock_orchestrator, mock_psutil, app):
        """Test listing with local HTTP service (localhost)"""
        mock_orchestrator.get_service_status.return_value = {
            "ollama_local": {
                "enabled": True,
                "healthy": True,
                "info": {
                    "type": "http",
                    "base_url": "http://localhost:11434"
                }
            }
        }

        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        local = next(m for m in data["machines"] if m["id"] == "local")

        # Service should be added to local machine
        assert len(local["services"]) == 1
        assert local["services"][0]["name"] == "ollama_local"
        assert local["services"][0]["healthy"] is True
        assert local["services"][0]["endpoint"] == "http://localhost:11434"

    def test_list_machines_with_remote_http_service(self, client, mock_orchestrator, mock_psutil, app):
        """Test listing with remote HTTP service"""
        mock_orchestrator.get_service_status.return_value = {
            "remote_gemini": {
                "enabled": True,
                "healthy": True,
                "info": {
                    "type": "http",
                    "base_url": "http://api.example.com:8080/llm"
                }
            }
        }

        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/")

        assert response.status_code == 200
        data = response.json()

        # Should have local + remote machine
        assert data["total"] == 2
        assert data["online"] == 2

        # Check remote machine
        remote = next((m for m in data["machines"] if m["id"].startswith("remote_")), None)
        assert remote is not None
        assert remote["name"] == "Remote Server (api.example.com)"
        assert remote["location"] == "api.example.com"
        assert remote["status"] == "online"
        assert remote["metrics"]["cpu_percent"] is None  # Unknown for remote

        # Check service
        assert len(remote["services"]) == 1
        assert remote["services"][0]["name"] == "remote_gemini"

    def test_list_machines_multiple_services_same_remote(self, client, mock_orchestrator, mock_psutil, app):
        """Test multiple services on same remote machine"""
        mock_orchestrator.get_service_status.return_value = {
            "service1": {
                "enabled": True,
                "healthy": True,
                "info": {
                    "type": "http",
                    "base_url": "http://remote.server.com:8000/api"
                }
            },
            "service2": {
                "enabled": True,
                "healthy": False,
                "info": {
                    "type": "http",
                    "base_url": "http://remote.server.com:9000/api"
                }
            }
        }

        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/")

        assert response.status_code == 200
        data = response.json()

        remote = next((m for m in data["machines"] if m["id"].startswith("remote_")), None)
        assert remote is not None

        # Both services should be on same machine
        assert len(remote["services"]) == 2
        assert remote["status"] == "online"  # At least one healthy

    def test_list_machines_unhealthy_remote(self, client, mock_orchestrator, mock_psutil, app):
        """Test remote machine with only unhealthy services"""
        mock_orchestrator.get_service_status.return_value = {
            "broken_service": {
                "enabled": True,
                "healthy": False,
                "info": {
                    "type": "http",
                    "base_url": "http://broken.server.com:8000"
                }
            }
        }

        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/")

        assert response.status_code == 200
        data = response.json()

        remote = next((m for m in data["machines"] if m["id"].startswith("remote_")), None)
        assert remote is not None
        assert remote["status"] == "offline"

    def test_list_machines_mixed_cli_and_http(self, client, mock_orchestrator, mock_psutil, app):
        """Test mixed CLI and HTTP services"""
        mock_orchestrator.get_service_status.return_value = {
            "qwen": {
                "enabled": True,
                "healthy": True,
                "info": {"type": "cli", "command": "qwen"}
            },
            "ollama": {
                "enabled": True,
                "healthy": True,
                "info": {
                    "type": "http",
                    "base_url": "http://localhost:11434"
                }
            },
            "remote_api": {
                "enabled": True,
                "healthy": True,
                "info": {
                    "type": "http",
                    "base_url": "http://api.remote.com"
                }
            }
        }

        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/")

        assert response.status_code == 200
        data = response.json()

        # Local + Remote
        assert data["total"] == 2

        local = next(m for m in data["machines"] if m["id"] == "local")
        # Only ollama should be in services (CLI services not included)
        assert len(local["services"]) == 1
        assert local["services"][0]["name"] == "ollama"

    def test_list_machines_no_base_url(self, client, mock_orchestrator, mock_psutil, app):
        """Test HTTP service without base_url is skipped"""
        mock_orchestrator.get_service_status.return_value = {
            "broken_http": {
                "enabled": True,
                "healthy": True,
                "info": {
                    "type": "http",
                    # Missing base_url
                }
            }
        }

        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/")

        assert response.status_code == 200
        data = response.json()

        # Only local machine, no remote
        assert data["total"] == 1
        local = data["machines"][0]
        assert len(local["services"]) == 0

    def test_list_machines_error_handling(self, client, mock_orchestrator, mock_psutil, app):
        """Test error handling when orchestrator fails"""
        mock_orchestrator.get_service_status.side_effect = Exception("Orchestrator error")

        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/")

        assert response.status_code == 200
        data = response.json()

        # Should return error gracefully
        assert "error" in data
        assert data["total"] == 0
        assert data["machines"] == []


class TestGetMachine:
    """Test GET /api/machines/{machine_id}"""

    def test_get_local_machine(self, client, mock_orchestrator, mock_psutil, app):
        """Test getting local machine details"""
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/local")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "local"
        assert data["name"] == "Local Machine"
        assert data["status"] == "online"

        # Should have disk metrics (not in list endpoint)
        assert "disk_percent" in data["metrics"]
        assert data["metrics"]["disk_percent"] == 75.0
        assert data["metrics"]["disk_used_gb"] == 250.0
        assert data["metrics"]["disk_total_gb"] == 500.0

    def test_get_remote_machine_not_implemented(self, client, mock_orchestrator, mock_psutil, app):
        """Test getting remote machine (not yet implemented)"""
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/remote_server_com")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "remote_server_com"
        assert "error" in data
        assert "not yet implemented" in data["error"].lower()

    def test_get_machine_error_handling(self, client, mock_orchestrator, app):
        """Test error handling when psutil fails"""
        with patch('oxide.web.backend.routes.machines.psutil') as mock_psutil:
            mock_psutil.cpu_percent.side_effect = Exception("CPU error")

            app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

            response = client.get("/api/machines/local")

            assert response.status_code == 200
            data = response.json()

            assert "error" in data


class TestServiceTypeVariations:
    """Test different service type formats"""

    def test_service_type_http_only(self, client, mock_orchestrator, mock_psutil, app):
        """Test service type as 'http'"""
        mock_orchestrator.get_service_status.return_value = {
            "service": {
                "enabled": True,
                "healthy": True,
                "info": {
                    "type": "http",
                    "base_url": "http://localhost:8000"
                }
            }
        }

        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/")
        assert response.status_code == 200
        data = response.json()

        local = data["machines"][0]
        assert len(local["services"]) == 1

    def test_service_type_servicetype_http(self, client, mock_orchestrator, mock_psutil, app):
        """Test service type as 'ServiceType.HTTP'"""
        mock_orchestrator.get_service_status.return_value = {
            "service": {
                "enabled": True,
                "healthy": True,
                "info": {
                    "type": "ServiceType.HTTP",
                    "base_url": "http://localhost:8000"
                }
            }
        }

        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/")
        assert response.status_code == 200
        data = response.json()

        local = data["machines"][0]
        assert len(local["services"]) == 1

    def test_service_type_case_insensitive(self, client, mock_orchestrator, mock_psutil, app):
        """Test service type check is case-insensitive"""
        mock_orchestrator.get_service_status.return_value = {
            "service": {
                "enabled": True,
                "healthy": True,
                "info": {
                    "type": "HTTP",
                    "base_url": "http://localhost:8000"
                }
            }
        }

        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

        response = client.get("/api/machines/")
        assert response.status_code == 200
        data = response.json()

        local = data["machines"][0]
        assert len(local["services"]) == 1


# Import statement that needs to be at module level for dependency override
from oxide.web.backend.routes.machines import get_orchestrator
