"""
Unit tests for caching utilities.
"""
import pytest
import time

from oxide.utils.cache import TTLCache, HealthCheckCache


class TestTTLCache:
    """Test suite for TTLCache."""

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = TTLCache(default_ttl=10.0)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        cache = TTLCache()

        assert cache.get("nonexistent") is None

    def test_expiration(self):
        """Test that entries expire after TTL."""
        cache = TTLCache(default_ttl=0.1)  # 100ms TTL

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(0.15)

        assert cache.get("key1") is None

    def test_custom_ttl(self):
        """Test setting custom TTL per entry."""
        cache = TTLCache(default_ttl=10.0)

        cache.set("key1", "value1", ttl=0.1)
        cache.set("key2", "value2", ttl=5.0)

        # key1 should expire quickly
        time.sleep(0.15)
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_invalidate(self):
        """Test manual invalidation."""
        cache = TTLCache()

        cache.set("key1", "value1")
        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None

        # Invalidating non-existent key
        assert cache.invalidate("nonexistent") is False

    def test_clear(self):
        """Test clearing all entries."""
        cache = TTLCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = TTLCache(default_ttl=0.1)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3", ttl=5.0)  # Won't expire

        # Wait for expiration
        time.sleep(0.15)

        removed = cache.cleanup_expired()

        assert removed == 2  # key1 and key2 expired
        assert cache.get("key3") == "value3"

    def test_size(self):
        """Test getting cache size."""
        cache = TTLCache()

        assert cache.size() == 0

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.size() == 2

        cache.invalidate("key1")

        assert cache.size() == 1

    def test_get_with_expiry(self):
        """Test getting value with remaining TTL."""
        cache = TTLCache(default_ttl=10.0)

        cache.set("key1", "value1")

        result = cache.get_with_expiry("key1")
        assert result is not None

        value, remaining = result
        assert value == "value1"
        assert 9.0 < remaining <= 10.0  # Should be close to 10s

    def test_get_with_expiry_expired(self):
        """Test get_with_expiry for expired entry."""
        cache = TTLCache(default_ttl=0.1)

        cache.set("key1", "value1")
        time.sleep(0.15)

        result = cache.get_with_expiry("key1")
        assert result is None

    def test_overwrite_entry(self):
        """Test overwriting an existing entry."""
        cache = TTLCache()

        cache.set("key1", "value1")
        cache.set("key1", "value2")

        assert cache.get("key1") == "value2"

    def test_different_value_types(self):
        """Test caching different value types."""
        cache = TTLCache()

        cache.set("string", "value")
        cache.set("int", 42)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"key": "value"})
        cache.set("bool", True)

        assert cache.get("string") == "value"
        assert cache.get("int") == 42
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"key": "value"}
        assert cache.get("bool") is True


class TestHealthCheckCache:
    """Test suite for HealthCheckCache."""

    def test_set_and_get_health(self):
        """Test basic health check caching."""
        cache = HealthCheckCache(ttl=10.0)

        cache.set_health("service1", True)
        cache.set_health("service2", False)

        assert cache.get_health("service1") is True
        assert cache.get_health("service2") is False

    def test_get_health_nonexistent(self):
        """Test getting health for non-cached service."""
        cache = HealthCheckCache()

        assert cache.get_health("nonexistent") is None

    def test_health_expiration(self):
        """Test that health checks expire."""
        cache = HealthCheckCache(ttl=0.1)

        cache.set_health("service1", True)
        assert cache.get_health("service1") is True

        # Wait for expiration
        time.sleep(0.15)

        assert cache.get_health("service1") is None

    def test_custom_ttl_per_service(self):
        """Test setting custom TTL for specific health check."""
        cache = HealthCheckCache(ttl=10.0)

        cache.set_health("service1", True, ttl=0.1)
        cache.set_health("service2", True, ttl=5.0)

        time.sleep(0.15)

        assert cache.get_health("service1") is None
        assert cache.get_health("service2") is True

    def test_invalidate_service(self):
        """Test invalidating specific service health."""
        cache = HealthCheckCache()

        cache.set_health("service1", True)
        cache.set_health("service2", True)

        assert cache.invalidate_service("service1") is True
        assert cache.get_health("service1") is None
        assert cache.get_health("service2") is True

    def test_clear_all_health(self):
        """Test clearing all health checks."""
        cache = HealthCheckCache()

        cache.set_health("service1", True)
        cache.set_health("service2", False)
        cache.set_health("service3", True)

        cache.clear_all()

        assert cache.get_health("service1") is None
        assert cache.get_health("service2") is None
        assert cache.get_health("service3") is None

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        cache = HealthCheckCache(ttl=30.0)

        cache.set_health("service1", True)
        cache.set_health("service2", False)

        stats = cache.get_cache_stats()

        assert stats["total_entries"] == 2
        assert stats["ttl_seconds"] == 30

    def test_update_health_status(self):
        """Test updating health status for same service."""
        cache = HealthCheckCache()

        cache.set_health("service1", True)
        assert cache.get_health("service1") is True

        cache.set_health("service1", False)
        assert cache.get_health("service1") is False

    def test_negative_health_cached(self):
        """Test that negative health checks are cached."""
        cache = HealthCheckCache(ttl=10.0)

        cache.set_health("failing_service", False)

        # Should return cached False without rechecking
        assert cache.get_health("failing_service") is False
