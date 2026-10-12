"""
Enterprise Observability
========================

Structured metrics and events for:
- Organization metrics
- Workflow metrics
- Approval latency
- Policy evaluations
- Resource usage
- Cluster health
- Plugin health
"""

from __future__ import annotations

import enum
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MetricType(enum.Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMING = "timing"


@dataclass
class EnterpriseMetric:
    """A single structured metric for enterprise observability."""
    name: str
    value: float
    metric_type: MetricType = MetricType.GAUGE
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    unit: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat(),
            "unit": self.unit,
        }


class ObservabilityHub:
    """Central hub for enterprise observability metrics and events.

    Collects, aggregates, and publishes structured metrics from
    all enterprise subsystems.
    """

    def __init__(self) -> None:
        self._metrics: List[EnterpriseMetric] = []
        self._subscribers: Dict[str, List[Callable]] = {}

    def record(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: Optional[Dict[str, str]] = None,
        unit: str = "",
        description: str = "",
    ) -> EnterpriseMetric:
        """Record a metric."""
        metric = EnterpriseMetric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {},
            unit=unit,
            description=description,
        )
        self._metrics.append(metric)
        self._notify("metric", metric)
        return metric

    def increment(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        self.record(name, 1.0, MetricType.COUNTER, tags)

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        self.record(name, value, MetricType.GAUGE, tags)

    def timing(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        self.record(name, duration_ms, MetricType.TIMING, tags, unit="ms")

    # Convenience methods for enterprise domains

    def record_organization_metric(self, org_id: str, name: str, value: float) -> None:
        self.record(f"org.{name}", value, tags={"org_id": org_id})

    def record_approval_latency(self, approval_id: str, duration_ms: float) -> None:
        self.record(
            "approval.latency", duration_ms, MetricType.TIMING,
            tags={"approval_id": approval_id}, unit="ms",
        )

    def record_policy_evaluation(self, policy: str, decision: str, duration_ms: float) -> None:
        self.record(
            "policy.evaluation", duration_ms, MetricType.TIMING,
            tags={"policy": policy, "decision": decision}, unit="ms",
        )

    def record_resource_usage(self, resource_type: str, usage: float, unit: str = "") -> None:
        self.record(
            f"resource.{resource_type}", usage, MetricType.GAUGE,
            unit=unit,
        )

    def record_cluster_health(self, cluster_id: str, healthy_nodes: int, total_nodes: int) -> None:
        self.record(
            "cluster.healthy_nodes", float(healthy_nodes), MetricType.GAUGE,
            tags={"cluster_id": cluster_id},
        )
        self.record(
            "cluster.total_nodes", float(total_nodes), MetricType.GAUGE,
            tags={"cluster_id": cluster_id},
        )

    def record_plugin_health(self, plugin_name: str, healthy: bool) -> None:
        self.record(
            "plugin.health", 1.0 if healthy else 0.0, MetricType.GAUGE,
            tags={"plugin": plugin_name},
        )

    # Subscriber system

    def subscribe(self, event_type: str, callback: Callable) -> None:
        self._subscribers.setdefault(event_type, []).append(callback)

    def _notify(self, event_type: str, data: Any) -> None:
        for callback in self._subscribers.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                logger.warning("Observability subscriber failed: %s", e)

    def query(
        self,
        name: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        tags: Optional[Dict[str, str]] = None,
        limit: int = 100,
    ) -> List[EnterpriseMetric]:
        """Query recorded metrics."""
        results = list(reversed(self._metrics))
        if name:
            results = [m for m in results if m.name == name]
        if metric_type:
            results = [m for m in results if m.metric_type == metric_type]
        if tags:
            results = [m for m in results if all(m.tags.get(k) == v for k, v in tags.items())]
        return results[:limit]

    def clear(self) -> None:
        self._metrics.clear()
