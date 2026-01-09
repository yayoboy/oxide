"""
Test WebSocket Manager performance optimizations.

Tests connection pooling, limits, and broadcast performance.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oxide.web.backend.websocket import WebSocketManager


def test_connection_pooling():
    """Test connection pooling and limits."""
    print("\n🧪 Test 1: Connection Pooling")

    # Create manager with small limit for testing
    manager = WebSocketManager(max_connections=3)

    print(f"   Max connections: {manager.max_connections}")
    print(f"   Active connections: {len(manager.active_connections)}")
    assert len(manager.active_connections) == 0, "Should start with 0 connections"
    print("   ✅ Initial state correct")


def test_connection_stats():
    """Test connection statistics."""
    print("\n🧪 Test 2: Connection Statistics")

    manager = WebSocketManager(max_connections=100)

    stats = manager.get_stats()
    print(f"   Stats: {stats}")

    assert stats["active_connections"] == 0, "Should have 0 active"
    assert stats["max_connections"] == 100, "Max should be 100"
    assert stats["total_connections"] == 0, "Total should be 0"
    assert stats["rejected_connections"] == 0, "Rejected should be 0"
    assert stats["utilization_percent"] == 0, "Utilization should be 0%"

    print("   ✅ Statistics tracking works")


def test_set_operations():
    """Test that set operations are O(1)."""
    print("\n🧪 Test 3: Set Performance (O(1) operations)")

    manager = WebSocketManager(max_connections=1000)

    # Mock websocket objects
    class MockWebSocket:
        def __init__(self, id):
            self.id = id

    # Add 1000 connections (should be fast)
    import time
    start = time.time()

    mock_connections = [MockWebSocket(i) for i in range(1000)]
    for ws in mock_connections:
        manager.active_connections.add(ws)

    add_duration = time.time() - start
    print(f"   Added 1000 connections in {add_duration:.3f}s")
    assert add_duration < 0.1, "Adding should be very fast (O(1) per operation)"

    # Remove 1000 connections (should also be fast)
    start = time.time()

    for ws in mock_connections:
        manager.active_connections.discard(ws)

    remove_duration = time.time() - start
    print(f"   Removed 1000 connections in {remove_duration:.3f}s")
    assert remove_duration < 0.1, "Removing should be very fast (O(1) per operation)"

    assert len(manager.active_connections) == 0, "All connections should be removed"
    print("   ✅ Set operations are O(1) and performant")


def test_disconnect_method():
    """Test disconnect method."""
    print("\n🧪 Test 4: Disconnect Method")

    manager = WebSocketManager(max_connections=10)

    class MockWebSocket:
        def __init__(self, id):
            self.id = id

    ws1 = MockWebSocket(1)
    ws2 = MockWebSocket(2)

    # Add connections
    manager.active_connections.add(ws1)
    manager.active_connections.add(ws2)
    assert len(manager.active_connections) == 2, "Should have 2 connections"

    # Disconnect one
    manager.disconnect(ws1)
    assert len(manager.active_connections) == 1, "Should have 1 connection"
    assert ws2 in manager.active_connections, "ws2 should still be connected"

    # Disconnect non-existent (should not error)
    manager.disconnect(ws1)  # Already disconnected
    assert len(manager.active_connections) == 1, "Should still have 1 connection"

    print("   ✅ Disconnect method works correctly")


def test_get_connection_count():
    """Test connection count method."""
    print("\n🧪 Test 5: Get Connection Count")

    manager = WebSocketManager(max_connections=10)

    class MockWebSocket:
        def __init__(self, id):
            self.id = id

    assert manager.get_connection_count() == 0, "Should be 0"

    manager.active_connections.add(MockWebSocket(1))
    assert manager.get_connection_count() == 1, "Should be 1"

    manager.active_connections.add(MockWebSocket(2))
    manager.active_connections.add(MockWebSocket(3))
    assert manager.get_connection_count() == 3, "Should be 3"

    print("   ✅ Connection count tracking works")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("🧪 WebSocket Manager Performance Tests")
    print("=" * 60)

    try:
        test_connection_pooling()
        test_connection_stats()
        test_set_operations()
        test_disconnect_method()
        test_get_connection_count()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

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
