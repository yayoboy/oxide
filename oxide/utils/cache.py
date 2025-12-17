"""
Simple TTL cache implementation for health checks.

Provides time-based caching to reduce redundant health check operations.
"""
import time
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with value and expiration time."""
    value: Any
    expires_at: float


class TTLCache:
    """
    Time-To-Live (TTL) cache implementation.

    Stores values with automatic expiration based on TTL.
    Thread-safe for single-threaded async applications.
    """

    def __init__(self, default_ttl: float = 30.0):
        """
        Initialize TTL cache.

        Args:
            default_ttl: Default time-to-live in seconds
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        current_time = time.time()

        # Check if expired
        if current_time >= entry.expires_at:
            # Remove expired entry
            del self._cache[key]
            return None

        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not provided)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + ttl

        self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    def invalidate(self, key: str) -> bool:
        """
        Invalidate (remove) a cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if key existed, False otherwise
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time >= entry.expires_at
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    def size(self) -> int:
        """
        Get current cache size (includes expired entries).

        Returns:
            Number of entries in cache
        """
        return len(self._cache)

    def get_with_expiry(self, key: str) -> Optional[Tuple[Any, float]]:
        """
        Get value and remaining TTL.

        Args:
            key: Cache key

        Returns:
            Tuple of (value, remaining_seconds) if found and not expired,
            None otherwise
        """
        value = self.get(key)
        if value is None:
            return None

        entry = self._cache[key]
        remaining = entry.expires_at - time.time()
        return (value, max(0.0, remaining))


class HealthCheckCache:
    """
    Specialized cache for health check results.

    Provides a higher-level interface specifically for caching
    service health check results.
    """

    def __init__(self, ttl: float = 30.0):
        """
        Initialize health check cache.

        Args:
            ttl: Time-to-live for health check results in seconds
        """
        self._cache = TTLCache(default_ttl=ttl)
        self._ttl = ttl

    def get_health(self, service_name: str) -> Optional[bool]:
        """
        Get cached health check result.

        Args:
            service_name: Name of service

        Returns:
            Cached health status (True/False) if available, None if not cached
        """
        return self._cache.get(f"health:{service_name}")

    def set_health(self, service_name: str, is_healthy: bool, ttl: Optional[float] = None) -> None:
        """
        Cache health check result.

        Args:
            service_name: Name of service
            is_healthy: Health check result
            ttl: Custom TTL for this entry (uses default if not provided)
        """
        self._cache.set(f"health:{service_name}", is_healthy, ttl=ttl)

    def invalidate_service(self, service_name: str) -> bool:
        """
        Invalidate cached health for a specific service.

        Args:
            service_name: Name of service to invalidate

        Returns:
            True if cache entry existed
        """
        return self._cache.invalidate(f"health:{service_name}")

    def clear_all(self) -> None:
        """Clear all cached health check results."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "total_entries": self._cache.size(),
            "ttl_seconds": int(self._ttl)
        }
