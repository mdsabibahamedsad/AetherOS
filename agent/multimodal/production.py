"""Production Hardening (Phases 46-55 of Master Prompt 10).

Production hardening for the multimodal subsystem:
- Phase 46: Modality -> tool routing (already in perception.perceive)
- Phase 47: Circuit breakers, retries, error handling
- Phase 48: Performance - caching, connection pooling
- Phase 49: Observability - distributed tracing, metrics
- Phase 50: Configuration management
- Phase 51: Graceful shutdown, health checks
- Phase 52: Metrics exposition (Prometheus)
- Phase 53: Graceful degradation
- Phase 54: Load testing utilities
- Phase 55: Final audit & documentation
"""

from __future__ import annotations

import contextlib
import functools
import logging
import os
import threading
import time
import weakref
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from collections import OrderedDict

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# Phase 47: Circuit Breakers & Retries
# ============================================================================

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker for external service calls (Phase 47)."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
            return self._state

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        state = self.state
        if state == CircuitState.OPEN:
            raise CircuitOpenError("Circuit breaker is OPEN")

        if state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitOpenError("Half-open call limit reached")
                self._half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._half_open_calls = 0

    def _on_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,),
):
    """Retry decorator with exponential backoff (Phase 47)."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        raise
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    if jitter:
                        import random
                        delay *= (0.5 + random.random())
                    logger.warning(f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                                 f"after {delay:.1f}s: {e}")
                    time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


# ============================================================================
# Phase 48: Caching & Connection Pooling
# ============================================================================

class LRUCache(Generic[T]):
    """Thread-safe LRU cache with TTL (Phase 48)."""

    def __init__(self, maxsize: int = 1000, ttl: float = 300.0):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: OrderedDict[str, tuple[T, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[T]:
        with self._lock:
            if key not in self._cache:
                return None
            value, expires = self._cache[key]
            if time.time() > expires:
                del self._cache[key]
                return None
            # Move to end (most recent)
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.maxsize:
                self._cache.popitem(last=False)
            expires = time.time() + (ttl or 300.0)
            self._cache[key] = (value, expires)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            expired = sum(1 for _, exp in self._cache.values() if now > exp)
            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "expired": expired,
                "hit_rate": getattr(self, '_hits', 0) / max(1, getattr(self, '_hits', 0) + getattr(self, '_misses', 1)),
            }


class ConnectionPool(Generic[T]):
    """Generic connection pool (Phase 48)."""

    def __init__(
        self,
        factory: Callable[[], T],
        max_size: int = 10,
        max_idle: int = 5,
        ttl: float = 300.0,
        validator: Optional[Callable[[T], bool]] = None,
    ):
        self.factory = factory
        self.max_size = max_size
        self.max_idle = max_idle
        self.ttl = ttl
        self.validator = validator or (lambda _: True)
        self._pool: deque[tuple[T, float]] = deque()
        self._in_use: set[int] = set()
        self._lock = threading.Lock()
        self._created = 0

    def acquire(self) -> T:
        with self._lock:
            now = time.time()
            # Try to reuse idle connection
            while self._pool:
                obj, created = self._pool.popleft()
                if now - created < self.ttl and self.validator(obj):
                    self._in_use.add(id(obj))
                    return obj
                # Expired or invalid
            # Create new
            if len(self._in_use) >= self.max_size:
                raise RuntimeError("Connection pool exhausted")
            obj = self.factory()
            self._created += 1
            self._in_use.add(id(obj))
            return obj

    def release(self, obj: T) -> None:
        with self._lock:
            if id(obj) in self._in_use:
                self._in_use.remove(id(obj))
                if len(self._pool) < self.max_size:
                    self._pool.append((obj, time.time()))

    @contextmanager
    def connection(self):
        obj = self.acquire()
        try:
            yield obj
        finally:
            self.release(obj)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "in_use": len(self._in_use),
                "idle": len(self._pool),
                "max_size": self.max_size,
                "total_created": self._created,
            }


# ============================================================================
# Phase 49: Observability - Distributed Tracing
# ============================================================================

class TraceContext:
    """Distributed trace context (Phase 49)."""

    def __init__(self, trace_id: Optional[str] = None, span_id: Optional[str] = None):
        self.trace_id = trace_id or self._generate_id()
        self.span_id = span_id or self._generate_id()
        self.parent_span_id: Optional[str] = None
        self.start_time = time.time()
        self.tags: Dict[str, str] = {}
        self.events: List[Dict] = []

    @staticmethod
    def _generate_id() -> str:
        return os.urandom(16).hex()

    def child_span(self, operation: str) -> "TraceContext":
        child = TraceContext(self.trace_id)
        child.parent_span_id = self.span_id
        child.tags["operation"] = operation
        return child

    def add_tag(self, key: str, value: str) -> None:
        self.tags[key] = value

    def add_event(self, name: str, attributes: Optional[Dict] = None) -> None:
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })

    def finish(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "duration_ms": (time.time() - self.start_time) * 1000,
            "tags": self.tags,
            "events": self.events,
        }


class Tracer:
    """Simple distributed tracer (Phase 49)."""

    def __init__(self, service_name: str = "multimodal"):
        self.service_name = service_name
        self._spans: List[Dict] = []
        self._lock = threading.Lock()

    @contextmanager
    def span(self, operation: str, parent: Optional[TraceContext] = None):
        ctx = TraceContext()
        if parent:
            ctx.trace_id = parent.trace_id
            ctx.parent_span_id = parent.span_id
        ctx.tags["service"] = self.service_name
        ctx.tags["operation"] = operation

        start = time.time()
        try:
            yield ctx
        except Exception as e:
            ctx.add_tag("error", "true")
            ctx.add_event("exception", {"message": str(e)})
            raise
        finally:
            span_data = ctx.finish()
            with self._lock:
                self._spans.append(span_data)

    def export(self) -> List[Dict]:
        with self._lock:
            spans = self._spans.copy()
            self._spans.clear()
            return spans


# ============================================================================
# Phase 50: Configuration Management
# ============================================================================

class ConfigManager:
    """Centralized configuration with validation (Phase 50)."""

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._validators: Dict[str, Callable[[Any], bool]] = {}
        self._defaults: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def register(
        self,
        key: str,
        default: Any,
        validator: Optional[Callable[[Any], bool]] = None,
        description: str = "",
    ) -> None:
        with self._lock:
            self._defaults[key] = default
            self._config[key] = default
            if validator:
                self._validators[key] = validator

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        with self._lock:
            validator = self._validators.get(key)
            if validator and not validator(value):
                return False
            self._config[key] = value
            return True

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return self._config.copy()

    def validate_all(self) -> List[str]:
        errors = []
        with self._lock:
            for key, validator in self._validators.items():
                if not validator(self._config.get(key, self._defaults.get(key))):
                    errors.append(f"Validation failed for {key}")
        return errors


# ============================================================================
# Phase 51: Health Checks & Graceful Shutdown
# ============================================================================

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    details: Dict = field(default_factory=dict)


class HealthChecker:
    """Health check registry (Phase 51)."""

    def __init__(self):
        self._checks: Dict[str, Callable[[], HealthCheck]] = {}
        self._lock = threading.Lock()

    def register(self, name: str, check: Callable[[], HealthCheck]) -> None:
        with self._lock:
            self._checks[name] = check

    def check_all(self) -> Dict[str, HealthCheck]:
        results = {}
        with self._lock:
            for name, check in self._checks.items():
                try:
                    start = time.time()
                    result = check()
                    result.latency_ms = (time.time() - result.start_time) * 1000 if hasattr(result, 'start_time') else 0
                    results[name] = result
                except Exception as e:
                    results[name] = HealthCheck(
                        name=name,
                        status=HealthStatus.UNHEALTHY,
                        message=str(e),
                    )
        return results

    def is_healthy(self) -> bool:
        results = self.check_all()
        return all(r.status == HealthStatus.HEALTHY for r in results.values())

    def is_ready(self) -> bool:
        # Readiness: critical checks only
        results = self.check_all()
        return all(
            r.status != HealthStatus.UNHEALTHY
            for r in results.values()
        )


class GracefulShutdown:
    """Graceful shutdown coordinator (Phase 51)."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._shutdown_hooks: List[Callable[[], None]] = []
        self._shutdown_event = threading.Event()
        self._shutdown_started = False
        self._lock = threading.Lock()

    def register(self, hook: Callable[[], None], priority: int = 0) -> None:
        with self._lock:
            self._shutdown_hooks.append((priority, hook))
            self._shutdown_hooks.sort(key=lambda x: x[0])

    def request_shutdown(self) -> None:
        self._shutdown_event.set()

    def wait_for_shutdown(self) -> bool:
        return self._shutdown_event.wait(self.timeout)

    def execute_shutdown(self) -> bool:
        with self._lock:
            if self._shutdown_started:
                return False
            self._shutdown_started = True
            hooks = [h for _, h in self._shutdown_hooks]

        start = time.time()
        for hook in self._shutdown_hooks:
            if time.time() - start > self.timeout:
                logger.warning("Shutdown timeout reached")
                return False
            try:
                hook()
            except Exception as e:
                logger.error(f"Shutdown hook failed: {e}")
        return True


