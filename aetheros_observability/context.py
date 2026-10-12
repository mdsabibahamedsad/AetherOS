"""Trace context propagation for AetherOS.

Every important request carries a correlation context across process,
thread, async, IPC, WebSocket, HTTP and MCP boundaries:

    traceId        — root identity of an end-to-end operation
    spanId         — current span identity
    parentSpanId   — identity of the calling span
    correlationId  — user-facing correlation key (stable across retries)
    causationId    — id of the event that caused this one
    sessionId      — conversation/session
    missionId      — autonomous mission (multi-task goal)
    taskId         — individual task under a mission
    agentId        — agent instance performing the work
    toolId         — tool invoked (when in a tool span)
    provider       — model provider (when in a model span)
    model          — model name (when in a model span)

The context lives in thread-local storage plus an async-local variant so
that both ``threading`` and ``asyncio`` code keep their context without
cross-contamination.  Values propagate to child contexts on creation; a
child context inherits the parent's fields and can override them.
"""

from __future__ import annotations

import contextvars
import threading
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Id generation
# ---------------------------------------------------------------------------


def new_trace_id() -> str:
    """Return a new 16-hex-char trace id."""
    return uuid.uuid4().hex[:16]


def new_span_id() -> str:
    """Return a new 16-hex-char span id."""
    return uuid.uuid4().hex[:16]


def new_correlation_id() -> str:
    """Return a new correlation id (28-hex-char, stable across retries)."""
    return uuid.uuid4().hex


def new_causation_id() -> str:
    """Return a new causation id (16-hex-char)."""
    return uuid.uuid4().hex[:16]


# ---------------------------------------------------------------------------
# TraceContext
# ---------------------------------------------------------------------------

#: Header names used when propagating context over HTTP / WebSocket / MCP.
HEADER_NAMES = {
    "trace_id": "X-AetherOS-Trace-ID",
    "span_id": "X-AetherOS-Span-ID",
    "parent_span_id": "X-AetherOS-Parent-Span-ID",
    "correlation_id": "X-AetherOS-Correlation-ID",
    "causation_id": "X-AetherOS-Causation-ID",
    "session_id": "X-AetherOS-Session-ID",
    "mission_id": "X-AetherOS-Mission-ID",
    "task_id": "X-AetherOS-Task-ID",
    "agent_id": "X-AetherOS-Agent-ID",
}


@dataclass
class TraceContext:
    """Correlation context carried by every important operation."""

    trace_id: str = field(default_factory=new_trace_id)
    span_id: str = field(default_factory=new_span_id)
    parent_span_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    session_id: Optional[str] = None
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    tool_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)

    def child(
        self,
        *,
        span_id: Optional[str] = None,
        tool_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        baggage: Optional[Dict[str, str]] = None,
    ) -> "TraceContext":
        """Return a child context for a nested span.

        The child keeps ``trace_id``/``correlation_id``/``causation_id``
        and the current span becomes its ``parent_span_id``.
        """
        return replace(
            self,
            parent_span_id=self.span_id,
            span_id=span_id or new_span_id(),
            tool_id=tool_id if tool_id is not None else self.tool_id,
            provider=provider if provider is not None else self.provider,
            model=model if model is not None else self.model,
            baggage=dict(self.baggage, **(baggage or {})),
        )

    def to_dict(self) -> Dict[str, str]:
        """Return a flat, header-safe dict of the context."""
        data: Dict[str, str] = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
        }
        for key, value in (
            ("parent_span_id", self.parent_span_id),
            ("correlation_id", self.correlation_id),
            ("causation_id", self.causation_id),
            ("session_id", self.session_id),
            ("mission_id", self.mission_id),
            ("task_id", self.task_id),
            ("agent_id", self.agent_id),
            ("tool_id", self.tool_id),
            ("provider", self.provider),
            ("model", self.model),
        ):
            if value:
                data[key] = value
        for key, value in self.baggage.items():
            data.setdefault(f"baggage.{key}", value)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceContext":
        """Rebuild a context from a dict (e.g. extracted headers)."""
        ctx = cls(
            trace_id=str(data.get("trace_id") or new_trace_id()),
            span_id=str(data.get("span_id") or new_span_id()),
            parent_span_id=data.get("parent_span_id"),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            session_id=data.get("session_id"),
            mission_id=data.get("mission_id"),
            task_id=data.get("task_id"),
            agent_id=data.get("agent_id"),
            tool_id=data.get("tool_id"),
            provider=data.get("provider"),
            model=data.get("model"),
        )
        baggage = {
            k[len("baggage."):]: str(v)
            for k, v in data.items()
            if k.startswith("baggage.") and v
        }
        if baggage:
            ctx.baggage = baggage
        return ctx

    # -- propagation over HTTP / WebSocket / MCP ----------------------------

    def inject_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Inject the context into an outbound header dict."""
        headers = dict(headers or {})
        for key, value in self.to_dict().items():
            header = HEADER_NAMES.get(key)
            if header and value:
                headers[header] = value
        return headers

    @classmethod
    def extract_headers(cls, headers: Dict[str, Any]) -> "TraceContext":
        """Extract a context from inbound headers (case-insensitive lookup)."""
        data: Dict[str, str] = {}
        lowered = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
        for key, header in HEADER_NAMES.items():
            value = lowered.get(header.lower())
            if value:
                data[key] = value
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# Context propagation (thread-local + async-local)
# ---------------------------------------------------------------------------

_thread_local = threading.local()
_async_local: contextvars.ContextVar = contextvars.ContextVar(
    "aetheros_trace_context", default=None
)


def set_current_context(ctx: Optional[TraceContext]) -> None:
    """Set the active context for the current thread and async task."""
    _thread_local.ctx = ctx
    _async_local.set(ctx)


def get_current_context() -> Optional[TraceContext]:
    """Return the active context (async-local wins, thread-local fallback)."""
    ctx = _async_local.get()
    if ctx is None:
        ctx = getattr(_thread_local, "ctx", None)
    return ctx


def clear_current_context() -> None:
    """Clear the active context for the current thread and async task."""
    _thread_local.ctx = None
    _async_local.set(None)


def get_or_create_context() -> TraceContext:
    """Return the current context, creating a fresh root if none exists."""
    ctx = get_current_context()
    if ctx is None:
        ctx = TraceContext()
        set_current_context(ctx)
    return ctx


def begin_trace(
    *,
    session_id: Optional[str] = None,
    mission_id: Optional[str] = None,
    task_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> TraceContext:
    """Start a new root trace and make it current.

    This is the entry point for a new end-to-end operation (a UI request,
    a gateway request, a mission, a task, an agent run).
    """
    ctx = TraceContext(
        correlation_id=correlation_id or new_correlation_id(),
        session_id=session_id,
        mission_id=mission_id,
        task_id=task_id,
        agent_id=agent_id,
    )
    set_current_context(ctx)
    return ctx


def fork_context() -> TraceContext:
    """Fork the current context for a new thread or worker.

    The fork shares the same ``trace_id``/``correlation_id`` but gets a
    fresh span id so it can be correlated back to the parent.
    """
    parent = get_current_context()
    if parent is None:
        return begin_trace()
    child = parent.child()
    set_current_context(child)
    return child