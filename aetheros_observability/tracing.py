"""Unified tracing facade.

Thin facade over the canonical AetherOS tracer
(``aetheros_production.observability.Tracer`` singleton) integrated with
the rich ``aetheros_observability.TraceContext``.

Provides span helpers for the full agent lifecycle hierarchy:

    User Request
    └── UI Request
        └── Gateway Request
            └── Mission
                └── Task
                    └── Agent
                        ├── Model Call
                        ├── Tool Call
                        ├── Memory Read / Write
                        └── Result

Spans record metadata only — never prompt/response content.
"""

from __future__ import annotations

import contextlib
import time
from typing import Any, Dict, Optional

from aetheros_observability.context import (
    TraceContext,
    get_current_context,
    set_current_context,
    new_span_id,
)
from aetheros_observability.metrics import get_unified_metrics


class UnifiedTracer:
    """Facade over the canonical tracer with trace-context propagation."""

    def __init__(self, tracer=None) -> None:
        self._tracer = tracer

    @property
    def tracer(self):
        """The underlying tracer (lazy)."""
        if self._tracer is None:
            from aetheros_production.observability import get_tracer
            self._tracer = get_tracer()
        return self._tracer

    @contextlib.contextmanager
    def start_span(
        self,
        name: str,
        *,
        attributes: Optional[Dict[str, Any]] = None,
        trace_context: Optional[TraceContext] = None,
    ):
        """Open a span, making its context current for the block.

        The span inherits the current trace context (or the provided one),
        so nested operations are correlated.  Exceptions set the span
        status to ``error`` and re-raise.
        """
        parent = trace_context or get_current_context()
        ctx = parent.child() if parent else TraceContext()
        ctx.tool_id = attributes.get("tool_id") if attributes else None
        ctx.provider = attributes.get("provider") if attributes else None
        ctx.model = attributes.get("model") if attributes else None

        span_attributes = _stringify_attributes(attributes)
        span_attributes["trace_id"] = ctx.trace_id
        span_attributes["span_id"] = ctx.span_id
        span_attributes["parent_span_id"] = ctx.parent_span_id or ""

        span = self.tracer.begin_span(name, attributes=span_attributes)
        previous = get_current_context()
        set_current_context(ctx)
        try:
            yield ctx
        except Exception:
            self.tracer.end_span(span, status="error")
            set_current_context(previous)
            raise
        else:
            self.tracer.end_span(span, status="ok")
            set_current_context(previous)

    def span(
        self,
        name: str,
        *,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Context-manager alias for :meth:`start_span`."""
        return self.start_span(name, attributes=attributes)

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    @contextlib.contextmanager
    def user_request(self, *, platform: str = "", session_id: str = ""):
        attrs = {"platform": platform or "unknown"}
        if session_id:
            attrs["session_id"] = session_id
        with self.start_span("user_request", attributes=attrs) as ctx:
            if session_id and not ctx.session_id:
                ctx.session_id = session_id
            yield ctx

    @contextlib.contextmanager
    def gateway_request(self, *, platform: str = "", session_id: str = ""):
        attrs = {"platform": platform or "unknown"}
        if session_id:
            attrs["session_id"] = session_id
        with self.start_span("gateway_request", attributes=attrs) as ctx:
            if session_id and not ctx.session_id:
                ctx.session_id = session_id
            yield ctx

    @contextlib.contextmanager
    def mission(self, mission_id: str, *, goal: str = ""):
        attrs = {"mission_id": mission_id}
        if goal:
            attrs["goal"] = goal
        with self.start_span("mission", attributes=attrs) as ctx:
            ctx.mission_id = mission_id
            yield ctx

    @contextlib.contextmanager
    def task(self, task_id: str, *, mission_id: str = "", agent_id: str = ""):
        attrs = {"task_id": task_id}
        if mission_id:
            attrs["mission_id"] = mission_id
        if agent_id:
            attrs["agent_id"] = agent_id
        with self.start_span("task", attributes=attrs) as ctx:
            ctx.task_id = task_id
            if mission_id:
                ctx.mission_id = mission_id
            if agent_id:
                ctx.agent_id = agent_id
            yield ctx

    @contextlib.contextmanager
    def agent_run(self, agent_id: str = "", *, mission_id: str = "", task_id: str = ""):
        attrs = {}
        if agent_id:
            attrs["agent_id"] = agent_id
        if mission_id:
            attrs["mission_id"] = mission_id
        if task_id:
            attrs["task_id"] = task_id
        with self.start_span("agent_run", attributes=attrs) as ctx:
            if agent_id:
                ctx.agent_id = agent_id
            if mission_id:
                ctx.mission_id = mission_id
            if task_id:
                ctx.task_id = task_id
            yield ctx

    def record_model_call(
        self,
        *,
        model: str,
        provider: str = "",
        status: str = "ok",
        duration_ms: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        finish_reason: str = "",
    ) -> None:
        """Record a model call span + metrics (metadata only)."""
        attrs = {
            "model": model or "unknown",
            "provider": provider or "unknown",
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
        }
        if finish_reason:
            attrs["finish_reason"] = finish_reason
        with self.start_span("model_call", attributes=attrs) as ctx:
            ctx.provider = provider or ctx.provider
            ctx.model = model or ctx.model
            get_unified_metrics().record_model_call(
                model=model, provider=provider, status=status,
                duration_ms=duration_ms, input_tokens=input_tokens,
                output_tokens=output_tokens, cached_tokens=cached_tokens,
                finish_reason=finish_reason,
            )

    def record_tool_call(
        self,
        *,
        tool_name: str,
        tool_id: str = "",
        status: str = "ok",
        duration_ms: float = 0.0,
        retry_count: int = 0,
    ) -> None:
        """Record a tool call span + metrics (no arguments/result content)."""
        attrs = {
            "tool": tool_name or "unknown",
            "status": status,
            "duration_ms": round(duration_ms, 2),
        }
        if tool_id:
            attrs["tool_id"] = tool_id
        with self.start_span("tool_call", attributes=attrs) as ctx:
            ctx.tool_id = tool_id or ctx.tool_id
            get_unified_metrics().record_tool_call(
                tool_id=tool_id, tool_name=tool_name, status=status,
                duration_ms=duration_ms, retry_count=retry_count,
            )

    def record_memory_op(
        self,
        *,
        operation: str = "read",
        status: str = "ok",
        duration_ms: float = 0.0,
        result_count: int = 0,
    ) -> None:
        """Record a memory operation span (no memory content)."""
        with self.start_span("memory_op", attributes={
            "operation": operation or "read",
            "status": status,
            "duration_ms": round(duration_ms, 2),
        }):
            get_unified_metrics().record_memory_op(
                operation=operation, status=status,
                duration_ms=duration_ms, result_count=result_count,
            )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_recent_spans(self, limit: int = 100) -> list:
        traces = self.tracer.get_traces()
        return traces[-limit:]

    def get_trace(self, trace_id: str) -> list:
        traces = self.tracer.get_traces()
        return [
            s for s in traces
            if s.get("trace_id") == trace_id
            or s.get("attributes", {}).get("trace_id") == trace_id
        ]

    def get_stats(self) -> dict:
        traces = self.tracer.get_traces()
        by_name: Dict[str, int] = {}
        for span in traces:
            by_name[span.get("name", "unknown")] = by_name.get(span.get("name", "unknown"), 0) + 1
        return {
            "total": len(traces),
            "span_count": len(traces),
            "by_name": by_name,
        }

    def export(self, path: str) -> bool:
        return self.tracer.export(path)

    def close(self) -> None:
        self.tracer.close()


def _stringify_attributes(attributes: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Flatten attribute values to strings for span storage."""
    if not attributes:
        return {}
    out: Dict[str, str] = {}
    for key, value in attributes.items():
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        elif value is None:
            out[key] = ""
        else:
            out[key] = str(value)
    return out


_unified_tracer: Optional[UnifiedTracer] = None


def get_unified_tracer() -> UnifiedTracer:
    """Return the process-wide UnifiedTracer singleton."""
    global _unified_tracer
    if _unified_tracer is None:
        _unified_tracer = UnifiedTracer()
    return _unified_tracer