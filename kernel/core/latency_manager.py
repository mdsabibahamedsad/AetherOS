"""
Latency Manager — tracks and manages latency across all kernel operations.

Tracks queue latency, planning latency, model latency, tool latency,
network latency, render latency, human approval latency, execution latency,
verification latency, and end-to-end latency.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from collections import defaultdict
from contextlib import contextmanager

from kernel.core.types import (
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class LatencySample:
    """A latency measurement."""
    sample_id: str
    operation: str
    agent_id: str = ""
    task_id: str = ""
    intent_id: str = ""
    latency_ms: float = 0.0
    stage: str = ""  # queue, planning, model, tool, network, render, approval, execution, verification, e2e
    success: bool = True
    timestamp: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LatencyManager:
    """
    Tracks latency across all kernel operations.
    
    Exposes p50, p95, p99 percentiles for each operation type.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        self._samples: List[LatencySample] = []
        self._aggregations: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0, "sum": 0, "min": float('inf'), "max": 0,
            "values": [],  # Keep last 10000 for percentiles
        })
        
        # Maximum samples to keep per operation
        self._max_samples_per_op = 10000
        
        # Wire event bus for automatic latency tracking
        self._wire_event_bus()

    def _wire_event_bus(self) -> None:
        """Wire event bus for automatic latency tracking."""
        if not self.event_bus:
            return

        # Track capability invocation latency
        self.event_bus.subscribe("capability.pre_invoke", self._on_capability_start)
        self.event_bus.subscribe("capability.post_invoke", self._on_capability_end)
        
        # Track task execution latency
        self.event_bus.subscribe("agent.task.started", self._on_task_start)
        self.event_bus.subscribe("agent.task.completed", self._on_task_end)
        self.event_bus.subscribe("agent.task.failed", self._on_task_end)
        
        # Track scheduler latency
        self.event_bus.subscribe("scheduler.admitted", self._on_schedule_start)
        self.event_bus.subscribe("scheduler.scheduled", self._on_schedule_end)
        
        # Track checkpoint latency
        self.event_bus.subscribe("checkpoint.created", self._on_checkpoint_end)
        
        # Track approval latency
        self.event_bus.subscribe("approval.requested", self._on_approval_start)
        self.event_bus.subscribe("approval.granted", self._on_approval_end)
        self.event_bus.subscribe("approval.denied", self._on_approval_end)

    @contextmanager
    def measure(self, operation: str, stage: str = "", agent_id: str = "", task_id: str = "", intent_id: str = ""):
        """Context manager for measuring latency."""
        start = time.perf_counter()
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            self.record_latency(
                operation=operation,
                stage=stage,
                latency_ms=latency_ms,
                agent_id=agent_id,
                task_id=task_id,
                intent_id=intent_id,
                success=success,
            )

    def record_latency(
        self,
        operation: str,
        latency_ms: float,
        stage: str = "",
        agent_id: str = "",
        task_id: str = "",
        intent_id: str = "",
        success: bool = True,
        metadata: Dict[str, Any] = None,
    ) -> LatencySample:
        """Record a latency measurement."""
        sample = LatencySample(
            sample_id=new_id("lat"),
            operation=operation,
            agent_id=agent_id,
            task_id=task_id,
            intent_id=intent_id,
            latency_ms=latency_ms,
            stage=stage,
            success=success,
            metadata=metadata or {},
        )

        with self._lock:
            self._samples.append(sample)
            
            # Update aggregation
            key = f"{operation}|{stage}"
            agg = self._aggregations[key]
            agg["count"] += 1
            agg["sum"] += latency_ms
            agg["min"] = min(agg["min"], latency_ms)
            agg["max"] = max(agg["max"], latency_ms)
            agg["values"].append(latency_ms)
            
            # Trim values
            if len(agg["values"]) > self._max_samples_per_op:
                agg["values"] = agg["values"][-self._max_samples_per_op // 2:]

        return sample

    def _on_capability_start(self, event: Any) -> None:
        data = event.data
        # Store start time in metadata
        invocation_id = data.get("invocation_id", "")
        if invocation_id:
            self._pending_invocations[invocation_id] = time.perf_counter()

    def _on_capability_end(self, event: Any) -> None:
        data = event.data
        invocation_id = data.get("invocation_id", "")
        start_time = self._pending_invocations.pop(invocation_id, None)
        
        if start_time:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.record_latency(
                operation=f"capability.{data.get('capability_id', 'unknown')}",
                stage="execution",
                latency_ms=latency_ms,
                agent_id=data.get("agent_id", ""),
                success=data.get("status") == "completed",
            )

    def _on_task_start(self, event: Any) -> None:
        data = event.data
        agent_id = data.get("agent_id", "")
        self._pending_tasks[agent_id] = time.perf_counter()

    def _on_task_end(self, event: Any) -> None:
        data = event.data
        agent_id = data.get("agent_id", "")
        start_time = self._pending_tasks.pop(agent_id, None)
        
        if start_time:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.record_latency(
                operation="agent.task.execute",
                stage="execution",
                latency_ms=latency_ms,
                agent_id=agent_id,
                success=event.topic.endswith(".completed"),
            )

    def _on_schedule_start(self, event: Any) -> None:
        data = event.data
        agent_id = data.get("agent_id", "")
        self._pending_schedules[agent_id] = time.perf_counter()

    def _on_schedule_end(self, event: Any) -> None:
        data = event.data
        agent_id = data.get("agent_id", "")
        start_time = self._pending_schedules.pop(agent_id, None)
        
        if start_time:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.record_latency(
                operation="scheduler.schedule",
                stage="queue",
                latency_ms=latency_ms,
                agent_id=agent_id,
            )

    def _on_checkpoint_end(self, event: Any) -> None:
        data = event.data
        self.record_latency(
            operation="checkpoint.create",
            stage="execution",
            latency_ms=0,  # Would need start event
            agent_id=data.get("agent_id", ""),
        )

    def _on_approval_start(self, event: Any) -> None:
        data = event.data
        approval_id = data.get("approval_id", "")
        if approval_id:
            self._pending_approvals[approval_id] = time.perf_counter()

    def _on_approval_end(self, event: Any) -> None:
        data = event.data
        approval_id = data.get("approval_id", "")
        start_time = self._pending_approvals.pop(approval_id, None)
        
        if start_time:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.record_latency(
                operation="human.approval",
                stage="approval",
                latency_ms=latency_ms,
                agent_id=data.get("agent_id", ""),
            )

    # Pending operations storage
    _pending_invocations: Dict[str, float] = {}
    _pending_tasks: Dict[str, float] = {}
    _pending_schedules: Dict[str, float] = {}
    _pending_approvals: Dict[str, float] = {}

    def get_percentiles(self, operation: str, stage: str = "") -> Dict[str, float]:
        """Get percentile latency for an operation."""
        key = f"{operation}|{stage}"
        with self._lock:
            agg = self._aggregations.get(key, {})
            values = sorted(agg.get("values", []))
        
        if not values:
            return {"p50": 0, "p95": 0, "p99": 0, "count": 0}
        
        def percentile(p: float) -> float:
            idx = int(len(values) * p / 100)
            idx = min(idx, len(values) - 1)
            return values[idx]
        
        return {
            "p50": percentile(50),
            "p95": percentile(95),
            "p99": percentile(99),
            "count": len(values),
            "mean": agg.get("sum", 0) / agg.get("count", 1),
            "min": agg.get("min", 0),
            "max": agg.get("max", 0),
        }

    def get_all_percentiles(self) -> Dict[str, Dict[str, float]]:
        """Get percentiles for all operations."""
        with self._lock:
            operations = list(self._aggregations.keys())
        
        return {op: self.get_percentiles(*op.split("|", 1)) for op in operations}

    def get_latency_summary(self, agent_id: str = "", since: float = 0) -> Dict[str, Any]:
        """Get latency summary."""
        with self._lock:
            samples = list(self._samples)

        if agent_id:
            samples = [s for s in samples if s.agent_id == agent_id]
        if since > 0:
            samples = [s for s in samples if s.timestamp >= since]

        if not samples:
            return {"total_samples": 0}

        by_operation: Dict[str, List[float]] = defaultdict(list)
        by_stage: Dict[str, List[float]] = defaultdict(list)

        for sample in samples:
            by_operation[sample.operation].append(sample.latency_ms)
            by_stage[sample.stage].append(sample.latency_ms)

        def stats(values: List[float]) -> Dict[str, float]:
            if not values:
                return {}
            sorted_v = sorted(values)
            return {
                "count": len(values),
                "mean": sum(values) / len(values),
                "p50": sorted_v[len(sorted_v) // 2],
                "p95": sorted_v[int(len(sorted_v) * 0.95)],
                "p99": sorted_v[int(len(sorted_v) * 0.99)],
                "min": min(values),
                "max": max(values),
            }

        return {
            "total_samples": len(samples),
            "by_operation": {k: stats(v) for k, v in by_operation.items()},
            "by_stage": {k: stats(v) for k, v in by_stage.items()},
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get latency manager statistics."""
        with self._lock:
            total_samples = len(self._samples)
            operations = len(self._aggregations)
            
            all_latencies = [s.latency_ms for s in self._samples]
            avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0

        return {
            "total_samples": total_samples,
            "tracked_operations": operations,
            "average_latency_ms": avg_latency,
        }

    def shutdown(self) -> None:
        """Shutdown the latency manager."""
        logger.info("LatencyManager: shutting down")
        with self._lock:
            self._samples.clear()
            self._aggregations.clear()
            self._pending_invocations.clear()
            self._pending_tasks.clear()
            self._pending_schedules.clear()
            self._pending_approvals.clear()