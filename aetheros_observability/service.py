"""Unified ObservabilityService facade.

Composes the observability sub-services into one stable public surface:

    trace  — end-to-end spans + trace-context propagation
    metric — counters / gauges / histograms (delegates to canonical registry)
    log    — structured, redacted log entries
    event  — telemetry events (model / tool / memory / gateway / desktop)
    diagnostic — safe diagnostic bundles + export
    health — liveness / readiness / component health / degraded mode
    evaluation — task success scoring
    alert  — incident detection + dedup + lifecycle
    recover — safe, budgeted, reversible self-healing

All sub-service calls are failure-isolated: observability problems can
degrade telemetry but can never crash the main application.
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from typing import Any, Dict, Optional

from aetheros_observability.context import (
    TraceContext,
    begin_trace,
    get_current_context,
    set_current_context,
)
from aetheros_observability.errors import (
    ErrorEnvelope,
    ErrorType,
    Severity,
    classify_error,
)
from aetheros_observability.redaction import redact_payload, redact_text

logger = logging.getLogger(__name__)


class ObservabilityService:
    """Single entry point for all observability concerns.

    Usage::

        from aetheros_observability.service import get_observability_service
        obs = get_observability_service()

        with obs.trace("user_request", platform="cli"):
            obs.event("gateway.request", platform="telegram")
            obs.metric("request.count", platform="cli")
            obs.alert_error(ErrorType.RATE_LIMIT, component="model")

        obs.health_summary()
        bundle = obs.diagnostic_bundle()
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self._lock = threading.RLock()
        self._sub: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lazy sub-service access
    # ------------------------------------------------------------------

    def _service(self, name: str):
        if name in self._sub:
            return self._sub[name]
        from aetheros_observability.metrics import get_unified_metrics
        from aetheros_observability.tracing import get_unified_tracer
        from aetheros_observability.health import get_health_service
        from aetheros_observability.diagnostics import get_diagnostics_service
        from aetheros_observability.incidents import get_incident_detector
        from aetheros_observability.recovery import get_recovery_service
        from aetheros_observability.evaluation import get_evaluation_service
        from aetheros_observability.cost import get_cost_tracker
        from aetheros_observability.storage import get_telemetry_store

        providers = {
            "metrics": get_unified_metrics,
            "tracing": get_unified_tracer,
            "health": get_health_service,
            "diagnostics": get_diagnostics_service,
            "incidents": get_incident_detector,
            "recovery": get_recovery_service,
            "evaluation": get_evaluation_service,
            "cost": get_cost_tracker,
            "storage": get_telemetry_store,
        }
        with self._lock:
            if name not in self._sub:
                self._sub[name] = providers[name]()
        return self._sub[name]

    # ------------------------------------------------------------------
    # Trace
    # ------------------------------------------------------------------

    @contextlib.contextmanager
    def trace(self, name: str, **attributes):
        """Open a named span, making its context current for the block."""
        if not self.enabled:
            yield TraceContext()
            return
        with self._service("tracing").start_span(name, attributes=attributes):
            yield get_current_context() or TraceContext()

    def begin(self, *, session_id: str = "", mission_id: str = "",
              task_id: str = "", agent_id: str = ""):
        """Start a new root trace and return its context."""
        return begin_trace(
            session_id=session_id or None,
            mission_id=mission_id or None,
            task_id=task_id or None,
            agent_id=agent_id or None,
        )

    def current(self) -> Optional[TraceContext]:
        return get_current_context()

    def bind(self, ctx: TraceContext) -> None:
        """Bind an existing context as current (e.g. extracted from headers)."""
        set_current_context(ctx)

    # ------------------------------------------------------------------
    # Metric
    # ------------------------------------------------------------------

    def metric(self, name: str, value: float = 1.0,
               labels: Optional[Dict[str, str]] = None,
               *, kind: str = "counter") -> None:
        """Record a metric.  ``kind``: counter | gauge | histogram."""
        if not self.enabled:
            return
        m = self._service("metrics")
        try:
            if kind == "counter":
                m.increment(name, value, labels)
            elif kind == "gauge":
                m.set_gauge(name, value, labels)
            else:
                m.observe(name, value, labels)
        except Exception as exc:
            logger.debug("metric record failed: %s", exc)

    def metrics_snapshot(self) -> Dict[str, Any]:
        try:
            return self._service("metrics").snapshot()
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Log / event
    # ------------------------------------------------------------------

    def log(self, message: str, *, level: str = "INFO",
            component: str = "", operation: str = "",
            error_type: str = "", duration_ms: float = 0.0,
            **extra) -> None:
        """Emit a structured, redacted log line."""
        if not self.enabled:
            return
        ctx = get_current_context()
        payload = redact_payload({
            "component": component,
            "operation": operation,
            "error_type": error_type,
            "duration_ms": duration_ms,
            **extra,
        })
        record = {
            "message": redact_text(message),
            "level": level.upper(),
            "component": component,
            "operation": operation,
            "error_type": error_type,
            "duration_ms": duration_ms,
            "trace_id": ctx.trace_id if ctx else None,
            "correlation_id": ctx.correlation_id if ctx else None,
            "session_id": ctx.session_id if ctx else None,
            "mission_id": ctx.mission_id if ctx else None,
            "task_id": ctx.task_id if ctx else None,
            "agent_id": ctx.agent_id if ctx else None,
            "extra": payload,
        }
        try:
            getattr(logger, level.lower(), logger.info)(redact_text(message), extra=record)
        except Exception:
            logger.info("%s", redact_text(message))
        self.event("log", component=component, message=message,
                   payload={"level": level.upper(), "error_type": error_type})

    def event(self, event_type: str, *, component: str = "",
              message: str = "", payload: Optional[Dict[str, Any]] = None,
              severity: str = "INFO") -> None:
        """Emit a telemetry event (persisted when storage is available)."""
        if not self.enabled:
            return
        ctx = get_current_context()
        event = {
            "event_type": event_type,
            "component": component,
            "severity": severity,
            "message": redact_text(message),
            "payload": redact_payload(payload or {}),
            "trace_id": ctx.trace_id if ctx else None,
            "session_id": ctx.session_id if ctx else None,
            "mission_id": ctx.mission_id if ctx else None,
            "task_id": ctx.task_id if ctx else None,
            "agent_id": ctx.agent_id if ctx else None,
            "timestamp": time.time(),
        }
        try:
            self._service("storage").save_event(event)
        except Exception as exc:
            logger.debug("event persist failed: %s", exc)

    # ------------------------------------------------------------------
    # Domain telemetry helpers
    # ------------------------------------------------------------------

    def record_model_call(self, *, model: str, provider: str = "",
                          status: str = "ok", duration_ms: float = 0.0,
                          input_tokens: int = 0, output_tokens: int = 0,
                          cached_tokens: int = 0, finish_reason: str = "",
                          agent_id: str = "", mission_id: str = "",
                          session_id: str = "") -> None:
        """Record model telemetry (metadata only, never prompt content)."""
        if not self.enabled:
            return
        try:
            self._service("tracing").record_model_call(
                model=model, provider=provider, status=status,
                duration_ms=duration_ms, input_tokens=input_tokens,
                output_tokens=output_tokens, cached_tokens=cached_tokens,
                finish_reason=finish_reason,
            )
            self._service("cost").record_model_call(
                model=model, provider=provider, input_tokens=input_tokens,
                output_tokens=output_tokens, cache_read_tokens=cached_tokens,
                agent_id=agent_id, mission_id=mission_id, session_id=session_id,
            )
        except Exception as exc:
            logger.debug("model telemetry failed: %s", exc)

    def record_tool_call(self, *, tool_name: str, tool_id: str = "",
                         status: str = "ok", duration_ms: float = 0.0,
                         retry_count: int = 0) -> None:
        if not self.enabled:
            return
        try:
            self._service("tracing").record_tool_call(
                tool_name=tool_name, tool_id=tool_id, status=status,
                duration_ms=duration_ms, retry_count=retry_count,
            )
        except Exception as exc:
            logger.debug("tool telemetry failed: %s", exc)

    def record_memory_op(self, *, operation: str = "read",
                         status: str = "ok", duration_ms: float = 0.0,
                         result_count: int = 0) -> None:
        if not self.enabled:
            return
        try:
            self._service("tracing").record_memory_op(
                operation=operation, status=status, duration_ms=duration_ms,
                result_count=result_count,
            )
        except Exception as exc:
            logger.debug("memory telemetry failed: %s", exc)

    def record_gateway_event(self, event_type: str, *, platform: str = "",
                             message: str = "", status: str = "ok") -> None:
        """Record a gateway event (request/auth/routing/queue)."""
        self.event(
            f"gateway.{event_type}",
            component="gateway",
            message=message,
            payload={"platform": platform, "status": status},
        )

    def record_desktop_event(self, event_type: str, *, component: str = "",
                             message: str = "", status: str = "ok") -> None:
        """Record a desktop lifecycle event (startup/shutdown/crash/restart)."""
        self.event(
            f"desktop.{event_type}",
            component=component or "desktop",
            message=message,
            payload={"status": status},
        )

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        try:
            return self._service("health").summary()
        except Exception:
            return {"status": "unknown"}

    def liveness(self) -> Dict[str, Any]:
        try:
            return self._service("health").liveness()
        except Exception:
            return {"status": "alive"}

    def readiness(self) -> Dict[str, Any]:
        try:
            return self._service("health").readiness()
        except Exception:
            return {"status": "unknown", "ready": False}

    def register_health_check(self, component: str, check_fn) -> None:
        self._service("health").register(component, check_fn)

    def set_degraded(self, component: str, reason: str) -> None:
        self._service("health").set_degraded(component, reason)

    def clear_degraded(self, component: str) -> None:
        self._service("health").clear_degraded(component)

    # ------------------------------------------------------------------
    # Diagnostic
    # ------------------------------------------------------------------

    def diagnostic_bundle(self, *, config: Optional[Dict[str, Any]] = None,
                          extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            return self._service("diagnostics").bundle(config=config, extra=extra)
        except Exception as exc:
            return {"error": f"diagnostic bundle failed: {exc}"}

    def export_diagnostics(self, bundle: Dict[str, Any], path: str,
                           fmt: str = "json") -> bool:
        try:
            return self._service("diagnostics").export(bundle, path, fmt)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, *, task_id: str, outcome: str,
                 agent_id: str = "", mission_id: str = "",
                 duration_ms: float = 0.0, cost_usd: float = 0.0,
                 error_type: str = "", tool_usage: int = 0,
                 model_usage: int = 0, policy_violation: str = "") -> None:
        """Record a task outcome for evaluation (Step 49-51)."""
        if not self.enabled:
            return
        try:
            from aetheros_observability.evaluation import TaskOutcome
            evals = self._service("evaluation")
            result = evals.record_result(
                task_id=task_id, outcome=TaskOutcome(outcome),
                agent_id=agent_id, mission_id=mission_id,
                duration_ms=duration_ms, cost_usd=cost_usd,
                error_type=error_type, tool_usage=tool_usage,
                model_usage=model_usage, policy_violation=policy_violation,
            )
            self._service("storage").save_evaluation(result.to_dict())
        except Exception as exc:
            logger.debug("evaluation record failed: %s", exc)

    def evaluation_summary(self, *, agent_id: str = "",
                           mission_id: str = "") -> Dict[str, Any]:
        try:
            return self._service("evaluation").summary(
                agent_id=agent_id, mission_id=mission_id)
        except Exception:
            return {"total": 0}

    # ------------------------------------------------------------------
    # Alert / incidents
    # ------------------------------------------------------------------

    def alert(self, *, message: str, component: str = "",
              error_type: str = "INTERNAL_ERROR", trace_id: str = "",
              severity: str = "") -> None:
        """Record an error, deduplicated into an incident."""
        if not self.enabled:
            return
        try:
            detector = self._service("incidents")
            incident = detector.record_error(
                error_type=error_type, component=component,
                message=message, trace_id=trace_id,
                severity=_severity_enum(severity),
            )
            if incident:
                self._service("storage").save_incident(incident.to_dict())
        except Exception as exc:
            logger.debug("alert record failed: %s", exc)

    def alert_error(self, error_type: ErrorType, *, component: str = "",
                    message: str = "") -> None:
        self.alert(message=message or error_type.value,
                   component=component, error_type=error_type.value)

    def incidents(self) -> Dict[str, Any]:
        try:
            return self._service("incidents").summary()
        except Exception:
            return {"active_count": 0}

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def register_recovery(self, action: str, *, trigger: str,
                          handler, max_attempts: int = 3,
                          cooldown_seconds: float = 60.0,
                          risk: str = "low") -> None:
        """Register a safe recovery action (Step 42)."""
        try:
            from aetheros_observability.recovery import RecoveryPolicy
            self._service("recovery").register(
                action,
                RecoveryPolicy(
                    action=action, trigger=trigger, risk=risk,
                    max_attempts=max_attempts,
                    cooldown_seconds=cooldown_seconds,
                ),
                handler,
            )
        except Exception as exc:
            logger.debug("recovery register failed: %s", exc)

    def recover(self, action: str, component: str,
                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            result = self._service("recovery").attempt(
                action, component, context)
            return result.to_dict()
        except Exception as exc:
            return {"action": action, "component": component,
                    "outcome": "failed", "message": str(exc)}

    def recovery_status(self) -> Dict[str, Any]:
        try:
            service = self._service("recovery")
            return {
                "history": service.history(limit=20),
                "crash_loops": service.crash_loops(),
                "audit": service.audit_log(limit=10),
            }
        except Exception:
            return {"history": [], "crash_loops": {}}

    # ------------------------------------------------------------------
    # Cost
    # ------------------------------------------------------------------

    def cost_summary(self) -> Dict[str, Any]:
        try:
            return self._service("cost").summary()
        except Exception:
            return {"total_estimated_usd": 0.0}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Flush buffered telemetry and close storage."""
        try:
            self._service("storage").cleanup(retention_days=0)
            self._service("storage").close()
        except Exception as exc:
            logger.debug("observability shutdown failed: %s", exc)


def _severity_enum(severity: str):
    if not severity:
        return None
    from aetheros_observability.incidents import AlertSeverity
    try:
        return AlertSeverity(severity.upper())
    except ValueError:
        return None


_observability_service: Optional[ObservabilityService] = None


def get_observability_service() -> ObservabilityService:
    """Return the process-wide ObservabilityService singleton."""
    global _observability_service
    if _observability_service is None:
        _observability_service = ObservabilityService()
        try:
            from aetheros_observability.config import apply_observability_config
            apply_observability_config()
        except Exception:
            pass
    return _observability_service