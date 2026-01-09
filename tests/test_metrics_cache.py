"""
Test MetricsCache performance optimizations.

Tests caching behavior, TTL, and async operations.
"""
import asyncio
import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oxide.utils.metrics_cache import MetricsCache, get_metrics_cache


def test_basic_cache():
    """Test basic cache get/set operations."""
    print("\n🧪 Test 1: Basic Cache Operations")
    cache = MetricsCache(ttl=1.0)

    # Set value
    cache.set("test_key", "test_value")

    # Get value (should be cached)
    value = cache.get("test_key")
    assert value == "test_value", "Cache get failed"
    print("   ✅ Cache set/get works")

    # Wait for TTL expiration
    time.sleep(1.1)

    # Get expired value (should return None)
    value = cache.get("test_key")
    assert value is None, "Cache didn't expire"
    print("   ✅ TTL expiration works")


def test_get_or_compute():
    """Test get_or_compute with expensive operation."""
    print("\n🧪 Test 2: Get or Compute")
    cache = MetricsCache(ttl=2.0)

    call_count = {"count": 0}

    def expensive_operation():
        call_count["count"] += 1
        time.sleep(0.1)  # Simulate expensive operation
        return f"result_{call_count['count']}"

    # First call - should compute
    start = time.time()
    result1 = cache.get_or_compute("expensive", expensive_operation)
    duration1 = time.time() - start
    print(f"   First call: {result1} (took {duration1:.3f}s)")
    assert call_count["count"] == 1, "Should compute on first call"
    assert duration1 >= 0.1, "Should take time to compute"

    # Second call - should use cache
    start = time.time()
    result2 = cache.get_or_compute("expensive", expensive_operation)
    duration2 = time.time() - start
    print(f"   Second call: {result2} (took {duration2:.3f}s)")
    assert call_count["count"] == 1, "Should NOT recompute (cached)"
    assert duration2 < 0.01, "Should be instant (cached)"
    assert result1 == result2, "Results should match"
    print("   ✅ Cache prevents recomputation")


async def test_async_get_or_compute():
    """Test async get_or_compute with executor."""
    print("\n🧪 Test 3: Async Get or Compute")
    cache = MetricsCache(ttl=2.0)

    call_count = {"count": 0}

    def blocking_operation():
        """Simulates blocking CPU operation like psutil.cpu_percent()."""
        call_count["count"] += 1
        time.sleep(0.1)  # Blocking call
        return f"cpu_{call_count['count']}%"

    # First call - should run in executor
    start = time.time()
    result1 = await cache.get_or_compute_async(
        "cpu_percent",
        blocking_operation,
        use_executor=True
    )
    duration1 = time.time() - start
    print(f"   First call: {result1} (took {duration1:.3f}s)")
    assert call_count["count"] == 1, "Should compute on first call"

    # Second call - should use cache
    start = time.time()
    result2 = await cache.get_or_compute_async(
        "cpu_percent",
        blocking_operation,
        use_executor=True
    )
    duration2 = time.time() - start
    print(f"   Second call: {result2} (took {duration2:.3f}s)")
    assert call_count["count"] == 1, "Should NOT recompute (cached)"
    assert duration2 < 0.01, "Should be instant (cached)"
    print("   ✅ Async cache with executor works")


async def test_concurrent_requests():
    """Test that concurrent requests don't duplicate expensive operations."""
    print("\n🧪 Test 4: Concurrent Request Deduplication")
    cache = MetricsCache(ttl=2.0)

    call_count = {"count": 0}

    def expensive_operation():
        call_count["count"] += 1
        time.sleep(0.2)  # Expensive operation
        return f"result_{call_count['count']}"

    # Make 5 concurrent requests for same key
    tasks = [
        cache.get_or_compute_async("concurrent_key", expensive_operation, use_executor=True)
        for _ in range(5)
    ]

    start = time.time()
    results = await asyncio.gather(*tasks)
    duration = time.time() - start

    print(f"   5 concurrent requests completed in {duration:.3f}s")
    print(f"   Results: {results}")
    print(f"   Expensive operation called: {call_count['count']} times")

    # Should only compute once (lock prevents duplicates)
    assert call_count["count"] == 1, f"Should compute only once, but called {call_count['count']} times"
    assert all(r == results[0] for r in results), "All results should be identical"
    print("   ✅ Lock prevents duplicate computations")


def test_cache_stats():
    """Test cache statistics."""
    print("\n🧪 Test 5: Cache Statistics")
    cache = MetricsCache(ttl=1.0)

    # Add some entries
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    stats = cache.get_stats()
    print(f"   Stats: {stats}")
    assert stats["total_entries"] == 3, "Should have 3 entries"
    assert stats["valid_entries"] == 3, "All should be valid"
    assert stats["expired_entries"] == 0, "None should be expired"

    # Wait for expiration
    time.sleep(1.1)

    stats = cache.get_stats()
    print(f"   Stats after TTL: {stats}")
    assert stats["expired_entries"] == 3, "All should be expired"
    print("   ✅ Stats tracking works")


async def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("🧪 MetricsCache Performance Tests")
    print("=" * 60)

    try:
        # Sync tests
        test_basic_cache()
        test_get_or_compute()
        test_cache_stats()

        # Async tests
        await test_async_get_or_compute()
        await test_concurrent_requests()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

        # Test global instance
        print("\n🧪 Test 6: Global Instance")
        cache1 = get_metrics_cache()
        cache2 = get_metrics_cache()
        assert cache1 is cache2, "Should return same instance"
        print("   ✅ Singleton pattern works")

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
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
