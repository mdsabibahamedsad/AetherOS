"""Performance Optimization for AetherOS.

Provides:
- Startup time optimization
- Lazy loading infrastructure
- Background loading
- Caching
- Memory optimization
- Duplicate initialization detection
"""

from __future__ import annotations

import functools
import importlib
import logging
import threading
import time
from typing import Any, Callable, Dict, Generic, Optional, Tuple, TypeVar

logger = logging.getLogger("aetheros_arch.performance")

T = TypeVar("T")


class LazyLoader(Generic[T]):
    """Lazily load and cache a value.

    The factory is called only on first access.
    Thread-safe.
    """

    def __init__(self, factory: Callable[[], T], name: str = "") -> None:
        self._factory = factory
        self._name = name
        self._value: T = None  # type: ignore
        self._loaded = False
        self._lock = threading.Lock()

    @property
    def value(self) -> T:
        if not self._loaded:
            with self._lock:
                if not self._loaded:
                    self._value = self._factory()
                    self._loaded = True
        return self._value

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def reset(self) -> None:
        with self._lock:
            self._loaded = False
            self._value = None  # type: ignore

    def __call__(self) -> T:
        return self.value


class LazyImport:
    """Lazily import a module.

    The module is imported only on first attribute access.
    """

    def __init__(self, module_name: str) -> None:
        self._module_name = module_name
        self._module: Any = None
        self._lock = threading.Lock()

    def __getattr__(self, name: str) -> Any:
        if self._module is None:
            with self._lock:
                if self._module is None:
                    self._module = importlib.import_module(self._module_name)
        return getattr(self._module, name)

    def __bool__(self) -> bool:
        return True


class BackgroundLoader:
    """Load resources in a background thread.

    Usage::

        loader = BackgroundLoader()
        loader.submit("config", load_config)
        # ... do other startup work ...
        config = loader.result("config")
    """

    def __init__(self) -> None:
        self._results: Dict[str, Any] = {}
        self._errors: Dict[str, Exception] = {}
        self._futures: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def submit(self, name: str, fn: Callable[[], Any]) -> None:
        """Submit a task to run in background."""
        def _run():
            try:
                result = fn()
                with self._lock:
                    self._results[name] = result
            except Exception as exc:
                with self._lock:
                    self._errors[name] = exc

        thread = threading.Thread(target=_run, name=f"bg-loader-{name}", daemon=True)
        thread.start()
        with self._lock:
            self._futures[name] = thread

    def result(self, name: str, timeout: Optional[float] = None) -> Any:
        """Get the result, blocking if not yet complete."""
        with self._lock:
            thread = self._futures.get(name)
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
        with self._lock:
            if name in self._errors:
                raise self._errors[name]
            return self._results.get(name)

    def wait_all(self, timeout: Optional[float] = None) -> None:
        """Wait for all submitted tasks to complete."""
        start = time.monotonic()
        with self._lock:
            threads = list(self._futures.values())
        for t in threads:
            remaining = None
            if timeout is not None:
                elapsed = (time.monotonic() - start) * 1000
                remaining = max(0.0, timeout - elapsed)
            t.join(timeout=remaining)

    def is_done(self, name: str) -> bool:
        with self._lock:
            return name in self._results or name in self._errors


class PerformanceOptimizer:
    """Performance optimization manager.

    Tracks startup timing, caches, and initialization status
    to prevent duplicate work.
    """

    def __init__(self) -> None:
        self._timings: Dict[str, float] = {}
        self._initialized: Dict[str, bool] = {}
        self._lock = threading.Lock()
        self._start_time = time.monotonic()
        self._background_loader = BackgroundLoader()

    @property
    def background(self) -> BackgroundLoader:
        return self._background_loader

    @property
    def uptime_ms(self) -> float:
        return (time.monotonic() - self._start_time) * 1000

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    def start_timer(self, name: str) -> None:
        with self._lock:
            self._timings[f"{name}_start"] = time.monotonic()

    def stop_timer(self, name: str) -> float:
        with self._lock:
            start = self._timings.pop(f"{name}_start", None)
            if start is None:
                return 0.0
            elapsed = (time.monotonic() - start) * 1000
            self._timings[name] = elapsed
            return elapsed

    def get_timing(self, name: str) -> float:
        return self._timings.get(name, 0.0)

    def get_all_timings(self) -> Dict[str, float]:
        with self._lock:
            return {
                k: v for k, v in self._timings.items()
                if not k.endswith("_start")
            }

    def timing_report(self) -> str:
        timings = self.get_all_timings()
        if not timings:
            return "No timing data"
        lines = ["Performance Timings:"]
        for name, ms in sorted(timings.items(), key=lambda x: -x[1]):
            lines.append(f"  {name}: {ms:.1f}ms")
        lines.append(f"  Total uptime: {self.uptime_ms:.0f}ms")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Duplicate initialization guard
    # ------------------------------------------------------------------

    def guard_init(self, name: str) -> bool:
        """Returns True if this is the first initialization.

        Use to prevent duplicate initialization::

            if not optimizer.guard_init("my_module"):
                return  # already initialized
            # ... do init ...
        """
        with self._lock:
            if self._initialized.get(name, False):
                return False
            self._initialized[name] = True
            return True

    def mark_init(self, name: str) -> None:
        with self._lock:
            self._initialized[name] = True

    def is_initialized(self, name: str) -> bool:
        return self._initialized.get(name, False)

    def reset_init(self, name: str) -> None:
        with self._lock:
            self._initialized.pop(name, None)