---
id: observability
title: Observability, Diagnostics and Self-Healing
sidebar_label: Observability
---

# Observability, Diagnostics and Self-Healing

AetherOS ships a unified observability layer that answers the questions
every operator cares about — **what** happened, **when**, **where**
(which component/tool), **why** (error taxonomy), **how much** (estimated
cost), **how long** (spans/latency), and **what failed and recovered**
(incidents + safe self-healing).

The layer is a *facade* over the existing AetherOS observability
infrastructure (`aetheros_production.observability`, `agent.redact`,
`agent.usage_pricing`, `aetheros_logging`). It does **not** introduce a
second logging, metrics or tracing system — it composes the canonical
ones into a single stable public surface.

## Architecture

```
aetheros_observability/            # unified public package
├── context.py        trace/span/correlation context propagation
├── errors.py         error taxonomy + user-safe envelopes
├── redaction.py      automatic secret redaction (delegates to agent.redact)
├── metrics.py        facade over get_metrics_registry()
├── tracing.py        facade over get_tracer() with context propagation
├── health.py         liveness / readiness / dependency graph / degraded mode
├── diagnostics.py    safe diagnostic bundles + export
├── incidents.py      incident detection, dedup, lifecycle, alerts
├── recovery.py       safe, budgeted, reversible self-healing
├── evaluation.py     task success scoring
├── cost.py           estimated cost tracking (delegates to agent.usage_pricing)
├── storage.py        telemetry persistence + retention (SQLite)
├── config.py         config.yaml integration
└── service.py        unified ObservabilityService facade
```

## Quick start

```python
from aetheros_observability.service import get_observability_service

obs = get_observability_service()

with obs.trace("user_request", platform="cli"):
    obs.record_model_call(model="gpt-4o", provider="openai",
                          input_tokens=1200, output_tokens=800)
    obs.alert_error(ErrorType.RATE_LIMIT, component="model",
                    message="429 from provider")

print(obs.health())                 # health summary
print(obs.incidents())              # active incidents
print(obs.cost_summary())           # estimated cost
```

## Trace context

Every important request carries a correlation context across process,
thread, async, IPC, WebSocket, HTTP and MCP boundaries:

| Field | Purpose |
|-------|---------|
| `traceId` | root identity of an end-to-end operation |
| `spanId` | current span identity |
| `parentSpanId` | identity of the calling span |
| `correlationId` | user-facing correlation key, stable across retries |
| `causationId` | id of the event that caused this one |
| `sessionId` | conversation/session |
| `missionId` | autonomous mission (multi-task goal) |
| `taskId` | individual task under a mission |
| `agentId` | agent instance performing the work |
| `toolId` / `provider` / `model` | tool/provider/model when in such a span |

Context propagates over HTTP / WebSocket / MCP headers:

```
X-AetherOS-Trace-ID, X-AetherOS-Span-ID, X-AetherOS-Parent-Span-ID,
X-AetherOS-Correlation-ID, X-AetherOS-Causation-ID, X-AetherOS-Session-ID,
X-AetherOS-Mission-ID, X-AetherOS-Task-ID, X-AetherOS-Agent-ID
```

```python
from aetheros_observability.context import begin_trace, TraceContext

ctx = begin_trace(session_id="sess-1", mission_id="m-1")
outbound = ctx.inject_headers()          # outbound headers
inbound = TraceContext.extract_headers(req.headers)  # inbound
```

The span hierarchy mirrors the agent lifecycle:

```
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
```

Spans record **metadata only** — never prompt/response content.

## Errors and user-safe messages

`errors.py` provides a stable taxonomy (17 error types) and
`ErrorEnvelope`, which strictly separates internal diagnostics from the
`safeMessage` users actually see. Secrets, stack traces and internal
paths never leak into `safeMessage`.

```python
from aetheros_observability.errors import ErrorEnvelope, classify_error

env = ErrorEnvelope.from_exception(exc, operation="tool_call")
print(env.type, env.safe_message, env.retryable)
```

Retryable types (`NETWORK_ERROR`, `TIMEOUT`, `RATE_LIMIT`,
`PROVIDER_ERROR`) drive fallback/retry decisions; authentication,
authorization, security and validation errors are never retried blindly.

## Redaction

Telemetry is redacted automatically before it reaches logs, traces,
metrics, diagnostic bundles or exports:

- dict keys matching sensitive patterns (`api_key`, `authorization`,
  `password`, `token`, `X-API-Key`, ...) are replaced with `[REDACTED]`
- embedded secrets in text (API keys, bearer tokens, secrets) are
  scrubbed by the canonical `agent.redact` engine

```python
from aetheros_observability.redaction import redact_payload
safe = redact_payload({"api_key": "sk-...", "model": "gpt-4o"})
```

## Health