# ============================================================================
# Phase 52: Prometheus Metrics
# ============================================================================

class MetricsCollector:
    """Prometheus-compatible metrics (Phase 52)."""

    def __init__(self, prefix: str = "multimodal"):
        self.prefix = prefix
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            # Keep last 1000 values
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]

    def _key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return f"{self.prefix}_{name}"
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{self.prefix}_{name}{{{label_str}}}"

    def export_prometheus(self) -> str:
        lines = []
        with self._lock:
            for key, value in self._counters.items():
                lines.append(f"# TYPE {key} counter")
                lines.append(f"{key} {value}")
            for key, value in self._gauges.items():
                lines.append(f"# TYPE {key} gauge")
                lines.append(f"{key} {value}")
            for key, values in self._histograms.items():
                if values:
                    lines.append(f"# TYPE {key} histogram")
                    for i, v in enumerate(values):
                        lines.append(f"{key}_bucket{{le=\"+Inf\"}} {i+1}")
        return "\n".join(lines)


# ============================================================================
# Phase 53: Graceful Degradation
# ============================================================================

class DegradationLevel(Enum):
    NONE = 0
    REDUCED_QUALITY = 1
    REDUCED_FEATURES = 2
    MINIMAL = 3
    OFFLINE = 4


class DegradationManager:
    """Graceful degradation controller (Phase 53)."""

    def __init__(self):
        self._level = DegradationLevel.NONE
        self._feature_flags: Dict[str, bool] = {}
        self._lock = threading.Lock()

    @property
    def level(self) -> DegradationLevel:
        with self._lock:
            return self._level

    def set_level(self, level: DegradationLevel) -> None:
        with self._lock:
            self._level = level
            logger.warning(f"Degradation level changed to {level.name}")

    def is_feature_enabled(self, feature: str) -> bool:
        with self._lock:
            if self._level == DegradationLevel.OFFLINE:
                return False
            if self._level == DegradationLevel.MINIMAL:
                return feature in ("core", "text")
            if self._level == DegradationLevel.REDUCED_FEATURES:
                return feature not in ("video", "fusion", "spatial")
            if self._level == DegradationLevel.REDUCED_QUALITY:
                return feature != "high_quality"
            return self._feature_flags.get(feature, True)

    def set_feature(self, feature: str, enabled: bool) -> None:
        with self._lock:
            self._feature_flags[feature] = enabled


