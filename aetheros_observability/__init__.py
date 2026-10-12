"""AetherOS Unified Observability — one coherent layer on top of the
existing logging/metrics/tracing infrastructure.

Modules
-------
context     — trace-context propagation (traceId/spanId/parentSpanId/
              correlationId/causationId/sessionId/missionId/taskId/
              agentId/toolId/provider/model)
errors      — error taxonomy, error envelopes, user-safe messages
redaction   — automatic secret redaction for telemetry
metrics     — facade over the canonical metrics registry
tracing     — facade over the canonical tracer with context propagation
health      — liveness / readiness / dependency graph / degraded mode
diagnostics — safe diagnostic bundles + export
incidents   — incident detection, dedup, lifecycle, alerts
recovery    — safe, budgeted, reversible self-healing
evaluation  — task success scoring
cost        — estimated cost tracking
storage     — telemetry persistence, retention, rotation, offline buffer
service     — unified ObservabilityService facade

Usage::

    from aetheros_observability.service import get_observability_service
    obs = get_observability_service()

    with obs.trace("user_request", platform="cli"):
        obs.record_model_call(model="gpt-4o", provider="openai",
                              input_tokens=120, output_tokens=80)
        obs.alert_error(ErrorType.RATE_LIMIT, component="model")

    print(obs.health())
    obs.export_diagnostics(obs.diagnostic_bundle(), "diag.json")
"""

from __future__ import annotations

from aetheros_observability.context import (
    TraceContext,
    begin_trace,
    clear_current_context,
    fork_context,
    get_current_context,
    get_or_create_context,
    new_causation_id,
    new_correlation_id,
    new_span_id,
    new_trace_id,
    set_current_context,
)
from aetheros_observability.errors import (
    ErrorEnvelope,
    ErrorType,
    Severity,
    classify_error,
    user_safe_message,
)
from aetheros_observability.redaction import (
    redact_payload,
    redact_text,
    redact_value,
)
from aetheros_observability.metrics import (
    UnifiedMetrics,
    get_unified_metrics,
)
from aetheros_observability.tracing import (
    UnifiedTracer,
    get_unified_tracer,
)
from aetheros_observability.health import (
    HealthService,
    HealthState,
    get_health_service,
)
from aetheros_observability.diagnostics import (
    DiagnosticsService,
    get_diagnostics_service,
)
from aetheros_observability.incidents import (
    AlertSeverity,
    Incident,
    IncidentDetector,
    IncidentState,
    get_incident_detector,
)
from aetheros_observability.recovery import (
    RecoveryOutcome,
    RecoveryPolicy,
    RecoveryResult,
    RecoveryService,
    get_recovery_service,
)
from aetheros_observability.evaluation import (
    EvaluationService,
    TaskEvaluation,
    TaskOutcome,
    get_evaluation_service,
)
from aetheros_observability.cost import (
    CostEstimate,
    CostTracker,
    get_cost_tracker,
)
from aetheros_observability.storage import (
    TelemetryStore,
    get_telemetry_store,
)
from aetheros_observability.service import (
    ObservabilityService,
    get_observability_service,
)

__all__ = [
    # context
    "TraceContext", "begin_trace", "clear_current_context", "fork_context",
    "get_current_context", "get_or_create_context", "new_causation_id",
    "new_correlation_id", "new_span_id", "new_trace_id", "set_current_context",
    # errors
    "ErrorEnvelope", "ErrorType", "Severity", "classify_error", "user_safe_message",
    # redaction
    "redact_payload", "redact_text", "redact_value",
    # metrics / tracing
    "UnifiedMetrics", "get_unified_metrics", "UnifiedTracer", "get_unified_tracer",
    # health
    "HealthService", "HealthState", "get_health_service",
    # diagnostics
    "DiagnosticsService", "get_diagnostics_service",
    # incidents
    "AlertSeverity", "Incident", "IncidentDetector", "IncidentState",
    "get_incident_detector",
    # recovery
    "RecoveryOutcome", "RecoveryPolicy", "RecoveryResult", "RecoveryService",
    "get_recovery_service",
    # evaluation
    "EvaluationService", "TaskEvaluation", "TaskOutcome", "get_evaluation_service",
    # cost
    "CostEstimate", "CostTracker", "get_cost_tracker",
    # storage
    "TelemetryStore", "get_telemetry_store",
    # facade
    "ObservabilityService", "get_observability_service",
]