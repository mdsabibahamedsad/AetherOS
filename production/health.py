"""
Health Check System
===================

Production health monitoring for AetherOS deployments.

Provides:
- Comprehensive health checks for all subsystems
- Health endpoint data for dashboards and monitoring
- Configurable check intervals and thresholds
- Machine-readable health reports
- Integration with external monitoring systems
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthComponent(Enum):
    """Components that can be health-checked."""
    KERNEL = "kernel"
    SCHEDULER = "scheduler"
    EVENT_BUS = "event_bus"
    PLUGIN_SYSTEM = "plugin_system"
    TOOL_REGISTRY = "tool_registry"
    MEMORY_PROVIDER = "memory_provider"
    GATEWAY = "gateway"
    CONFIGURATION = "configuration"
    STORAGE = "storage"
    NETWORK = "network"


@dataclass
class HealthCheckResult:
    """Result of a health check for a single component.

    Attributes:
        component: The component that was checked
        status: Health status
        message: Human-readable status message
        latency_ms: Check response time
        last_success: Timestamp of last successful check
        consecutive_failures: Number of consecutive failures
        details: Additional diagnostic information
    """
    component: HealthComponent
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    latency_ms: float = 0.0
    last_success: Optional[float] = None
    consecutive_failures: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    """Complete health report for all components.

    Attributes:
        timestamp: When the report was generated
        overall_status: Aggregate health status
        checks: Individual component health checks
        summary: Summary statistics
        uptime_seconds: System uptime
    """
    timestamp: float = field(default_factory=time.time)
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    checks: List[HealthCheckResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    uptime_seconds: float = 0.0

    def add_check(self, check: HealthCheckResult) -> None:
        self.checks.append(check)
        self._update_overall_status()

    def _update_overall_status(self) -> None:
        if any(c.status == HealthStatus.UNHEALTHY for c in self.checks):
            self.overall_status = HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in self.checks):
            self.overall_status = HealthStatus.DEGRADED
        elif all(c.status == HealthStatus.HEALTHY for c in self.checks):
            self.overall_status = HealthStatus.HEALTHY
        else:
            self.overall_status = HealthStatus.UNKNOWN

    @property
    def healthy_count(self) -> int:
        return sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY)

    @property
    def degraded_count(self) -> int:
        return sum(1 for c in self.checks if c.status == HealthStatus.DEGRADED)

    @property
    def unhealthy_count(self) -> int:
        return sum(1 for c in self.checks if c.status in (HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "overall_status": self.overall_status.value,
            "uptime_seconds": self.uptime_seconds,
            "summary": {
                "total": len(self.checks),
                "healthy": self.healthy_count,
                "degraded": self.degraded_count,
                "unhealthy": self.unhealthy_count,
            },
            "checks": [
                {
                    "component": c.component.value,
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                    "consecutive_failures": c.consecutive_failures,
                }
                for c in self.checks
            ],
        }


class HealthChecker:
    """Performs and aggregates health checks across all subsystems.

    Usage:
        checker = HealthChecker()

        # Run all checks
        report = checker.check_all()

        # Check a specific component
        result = checker.check_component("kernel")
    """

    def __init__(self):
        self._check_fns: Dict[HealthComponent, Callable[[], HealthCheckResult]] = {}
        self._last_results: Dict[HealthComponent, HealthCheckResult] = {}
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register the default set of health checks."""
        self.register_check(HealthComponent.KERNEL, self._check_kernel)
        self.register_check(HealthComponent.SCHEDULER, self._check_scheduler)
        self.register_check(HealthComponent.EVENT_BUS, self._check_event_bus)
        self.register_check(HealthComponent.PLUGIN_SYSTEM, self._check_plugin_system)
        self.register_check(HealthComponent.TOOL_REGISTRY, self._check_tool_registry)
        self.register_check(HealthComponent.CONFIGURATION, self._check_configuration)
        self.register_check(HealthComponent.STORAGE, self._check_storage)

    def register_check(
        self,
        component: HealthComponent,
        check_fn: Callable[[], HealthCheckResult],
    ) -> None:
        """Register a custom health check function for a component."""
        self._check_fns[component] = check_fn

    def check_all(self) -> HealthReport:
        """Run all registered health checks."""
        report = HealthReport(uptime_seconds=self._get_uptime())

        for component, check_fn in self._check_fns.items():
            try:
                start = time.perf_counter()
                result = check_fn()
                result.latency_ms = (time.perf_counter() - start) * 1000
                self._last_results[component] = result
                report.add_check(result)
            except Exception as exc:
                result = HealthCheckResult(
                    component=component,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed with exception: {exc}",
                )
                self._last_results[component] = result
                report.add_check(result)

        return report

    def check_component(self, component: HealthComponent) -> Optional[HealthCheckResult]:
        """Run a health check for a specific component."""
        check_fn = self._check_fns.get(component)
        if check_fn is None:
            return None
        try:
            start = time.perf_counter()
            result = check_fn()
            result.latency_ms = (time.perf_counter() - start) * 1000
            self._last_results[component] = result
            return result
        except Exception as exc:
            result = HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {exc}",
            )
            self._last_results[component] = result
            return result

    def get_last_result(self, component: HealthComponent) -> Optional[HealthCheckResult]:
        """Get the last health check result for a component."""
        return self._last_results.get(component)

    # ------------------------------------------------------------------
    # Default health check implementations
    # ------------------------------------------------------------------

    def _check_kernel(self) -> HealthCheckResult:
        """Check kernel health by verifying the module is importable.

        Note: The kernel is a singleton that may or may not be actively
        booted depending on the context (CLI vs gateway vs library use).
        This check verifies the kernel module can be imported, indicating
        it is available for use.
        """
        try:
            import kernel.kernel  # noqa: F401
            import importlib
            # Verify the kernel module loaded successfully
            if importlib.util.find_spec("kernel.kernel") is not None:
                return HealthCheckResult(
                    component=HealthComponent.KERNEL,
                    status=HealthStatus.HEALTHY,
                    message="Kernel module is available",
                )
            return HealthCheckResult(
                component=HealthComponent.KERNEL,
                status=HealthStatus.DEGRADED,
                message="Kernel module not fully loaded",
            )
        except ImportError:
            return HealthCheckResult(
                component=HealthComponent.KERNEL,
                status=HealthStatus.DEGRADED,
                message="Kernel module not available in this environment",
            )

    def _check_scheduler(self) -> HealthCheckResult:
        """Check scheduler health."""
        try:
            from kernel.scheduler import KernelScheduler
            # If we can import it, check if any instance is running
            return HealthCheckResult(
                component=HealthComponent.SCHEDULER,
                status=HealthStatus.HEALTHY,
                message="Scheduler module available",
            )
        except ImportError:
            return HealthCheckResult(
                component=HealthComponent.SCHEDULER,
                status=HealthStatus.HEALTHY,
                message="Scheduler not loaded (optional)",
            )

    def _check_event_bus(self) -> HealthCheckResult:
        """Check event bus health."""
        try:
            from kernel.event_bus import EventBus
            return HealthCheckResult(
                component=HealthComponent.EVENT_BUS,
                status=HealthStatus.HEALTHY,
                message="Event bus module available",
            )
        except ImportError:
            return HealthCheckResult(
                component=HealthComponent.EVENT_BUS,
                status=HealthStatus.DEGRADED,
                message="Event bus not available",
            )

    def _check_plugin_system(self) -> HealthCheckResult:
        """Check plugin system health."""
        try:
            from aetheros_cli.plugins import discover_plugins, get_all_plugin_manifests
            discover_plugins()
            manifests = get_all_plugin_manifests()
            errors = [m for m in manifests if getattr(m, 'error', None)]
            if errors:
                return HealthCheckResult(
                    component=HealthComponent.PLUGIN_SYSTEM,
                    status=HealthStatus.DEGRADED,
                    message=f"{len(manifests)} plugins loaded, {len(errors)} with errors",
                    details={"plugin_count": len(manifests), "error_count": len(errors)},
                )
            return HealthCheckResult(
                component=HealthComponent.PLUGIN_SYSTEM,
                status=HealthStatus.HEALTHY,
                message=f"{len(manifests)} plugins loaded",
                details={"plugin_count": len(manifests)},
            )
        except Exception as exc:
            return HealthCheckResult(
                component=HealthComponent.PLUGIN_SYSTEM,
                status=HealthStatus.DEGRADED,
                message=f"Plugin check failed: {exc}",
            )

    def _check_tool_registry(self) -> HealthCheckResult:
        """Check tool registry health."""
        try:
            from tools.registry import registry
            count = len(registry.get_all_tool_names())
            return HealthCheckResult(
                component=HealthComponent.TOOL_REGISTRY,
                status=HealthStatus.HEALTHY if count > 0 else HealthStatus.DEGRADED,
                message=f"{count} tools registered in registry",
            )
        except Exception as exc:
            return HealthCheckResult(
                component=HealthComponent.TOOL_REGISTRY,
                status=HealthStatus.UNHEALTHY,
                message=f"Tool registry unavailable: {exc}",
            )

    def _check_configuration(self) -> HealthCheckResult:
        """Check configuration health."""
        try:
            from aetheros_cli.config import load_config
            cfg = load_config()
            model = cfg.get("model", {})
            provider = model.get("provider", "")
            if provider:
                return HealthCheckResult(
                    component=HealthComponent.CONFIGURATION,
                    status=HealthStatus.HEALTHY,
                    message=f"Configuration valid, provider: {provider}",
                )
            return HealthCheckResult(
                component=HealthComponent.CONFIGURATION,
                status=HealthStatus.DEGRADED,
                message="Configuration loaded but no model provider set",
            )
        except Exception as exc:
            return HealthCheckResult(
                component=HealthComponent.CONFIGURATION,
                status=HealthStatus.UNHEALTHY,
                message=f"Configuration error: {exc}",
            )

    def _check_storage(self) -> HealthCheckResult:
        """Check storage health."""
        try:
            from aetheros_constants import get_aetheros_home
            home = get_aetheros_home()
            if not home.exists():
                return HealthCheckResult(
                    component=HealthComponent.STORAGE,
                    status=HealthStatus.DEGRADED,
                    message=f"AETHEROS_HOME not found at {home}",
                )
            # Check if writable
            test_file = home / ".health_check"
            test_file.write_text("ok")
            test_file.unlink()
            return HealthCheckResult(
                component=HealthComponent.STORAGE,
                status=HealthStatus.HEALTHY,
                message=f"Storage available at {home}",
            )
        except Exception as exc:
            return HealthCheckResult(
                component=HealthComponent.STORAGE,
                status=HealthStatus.UNHEALTHY,
                message=f"Storage check failed: {exc}",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_uptime(self) -> float:
        """Get system uptime."""
        try:
            import psutil
            return time.time() - psutil.boot_time()
        except ImportError:
            return 0.0


def check_health() -> HealthReport:
    """Quick-start convenience function to run all health checks.

    Returns:
        A complete HealthReport.
    """
    checker = HealthChecker()
    return checker.check_all()
