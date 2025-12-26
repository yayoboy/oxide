"""
Tests for Configuration Hot Reload System

Tests hot reload functionality:
- File watching
- Configuration reload
- Change detection
- Callback system
"""
import pytest
import tempfile
import time
import yaml
from pathlib import Path

from oxide.config.hot_reload import HotReloadManager, ConfigChangeEvent
from oxide.config.loader import Config


@pytest.fixture
def temp_config_file():
    """Create a temporary configuration file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        # Write minimal valid config
        config_data = {
            "services": {
                "test_service": {
                    "type": "cli",
                    "executable": "test",
                    "enabled": True
                }
            },
            "routing_rules": {
                "test_task": {
                    "primary": "test_service",
                    "fallback": []
                }
            },
            "execution": {
                "max_parallel_workers": 3,
                "timeout_seconds": 120
            },
            "logging": {
                "level": "INFO",
                "console": True
            }
        }
        yaml.dump(config_data, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


def test_hot_reload_manager_initialization(temp_config_file):
    """Test hot reload manager initialization"""
    manager = HotReloadManager(
        config_path=temp_config_file,
        auto_reload=False
    )

    assert manager.config_path == temp_config_file
    assert manager.auto_reload is False
    assert manager.current_config is None
    assert manager.reload_count == 0


def test_hot_reload_manager_start(temp_config_file):
    """Test starting hot reload manager"""
    manager = HotReloadManager(
        config_path=temp_config_file,
        auto_reload=True
    )

    # Start manager
    manager.start()

    # Check that configuration was loaded
    assert manager.current_config is not None
    assert isinstance(manager.current_config, Config)
    assert "test_service" in manager.current_config.services

    # Cleanup
    manager.stop()


def test_manual_reload(temp_config_file):
    """Test manual configuration reload"""
    manager = HotReloadManager(
        config_path=temp_config_file,
        auto_reload=False
    )
    manager.start()

    # Get initial reload count
    initial_count = manager.reload_count

    # Modify configuration file
    with open(temp_config_file, 'r') as f:
        config_data = yaml.safe_load(f)

    # Add a second service first (so we can disable the first one)
    config_data['services']['test_service2'] = {
        "type": "cli",
        "executable": "test2",
        "enabled": True
    }
    config_data['services']['test_service']['enabled'] = False

    with open(temp_config_file, 'w') as f:
        yaml.dump(config_data, f)

    # Manually reload
    new_config = manager.reload()

    # Check reload happened
    assert manager.reload_count == initial_count + 1
    assert new_config.services['test_service'].enabled is False
    assert new_config.services['test_service2'].enabled is True

    # Cleanup
    manager.stop()


def test_change_detection(temp_config_file):
    """Test configuration change detection"""
    manager = HotReloadManager(
        config_path=temp_config_file,
        auto_reload=False
    )
    manager.start()

    # Modify service
    with open(temp_config_file, 'r') as f:
        config_data = yaml.safe_load(f)

    # Add a second service and disable first
    config_data['services']['test_service2'] = {
        "type": "cli",
        "executable": "test2",
        "enabled": True
    }
    config_data['services']['test_service']['enabled'] = False

    with open(temp_config_file, 'w') as f:
        yaml.dump(config_data, f)

    # Reload
    manager.reload()

    # Check last reload time was updated
    assert manager.last_reload_time is not None
    assert manager.last_reload_success is True

    # Cleanup
    manager.stop()


def test_reload_callback(temp_config_file):
    """Test reload callback system"""
    manager = HotReloadManager(
        config_path=temp_config_file,
        auto_reload=False
    )
    manager.start()

    # Add callback
    callback_called = False
    callback_event = None

    def on_reload(event: ConfigChangeEvent):
        nonlocal callback_called, callback_event
        callback_called = True
        callback_event = event

    manager.add_reload_callback(on_reload)

    # Modify config
    with open(temp_config_file, 'r') as f:
        config_data = yaml.safe_load(f)

    # Add another service (valid change)
    config_data['services']['test_service2'] = {
        "type": "cli",
        "executable": "test2",
        "enabled": True
    }

    with open(temp_config_file, 'w') as f:
        yaml.dump(config_data, f)

    # Reload
    manager.reload()

    # Check callback was called
    assert callback_called is True
    assert callback_event is not None
    assert isinstance(callback_event, ConfigChangeEvent)

    # Cleanup
    manager.stop()


def test_get_stats(temp_config_file):
    """Test getting reload statistics"""
    manager = HotReloadManager(
        config_path=temp_config_file,
        auto_reload=True
    )
    manager.start()

    # Get stats
    stats = manager.get_stats()

    assert "auto_reload_enabled" in stats
    assert stats["auto_reload_enabled"] is True
    assert "reload_count" in stats
    assert "watching" in stats
    assert "config_path" in stats

    # Cleanup
    manager.stop()


def test_change_detection_details(temp_config_file):
    """Test detailed change detection"""
    manager = HotReloadManager(
        config_path=temp_config_file,
        auto_reload=True  # Need auto_reload=True to load initial config
    )
    manager.start()

    # Get initial service count
    initial_service_count = len(manager.current_config.services)

    # Add new service
    with open(temp_config_file, 'r') as f:
        config_data = yaml.safe_load(f)

    config_data['services']['new_service'] = {
        "type": "cli",
        "executable": "new",
        "enabled": True
    }

    with open(temp_config_file, 'w') as f:
        yaml.dump(config_data, f)

    # Reload
    new_config = manager.reload()

    # Check new service was added
    assert len(new_config.services) == initial_service_count + 1
    assert "new_service" in new_config.services

    # Cleanup
    manager.stop()


def test_invalid_config_reload(temp_config_file):
    """Test reload with invalid configuration"""
    manager = HotReloadManager(
        config_path=temp_config_file,
        auto_reload=False
    )
    manager.start()

    # Write invalid config (missing required fields)
    with open(temp_config_file, 'w') as f:
        f.write("invalid: yaml: content")

    # Try to reload - should raise error
    with pytest.raises(Exception):
        manager.reload()

    # Last reload should be marked as failed
    assert manager.last_reload_success is False

    # Cleanup
    manager.stop()


def test_callback_error_handling(temp_config_file):
    """Test that callback errors don't break reload"""
    manager = HotReloadManager(
        config_path=temp_config_file,
        auto_reload=False
    )
    manager.start()

    # Add callback that raises error
    def bad_callback(event):
        raise ValueError("Callback error")

    manager.add_reload_callback(bad_callback)

    # Modify config
    with open(temp_config_file, 'r') as f:
        config_data = yaml.safe_load(f)

    # Add another service (valid change)
    config_data['services']['test_service2'] = {
        "type": "cli",
        "executable": "test2",
        "enabled": True
    }

    with open(temp_config_file, 'w') as f:
        yaml.dump(config_data, f)

    # Reload should succeed despite callback error
    new_config = manager.reload()
    assert new_config is not None

    # Cleanup
    manager.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
