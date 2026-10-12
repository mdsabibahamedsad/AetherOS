"""
Observability for AetherOS
==========================

Structured logging, metrics, health checks, diagnostics, crash reports.

Usage::

    from aetheros_production.observability import HealthChecker, DiagnosticsManager

    checker = HealthChecker()
    health = checker.get_full_health_status()

    diagnostics = DiagnosticsManager()
    report = diagnostics.run_diagnostics()
"""

from __future__ import annotations

import json
import logging
import os
import platform
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """A health check result."""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class Metric:
    """A metric data point."""
    name: str
    value: float
    unit: str
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class CrashReport:
    """A crash report."""
    crash_id: str
    timestamp: float
    error_type: str
    error_message: str
    stack_trace: str = ""
    system_info: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """Performs health checks for AetherOS components.

    Usage::

        checker = HealthChecker()

        # Get full health status
        health = checker.get_full_health_status()

        # Check specific component
        result = checker.check_component("agent")
    """

    def __init__(self) -> None:
        self._checks: Dict[str, callable] = {
            "system": self._check_system,
            "agent": self._check_agent,
            "plugins": self._check_plugins,
            "memory": self._check_memory,
            "tools": self._check_tools,
            "gateway": self._check_gateway,
            "workflows": self._check_workflows,
            "voice": self._check_voice,
            "knowledge": self._check_knowledge,
        }

    def get_full_health_status(self) -> Dict[str, Any]:
        """Get health status of all components."""
        results = {}
        overall_status = HealthStatus.HEALTHY

        for name, check_fn in self._checks.items():
            try:
                result = check_fn()
                results[name] = result
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
            except Exception as exc:
                results[name] = HealthCheck(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=str(exc),
                    timestamp=time.time(),
                )

        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "components": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "latency_ms": check.latency_ms,
                }
                for name, check in results.items()
            },
        }

    def check_component(self, component: str) -> HealthCheck:
        """Check health of a specific component."""
        check_fn = self._checks.get(component)
        if not check_fn:
            return HealthCheck(
                name=component,
                status=HealthStatus.UNKNOWN,
                message=f"Unknown component: {component}",
            )
        return check_fn()

    def _check_system(self) -> HealthCheck:
        """Check system health."""
        start = time.time()

        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()

            status = HealthStatus.HEALTHY
            if cpu > 90 or memory.percent > 90:
                status = HealthStatus.UNHEALTHY
            elif cpu > 70 or memory.percent > 70:
                status = HealthStatus.DEGRADED

            return HealthCheck(
                name="system",
                status=status,
                message=f"CPU: {cpu}%, Memory: {memory.percent}%",
                latency_ms=(time.time() - start) * 1000,
                details={
                    "cpu_percent": cpu,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024 ** 3),
                },
                timestamp=time.time(),
            )
        except ImportError:
            return HealthCheck(
                name="system",
                status=HealthStatus.UNKNOWN,
                message="psutil not available",
                timestamp=time.time(),
            )

    def _check_agent(self) -> HealthCheck:
        """Check agent health."""
        start = time.time()
        try:
            from run_agent import AIAgent
            return HealthCheck(
                name="agent",
                status=HealthStatus.HEALTHY,
                message="Agent module available",
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )
        except Exception as exc:
            return HealthCheck(
                name="agent",
                status=HealthStatus.UNHEALTHY,
                message=f"Agent unavailable: {exc}",
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )

    def _check_plugins(self) -> HealthCheck:
        """Check plugins health."""
        start = time.time()
        try:
            from extensions.manager import get_extension_manager
            manager = get_extension_manager()
            extensions = manager.list_extensions()
            health = manager.get_health_summary()

            status = HealthStatus.HEALTHY
            if health.get("error", 0) > 0:
                status = HealthStatus.DEGRADED

            return HealthCheck(
                name="plugins",
                status=status,
                message=f"{health.get('total', 0)} plugins, {health.get('error', 0)} errors",
                latency_ms=(time.time() - start) * 1000,
                details=health,
                timestamp=time.time(),
            )
        except Exception as exc:
            return HealthCheck(
                name="plugins",
                status=HealthStatus.UNKNOWN,
                message=str(exc),
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )

    def _check_memory(self) -> HealthCheck:
        """Check memory system health."""
        start = time.time()
        try:
            from agent.memory_manager import get_memory_manager
            return HealthCheck(
                name="memory",
                status=HealthStatus.HEALTHY,
                message="Memory system available",
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )
        except Exception as exc:
            return HealthCheck(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message=str(exc),
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )

    def _check_tools(self) -> HealthCheck:
        """Check tools registry health."""
        start = time.time()
        try:
            from tools.registry import registry
            return HealthCheck(
                name="tools",
                status=HealthStatus.HEALTHY,
                message="Tool registry available",
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )
        except Exception as exc:
            return HealthCheck(
                name="tools",
                status=HealthStatus.UNHEALTHY,
                message=str(exc),
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )

    def _check_gateway(self) -> HealthCheck:
        """Check gateway health."""
        start = time.time()
        try:
            from gateway.run import GatewayRunner
            return HealthCheck(
                name="gateway",
                status=HealthStatus.HEALTHY,
                message="Gateway module available",
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )
        except Exception as exc:
            return HealthCheck(
                name="gateway",
                status=HealthStatus.UNKNOWN,
                message=str(exc),
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )

    def _check_workflows(self) -> HealthCheck:
        """Check workflows health."""
        start = time.time()
        try:
            from workflows.engine import WorkflowEngine
            return HealthCheck(
                name="workflows",
                status=HealthStatus.HEALTHY,
                message="Workflow engine available",
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )
        except Exception as exc:
            return HealthCheck(
                name="workflows",
                status=HealthStatus.UNKNOWN,
                message=str(exc),
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )

    def _check_voice(self) -> HealthCheck:
        """Check voice engine health."""
        start = time.time()
        try:
            from aetheros_voice import VoiceManager
            return HealthCheck(
                name="voice",
                status=HealthStatus.HEALTHY,
                message="Voice engine available",
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )
        except Exception as exc:
            return HealthCheck(
                name="voice",
                status=HealthStatus.UNKNOWN,
                message=str(exc),
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )

    def _check_knowledge(self) -> HealthCheck:
        """Check knowledge system health."""
        start = time.time()
        try:
            from aetheros_knowledge import KnowledgeManager
            return HealthCheck(
                name="knowledge",
                status=HealthStatus.HEALTHY,
                message="Knowledge system available",
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )
        except Exception as exc:
            return HealthCheck(
                name="knowledge",
                status=HealthStatus.UNKNOWN,
                message=str(exc),
                latency_ms=(time.time() - start) * 1000,
                timestamp=time.time(),
            )


