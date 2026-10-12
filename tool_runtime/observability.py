"""Observability System.

Collects and exposes metrics:
- Latency per tool/runtime
- Failure count and rate
- Retry counts
- Resource usage
- Success rate
- Approval requests
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "tags": self.tags,
            "timestamp": self.timestamp,
        }


class ObservabilityCollector:
    """Collects and exposes observability metrics.

    Features:
    - Per-tool latency tracking
    - Success/failure counting
    - Retry tracking
    - Resource usage monitoring
    - Approval request tracking
    - Category and risk-level aggregation
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._executions: Dict[str, List[Dict[str, Any]]] = {}
        self._latency_buckets: Dict[str, List[float]] = defaultdict(list)
        self._failure_counts: Dict[str, int] = defaultdict(int)
        self._success_counts: Dict[str, int] = defaultdict(int)
        self._retry_counts: Dict[str, int] = defaultdict(int)
        self._approval_requests: List[Dict[str, Any]] = []
        self._raw_metrics: List[MetricPoint] = []
        self._max_raw_metrics = 10000
        self._start_time = time.time()

    def record_execution(
        self,
        tool_name: str,
        success: bool,
        duration_ms: float,
        category: Optional[str] = None,
        risk_level: Optional[str] = None,
        retry_attempt: int = 0,
    ) -> None:
        """Record a tool execution metric."""
        tags = {"category": category or "unknown", "risk_level": risk_level or "unknown"}
        self._record_metric(f"tool.{tool_name}.duration_ms", duration_ms, tags)
        self._record_metric(f"tool.{tool_name}.{'success' if success else 'failure'}", 1, tags)
        self._record_metric(f"tool.execution.duration_ms", duration_ms, tags)

        with self._lock:
            self._latency_buckets[tool_name].append(duration_ms)
            if success:
                self._success_counts[tool_name] += 1
            else:
                self._failure_counts[tool_name] += 1
            if retry_attempt > 0:
                self._retry_counts[tool_name] += retry_attempt

            if tool_name not in self._executions:
                self._executions[tool_name] = []
            self._executions[tool_name].append({
                "success": success,
                "duration_ms": duration_ms,
                "category": category,
                "risk_level": risk_level,
                "timestamp": time.time(),
            })
            max_per_tool = 1000
            if len(self._executions[tool_name]) > max_per_tool:
                self._executions[tool_name] = self._executions[tool_name][-max_per_tool:]

    def record_approval_request(self, tool_name: str, request_id: str) -> None:
        """Record an approval request."""
        entry = {
            "tool_name": tool_name,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._approval_requests.append(entry)

    def _record_metric(self, name: str, value: float, tags: Dict[str, str]) -> None:
        point = MetricPoint(name=name, value=value, tags=tags)
        with self._lock:
            self._raw_metrics.append(point)
            if len(self._raw_metrics) > self._max_raw_metrics:
                self._raw_metrics = self._raw_metrics[-self._max_raw_metrics:]

    def get_latency_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get latency statistics for a tool or all tools."""
        with self._lock:
            if tool_name:
                buckets = self._latency_buckets.get(tool_name, [])
            else:
                buckets = [v for vals in self._latency_buckets.values() for v in vals]

        if not buckets:
            return {"avg_ms": 0, "max_ms": 0, "min_ms": 0, "count": 0, "p95_ms": 0}

        sorted_buckets = sorted(buckets)
        n = len(sorted_buckets)
        return {
            "avg_ms": round(sum(sorted_buckets) / n, 2),
            "max_ms": round(max(sorted_buckets), 2),
            "min_ms": round(min(sorted_buckets), 2),
            "count": n,
            "p95_ms": round(sorted_buckets[int(n * 0.95)], 2),
            "p99_ms": round(sorted_buckets[int(n * 0.99)], 2),
        }

    def get_success_rate(self, tool_name: Optional[str] = None) -> float:
        with self._lock:
            if tool_name:
                successes = self._success_counts.get(tool_name, 0)
                failures = self._failure_counts.get(tool_name, 0)
            else:
                successes = sum(self._success_counts.values())
                failures = sum(self._failure_counts.values())

        total = successes + failures
        if total == 0:
            return 1.0
        return round(successes / total, 4)

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        with self._lock:
            total_successes = sum(self._success_counts.values())
            total_failures = sum(self._failure_counts.values())
            total_retries = sum(self._retry_counts.values())

        total = total_successes + total_failures
        success_rate = round(total_successes / total * 100, 2) if total > 0 else 100.0
        latency = self.get_latency_stats()
        uptime = time.time() - self._start_time

        return {
            "total_executions": total,
            "successful": total_successes,
            "failed": total_failures,
            "success_rate_pct": success_rate,
            "total_retries": total_retries,
            "latency": latency,
            "approval_requests": len(self._approval_requests),
            "tools_tracked": len(self._executions),
            "uptime_seconds": round(uptime, 2),
        }

    def get_tool_breakdown(self) -> List[Dict[str, Any]]:
        """Get per-tool metrics breakdown."""
        with self._lock:
            tools = list(self._executions.keys())

        result = []
        for tool in sorted(tools):
            latency = self.get_latency_stats(tool)
            success_rate = self.get_success_rate(tool)
            with self._lock:
                failures = self._failure_counts.get(tool, 0)
                retries = self._retry_counts.get(tool, 0)
            result.append({
                "tool_name": tool,
                "success_rate_pct": round(success_rate * 100, 2),
                "failures": failures,
                "retries": retries,
                "avg_duration_ms": latency["avg_ms"],
                "p95_duration_ms": latency["p95_ms"],
                "total_calls": latency["count"],
            })
        return result

    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for external systems."""
        return {
            "summary": self.get_metrics(),
            "tool_breakdown": self.get_tool_breakdown(),
            "latency_all": self.get_latency_stats(),
        }


# Global singleton
_observability_instance: Optional[ObservabilityCollector] = None


def get_observability_collector() -> ObservabilityCollector:
    global _observability_instance
    if _observability_instance is None:
        _observability_instance = ObservabilityCollector()
    return _observability_instance
