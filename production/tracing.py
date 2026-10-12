"""
Distributed Tracing
===================

Distributed tracing for AetherOS production deployments.

Provides:
- Span-based distributed tracing
- Trace context propagation
- Parent-child span relationships
- Timing and metadata collection
- Export to tracing backends
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Span:
    """A single span in a distributed trace.

    Attributes:
        span_id: Unique span identifier
        trace_id: Parent trace identifier
        parent_span_id: Parent span identifier (None for root spans)
        name: Span name
        start_time: When the span started
        end_time: When the span ended
        duration_ms: Calculated duration
        tags: Span tags/attributes
        status: Span status
        error: Error message if span failed
    """
    span_id: str = ""
    trace_id: str = ""
    parent_span_id: Optional[str] = None
    name: str = ""
    start_time: float = 0.0
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    status: str = "ok"
    error: str = ""

    @property
    def is_completed(self) -> bool:
        return self.end_time is not None

    def finish(self, status: str = "ok", error: str = "") -> None:
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        if error:
            self.error = error

    def set_tag(self, key: str, value: str) -> None:
        self.tags[key] = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "status": self.status,
            "error": self.error,
        }


@dataclass
class TraceContext:
    """Context for a distributed trace, propagated through execution.

    Attributes:
        trace_id: Unique trace identifier
        current_span_id: The currently active span
        root_span_id: The root span in this trace
        baggage: Key-value baggage for cross-process propagation
    """
    trace_id: str
    current_span_id: Optional[str] = None
    root_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)


@dataclass
class TraceReport:
    """Report containing all spans in a trace.

    Attributes:
        trace_id: Trace identifier
        spans: All spans in the trace
        root_span: The root span
        total_duration_ms: Total trace duration
        span_count: Number of spans
    """
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    root_span: Optional[Span] = None
    total_duration_ms: float = 0.0

    @property
    def span_count(self) -> int:
        return len(self.spans)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_count": self.span_count,
            "total_duration_ms": self.total_duration_ms,
            "spans": [s.to_dict() for s in self.spans],
        }


class Tracer:
    """Distributed tracer for creating and managing spans.

    Usage:
        tracer = Tracer()

        # Create a root span
        with tracer.span("workflow.execute") as span:
            # Create a child span
            with tracer.span("tool.call", parent=span) as child:
                result = tool.execute()

        report = tracer.get_report(span.trace_id)
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._spans: Dict[str, Span] = {}
        self._traces: Dict[str, List[str]] = {}  # trace_id -> [span_ids]
        self._local = threading.local()

    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> Span:
        """Create and start a new span.

        Args:
            name: Span name
            trace_id: Trace ID (generated if not provided)
            parent_span_id: Parent span ID

        Returns:
            The new Span object.
        """
        span_id = uuid.uuid4().hex[:16]
        if trace_id is None:
            trace_id = uuid.uuid4().hex[:16]

        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            start_time=time.time(),
        )

        with self._lock:
            self._spans[span_id] = span
            self._traces.setdefault(trace_id, []).append(span_id)

        # Update local context
        self._local.current_span_id = span_id
        self._local.trace_id = trace_id

        return span

    def end_span(self, span: Span, status: str = "ok", error: str = "") -> None:
        """End a span with optional status."""
        span.finish(status=status, error=error)

        # Restore parent context
        if span.parent_span_id:
            self._local.current_span_id = span.parent_span_id
        else:
            self._local.current_span_id = None

    @contextmanager
    def span(self, name: str, parent: Optional[Span] = None) -> Iterator[Span]:
        """Context manager for creating a span.

        Usage:
            with tracer.span("operation") as span:
                do_work()
        """
        parent_id = parent.span_id if parent else self._local.current_span_id
        trace_id = parent.trace_id if parent else self._local.trace_id

        span = self.start_span(name, trace_id=trace_id, parent_span_id=parent_id)
        try:
            yield span
        except Exception as exc:
            span.finish(status="error", error=str(exc))
            raise
        else:
            if not span.is_completed:
                span.finish()

    def get_span(self, span_id: str) -> Optional[Span]:
        """Get a span by ID."""
        with self._lock:
            return self._spans.get(span_id)

    def get_report(self, trace_id: str) -> Optional[TraceReport]:
        """Get a complete trace report."""
        with self._lock:
            span_ids = self._traces.get(trace_id)
            if not span_ids:
                return None

            spans = [self._spans[sid] for sid in span_ids if sid in self._spans]
            if not spans:
                return None

            root = next((s for s in spans if s.parent_span_id is None), spans[0])
            total_duration = root.duration_ms if root.is_completed else (
                time.time() - root.start_time
            )

            return TraceReport(
                trace_id=trace_id,
                spans=spans,
                root_span=root,
                total_duration_ms=total_duration,
            )

    def get_current_context(self) -> Optional[TraceContext]:
        """Get the current trace context (for propagation)."""
        trace_id = getattr(self._local, "trace_id", None)
        current_span_id = getattr(self._local, "current_span_id", None)
        if not trace_id:
            return None

        return TraceContext(
            trace_id=trace_id,
            current_span_id=current_span_id,
            root_span_id=current_span_id,
        )

    def get_all_traces(self) -> Dict[str, TraceReport]:
        """Get reports for all traces."""
        with self._lock:
            trace_ids = list(self._traces.keys())
        reports: Dict[str, TraceReport] = {}
        for tid in trace_ids:
            report = self.get_report(tid)
            if report:
                reports[tid] = report
        return reports

    def clear(self) -> None:
        """Clear all stored spans and traces."""
        with self._lock:
            self._spans.clear()
            self._traces.clear()