class DiagnosticsManager:
    """Manages system diagnostics.

    Usage::

        diagnostics = DiagnosticsManager()
        report = diagnostics.run_diagnostics()
        diagnostics.export_diagnostics(report, "diagnostics.json")
    """

    def __init__(self) -> None:
        self._diagnostics_path = Path("diagnostics")

    def run_diagnostics(self) -> Dict[str, Any]:
        """Run full diagnostics."""
        logger.info("Running diagnostics")

        report = {
            "timestamp": time.time(),
            "system": self._get_system_info(),
            "python": self._get_python_info(),
            "aetheros": self._get_aetheros_info(),
            "environment": self._get_environment_info(),
            "disk": self._get_disk_info(),
            "network": self._get_network_info(),
        }

        return report

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        import platform
        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
        }

        try:
            import psutil
            info["cpu_count"] = psutil.cpu_count()
            info["memory_total_gb"] = psutil.virtual_memory().total / (1024 ** 3)
        except ImportError:
            pass

        return info

    def _get_python_info(self) -> Dict[str, Any]:
        """Get Python information."""
        import sys
        return {
            "version": sys.version,
            "implementation": sys.implementation.name,
            "executable": sys.executable,
        }

    def _get_aetheros_info(self) -> Dict[str, Any]:
        """Get AetherOS information."""
        try:
            from aetheros_constants import get_aetheros_home
            home = get_aetheros_home()
            return {
                "home": str(home),
                "version": "1.0.0",
                "config_exists": (home / "config.yaml").exists(),
            }
        except Exception:
            return {"error": "Could not retrieve AetherOS info"}

    def _get_environment_info(self) -> Dict[str, Any]:
        """Get environment information."""
        return {
            "pythonpath": os.environ.get("PYTHONPATH", ""),
            "path_length": len(os.environ.get("PATH", "").split(os.pathsep)),
            "shell": os.environ.get("SHELL", os.environ.get("COMSPEC", "")),
        }

    def _get_disk_info(self) -> Dict[str, Any]:
        """Get disk information."""
        try:
            import shutil
            usage = shutil.disk_usage("/")
            return {
                "total_gb": usage.total / (1024 ** 3),
                "used_gb": usage.used / (1024 ** 3),
                "free_gb": usage.free / (1024 ** 3),
            }
        except Exception:
            return {"error": "Could not retrieve disk info"}

    def _get_network_info(self) -> Dict[str, Any]:
        """Get network information."""
        try:
            import socket
            hostname = socket.gethostname()
            return {
                "hostname": hostname,
                "internet": self._check_internet(),
            }
        except Exception:
            return {"error": "Could not retrieve network info"}

    def _check_internet(self) -> bool:
        """Check internet connectivity."""
        try:
            import urllib.request
            urllib.request.urlopen("https://www.google.com", timeout=5)
            return True
        except Exception:
            return False

    def export_diagnostics(self, report: Dict[str, Any], output_path: str) -> bool:
        """Export diagnostics report."""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            return True
        except Exception as exc:
            logger.error("Failed to export diagnostics: %s", exc)
            return False


