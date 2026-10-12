# AetherOS Automation — Architecture (Master 43)

## Substrate reused (not duplicated)

- Swarm ops: ApprovalQueue pattern, AuditLog, CheckpointStore, Tracer,
  EventStream (`aetheros_swarm/ops.py` — AuditLog reused directly).
- Swarm budgets/orchestrator for automation-launched agent teams
  (injected `swarm_runner`; default off).
- Master-41 memory for run lessons (injected `memory_create`).
- cron/ left untouched; `mirror_to_cron()` bridges cron-kind schedules via
  lazy import (failure-safe, returns reason when unavailable).
- Tool availability via registry check_fn; policy grants per automation.

## New package `aetheros_autonomy/`

| Module | Responsibility |
|---|---|
| models | AutomationDefinition (v1/v2/v3 history), RunRecord (idempotency), AutonomyLevel 0–5, ActionRisk, ApprovalPolicy, MissedPolicy, NotifyMode, ChangeClass |
| schedule | cron/interval/once canonical form, NL parser (weekday/weekly/monthly/daily/every-N/in-N) with preview, zoneinfo tz/DST |
| store | atomic JSON, versioned updates + rollback, validated import/export (UNTRUSTED), retention prune, batched() write coalescing |
| triggers | event matcher + IF/AND/OR/NOT/THRESHOLD/CHANGE/TIME/MEMORY/TASK/RESEARCH conditions |
| scheduler | virtual-clock tick, missed policies, concurrency keys, idempotent fire, retry/backoff/jitter policy, recursion depth+cycle+cooldown, per-auto rate limit |
| workflow | branch/loop (bounded 1..1000 + timeout)/wait actions, dry-run would-do, simulation describe, step debugger |
| watchers | file (debounce/ignore/types/size/dedupe), repo (observe-only ref_fn), web (fetch_fn+snapshot+freshness), change classifier |
| runtime | thread-pool BackgroundAgentRuntime (main/renderer never blocked), offline LOCAL vs WAITING_NETWORK, ProactiveAgent (suggest-only) |
| notify | channel center (external requires authorization), digest/daily/weekly batching, DigestEngine grouping |
| safety | risk→autonomy→approval gating, scoped expiring approvals, safe mode |
| templates | 10 real factories + safety cards, never auto-enabled |
| service | facade: CRUD, preview, enable/approve-import, run-now/dry-run, emit, NL builder, templates, pause/resume, e-stop, safe mode, settings, health/metrics, export/import, cron mirror |

## Invariants

- Definitions are DRAFT + UNTRUSTED until reviewed; activation explicit.
- Dry-run never performs side effects (would-do list instead).
- External delivery never fires without authorization (delivery_note proves it).
- Missed backlog never auto-executes dangerous work (SKIP default; CATCH_UP single compensating run).
- Destructive actions never blind-retried.
- Restart reconciles from durable state (reconcile()).
