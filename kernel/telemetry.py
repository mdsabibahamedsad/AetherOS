"""
Telemetry Collector — collects execution metrics, latency, errors, and usage data.

Provides:
  - Execution metrics (duration, tool calls, token usage)
  - Latency tracking
  - Error collection and categorization
  - Runtime health metrics
  - Vendor-agnostic metric emission

This is NOT a vendor-specific APM integration. It provides structured
metric collection that can be exported to any backend.
"""

from __future__ import annotations

import logging
import statistics
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point.

    Attributes:
        name: Metric name (e.g. "agent.duration", "tool.calls")
        value: Numeric value
        labels: Label dict for dimensionality
        timestamp: Unix timestamp
        unit: Unit string ("ms", "count", "tokens", etc.)
    """
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    unit: str = "count"


class TelemetryCollector:
    """Collects and aggregates kernel telemetry metrics.

    Usage:
        telemetry = TelemetryCollector(event_bus)

        # Record a metric
        telemetry.record("agent.duration", 12.5, labels={"agent": "worker-1"})

        # Start a timed operation
        with telemetry.timed("tool.execution", labels={"tool": "web_search"}):
            result = search()

        # Get stats
        stats = telemetry.get_stats("tool.execution")
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        # name -> list of MetricPoint
        self._metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._exporters: List[Callable[[MetricPoint], None]] = []
        self._max_points_per_metric = 10000
        self._start_time = time.time()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, name: str, value: float,
               labels: Dict[str, str] = None,
               unit: str = "count") -> MetricPoint:
        """Record a metric point."""
        point = MetricPoint(
            name=name,
            value=value,
            labels=labels or {},
            unit=unit,
        )

        with self._lock:
            points = self._metrics[name]
            points.append(point)
            # Trim to max size
            if len(points) > self._max_points_per_metric:
                points[:len(points) - self._max_points_per_metric] = []

        # Notify exporters
        for exporter in list(self._exporters):
            try:
                exporter(point)
            except Exception as exc:
                logger.debug("Telemetry: exporter failed: %s", exc)

        return point

    def increment(self, name: str, labels: Dict[str, str] = None,
                  amount: float = 1.0) -> MetricPoint:
        """Increment a counter metric."""
        return self.record(name, amount, labels=labels, unit="count")

    def record_error(self, category: str, error: str,
                     labels: Dict[str, str] = None) -> None:
        """Record an error occurrence."""
        with self._lock:
            self._error_counts[category] += 1

        self.record("error.count", 1.0, labels={
            "category": category,
            **(labels or {}),
        })
        logger.debug("Telemetry: error [%s]: %s", category, error)

    # ------------------------------------------------------------------
    # Timed operations
    # ------------------------------------------------------------------

    def timed(self, name: str, labels: Dict[str, str] = None):
        """Context manager for timing operations.

        Usage:
            with telemetry.timed("tool.execution", {"tool": "web_search"}):
                result = tool.execute()
        """
        return _TimedContext(self, name, labels or {})

    def record_duration(self, name: str, duration_seconds: float,
                        labels: Dict[str, str] = None) -> MetricPoint:
        """Record a duration metric (in milliseconds)."""
        return self.record(
            name, duration_seconds * 1000,
            labels=labels, unit="ms",
        )

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def get_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """Get statistical summary for a metric."""
        with self._lock:
            points = list(self._metrics.get(name, []))

        if not points:
            return None

        values = [p.value for p in points]
        return {
            "name": name,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values) if len(values) > 1 else values[0],
            "sum": sum(values),
            "last": values[-1],
            "unit": points[-1].unit if points else "count",
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistical summaries for all metrics."""
        with self._lock:
            names = list(self._metrics.keys())
        return {
            name: self.get_stats(name)
            for name in sorted(names)
        }

    def get_error_summary(self) -> Dict[str, Any]:
        """Get error count summary."""
        with self._lock:
            return {
                "total": sum(self._error_counts.values()),
                "by_category": dict(self._error_counts),
            }

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_uptime(self) -> float:
        """Get collector uptime in seconds."""
        return time.time() - self._start_time

    def summary(self) -> Dict[str, Any]:
        """Get a complete telemetry summary."""
        metric_count = 0
        with self._lock:
            for points in self._metrics.values():
                metric_count += len(points)

        return {
            "uptime_seconds": self.get_uptime(),
            "total_metrics": metric_count,
            "metric_names": sorted(self._metrics.keys()),
            "metric_count": len(self._metrics),
            "errors": self.get_error_summary(),
            "stats": self.get_all_stats(),
        }

    # ------------------------------------------------------------------
    # Exporters
    # ------------------------------------------------------------------

    def add_exporter(self, exporter_fn: Callable[[MetricPoint], None]) -> None:
        """Register a metric exporter callback.

        The exporter receives every MetricPoint as it is recorded.
        Exporters should be non-blocking and handle their own errors.
        """
        with self._lock:
            self._exporters.append(exporter_fn)
        logger.debug("Telemetry: registered exporter %s", getattr(exporter_fn, "__name__", "?"))

    def remove_exporter(self, exporter_fn: Callable) -> bool:
        """Remove a metric exporter."""
        with self._lock:
            try:
                self._exporters.remove(exporter_fn)
                return True
            except ValueError:
                return False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all collected metrics."""
        with self._lock:
            self._metrics.clear()
            self._error_counts.clear()
        logger.info("Telemetry: reset all metrics")

    def shutdown(self) -> None:
        """Shutdown the telemetry collector."""
        logger.info("Telemetry: shutdown (collected %d metrics across %d names)",
                     sum(len(v) for v in self._metrics.values()),
                     len(self._metrics))


class _TimedContext:
    """Context manager for timing code blocks."""

    def __init__(self, collector: TelemetryCollector, name: str,
                 labels: Dict[str, str]):
        self._collector = collector
        self._name = name
        self._labels = labels
        self._start: Optional[float] = None

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, *args):
        if self._start is not None:
            duration = time.time() - self._start
            self._collector.record_duration(
                self._name, duration, labels=self._labels,
            )