class CrashReporter:
    """Manages crash reports."""

    def __init__(self) -> None:
        self._crash_dir = Path("crash_reports")
        self._crash_dir.mkdir(exist_ok=True)

    def report_crash(
        self,
        error_type: str,
        error_message: str,
        stack_trace: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Report a crash."""
        import uuid

        crash_id = str(uuid.uuid4())[:8]
        timestamp = time.time()

        report = CrashReport(
            crash_id=crash_id,
            timestamp=timestamp,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            system_info=self._get_system_info(),
            context=context or {},
        )

        # Save crash report
        report_path = self._crash_dir / f"crash_{crash_id}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "crash_id": report.crash_id,
                "timestamp": report.timestamp,
                "error_type": report.error_type,
                "error_message": report.error_message,
                "stack_trace": report.stack_trace,
                "system_info": report.system_info,
                "context": report.context,
            }, f, indent=2)

        logger.error("Crash reported: %s - %s", error_type, error_message)
        return crash_id

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system info for crash report."""
        import platform
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "python": platform.python_version(),
            "architecture": platform.machine(),
        }

    def list_crash_reports(self) -> List[Dict[str, Any]]:
        """List all crash reports."""
        reports = []
        for report_file in sorted(self._crash_dir.glob("crash_*.json"), reverse=True):
            try:
                with open(report_file, encoding="utf-8") as f:
                    reports.append(json.load(f))
            except Exception:
                pass
        return reports[:100]  # Last 100 reports

    def clear_crash_reports(self) -> int:
        """Clear all crash reports."""
        count = 0
        for report_file in self._crash_dir.glob("crash_*.json"):
            report_file.unlink()
            count += 1
        return count


# Global instances
_health_checker: Optional[HealthChecker] = None
_diagnostics_manager: Optional[DiagnosticsManager] = None
_crash_reporter: Optional[CrashReporter] = None


