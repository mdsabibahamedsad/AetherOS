"""Health model — liveness, readiness, dependency graph, degraded mode.

Two distinct signals are supported:

* **Liveness** — "is the process alive?" (cheap, no dependencies touched)
* **Readiness** — "can it safely accept work?" (checks dependencies)

A dependency graph is maintained so that one failed dependency degrades
only the components that depend on it — it never incorrectly marks the
entire system as failed.

Components: SYSTEM, DESKTOP, BACKEND, GATEWAY, DATABASE, MEMORY,
AGENT_RUNTIME, MODEL_PROVIDER, TOOL_RUNTIME, MCP, IPC, STORAGE, SECURITY.
"""

from __future__ import annotations

import enum
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


class HealthState(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# Component constants
SYSTEM = "SYSTEM"
DESKTOP = "DESKTOP"
BACKEND = "BACKEND"
GATEWAY = "GATEWAY"
DATABASE = "DATABASE"
MEMORY = "MEMORY"
AGENT_RUNTIME = "AGENT_RUNTIME"
MODEL_PROVIDER = "MODEL_PROVIDER"
TOOL_RUNTIME = "TOOL_RUNTIME"
MCP = "MCP"
IPC = "IPC"
STORAGE = "STORAGE"
SECURITY = "SECURITY"

COMPONENTS = (
    SYSTEM, DESKTOP, BACKEND, GATEWAY, DATABASE, MEMORY,
    AGENT_RUNTIME, MODEL_PROVIDER, TOOL_RUNTIME, MCP, IPC, STORAGE, SECURITY,
)

#: Dependency graph — a component is only as healthy as its dependencies.
#: ``KEY: (deps,)`` means KEY depends on each listed component.
DEPENDENCIES: Dict[str, Tuple[str, ...]] = {
    SYSTEM: (),
    DESKTOP: (BACKEND, IPC),
    BACKEND: (AGENT_RUNTIME, STORAGE, SECURITY),
    GATEWAY: (AGENT_RUNTIME, IPC, SECURITY),
    DATABASE: (STORAGE,),
    MEMORY: (STORAGE,),
    AGENT_RUNTIME: (MODEL_PROVIDER, TOOL_RUNTIME, MEMORY),
    MODEL_PROVIDER: (),
    TOOL_RUNTIME: (),
    MCP: (IPC,),
    IPC: (),
    STORAGE: (),
    SECURITY: (),
}


@dataclass
class ComponentHealth:
    component: str
    state: HealthState = HealthState.UNKNOWN
    message: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        return self.state == HealthState.HEALTHY

    @property
    def is_passing(self) -> bool:
        return self.state in (HealthState.HEALTHY, HealthState.DEGRADED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "state": self.state.value,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }


HealthCheckFn = Callable[[], Tuple[HealthState, str]]


class HealthService:
    """Orchestrates liveness, readiness and per-component health.

    Usage::

        hs = get_health_service()
        hs.register(MODEL_PROVIDER, lambda: (HealthState.HEALTHY, "ok"))
        hs.check_all()
        print(hs.readiness())
        print(hs.liveness())
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._checks: Dict[str, HealthCheckFn] = {}
        self._results: Dict[str, ComponentHealth] = {}
        self._start_time = time.time()
        self._degraded_reasons: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, component: str, check_fn: HealthCheckFn) -> None:
        """Register a health check function for *component*."""
        with self._lock:
            self._checks[component] = check_fn

    def unregister(self, component: str) -> None:
        with self._lock:
            self._checks.pop(component, None)
            self._results.pop(component, None)

    def is_registered(self, component: str) -> bool:
        return component in self._checks

    # ------------------------------------------------------------------
    # Liveness / Readiness
    # ------------------------------------------------------------------

    def liveness(self) -> Dict[str, Any]:
        """Cheap process-alive signal."""
        return {
            "status": "alive",
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "timestamp": time.time(),
        }

    def readiness(self) -> Dict[str, Any]:
        """Can the system safely accept work?"""
        results = self.check_all()
        overall = self._aggregate_overall(results)
        return {
            "status": overall.value,
            "ready": overall in (HealthState.HEALTHY, HealthState.DEGRADED),
            "components": {c.component: c.state.value for c in results},
            "timestamp": time.time(),
        }

    # ------------------------------------------------------------------
    # Checking
    # ------------------------------------------------------------------

    def check(self, component: str) -> ComponentHealth:
        """Run a single component health check."""
        with self._lock:
            check_fn = self._checks.get(component)
        if check_fn is None:
            result = ComponentHealth(
                component=component,
                state=HealthState.UNKNOWN,
                message="No check registered",
            )
        else:
            start = time.monotonic()
            try:
                state, message = check_fn()
                result = ComponentHealth(
                    component=component,
                    state=state,
                    message=message,
                    latency_ms=round((time.monotonic() - start) * 1000, 2),
                )
            except Exception as exc:
                result = ComponentHealth(
                    component=component,
                    state=HealthState.UNHEALTHY,
                    message=f"{type(exc).__name__}: {exc}",
                    latency_ms=round((time.monotonic() - start) * 1000, 2),
                )
        # Apply degraded-mode override
        with self._lock:
            reason = self._degraded_reasons.get(component)
            if reason and result.state == HealthState.HEALTHY:
                result.state = HealthState.DEGRADED
                result.message = reason
            self._results[component] = result
        return result

    def check_all(self) -> List[ComponentHealth]:
        """Run every registered check, honoring the dependency graph."""
        results = {c: self.check(c) for c in list(self._checks.keys())}
        self._propagate_dependencies(results)
        return list(results.values())

    def get_result(self, component: str) -> Optional[ComponentHealth]:
        with self._lock:
            return self._results.get(component)

    def get_all_results(self) -> Dict[str, ComponentHealth]:
        with self._lock:
            return dict(self._results)

    # ------------------------------------------------------------------
    # Degraded mode
    # ------------------------------------------------------------------

    def set_degraded(self, component: str, reason: str) -> None:
        """Mark a component as degraded with a human-readable reason.

        Only lowers HEALTHY → DEGRADED; never masks an UNHEALTHY state.
        """
        with self._lock:
            self._degraded_reasons[component] = reason

    def clear_degraded(self, component: str) -> None:
        with self._lock:
            self._degraded_reasons.pop(component, None)

    def degraded_components(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._degraded_reasons)

    # ------------------------------------------------------------------
    # Dependency propagation
    # ------------------------------------------------------------------

    def _propagate_dependencies(self, results: Dict[str, ComponentHealth]) -> None:
        """Downgrade dependents of unhealthy dependencies.

        A component whose dependency is UNHEALTHY becomes DEGRADED (it may
        still partially work) — never UNHEALTHY itself, so a single leaf
        failure does not mark the whole system failed.
        """
        for component in list(results.keys()):
            for dep in DEPENDENCIES.get(component, ()):
                dep_result = results.get(dep)
                if dep_result and dep_result.state == HealthState.UNHEALTHY:
                    own = results[component]
                    if own.state == HealthState.HEALTHY:
                        own.state = HealthState.DEGRADED
                        own.message = f"dependency unhealthy: {dep}"
                        with self._lock:
                            self._results[component] = own

    def _aggregate_overall(self, results: List[ComponentHealth]) -> HealthState:
        if not results:
            return HealthState.UNKNOWN
        if any(r.state == HealthState.UNHEALTHY for r in results):
            return HealthState.UNHEALTHY
        if any(r.state == HealthState.DEGRADED for r in results):
            return HealthState.DEGRADED
        if any(r.state == HealthState.UNKNOWN for r in results):
            return HealthState.UNKNOWN
        return HealthState.HEALTHY

    def overall(self) -> HealthState:
        return self._aggregate_overall(self.check_all())

    def summary(self) -> Dict[str, Any]:
        """A full health summary dict (state, liveness, readiness, components)."""
        results = self.check_all()
        return {
            "status": self._aggregate_overall(results).value,
            "liveness": self.liveness(),
            "readiness": {
                "status": self._aggregate_overall(results).value,
                "ready": self._aggregate_overall(results)
                in (HealthState.HEALTHY, HealthState.DEGRADED),
            },
            "components": {
                c.component: c.to_dict() for c in results
            },
            "degraded": self.degraded_components(),
            "timestamp": time.time(),
        }


_health_service: Optional[HealthService] = None


def get_health_service() -> HealthService:
    """Return the process-wide HealthService singleton."""
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service