`health.py` distinguishes **liveness** (process alive) from
**readiness** (safe to accept work) and keeps a dependency graph so one
failed leaf degrades only its dependents, never the whole system.

```python
from aetheros_observability.health import get_health_service, HealthState

hs = get_health_service()
hs.register("model_provider", lambda: (HealthState.HEALTHY, "ok"))
hs.set_degraded("storage", "read-only disk")
print(hs.readiness())
print(hs.summary())
```

## Incidents

`incidents.py` deduplicates alerts into incidents grouped by a key —
thousands of identical errors collapse into one incident carrying
`firstSeen` / `lastSeen` / `count` / `traceIds` / `recoveryState`.
Lifecycle: `DETECTED → ACKNOWLEDGED → INVESTIGATING → MITIGATING →
RECOVERED → RESOLVED` (or `ESCALATED`). Security events are never
sampled or dropped.

```python
from aetheros_observability.incidents import get_incident_detector

det = get_incident_detector()
det.record_error(error_type="RATE_LIMIT", component="model")
print(det.summary())
```

## Safe self-healing

`recovery.py` performs **only** safe, reversible, budgeted recovery.
Every action must declare a `RecoveryPolicy` (action, trigger,
precondition, risk, rollback, `maxAttempts`, cooldown, auditEvent).
Crash-loop detection and recovery budgets prevent endless restart loops.

Automatic recovery **never** does any of the following:

- deletes user data, memories or credentials
- rotates credentials without authorization
- changes security policy or disables security controls
- executes destructive shell commands or modifies arbitrary files

```python
from aetheros_observability.recovery import (
    get_recovery_service, RecoveryPolicy,
)

def reconnect(component, context):
    # safe, reversible reconnect logic
    return "ok"

rs = get_recovery_service()
rs.register("reconnect",
            RecoveryPolicy(action="reconnect",
                           trigger="connection_dropped",
                           max_attempts=3, cooldown_seconds=60),
            reconnect)
result = rs.attempt("reconnect", "gateway")
print(result.outcome, result.message)
```

## Evaluation

`evaluation.py` scores task outcomes (`COMPLETED`, `FAILED`,
`CANCELLED`, ...) into success rate, failure rate, average latency and
total estimated cost.

```python
from aetheros_observability.evaluation import get_evaluation_service, TaskOutcome

evals = get_evaluation_service()
evals.record_result(task_id="t1", outcome=TaskOutcome.COMPLETED,
                    duration_ms=1200, cost_usd=0.02)
print(evals.summary())
```

## Cost

`cost.py` estimates cost by delegating to the canonical AetherOS pricing
engine (`agent.usage_pricing.estimate_usage_cost`). **All amounts are
marked `ESTIMATED` unless exact provider billing data exists** — cost is
never presented as an exact bill.

## Diagnostics bundle

`diagnostics.py` produces a redacted, validated diagnostic bundle for
export — safe to share because secrets are scrubbed automatically.

```python
from aetheros_observability.diagnostics import get_diagnostics_service

d = get_diagnostics_service()
bundle = d.bundle(config={"model": "gpt-4o"})
d.export(bundle, "/tmp/aetheros-diag.json", "json")  # json | csv | text
print(d.validate(bundle))
```

## Storage

`storage.py` persists events, spans, incidents and evaluations to
SQLite under `<aetheros-home>/observability/telemetry.db` (profile-aware
via `get_aetheros_home()`). Retention cleanup and a bounded offline
buffer keep the store failure-isolated — a telemetry failure can degrade
observability but can never crash the application.

## Config

Behavior is controlled from `config.yaml` (never new env vars):

```yaml
observability:
  enabled: true
  retention_days: 30        # 0 disables automatic deletion
  capture_content: false    # keep OFF; content is redacted anyway
  incident_thresholds:
    error_spike_count: 5
    latency_spike_ms: 10000
    window_seconds: 300
  recovery_enabled: true
  recovery_max_attempts: 3
```

## CLI

`aetheros platform observability <subcommand>` (also the `/observability`
slash command) exposes the layer:

```
status  metrics  traces  logs  telemetry  analytics  export
health  diagnostics  incidents  recovery  costs  evaluation
```

Examples:

```bash
aetheros platform observability status
aetheros platform observability incidents
aetheros platform observability costs
aetheros platform observability diagnostics --out diag.json
aetheros platform observability export --format json --out bundle.json
```

## Failure isolation

Every sub-service call in the facade is wrapped so observability
problems never crash the main application:

```python
obs.metrics_snapshot()   # returns {} if the registry is down
obs.cost_summary()       # returns a safe empty summary if unavailable
```

## Related documentation

- [agent-loop.md](agent-loop.md) — the conversation loop that produces the
  model/tool/memory spans
- [session-storage.md](session-storage.md) — session persistence
- [provider-runtime.md](provider-runtime.md) — provider fallback and routing