class MetricsRegistry:
    """In-process metrics registry (counters, gauges, histograms).

    Thread-safe collection of metrics that can be snapshotted and exported
    to Prometheus / OpenTelemetry / JSON formats.

    Usage::

        registry = get_metrics_registry()

        registry.increment("agent.messages", labels={"platform": "cli"})
        registry.observe("agent.latency_ms", 42.0)
        registry.set_gauge("agent.active_sessions", 3)

        snapshot = registry.snapshot()
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._counters: Dict[tuple, float] = {}
        self._gauges: Dict[tuple, float] = {}
        self._histograms: Dict[tuple, List[float]] = {}
        self._names: Dict[tuple, str] = {}

    def _key(self, name: str, labels: Dict[str, str]) -> tuple:
        normalized = tuple(sorted((labels or {}).items()))
        return (name, normalized)

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        with self._lock:
            key = self._key(name, labels)
            self._counters[key] = self._counters.get(key, 0.0) + value
            self._names[key] = name

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric (current value)."""
        with self._lock:
            key = self._key(name, labels)
            self._gauges[key] = float(value)
            self._names[key] = name

    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record an observation into a histogram metric."""
        with self._lock:
            key = self._key(name, labels)
            self._histograms.setdefault(key, []).append(float(value))
            self._names[key] = name

    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of all metrics.

        Returns:
            Dict with "counters", "gauges" and "histograms" sections. Each
            section maps ``name{label=value,...}`` to the metric value
            (histograms also include count/sum).
        """
        with self._lock:
            counters = {
                self._format_name(k): v
                for k, v in sorted(self._counters.items())
            }
            gauges = {
                self._format_name(k): v
                for k, v in sorted(self._gauges.items())
            }
            histograms = {}
            for k, values in sorted(self._histograms.items()):
                histograms[self._format_name(k)] = {
                    "count": len(values),
                    "sum": sum(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values) if values else 0.0,
                }
            return {
                "timestamp": time.time(),
                "counters": counters,
                "gauges": gauges,
                "histograms": histograms,
            }

    def _format_name(self, key: tuple) -> str:
        name, labels = key
        if labels:
            label_str = ",".join(f"{k}=\"{v}\"" for k, v in labels)
            return f"{name}{{{label_str}}}"
        return name

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text exposition format."""
        lines: List[str] = []
        snap = self.snapshot()
        for key, value in snap["counters"].items():
            lines.append(f"# TYPE {key} counter")
            lines.append(f"{key} {value}")
        for key, value in snap["gauges"].items():
            lines.append(f"# TYPE {key} gauge")
            lines.append(f"{key} {value}")
        for key, value in snap["histograms"].items():
            lines.append(f"# TYPE {key} histogram")
            lines.append(f"{key}_count {value['count']}")
            lines.append(f"{key}_sum {value['sum']}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


@dataclass
class Span:
    """A single trace span."""
    name: str
    span_id: str
    trace_id: str
    parent_id: Optional[str] = None
    start_time: float = 0.0
    end_time: Optional[float] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    status: str = "ok"

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000


class Tracer:
    """Simple distributed tracing: trace/span creation, collection, export.

    Usage::

        tracer = get_tracer()

        with tracer.start_span("agent.chat", attributes={"platform": "cli"}) as span:
            do_work()

        traces = tracer.get_traces()
        tracer.export("traces.json")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._spans: List[Span] = []
        self._max_spans = 1000
        self._current_span_id: Optional[str] = None

    def start_span(
        self,
        name: str,
        *,
        attributes: Optional[Dict[str, str]] = None,
        parent_id: Optional[str] = None,
    ) -> Span:
        """Start a new span, setting it as the current span."""
        import uuid

        trace_id = str(uuid.uuid4()).replace("-", "")[:16]
        span_id = str(uuid.uuid4()).replace("-", "")[:16]

        if parent_id is None:
            parent_id = self._current_span_id

        span = Span(
            name=name,
            span_id=span_id,
            trace_id=trace_id,
            parent_id=parent_id,
            start_time=time.time(),
            attributes=dict(attributes or {}),
        )
        with self._lock:
            self._current_span_id = span_id
            self._spans.append(span)
        return span

    def end_span(self, span: Span, *, status: str = "ok") -> None:
        """End a span and restore the previous current span."""
        span.end_time = time.time()
        span.status = status
        with self._lock:
            parent = span.parent_id
            self._current_span_id = parent if parent else None

    @contextmanager
    def start_span(self, name: str, *, attributes: Optional[Dict[str, str]] = None):
        """Context-manager span: ``with tracer.start_span(...) as span:``.

        Also usable without ``as``::

            with tracer.start_span("work"):
                do_work()
        """
        span = self._new_span(name, attributes=attributes)
        try:
            yield span
        except Exception:
            self.end_span(span, status="error")
            raise
        else:
            self.end_span(span, status="ok")

    def begin_span(
        self,
        name: str,
        *,
        attributes: Optional[Dict[str, str]] = None,
        parent_id: Optional[str] = None,
    ) -> Span:
        """Manually start a span (call :meth:`end_span` when done)."""
        return self._new_span(name, attributes=attributes, parent_id=parent_id)

    def _new_span(
        self,
        name: str,
        *,
        attributes: Optional[Dict[str, str]] = None,
        parent_id: Optional[str] = None,
    ) -> Span:
        """Create and register a new span as the current span."""
        import uuid

        trace_id = str(uuid.uuid4()).replace("-", "")[:16]
        span_id = str(uuid.uuid4()).replace("-", "")[:16]

        if parent_id is None:
            parent_id = self._current_span_id

        span = Span(
            name=name,
            span_id=span_id,
            trace_id=trace_id,
            parent_id=parent_id,
            start_time=time.time(),
            attributes=dict(attributes or {}),
        )
        with self._lock:
            self._current_span_id = span_id
            self._spans.append(span)
            if len(self._spans) > self._max_spans:
                self._spans = self._spans[-self._max_spans:]
        return span

    def get_traces(self) -> List[Dict[str, Any]]:
        """Return all spans as a list of dicts."""
        with self._lock:
            spans = list(self._spans)
        return [{
            "name": s.name,
            "trace_id": s.trace_id,
            "span_id": s.span_id,
            "parent_id": s.parent_id,
            "duration_ms": s.duration_ms,
            "status": s.status,
            "attributes": s.attributes,
        } for s in spans]

    def export(self, path: str) -> bool:
        """Export spans to a JSON file."""
        try:
            data = {"traces": self.get_traces(), "timestamp": time.time()}
            Path(path).write_text(json.dumps(data, indent=2), "utf-8")
            return True
        except Exception as exc:
            logger.error("Failed to export traces: %s", exc)
            return False


# Global instances
_metrics_registry: Optional[MetricsRegistry] = None
_tracer: Optional[Tracer] = None


def get_health_checker() -> HealthChecker:
    """Return the global HealthChecker singleton."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def get_diagnostics_manager() -> DiagnosticsManager:
    """Return the global DiagnosticsManager singleton."""
    global _diagnostics_manager
    if _diagnostics_manager is None:
        _diagnostics_manager = DiagnosticsManager()
    return _diagnostics_manager


def get_crash_reporter() -> CrashReporter:
    """Return the global CrashReporter singleton."""
    global _crash_reporter
    if _crash_reporter is None:
        _crash_reporter = CrashReporter()
    return _crash_reporter


def get_metrics_registry() -> MetricsRegistry:
    """Return the global MetricsRegistry singleton."""
    global _metrics_registry
    if _metrics_registry is None:
        _metrics_registry = MetricsRegistry()
    return _metrics_registry


def get_tracer() -> Tracer:
    """Return the global Tracer singleton."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
