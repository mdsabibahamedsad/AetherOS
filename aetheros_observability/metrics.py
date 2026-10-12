"""Unified metrics facade.

Thin, thread-safe facade over the existing AetherOS metrics registry
(``aetheros_production.observability.MetricsRegistry`` — the canonical
in-process registry) plus domain-specific convenience helpers for the
agent lifecycle.

We do NOT create a second metrics system: every call delegates to the
existing registry singleton so Prometheus/JSON export, tests and any
other consumer keep seeing one coherent dataset.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

from aetheros_observability.redaction import redact_payload


class UnifiedMetrics:
    """Facade over the canonical metrics registry.

    Usage::

        from aetheros_observability.metrics import get_unified_metrics
        m = get_unified_metrics()
        m.record_request(platform="cli", status="ok", duration_ms=12.3)
        m.record_model_call(model="gpt-4o", provider="openai", status="ok")
        snapshot = m.snapshot()
    """

    def __init__(self, registry=None) -> None:
        self._registry = registry

    @property
    def registry(self):
        """The underlying metrics registry (lazy)."""
        if self._registry is None:
            from aetheros_production.observability import get_metrics_registry
            self._registry = get_metrics_registry()
        return self._registry

    # ------------------------------------------------------------------
    # Generic primitives
    # ------------------------------------------------------------------

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        self.registry.increment(name, value, labels)

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self.registry.set_gauge(name, value, labels)

    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self.registry.observe(name, value, labels)

    def snapshot(self) -> Dict[str, Any]:
        return self.registry.snapshot()

    def export_prometheus(self) -> str:
        return self.registry.export_prometheus()

    def clear(self) -> None:
        self.registry.clear()

    # ------------------------------------------------------------------
    # Domain helpers — requests / latency / errors
    # ------------------------------------------------------------------

    def record_request(
        self,
        *,
        platform: str = "",
        status: str = "ok",
        duration_ms: float = 0.0,
    ) -> None:
        """Record an incoming request (UI, gateway, IPC, API)."""
        labels = {"platform": platform or "unknown", "status": status}
        self.increment("aetheros.request.count", 1.0, labels)
        self.observe("aetheros.request.duration_ms", duration_ms, labels)
        if status != "ok":
            self.increment("aetheros.request.error.count", 1.0, labels)

    def record_error(
        self,
        *,
        component: str = "",
        error_type: str = "INTERNAL_ERROR",
        message: str = "",
    ) -> None:
        """Record an error, optionally with a redacted message attribute."""
        labels = {"component": component or "unknown", "type": error_type}
        self.increment("aetheros.error.count", 1.0, labels)
        if message:
            redacted = redact_payload({"message": message})
            self.observe("aetheros.error.detail", 1.0, {**labels, "sample": str(redacted["message"])[:120]})

    def record_retry(self, *, component: str = "", attempt: int = 1) -> None:
        self.increment("aetheros.retry.count", 1.0, {"component": component or "unknown"})

    def record_fallback(self, *, primary: str = "", fallback: str = "") -> None:
        self.increment(
            "aetheros.fallback.count", 1.0,
            {"primary": primary or "unknown", "fallback": fallback or "unknown"},
        )

    def set_circuit_breaker(self, state: str, component: str = "") -> None:
        """Record circuit-breaker state (open/closed/half_open)."""
        self.set_gauge(
            "aetheros.circuit_breaker.state",
            1.0 if state in ("open", "half_open") else 0.0,
            {"component": component or "unknown", "state": state},
        )

    def set_queue_depth(self, depth: int, queue: str = "") -> None:
        self.set_gauge("aetheros.queue.depth", float(depth), {"queue": queue or "default"})

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def record_agent_execution(
        self,
        *,
        agent_id: str = "",
        status: str = "ok",
        duration_ms: float = 0.0,
    ) -> None:
        labels = {"agent_id": agent_id or "unknown", "status": status}
        self.increment("aetheros.agent.execution.count", 1.0, labels)
        self.observe("aetheros.agent.latency_ms", duration_ms, labels)

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def record_model_call(
        self,
        *,
        model: str = "",
        provider: str = "",
        status: str = "ok",
        duration_ms: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        finish_reason: str = "",
    ) -> None:
        """Record a model call with token usage (no prompt content)."""
        labels = {
            "model": model or "unknown",
            "provider": provider or "unknown",
            "status": status,
        }
        self.increment("aetheros.model.call.count", 1.0, labels)
        self.observe("aetheros.model.latency_ms", duration_ms, labels)
        self.increment("aetheros.model.input_tokens", float(input_tokens), labels)
        self.increment("aetheros.model.output_tokens", float(output_tokens), labels)
        self.increment("aetheros.model.cached_tokens", float(cached_tokens), labels)
        if status != "ok":
            self.increment("aetheros.model.error.count", 1.0, labels)
        if finish_reason:
            self.increment("aetheros.model.finish.count", 1.0, {**labels, "finish_reason": finish_reason})

    # ------------------------------------------------------------------
    # Tool lifecycle
    # ------------------------------------------------------------------

    def record_tool_call(
        self,
        *,
        tool_id: str = "",
        tool_name: str = "",
        agent_id: str = "",
        status: str = "ok",
        duration_ms: float = 0.0,
        retry_count: int = 0,
    ) -> None:
        labels = {
            "tool": tool_name or "unknown",
            "agent_id": agent_id or "unknown",
            "status": status,
        }
        self.increment("aetheros.tool.call.count", 1.0, labels)
        self.observe("aetheros.tool.latency_ms", duration_ms, labels)
        if status != "ok":
            self.increment("aetheros.tool.error.count", 1.0, labels)
        if retry_count:
            self.increment("aetheros.tool.retry.count", float(retry_count), labels)

    # ------------------------------------------------------------------
    # Memory lifecycle
    # ------------------------------------------------------------------

    def record_memory_op(
        self,
        *,
        operation: str = "read",
        status: str = "ok",
        duration_ms: float = 0.0,
        result_count: int = 0,
        cache_hit: Optional[bool] = None,
    ) -> None:
        labels = {
            "operation": operation or "read",
            "status": status,
        }
        self.increment("aetheros.memory.operation.count", 1.0, labels)
        self.observe("aetheros.memory.latency_ms", duration_ms, labels)
        if cache_hit is not None:
            self.increment(
                "aetheros.memory.cache.hit" if cache_hit else "aetheros.memory.cache.miss",
                1.0,
                {"operation": labels["operation"]},
            )
        if result_count:
            self.increment("aetheros.memory.result_count", float(result_count), labels)


_unified_metrics: Optional[UnifiedMetrics] = None


def get_unified_metrics() -> UnifiedMetrics:
    """Return the process-wide UnifiedMetrics singleton."""
    global _unified_metrics
    if _unified_metrics is None:
        _unified_metrics = UnifiedMetrics()
    return _unified_metrics


@contextmanager
def latency_timer(name: str, labels: Optional[Dict[str, str]] = None):
    """Context manager that records a latency histogram on exit.

    Usage::

        with latency_timer("aetheros.agent.latency_ms", {"platform": "cli"}):
            do_work()
    """
    start = time.monotonic()
    try:
        yield
    finally:
        get_unified_metrics().observe(name, (time.monotonic() - start) * 1000.0, labels)