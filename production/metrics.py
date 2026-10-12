"""
Metrics Collector
=================

Metrics collection and export for AetherOS production deployments.

Provides:
- Counter, gauge, histogram, and timing metrics
- Configurable aggregation windows
- Multiple export formats (JSON, Prometheus, OpenTelemetry)
- Integration with kernel telemetry and cluster metrics
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMING = "timing"


class MetricUnit(Enum):
    """Units for metrics."""
    COUNT = "count"
    MILLISECONDS = "ms"
    SECONDS = "seconds"
    BYTES = "bytes"
    PERCENT = "percent"
    RATIO = "ratio"


@dataclass
class MetricPoint:
    """A single metric data point.

    Attributes:
        name: Metric name
        value: Metric value
        metric_type: Type of metric
        unit: Unit of measurement
        tags: Tag dictionary
        timestamp: When the point was recorded
        source: Source component
    """
    name: str
    value: float
    metric_type: MetricType = MetricType.GAUGE
    unit: MetricUnit = MetricUnit.COUNT
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "aetheros"


@dataclass
class MetricsSnapshot:
    """A snapshot of metrics at a point in time.

    Attributes:
        timestamp: When the snapshot was taken
        counters: Current counter values
        gauges: Current gauge values
        histograms: Histogram percentiles
        timings: Timing statistics
    """
    timestamp: float = field(default_factory=time.time)
    counters: Dict[str, int] = field(default_factory=dict)
    gauges: Dict[str, float] = field(default_factory=dict)
    histograms: Dict[str, Dict[str, float]] = field(default_factory=dict)
    timings: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {k: dict(v) for k, v in self.histograms.items()},
            "timings": {k: dict(v) for k, v in self.timings.items()},
        }

    def to_prometheus(self) -> str:
        """Format metrics in Prometheus exposition format."""
        lines: List[str] = []
        lines.append(f"# HELP aetheros_metrics AetherOS production metrics")
        lines.append(f"# TYPE aetheros_metrics untyped")
        lines.append(f"aetheros_metrics_info{{version=\"1.0\"}} 1")

        for name, value in self.counters.items():
            safe_name = name.replace(".", "_").replace("-", "_")
            lines.append(f"aetheros_{safe_name}{{type=\"counter\"}} {value}")

        for name, value in self.gauges.items():
            safe_name = name.replace(".", "_").replace("-", "_")
            lines.append(f"aetheros_{safe_name}{{type=\"gauge\"}} {value}")

        return "\n".join(lines)


class MetricsCollector:
    """Collects and aggregates production metrics.

    Thread-safe. Provides counters, gauges, histograms, and timing metrics.

    Usage:
        metrics = MetricsCollector()
        metrics.increment("requests.total")
        metrics.gauge("active_sessions", 5)
        metrics.observe("response_time", 150.0, MetricType.TIMING)
        snapshot = metrics.snapshot()
    """

    def __init__(self, max_histogram_buckets: int = 1000):
        self._lock = threading.RLock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timings: Dict[str, List[float]] = defaultdict(list)
        self._exporters: List[Callable[[MetricPoint], None]] = []
        self._max_histogram_buckets = max_histogram_buckets
        self._start_time = time.time()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def increment(self, name: str, value: int = 1,
                  tags: Optional[Dict[str, str]] = None) -> int:
        """Increment a counter metric."""
        with self._lock:
            self._counters[name] += value
            current = self._counters[name]
        self._notify(MetricPoint(name, float(value), MetricType.COUNTER,
                                 tags=tags or {}))
        return current

    def gauge(self, name: str, value: float,
              tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        with self._lock:
            self._gauges[name] = value
        self._notify(MetricPoint(name, value, MetricType.GAUGE, tags=tags or {}))

    def observe(self, name: str, value: float,
                metric_type: MetricType = MetricType.HISTOGRAM,
                tags: Optional[Dict[str, str]] = None) -> None:
        """Observe a value for histogram or timing distribution."""
        with self._lock:
            if metric_type == MetricType.TIMING:
                self._timings[name].append(value)
                if len(self._timings[name]) > self._max_histogram_buckets:
                    self._timings[name] = self._timings[name][-self._max_histogram_buckets:]
            else:
                self._histograms[name].append(value)
                if len(self._histograms[name]) > self._max_histogram_buckets:
                    self._histograms[name] = self._histograms[name][-self._max_histogram_buckets:]

        self._notify(MetricPoint(name, value, metric_type, tags=tags or {}))

    def time(self, name: str,
             tags: Optional[Dict[str, str]] = None) -> "_TimedContext":
        """Context manager to time an operation."""
        return _TimedContext(self, name, tags)

    # ------------------------------------------------------------------
    # Exporters
    # ------------------------------------------------------------------

    def add_exporter(self, exporter_fn: Callable[[MetricPoint], None]) -> None:
        """Register a metric exporter callback."""
        with self._lock:
            self._exporters.append(exporter_fn)

    def _notify(self, point: MetricPoint) -> None:
        """Notify all registered exporters."""
        for exporter in list(self._exporters):
            try:
                exporter(point)
            except Exception as exc:
                logger.debug("Metrics exporter failed: %s", exc)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_counter(self, name: str) -> int:
        with self._lock:
            return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> Optional[float]:
        with self._lock:
            return self._gauges.get(name)

    def snapshot(self) -> MetricsSnapshot:
        """Take a snapshot of all current metrics."""
        with self._lock:
            histograms_stats: Dict[str, Dict[str, float]] = {}
            for name, values in self._histograms.items():
                if values:
                    sorted_vals = sorted(values)
                    n = len(sorted_vals)
                    histograms_stats[name] = {
                        "count": n,
                        "min": sorted_vals[0],
                        "max": sorted_vals[-1],
                        "avg": sum(sorted_vals) / n,
                        "p50": sorted_vals[int(n * 0.50)],
                        "p90": sorted_vals[int(n * 0.90)],
                        "p95": sorted_vals[int(n * 0.95)],
                        "p99": sorted_vals[int(n * 0.99)] if n >= 100 else sorted_vals[-1],
                    }

            timings_stats: Dict[str, Dict[str, float]] = {}
            for name, values in self._timings.items():
                if values:
                    sorted_vals = sorted(values)
                    n = len(sorted_vals)
                    timings_stats[name] = {
                        "count": n,
                        "min_ms": sorted_vals[0],
                        "max_ms": sorted_vals[-1],
                        "avg_ms": sum(sorted_vals) / n,
                        "p50_ms": sorted_vals[int(n * 0.50)],
                        "p95_ms": sorted_vals[int(n * 0.95)],
                        "p99_ms": sorted_vals[int(n * 0.99)] if n >= 100 else sorted_vals[-1],
                    }

            return MetricsSnapshot(
                counters=dict(self._counters),
                gauges=dict(self._gauges),
                histograms=histograms_stats,
                timings=timings_stats,
            )

    def reset(self) -> None:
        """Reset all collected metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timings.clear()

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    def stats(self) -> Dict[str, Any]:
        return {
            "uptime_seconds": self.uptime_seconds,
            "counter_count": len(self._counters),
            "gauge_count": len(self._gauges),
            "histogram_count": len(self._histograms),
            "timing_count": len(self._timings),
            "exporter_count": len(self._exporters),
        }


class _TimedContext:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, name: str,
                 tags: Optional[Dict[str, str]]):
        self._collector = collector
        self._name = name
        self._tags = tags
        self._start: Optional[float] = None

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        if self._start is not None:
            elapsed_ms = (time.perf_counter() - self._start) * 1000
            self._collector.observe(self._name, elapsed_ms,
                                    MetricType.TIMING, self._tags)
