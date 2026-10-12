"""
Observability Engine — tracing, metrics, and observability.

Provides distributed tracing, metrics collection, and real-time observability.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict
from contextlib import contextmanager

from kernel.core.types import (
    ProvenanceType,
    new_id,
    _now,
)
from kernel.event_bus import EventBus, EventTopics

logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    """A trace span."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation: str
    agent_id: str = ""
    process_id: str = ""
    task_id: str = ""
    intent_id: str = ""
    start_time: float = field(default_factory=_now)
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    status: str = "started"  # started, completed, failed
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    provenance: ProvenanceType = ProvenanceType.SYSTEM_DERIVED


@dataclass
class MetricPoint:
    """A metric data point."""
    name: str
    value: float
    timestamp: float = field(default_factory=_now)
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"  # gauge, counter, histogram


class ObservabilityEngine:
    """
    Observability engine for tracing, metrics, and real-time monitoring.
    
    Provides:
    - Distributed tracing with span hierarchy
    - Metrics collection and aggregation
    - Real-time event streaming
    - Health and performance monitoring
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        # Tracing
        self._spans: Dict[str, TraceSpan] = {}
        self._active_spans: Dict[str, TraceSpan] = {}  # span_id -> span
        self._trace_index: Dict[str, List[str]] = defaultdict(list)  # trace_id -> span_ids
        
        # Metrics
        self._metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._metric_aggregations: Dict[str, Dict[str, float]] = {}
        
        # Sampling
        self._trace_sampling_rate = config.trace_sampling_rate
        
        # Callbacks
        self._span_callbacks: List[Callable[[TraceSpan], None]] = []
        self._metric_callbacks: List[Callable[[MetricPoint], None]] = []

        # Wire event bus
        self._wire_event_bus()

    def _wire_event_bus(self) -> None:
        """Wire event bus for automatic tracing."""
        if not self.event_bus:
            return

        # Trace agent lifecycle
        self.event_bus.subscribe("agent.lifecycle.transition", self._on_agent_transition)
        self.event_bus.subscribe("agent.task.started", self._on_task_started)
        self.event_bus.subscribe("agent.task.completed", self._on_task_completed)
        self.event_bus.subscribe("agent.task.failed", self._on_task_failed)
        
        # Trace capability invocations
        self.event_bus.subscribe("capability.pre_invoke", self._on_capability_pre_invoke)
        self.event_bus.subscribe("capability.post_invoke", self._on_capability_post_invoke)
        
        # Trace intent
        self.event_bus.subscribe("intent.created", self._on_intent_created)
        self.event_bus.subscribe("intent.admitted", self._on_intent_admitted)
        
        # Trace scheduler
        self.event_bus.subscribe("scheduler.scheduled", self._on_scheduled)
        self.event_bus.subscribe("scheduler.preempted", self._on_preempted)
        
        # Trace checkpoints
        self.event_bus.subscribe("checkpoint.created", self._on_checkpoint_created)

    def _should_sample(self) -> bool:
        """Check if trace should be sampled."""
        import random
        return random.random() < self._trace_sampling_rate

    @contextmanager
    def trace(
        self,
        operation: str,
        agent_id: str = "",
        process_id: str = "",
        task_id: str = "",
        intent_id: str = "",
        parent_span: TraceSpan = None,
        tags: Dict[str, str] = None,
    ):
        """Context manager for creating a trace span."""
        if not self._should_sample():
            yield None
            return

        trace_id = parent_span.trace_id if parent_span else new_id("trace")
        span_id = new_id("span")
        parent_span_id = parent_span.span_id if parent_span else None

        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation=operation,
            agent_id=agent_id,
            process_id=process_id,
            task_id=task_id,
            intent_id=intent_id,
            tags=tags or {},
        )

        with self._lock:
            self._spans[span_id] = span
            self._active_spans[span_id] = span
            self._trace_index[trace_id].append(span_id)

        start_time = _now()

        try:
            yield span
            span.status = "completed"
        except Exception as exc:
            span.status = "failed"
            span.tags["error"] = str(exc)
            raise
        finally:
            span.end_time = _now()
            span.duration_ms = (span.end_time - start_time) * 1000
            
            with self._lock:
                self._active_spans.pop(span_id, None)

            # Call callbacks
            for callback in self._span_callbacks:
                try:
                    callback(span)
                except Exception as exc:
                    logger.error("Span callback error: %s", exc)

    def start_span(
        self,
        operation: str,
        agent_id: str = "",
        process_id: str = "",
        task_id: str = "",
        intent_id: str = "",
        parent_span: TraceSpan = None,
        tags: Dict[str, str] = None,
    ) -> Optional[TraceSpan]:
        """Start a new span (manual management)."""
        if not self._should_sample():
            return None

        trace_id = parent_span.trace_id if parent_span else new_id("trace")
        span_id = new_id("span")
        parent_span_id = parent_span.span_id if parent_span else None

        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation=operation,
            agent_id=agent_id,
            process_id=process_id,
            task_id=task_id,
            intent_id=intent_id,
            tags=tags or {},
        )

        with self._lock:
            self._spans[span_id] = span
            self._active_spans[span_id] = span
            self._trace_index[trace_id].append(span_id)

        return span

    def end_span(self, span: TraceSpan, status: str = "completed", error: str = "") -> None:
        """End a span."""
        if not span:
            return

        span.end_time = _now()
        span.duration_ms = (span.end_time - span.start_time) * 1000
        span.status = status
        if error:
            span.tags["error"] = error

        with self._lock:
            self._active_spans.pop(span.span_id, None)

        for callback in self._span_callbacks:
            try:
                callback(span)
            except Exception as exc:
                logger.error("Span callback error: %s", exc)

    def add_span_log(self, span: TraceSpan, message: str, fields: Dict[str, Any] = None) -> None:
        """Add a log entry to a span."""
        if not span:
            return
        span.logs.append({
            "timestamp": _now(),
            "message": message,
            "fields": fields or {},
        })

    def add_span_tag(self, span: TraceSpan, key: str, value: str) -> None:
        """Add a tag to a span."""
        if not span:
            return
        span.tags[key] = value

    def record_metric(
        self,
        name: str,
        value: float,
        labels: Dict[str, str] = None,
        metric_type: str = "gauge",
    ) -> None:
        """Record a metric point."""
        point = MetricPoint(
            name=name,
            value=value,
            labels=labels or {},
            metric_type=metric_type,
        )

        with self._lock:
            self._metrics[name].append(point)
            
            # Update aggregations
            key = name + "|" + "|".join(f"{k}={v}" for k, v in sorted((labels or {}).items()))
            agg = self._metric_aggregations.setdefault(key, {
                "count": 0, "sum": 0, "min": float('inf'), "max": float('-inf')
            })
            agg["count"] += 1
            agg["sum"] += value
            agg["min"] = min(agg["min"], value)
            agg["max"] = max(agg["max"], value)

        for callback in self._metric_callbacks:
            try:
                callback(point)
            except Exception as exc:
                logger.error("Metric callback error: %s", exc)

    def increment_counter(self, name: str, labels: Dict[str, str] = None, value: float = 1.0) -> None:
        """Increment a counter metric."""
        self.record_metric(name, value, labels, "counter")

    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Record a histogram value."""
        self.record_metric(name, value, labels, "histogram")

    def get_trace(self, trace_id: str) -> List[TraceSpan]:
        """Get all spans for a trace."""
        with self._lock:
            span_ids = self._trace_index.get(trace_id, [])
            return [self._spans[sid] for sid in span_ids if sid in self._spans]

    def get_span(self, span_id: str) -> Optional[TraceSpan]:
        """Get a span by ID."""
        with self._lock:
            return self._spans.get(span_id)

    def get_active_spans(self) -> List[TraceSpan]:
        """Get all active spans."""
        with self._lock:
            return list(self._active_spans.values())

    def get_metric_aggregation(self, name: str, labels: Dict[str, str] = None) -> Dict[str, float]:
        """Get metric aggregation."""
        key = name + "|" + "|".join(f"{k}={v}" for k, v in sorted((labels or {}).items()))
        with self._lock:
            return self._metric_aggregations.get(key, {})

    def register_span_callback(self, callback: Callable[[TraceSpan], None]) -> None:
        """Register a span callback."""
        self._span_callbacks.append(callback)

    def register_metric_callback(self, callback: Callable[[MetricPoint], None]) -> None:
        """Register a metric callback."""
        self._metric_callbacks.append(callback)

    # Event handlers for automatic tracing
    def _on_agent_transition(self, event: Any) -> None:
        data = event.data
        span = self.start_span(
            f"agent.{data.get('to_state', 'transition')}",
            agent_id=data.get("agent_id", ""),
            tags={"from_state": data.get("from_state", ""), "to_state": data.get("to_state", "")},
        )
        if span:
            self.end_span(span)

    def _on_task_started(self, event: Any) -> None:
        data = event.data
        span = self.start_span(
            "agent.task.execute",
            agent_id=data.get("agent_id", ""),
            tags={"task": data.get("task", "")[:100]},
        )
        # Span will be ended by completion/failed handlers

    def _on_task_completed(self, event: Any) -> None:
        data = event.data
        # Find and end the task span
        for span in self._active_spans.values():
            if span.agent_id == data.get("agent_id") and span.operation == "agent.task.execute":
                self.end_span(span, "completed")
                break

    def _on_task_failed(self, event: Any) -> None:
        data = event.data
        for span in self._active_spans.values():
            if span.agent_id == data.get("agent_id") and span.operation == "agent.task.execute":
                self.end_span(span, "failed", data.get("error", ""))
                break

    def _on_capability_pre_invoke(self, event: Any) -> None:
        data = event.data
        span = self.start_span(
            f"capability.{data.get('capability_id', 'unknown')}",
            agent_id=data.get("agent_id", ""),
            tags={
                "invocation_id": data.get("invocation_id", ""),
                "trace_id": data.get("trace_id", ""),
            },
        )
        if span:
            # Store for post-invoke
            span.tags["_capability_invocation_id"] = data.get("invocation_id", "")

    def _on_capability_post_invoke(self, event: Any) -> None:
        data = event.data
        invocation_id = data.get("invocation_id", "")
        for span in self._active_spans.values():
            if span.tags.get("_capability_invocation_id") == invocation_id:
                status = "completed" if data.get("status") == "completed" else "failed"
                error = data.get("error", "")
                self.end_span(span, status, error)
                break

    def _on_intent_created(self, event: Any) -> None:
        data = event.data
        span = self.start_span(
            "intent.create",
            agent_id=data.get("actor", ""),
            tags={"intent_id": data.get("intent_id", "")},
        )
        if span:
            self.end_span(span)

    def _on_intent_admitted(self, event: Any) -> None:
        data = event.data
        span = self.start_span(
            "intent.admit",
            agent_id=data.get("actor", ""),
            tags={"intent_id": data.get("intent_id", ""), "risk": data.get("risk_level", "")},
        )
        if span:
            self.end_span(span)

    def _on_scheduled(self, event: Any) -> None:
        data = event.data
        span = self.start_span(
            "scheduler.schedule",
            agent_id=data.get("agent_id", ""),
            tags={"priority": data.get("priority", "")},
        )
        if span:
            self.end_span(span)

    def _on_preempted(self, event: Any) -> None:
        data = event.data
        span = self.start_span(
            "scheduler.preempt",
            agent_id=data.get("agent_id", ""),
        )
        if span:
            self.end_span(span)

    def _on_checkpoint_created(self, event: Any) -> None:
        data = event.data
        span = self.start_span(
            "checkpoint.create",
            agent_id=data.get("agent_id", ""),
            tags={"checkpoint_id": data.get("checkpoint_id", "")},
        )
        if span:
            self.end_span(span)

    def get_stats(self) -> Dict[str, Any]:
        """Get observability engine statistics."""
        with self._lock:
            total_spans = len(self._spans)
            active_spans = len(self._active_spans)
            total_traces = len(self._trace_index)
            total_metrics = sum(len(v) for v in self._metrics.values())
            
            # Compute span duration stats
            completed_spans = [s for s in self._spans.values() if s.end_time]
            durations = [s.duration_ms for s in completed_spans]
            avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_spans": total_spans,
            "active_spans": active_spans,
            "total_traces": total_traces,
            "total_metric_points": total_metrics,
            "avg_span_duration_ms": avg_duration,
            "sampling_rate": self._trace_sampling_rate,
        }

    def shutdown(self) -> None:
        """Shutdown the observability engine."""
        logger.info("ObservabilityEngine: shutting down")
        with self._lock:
            self._spans.clear()
            self._active_spans.clear()
            self._trace_index.clear()
            self._metrics.clear()
            self._metric_aggregations.clear()