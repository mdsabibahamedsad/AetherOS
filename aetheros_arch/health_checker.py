"""Centralized Health Check System for AetherOS.

Provides a unified health check framework that monitors all
system components: backend, gateway, runtime, providers, plugins,
memory, browser, desktop, voice, vision, and MCP.

Usage::

    hc = HealthChecker()
    hc.register("gateway", lambda: check_gateway())
    hc.register("provider.openai", lambda: check_openai())
    results = hc.run_all()
    print(results.summary())
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("aetheros_arch.health")


class HealthStatus(enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    component: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    @property
    def is_passing(self) -> bool:
        return self.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)


@dataclass
class HealthSummary:
    total: int = 0
    healthy: int = 0
    degraded: int = 0
    unhealthy: int = 0
    unknown: int = 0
    results: List[HealthCheckResult] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def score(self) -> float:
        if self.total == 0:
            return 1.0
        return (self.healthy + self.degraded * 0.5) / self.total

    @property
    def all_healthy(self) -> bool:
        return self.unhealthy == 0

    def summary(self) -> str:
        return (
            f"Health: {self.healthy}/{self.total} healthy, "
            f"{self.degraded} degraded, "
            f"{self.unhealthy} unhealthy "
            f"({self.duration_ms:.0f}ms, score={self.score:.0%})"
        )


HealthCheckFn = Callable[[], Tuple[HealthStatus, str]]


class HealthChecker:
    """Centralized health check system.

    Components register a check function that returns ``(status, message)``.
    ``run_all()`` executes all checks and returns a summary.
    """

    def __init__(self) -> None:
        self._checks: Dict[str, HealthCheckFn] = {}
        self._results: Dict[str, HealthCheckResult] = {}
        self._labels: Dict[str, str] = {}

    def register(
        self,
        component: str,
        check_fn: HealthCheckFn,
        label: Optional[str] = None,
    ) -> None:
        """Register a health check for *component*.

        The *check_fn* should return ``(HealthStatus, message)``.
        """
        self._checks[component] = check_fn
        self._labels[component] = label or component

    def unregister(self, component: str) -> None:
        self._checks.pop(component, None)
        self._results.pop(component, None)
        self._labels.pop(component, None)

    def run(self, component: str) -> Optional[HealthCheckResult]:
        """Run a single health check."""
        if component not in self._checks:
            return None
        return self._run_single(component)

    def run_all(self, timeout: float = 30.0) -> HealthSummary:
        """Run all registered health checks and return a summary."""
        start = time.monotonic()
        summary = HealthSummary()

        for component in list(self._checks.keys()):
            result = self._run_single(component, timeout)
            self._results[component] = result
            summary.results.append(result)
            summary.total += 1
            if result.status == HealthStatus.HEALTHY:
                summary.healthy += 1
            elif result.status == HealthStatus.DEGRADED:
                summary.degraded += 1
            elif result.status == HealthStatus.UNHEALTHY:
                summary.unhealthy += 1
            else:
                summary.unknown += 1

        summary.duration_ms = (time.monotonic() - start) * 1000
        return summary

    def run_category(self, category: str) -> HealthSummary:
        """Run checks for a category (e.g. 'gateway', 'provider')."""
        start = time.monotonic()
        summary = HealthSummary()
        prefix = f"{category}."

        for component in list(self._checks.keys()):
            if component.startswith(prefix) or component == category:
                result = self._run_single(component)
                self._results[component] = result
                summary.results.append(result)
                summary.total += 1
                self._increment_summary(summary, result.status)

        summary.duration_ms = (time.monotonic() - start) * 1000
        return summary

    def get_result(self, component: str) -> Optional[HealthCheckResult]:
        return self._results.get(component)

    def get_all_results(self) -> Dict[str, HealthCheckResult]:
        return dict(self._results)

    def is_healthy(self, component: str) -> bool:
        result = self._results.get(component)
        return result is not None and result.is_healthy

    @property
    def components(self) -> List[str]:
        return list(self._checks.keys())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_single(self, component: str, timeout: float = 30.0) -> HealthCheckResult:
        check_fn = self._checks.get(component)
        if check_fn is None:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNKNOWN,
                message="No check registered",
            )

        start = time.monotonic()
        try:
            status, message = check_fn()
            latency = (time.monotonic() - start) * 1000
            return HealthCheckResult(
                component=component,
                status=status,
                message=message,
                latency_ms=round(latency, 1),
            )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            logger.warning("Health check %s failed: %s", component, exc)
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message=str(exc),
                latency_ms=round(latency, 1),
            )

    @staticmethod
    def _increment_summary(summary: HealthSummary, status: HealthStatus) -> None:
        if status == HealthStatus.HEALTHY:
            summary.healthy += 1
        elif status == HealthStatus.DEGRADED:
            summary.degraded += 1
        elif status == HealthStatus.UNHEALTHY:
            summary.unhealthy += 1
        else:
            summary.unknown += 1


def ping_component(host: str, port: int, timeout: float = 5.0) -> bool:
    """Check if a TCP port is reachable."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_filesystem(path: str) -> Tuple[HealthStatus, str]:
    """Check if a filesystem path exists and is accessible."""
    p = Path(path)
    if not p.exists():
        return HealthStatus.UNHEALTHY, f"Path does not exist: {path}"
    if not os.access(str(p), os.R_OK):
        return HealthStatus.DEGRADED, f"Path not readable: {path}"
    return HealthStatus.HEALTHY, "OK"


from pathlib import Path
import os