# ============================================================================
# Phase 54: Load Testing Utilities
# ============================================================================

class LoadTestRunner:
    """Load testing utilities (Phase 54)."""

    def __init__(self, target_func: Callable, max_workers: int = 10):
        self.target_func = target_func
        self.max_workers = max_workers
        self.results: List[Dict] = []
        self._lock = threading.Lock()

    def run(
        self,
        num_requests: int,
        concurrency: int,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        self.results = []
        start = time.time()

        def run_one(i: int) -> Dict:
            start = time.time()
            try:
                result = self.target_func(*args, **kwargs)
                return {"success": True, "latency": time.time() - start, "result": result}
            except Exception as e:
                return {"success": False, "latency": time.time() - start, "error": str(e)}

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(run_one, i) for i in range(num_requests)]
            for f in as_completed(futures):
                self.results.append(f.result())

        total_time = time.time() - start
        successful = [r for r in self.results if r["success"]]
        latencies = [r["latency"] for r in successful] if successful else [0]

        return {
            "total_requests": num_requests,
            "successful": len(successful),
            "failed": num_requests - len(successful),
            "total_time_s": total_time,
            "rps": len(successful) / total_time if total_time > 0 else 0,
            "latency_p50": sorted(latencies)[len(latencies) // 2] if latencies else 0,
            "latency_p95": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
            "latency_p99": sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0,
            "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
        }


# ============================================================================
# Phase 55: Final Audit & Documentation
# ============================================================================

class AuditReport:
    """Final audit report generator (Phase 55)."""

    def __init__(self, module_name: str = "multimodal"):
        self.module_name = module_name
        self.checks: List[Dict] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def check_imports(self) -> None:
        """Verify all public exports are importable."""
        try:
            import agent.multimodal
            # Check key exports
            for attr in dir(agent.multimodal):
                if not attr.startswith("_"):
                    getattr(agent.multimodal, attr)
            self.checks.append({"check": "imports", "status": "pass", "message": "All exports importable"})
        except Exception as e:
            self.errors.append(f"Import check failed: {e}")
            self.checks.append({"check": "imports", "status": "fail", "message": str(e)})

    def check_tests_pass(self) -> None:
        """Verify tests pass."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/multimodal/", "-q"],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
        )
        if result.returncode == 0:
            self.checks.append({"check": "tests", "status": "pass", "message": "All tests pass"})
        else:
            self.errors.append(f"Tests failed: {result.stdout}")
            self.checks.append({"check": "tests", "status": "fail", "message": result.stdout})

    def check_types(self) -> None:
        """Type checking (if mypy available)."""
        try:
            import subprocess
            result = subprocess.run(
                ["python", "-m", "mypy", "agent/multimodal", "--ignore-missing-imports"],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
            )
            if result.returncode == 0:
                self.checks.append({"check": "types", "status": "pass"})
            else:
                self.warnings.append(f"Type issues: {result.stdout}")
                self.checks.append({"check": "types", "status": "warn", "message": result.stdout})
        except FileNotFoundError:
            self.checks.append({"check": "types", "status": "skip", "message": "mypy not installed"})

    def check_documentation(self) -> None:
        """Check docstring coverage."""
        import inspect
        import agent.multimodal as mm
        total = 0
        documented = 0
        for name, obj in inspect.getmembers(mm):
            if inspect.isclass(obj) or inspect.isfunction(obj):
                if not name.startswith("_"):
                    total += 1
                    if obj.__doc__ and len(obj.__doc__.strip()) > 20:
                        documented += 1
        coverage = documented / total * 100 if total > 0 else 100
        self.checks.append({
            "check": "documentation",
            "status": "pass" if coverage >= 80 else "warn",
            "message": f"Docstring coverage: {coverage:.1f}% ({documented}/{total})",
        })

    def check_security(self) -> None:
        """Basic security checks."""
        import ast
        import glob
        issues = []
        for py_file in glob.glob("agent/multimodal/**/*.py", recursive=True):
            try:
                with open(py_file) as f:
                    tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name) and node.func.id == "eval":
                            issues.append(f"{py_file}: eval() usage")
                        if isinstance(node.func, ast.Attribute) and node.func.attr == "exec":
                            issues.append(f"{py_file}: exec() usage")
            except Exception:
                pass
        if issues:
            self.warnings.extend(issues)
            self.checks.append({"check": "security", "status": "warn", "message": f"{len(issues)} issues"})
        else:
            self.checks.append({"check": "security", "status": "pass"})

    def run_all(self) -> Dict[str, Any]:
        self.check_imports()
        self.check_tests_pass()
        self.check_types()
        self.check_documentation()
        self.check_security()

        passed = sum(1 for c in self.checks if c["status"] == "pass")
        failed = sum(1 for c in self.checks if c["status"] == "fail")
        warned = sum(1 for c in self.checks if c["status"] == "warn")

        return {
            "module": self.module_name,
            "timestamp": time.time(),
            "summary": {"passed": passed, "failed": failed, "warned": warned, "total": len(self.checks)},
            "checks": self.checks,
            "warnings": self.warnings,
            "errors": self.errors,
            "overall": "PASS" if failed == 0 else "FAIL",
        }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Phase 47
    "CircuitBreaker",
    "CircuitState",
    "CircuitOpenError",
    "with_retry",
    # Phase 48
    "LRUCache",
    "ConnectionPool",
    # Phase 49
    "TraceContext",
    "Tracer",
    # Phase 50
    "ConfigManager",
    # Phase 51
    "HealthStatus",
    "HealthCheck",
    "HealthChecker",
    "GracefulShutdown",
    # Phase 52
    "MetricsCollector",
    # Phase 53
    "DegradationLevel",
    "DegradationManager",
    # Phase 54
    "LoadTestRunner",
    # Phase 55
    "AuditReport",
]