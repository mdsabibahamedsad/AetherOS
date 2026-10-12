"""
Memory Cache — in-memory cache with TTL support and LRU eviction.

Provides fast access to frequently used memory entries without hitting
slower storage backends. Used internally by the memory manager and
retrieval engine.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class _CacheEntry:
    """A single entry in the memory cache."""

    __slots__ = ("key", "value", "expires_at", "access_count", "access_order")

    def __init__(self, key: str, value: Any, ttl: float, access_order: int = 0):
        self.key = key
        self.value = value
        self.expires_at = time.time() + ttl
        self.access_count = 1
        self.access_order = access_order

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def access(self, order: int) -> None:
        self.access_count += 1
        self.access_order = order


class MemoryCache:
    """Thread-safe in-memory cache with TTL and LRU eviction.

    Uses a monotonically increasing counter for LRU tracking so that
    entries with identical timestamps are still ordered correctly.

    Usage:
        cache = MemoryCache(max_size=1000, default_ttl=300)
        cache.set("key", value)
        value = cache.get("key")
        cache.delete("key")
    """

    def __init__(self, max_size: int = 10000, default_ttl: float = 300.0):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        self._entries: Dict[str, _CacheEntry] = {}
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._order_counter = 0

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache. Returns default if not found or expired."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return default
            if entry.is_expired:
                del self._entries[key]
                self._misses += 1
                return default
            self._order_counter += 1
            entry.access(self._order_counter)
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set a value in cache with optional TTL override."""
        ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            if len(self._entries) >= self._max_size:
                self._evict_lru()
            self._order_counter += 1
            self._entries[key] = _CacheEntry(key, value, ttl, self._order_counter)

    def delete(self, key: str) -> bool:
        """Delete a key from cache. Returns True if existed."""
        with self._lock:
            return self._entries.pop(key, None) is not None

    def clear(self) -> int:
        """Clear all cache entries. Returns count cleared."""
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            return count

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values at once."""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, items: Dict[str, Any],
                 ttl: Optional[float] = None) -> None:
        """Set multiple values at once."""
        for key, value in items.items():
            self.set(key, value, ttl)

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def _evict_lru(self) -> None:
        """Evict the least recently used entry (lowest access_order)."""
        if not self._entries:
            return
        oldest = min(self._entries.values(), key=lambda e: e.access_order)
        del self._entries[oldest.key]
        self._evictions += 1

    def prune_expired(self) -> int:
        """Remove all expired entries. Returns count pruned."""
        count = 0
        with self._lock:
            expired = [k for k, e in self._entries.items() if e.is_expired]
            for k in expired:
                del self._entries[k]
                count += 1
        return count

    def contains(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._entries[key]
                return False
            return True

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        with self._lock:
            return {
                "size": len(self._entries),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_ratio": (
                    self._hits / (self._hits + self._misses)
                    if (self._hits + self._misses) > 0 else 0.0
                ),
                "default_ttl": self._default_ttl,
            }

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._entries)
