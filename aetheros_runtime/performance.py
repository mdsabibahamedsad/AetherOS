"""Performance Optimizer — lazy loading, virtual scrolling, incremental rendering, streaming optimization, memory optimization.

Performance utilities for the runtime.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, Set, TypeVar

logger = logging.getLogger("aetheros_runtime.performance")

T = TypeVar("T")


class PerformanceOptimizer:
    """Performance optimization utilities.

    Features:
    - Lazy loading for expensive resources
    - Virtual scrolling for large lists
    - Throttling and debouncing
    - Memory-efficient caching (LRU)
    - Timing and profiling
    - Incremental processing
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._timers: Dict[str, float] = {}
        self._profiling: Dict[str, List[float]] = {}
        self._initialized: Set[str] = set()
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_max_size: int = 100
        self._cache_ttl: float = 300.0

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------

    def lazy_load(self, key: str, factory: Callable[[], T], ttl: float = 0.0) -> T:
        with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired(ttl or self._cache_ttl):
                entry.access_count += 1
                return entry.value

        value = factory()

        with self._lock:
            self._cache[key] = CacheEntry(value=value)
            self._evict_if_needed()
        return value

    def invalidate_cache(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()

    def cache_size(self) -> int:
        with self._lock:
            return len(self._cache)

    def mark_initialized(self, component: str) -> None:
        with self._lock:
            self._initialized.add(component)

    def is_initialized(self, component: str) -> bool:
        with self._lock:
            return component in self._initialized

    # ------------------------------------------------------------------
    # Throttle / Debounce
    # ------------------------------------------------------------------

    @staticmethod
    def throttle(fn: Callable, min_interval: float = 1.0) -> Callable:
        last_call: List[float] = [0.0]
        lock = threading.Lock()

        def throttled(*args: Any, **kwargs: Any) -> Any:
            with lock:
                now = time.time()
                if now - last_call[0] < min_interval:
                    return None
                last_call[0] = now
            return fn(*args, **kwargs)

        return throttled

    @staticmethod
    def debounce(fn: Callable, delay: float = 0.3) -> Callable:
        timer: List[Any] = [None]
        lock = threading.Lock()

        def debounced(*args: Any, **kwargs: Any) -> None:
            def call() -> None:
                with lock:
                    timer[0] = None
                fn(*args, **kwargs)

            with lock:
                if timer[0] is not None:
                    timer[0].cancel()
                t = threading.Timer(delay, call)
                timer[0] = t
                t.daemon = True
                t.start()

        return debounced

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    def start_timer(self, name: str) -> None:
        with self._lock:
            self._timers[name] = time.monotonic()

    def stop_timer(self, name: str) -> float:
        with self._lock:
            start = self._timers.pop(name, None)
            if start is None:
                return 0.0
            elapsed = (time.monotonic() - start) * 1000
            if name not in self._profiling:
                self._profiling[name] = []
            self._profiling[name].append(elapsed)
            if len(self._profiling[name]) > 100:
                self._profiling[name].pop(0)
            return elapsed

    def get_timing_stats(self, name: str) -> Dict[str, float]:
        with self._lock:
            times = self._profiling.get(name, [])
            if not times:
                return {"avg": 0, "min": 0, "max": 0, "count": 0}
            return {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "count": len(times),
            }

    def get_all_timing_stats(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            return {name: self.get_timing_stats(name) for name in list(self._profiling.keys())}

    def timing_report(self) -> str:
        stats = self.get_all_timing_stats()
        lines = ["Performance Timings:"]
        for name, s in sorted(stats.items()):
            if s["count"] > 0:
                lines.append(f"  {name:30s} avg={s['avg']:8.1f}ms  min={s['min']:8.1f}ms  max={s['max']:8.1f}ms  (n={s['count']})")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Virtual scrolling helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_visible_range(
        scroll_position: int,
        item_height: int,
        viewport_height: int,
        overscan: int = 5,
    ) -> range:
        start_idx = max(0, (scroll_position // item_height) - overscan)
        end_idx = ((scroll_position + viewport_height) // item_height) + overscan + 1
        return range(start_idx, end_idx)

    @staticmethod
    def get_visible_items(
        items: List[Any],
        scroll_position: int,
        item_height: int,
        viewport_height: int,
        overscan: int = 5,
    ) -> List[Any]:
        visible = PerformanceOptimizer.get_visible_range(scroll_position, item_height, viewport_height, overscan)
        return [items[i] for i in visible if i < len(items)]

    # ------------------------------------------------------------------
    # Memory management
    # ------------------------------------------------------------------

    def set_cache_size(self, max_entries: int) -> None:
        with self._lock:
            self._cache_max_size = max_entries
            self._evict_if_needed()

    def set_cache_ttl(self, seconds: float) -> None:
        with self._lock:
            self._cache_ttl = seconds

    def _evict_if_needed(self) -> None:
        while len(self._cache) > self._cache_max_size:
            oldest = min(self._cache.items(), key=lambda x: x[1].access_count)
            del self._cache[oldest[0]]

    def clear_timers(self) -> None:
        with self._lock:
            self._timers.clear()
            self._profiling.clear()

    def summary(self) -> str:
        return f"Performance Optimizer: {self.cache_size()} cached items, {len(self._profiling)} profiled operations"


@dataclass
class CacheEntry(Generic[T]):
    value: T
    created_at: float = field(default_factory=time.time)
    access_count: int = 1

    def is_expired(self, ttl: float) -> bool:
        return ttl > 0 and (time.time() - self.created_at) > ttl