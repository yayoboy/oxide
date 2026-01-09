"""
Test backend integration with new performance optimizations.

Verifies that all modules import correctly and dependency injection works.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Test that all modified modules can be imported."""
    print("\n🧪 Test 1: Module Imports")

    try:
        # Core imports
        from oxide.utils.metrics_cache import MetricsCache, get_metrics_cache
        print("   ✅ MetricsCache imported")

        from oxide.web.backend.websocket import WebSocketManager
        print("   ✅ WebSocketManager imported")

        # Main app imports
        from oxide.web.backend.main import AppState, get_orchestrator, get_ws_manager, get_metrics_cache_instance
        print("   ✅ Main module imported")

        # Routes imports
        from oxide.web.backend.routes.monitoring import router as monitoring_router
        print("   ✅ Monitoring routes imported")

        return True

    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_state():
    """Test AppState container."""
    print("\n🧪 Test 2: AppState Container")

    from oxide.web.backend.main import AppState

    state = AppState()

    # Check initial state
    assert state.orchestrator is None, "Orchestrator should be None initially"
    assert state.ws_manager is None, "WS manager should be None initially"
    assert state.metrics_cache is not None, "Metrics cache should be initialized"
    assert state.hot_reload_manager is None, "Hot reload manager should be None initially"
    assert state.cluster_coordinator is None, "Cluster coordinator should be None initially"

    print("   ✅ AppState initialized correctly")

    # Check metrics cache
    cache = state.metrics_cache
    cache.set("test", "value")
    assert cache.get("test") == "value", "Cache should work"
    print("   ✅ Metrics cache in AppState works")


def test_websocket_manager_in_state():
    """Test WebSocket manager initialization in AppState."""
    print("\n🧪 Test 3: WebSocket Manager in AppState")

    from oxide.web.backend.main import AppState
    from oxide.web.backend.websocket import WebSocketManager

    state = AppState()
    state.ws_manager = WebSocketManager(max_connections=100)

    assert state.ws_manager is not None, "WS manager should be set"
    assert state.ws_manager.max_connections == 100, "Max connections should be 100"
    assert state.ws_manager.get_connection_count() == 0, "Should start with 0 connections"

    print("   ✅ WebSocket manager works in AppState")


def test_dependency_injection_pattern():
    """Test dependency injection pattern."""
    print("\n🧪 Test 4: Dependency Injection Pattern")

    from oxide.web.backend.main import AppState
    from fastapi import FastAPI

    # Create app
    app = FastAPI()

    # Create and attach state
    state = AppState()
    app.state.oxide = state

    # Verify state is accessible
    assert hasattr(app.state, 'oxide'), "App should have oxide state"
    assert app.state.oxide is state, "State should be same instance"

    print("   ✅ Dependency injection pattern works")


def test_metrics_cache_singleton():
    """Test that get_metrics_cache returns singleton."""
    print("\n🧪 Test 5: MetricsCache Singleton")

    from oxide.utils.metrics_cache import get_metrics_cache

    cache1 = get_metrics_cache()
    cache2 = get_metrics_cache()

    assert cache1 is cache2, "Should return same instance"
    print("   ✅ MetricsCache singleton works")


def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("🧪 Backend Integration Tests")
    print("=" * 60)

    try:
        if not test_imports():
            return 1

        test_app_state()
        test_websocket_manager_in_state()
        test_dependency_injection_pattern()
        test_metrics_cache_singleton()

        print("\n" + "=" * 60)
        print("✅ All integration tests passed!")
        print("=" * 60)

        print("\n📋 Summary:")
        print("   ✅ All modules import successfully")
        print("   ✅ AppState container works correctly")
        print("   ✅ WebSocket manager integrates properly")
        print("   ✅ Dependency injection pattern is valid")
        print("   ✅ MetricsCache singleton functions correctly")
        print("\n   The backend is ready to run with performance optimizations!")

        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
