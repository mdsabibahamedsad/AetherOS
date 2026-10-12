"""
Cluster Metrics Collector — collects and exposes cluster-level metrics.

Tracks:
  - Cluster health and availability
  - Node-level metrics (CPU, memory, load)
  - Task distribution across nodes
  - Execution latency
  - Queue depths
  - Failure rates
  - Resource utilization

Provides structured metrics for monitoring and observability.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class MetricCategory(enum.Enum):
    """Categories of cluster metrics."""
    SYSTEM = "system"             # Overall cluster health
    NODE = "node"                 # Per-node metrics
    TASK = "task"                 # Task execution metrics
    NETWORK = "network"           # Network and transport metrics
    SCHEDULER = "scheduler"       # Scheduling metrics
    RESOURCE = "resource"         # Resource utilization
    ERROR = "error"               # Error and failure metrics


@dataclass
class MetricPoint:
    """A single metric data point.

    Attributes:
        name: Metric name
        value: Metric value
        category: Metric category
        node_id: Associated node (empty for cluster-level)
        timestamp: When the metric was recorded
        labels: Additional label tags
    """
    name: str = ""
    value: float = 0.0
    category: MetricCategory = MetricCategory.SYSTEM
    node_id: str = ""
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


class ClusterMetricsCollector:
    """Collects and exposes cluster metrics.

    Aggregates metrics from all cluster nodes and provides
    structured summaries for monitoring and observability.

    Usage:
        metrics = ClusterMetricsCollector(event_bus)

        # Record a metric
        metrics.record("task.latency_ms", 1500.0, MetricCategory.TASK, node_id="node-1")

        # Get summary
        summary = metrics.summary()
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()

        # Metric storage
        self._metrics: Dict[str, List[float]] = defaultdict(list)
        # Counter metrics (monotonically increasing)
        self._counters: Dict[str, int] = defaultdict(int)
        # Gauges (latest value)
        self._gauges: Dict[str, float] = {}
        # Histograms (value distributions)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        # Per-node metrics
        self._node_metrics: Dict[str, Dict[str, float]] = defaultdict(dict)

        # Configuration
        self._max_metric_history = 1000
        self._histogram_buckets = [1, 5, 10, 50, 100, 500, 1000, 5000, 10000, 30000]

        # Time series tracking
        self._start_time = time.time()
        self._metric_count = 0

    # ------------------------------------------------------------------
    # Metric recording
    # ------------------------------------------------------------------

    def record(self, name: str, value: float,
               category: MetricCategory = MetricCategory.SYSTEM,
               node_id: str = "",
               labels: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value."""
        now = time.time()

        with self._lock:
            self._metrics[name].append(value)
            if len(self._metrics[name]) > self._max_metric_history:
                self._metrics[name] = self._metrics[name][-self._max_metric_history:]
            self._gauges[name] = value
            self._metric_count += 1

            if node_id:
                self._node_metrics[node_id][name] = value

        if self._event_bus:
            self._event_bus.emit_async("cluster.metric_recorded", {
                "name": name,
                "value": value,
                "category": category.value,
                "node_id": node_id,
                "labels": labels or {},
            })

    def increment(self, name: str, delta: int = 1,
                  node_id: str = "") -> None:
        """Increment a counter metric."""
        with self._lock:
            self._counters[name] += delta
            if node_id:
                key = f"{node_id}:{name}"
                self._counters[key] += delta

    def observe_histogram(self, name: str, value: float) -> None:
        """Record a value for histogram distribution."""
        with self._lock:
            self._histograms[name].append(value)
            if len(self._histograms[name]) > self._max_metric_history:
                self._histograms[name] = self._histograms[name][-self._max_metric_history:]

    def set_gauge(self, name: str, value: float,
                  node_id: str = "") -> None:
        """Set a gauge metric to a specific value."""
        with self._lock:
            self._gauges[name] = value
            if node_id:
                self._node_metrics[node_id][name] = value

    # ------------------------------------------------------------------
    # Convenience recording methods
    # ------------------------------------------------------------------

    def record_task_latency(self, task_id: str, latency_ms: float,
                            node_id: str = "") -> None:
        """Record task execution latency."""
        self.record("task.latency_ms", latency_ms, MetricCategory.TASK, node_id)
        self.observe_histogram("task.latency_ms", latency_ms)

    def record_task_success(self, node_id: str = "") -> None:
        """Record a successful task execution."""
        self.increment("task.completed", node_id=node_id)

    def record_task_failure(self, node_id: str = "",
                            error_type: str = "unknown") -> None:
        """Record a task failure."""
        self.increment("task.failed", node_id=node_id)
        self.increment(f"task.failed.{error_type}")

    def record_node_load(self, node_id: str, load: float) -> None:
        """Record a node's current load."""
        self.set_gauge("node.load", load, node_id)

    def record_node_memory(self, node_id: str, used_mb: int,
                           total_mb: int) -> None:
        """Record node memory usage."""
        utilization = (used_mb / total_mb * 100) if total_mb > 0 else 0
        self.set_gauge("node.memory_used_mb", float(used_mb), node_id)
        self.set_gauge("node.memory_total_mb", float(total_mb), node_id)
        self.set_gauge("node.memory_utilization_pct", utilization, node_id)

    def record_node_cpu(self, node_id: str, cpu_percent: float) -> None:
        """Record node CPU usage percentage."""
        self.set_gauge("node.cpu_percent", cpu_percent, node_id)

    def record_network_latency(self, source: str, target: str,
                               latency_ms: float) -> None:
        """Record network latency between nodes."""
        self.record(
            f"network.latency.{source}.{target}",
            latency_ms,
            MetricCategory.NETWORK,
        )

    def record_scheduler_decision(self, strategy: str) -> None:
        """Record a scheduling decision."""
        self.increment(f"scheduler.decision.{strategy}")

    def record_queue_depth(self, depth: int) -> None:
        """Record the current queue depth."""
        self.set_gauge("scheduler.queue_depth", float(depth))

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_metric(self, name: str) -> Optional[float]:
        """Get the latest value of a metric."""
        with self._lock:
            return self._gauges.get(name)

    def get_counter(self, name: str) -> int:
        """Get the current counter value."""
        with self._lock:
            return self._counters.get(name, 0)

    def get_metric_history(self, name: str) -> List[float]:
        """Get the recorded history of a metric."""
        with self._lock:
            return list(self._metrics.get(name, []))

    def get_metric_stats(self, name: str) -> Dict[str, float]:
        """Get statistical summary of a metric."""
        with self._lock:
            values = self._metrics.get(name, [])
            if not values:
                return {"count": 0, "min": 0, "max": 0, "avg": 0, "last": 0}

            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "last": values[-1] if values else 0,
            }

    def get_histogram_percentiles(self, name: str) -> Dict[str, float]:
        """Get percentile distribution of a histogram metric."""
        with self._lock:
            values = sorted(self._histograms.get(name, []))
            if not values:
                return {}

            n = len(values)
            return {
                "p50": values[int(n * 0.50)],
                "p75": values[int(n * 0.75)],
                "p90": values[int(n * 0.90)],
                "p95": values[int(n * 0.95)],
                "p99": values[int(n * 0.99)] if n >= 100 else values[-1],
                "count": n,
            }

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_node_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get all per-node metrics."""
        with self._lock:
            return dict(self._node_metrics)

    def summary(self) -> Dict[str, Any]:
        """Get a comprehensive metrics summary."""
        with self._lock:
            total_operations = sum(
                v for k, v in self._counters.items()
                if "failed" not in k
            )
            total_errors = sum(
                v for k, v in self._counters.items()
                if "failed" in k or "error" in k
            )

            error_rate = 0.0
            if total_operations + total_errors > 0:
                error_rate = total_errors / (total_operations + total_errors) * 100

            return {
                "uptime_seconds": time.time() - self._start_time,
                "total_metrics": self._metric_count,
                "tracked_metrics": len(self._metrics),
                "total_operations": total_operations,
                "total_errors": total_errors,
                "error_rate_pct": round(error_rate, 2),
                "counters": dict(self._counters),
                "latest_gauges": dict(self._gauges),
                "nodes_tracked": len(self._node_metrics),
            }

    def get_stats(self) -> Dict[str, Any]:
        """Return collector statistics."""
        with self._lock:
            return {
                "tracked_metrics": len(self._metrics),
                "tracked_counters": len(self._counters),
                "tracked_histograms": len(self._histograms),
                "tracked_gauges": len(self._gauges),
                "tracked_nodes": len(self._node_metrics),
                "metric_count": self._metric_count,
            }
