"""Distributed tracing — span creation, context propagation, trace export."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "ok"
    attributes: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
        }


@dataclass
class TraceContext:
    trace_id: str
    span_id: str
    baggage: dict = field(default_factory=dict)


class Tracer:
    def __init__(self, service_name: str = "aetheros"):
        self.service_name = service_name
        self._spans: dict[str, Span] = {}
        self._lock = threading.Lock()
        self._local = threading.local()
        self._exporters: list[callable] = []

    def add_exporter(self, exporter: callable):
        self._exporters.append(exporter)

    def start_span(self, name: str,
                    parent: Optional[TraceContext] = None,
                    attributes: dict = None) -> Span:
        trace_id = parent.trace_id if parent else str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        parent_span_id = parent.span_id if parent else None
        span = Span(
            span_id=span_id, trace_id=trace_id,
            parent_span_id=parent_span_id, name=name,
            start_time=time.time(),
            attributes=attributes or {},
        )
        with self._lock:
            self._spans[span_id] = span
        self._local.current_span = span
        return span

    def end_span(self, span: Span, status: str = "ok"):
        span.end_time = time.time()
        span.status = status
        with self._lock:
            self._spans[span.span_id] = span
        for exporter in self._exporters:
            try:
                exporter(span.to_dict())
            except Exception as e:
                logger.debug("Tracer exporter error: %s", e)

    def add_event(self, span: Span, name: str,
                   attributes: dict = None):
        span.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })

    def inject(self, span: Span) -> TraceContext:
        return TraceContext(
            trace_id=span.trace_id,
            span_id=span.span_id,
        )

    def extract(self, headers: dict) -> Optional[TraceContext]:
        trace_id = headers.get("X-Trace-ID") or headers.get("trace_id")
        span_id = headers.get("X-Span-ID") or headers.get("span_id")
        if trace_id and span_id:
            return TraceContext(trace_id=trace_id, span_id=span_id)
        return None

    def current_span(self) -> Optional[Span]:
        return getattr(self._local, "current_span", None)

    def trace(self, name: str, attributes: dict = None):
        def decorator(func):
            def wrapper(*args, **kwargs):
                ctx = self.current_span()
                span = self.start_span(name, parent=self.inject(ctx)
                                       if ctx else None, attributes=attributes)
                try:
                    result = func(*args, **kwargs)
                    self.end_span(span, "ok")
                    return result
                except Exception as e:
                    self.end_span(span, "error")
                    raise
            return wrapper
        return decorator

    def async_trace(self, name: str, attributes: dict = None):
        def decorator(func):
            async def wrapper(*args, **kwargs):
                ctx = self.current_span()
                span = self.start_span(name, parent=self.inject(ctx)
                                       if ctx else None, attributes=attributes)
                try:
                    result = await func(*args, **kwargs)
                    self.end_span(span, "ok")
                    return result
                except Exception as e:
                    self.end_span(span, "error")
                    raise
            return wrapper
        return decorator

    def get_trace(self, trace_id: str) -> list[Span]:
        with self._lock:
            return [s for s in self._spans.values()
                    if s.trace_id == trace_id]

    def get_recent_spans(self, limit: int = 100) -> list[dict]:
        with self._lock:
            sorted_spans = sorted(
                self._spans.values(),
                key=lambda s: s.start_time, reverse=True)
            return [s.to_dict() for s in sorted_spans[:limit]]

    def get_stats(self) -> dict:
        with self._lock:
            total = len(self._spans)
            by_status = {}
            for s in self._spans.values():
                by_status[s.status] = by_status.get(s.status, 0) + 1
            return {
                "total_spans": total,
                "by_status": by_status,
                "service": self.service_name,
            }

    def close(self):
        self._spans.clear()
        self._exporters.clear()
