"""
Metrics caching system for performance optimization.

Prevents expensive operations like CPU/memory monitoring from blocking
the event loop and reduces redundant computations.
"""
import asyncio
import time
from typing import Any, Callable, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with value and timestamp."""
    value: Any
    timestamp: float


class MetricsCache:
    """
    Time-based cache for expensive metrics operations.

    Caches values with a TTL (time-to-live) to prevent redundant
    expensive operations like CPU monitoring.

    Example:
        cache = MetricsCache(ttl=2.0)

        # First call: expensive operation
        value = cache.get_or_compute("cpu", lambda: psutil.cpu_percent(0.1))

        # Second call within 2s: cached value
        value = cache.get_or_compute("cpu", lambda: psutil.cpu_percent(0.1))
    """

    def __init__(self, ttl: float = 2.0):
        """
        Initialize metrics cache.

        Args:
            ttl: Time-to-live in seconds for cached values
        """
        self.ttl = ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/missing
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if time.time() - entry.timestamp < self.ttl:
            return entry.value

        # Entry expired, remove it
        del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """
        Set cached value.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = CacheEntry(
            value=value,
            timestamp=time.time()
        )

    def get_or_compute(self, key: str, compute_fn: Callable[[], Any]) -> Any:
        """
        Get cached value or compute and cache it.

        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached

        Returns:
            Cached or computed value
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        value = compute_fn()
        self.set(key, value)
        return value

    async def get_or_compute_async(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        use_executor: bool = True
    ) -> Any:
        """
        Get cached value or compute it asynchronously.

        Uses a lock per key to prevent duplicate expensive operations
        and optionally runs blocking functions in a thread pool executor.

        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached
            use_executor: Run compute_fn in executor for blocking operations

        Returns:
            Cached or computed value
        """
        # Check cache first (fast path)
        cached = self.get(key)
        if cached is not None:
            return cached

        # Ensure we have a lock for this key
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        # Acquire lock to prevent duplicate computations
        async with self._locks[key]:
            # Double-check cache after acquiring lock
            cached = self.get(key)
            if cached is not None:
                return cached

            # Compute value
            if use_executor:
                # Run blocking operation in thread pool
                loop = asyncio.get_event_loop()
                value = await loop.run_in_executor(None, compute_fn)
            else:
                # Run directly (for async functions)
                value = compute_fn()
                if asyncio.iscoroutine(value):
                    value = await value

            # Cache and return
            self.set(key, value)
            return value

    def invalidate(self, key: str) -> None:
        """
        Invalidate a cache entry.

        Args:
            key: Cache key to invalidate
        """
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        now = time.time()
        valid_entries = sum(
            1 for entry in self._cache.values()
            if now - entry.timestamp < self.ttl
        )

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "ttl_seconds": self.ttl
        }


# Global metrics cache instance with 2-second TTL
_metrics_cache: Optional[MetricsCache] = None


def get_metrics_cache(ttl: float = 2.0) -> MetricsCache:
    """
    Get or create global metrics cache instance.

    Args:
        ttl: Time-to-live for cache entries (default: 2 seconds)

    Returns:
        MetricsCache instance
    """
    global _metrics_cache

    if _metrics_cache is None:
        _metrics_cache = MetricsCache(ttl=ttl)

    return _metrics_cache
