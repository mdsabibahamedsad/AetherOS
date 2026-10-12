# Master 43 audit — actual repository state (2026-09-04)

## 1. Existing automation infrastructure
- `cron/` — persistent `jobs.json` store, `tick()` loop with file lock,
  croniter support, prompt-injection scanning, per-job output dirs.
- `aetheros_automation/` — full stack: TaskOrchestrator, ExecutionEngine,
  CheckpointManager, RetryHandler, approvals, templates, NLPAutomationEngine,
  model router, validator, lifecycle, multi-agent collaboration.

## 2. Existing scheduler
- `cron/scheduler.py` tick (gateway calls every 60s, background thread).
- No virtual clock; scheduler tests would need one (built new).

## 3. Existing background workers
- cron tick threads, gateway watcher threads, swarm ThreadPool executor,
  kanban dispatcher loop. No unified worker pool (built into runtime).

## 4. Existing task/orchestration systems
- Master 38 automation orchestrator, Master 42 `aetheros_swarm/`
  (orchestrator, budgets, ApprovalQueue, AuditLog, CheckpointStore,
  Tracer, EventStream). Reused directly — no duplicates created.

## 5. Existing notification infrastructure
- Scattered (gateway watchers, update notifications). No unified center
  (built `notify.py` with channels + digest).

## 6. Existing desktop UI
- `app/automation` (canvas editor), `app/automations` (list),
  `app/cron`, `app/swarm-center`, `app/task-orchestrator`. New
  `app/automation-center` wired to real `automation.*` IPC.

## 7. Existing security boundaries
- cron disabled toolsets + injection scanning, delegate blocked tools,
  swarm ToolAuthorizer + approval gates, Master-41 scopes. Reused.

## 8. Reusable components
- swarm ops (approvals/audit/checkpoints/tracer/events), swarm budgets +
  orchestrator, MemoryService, cron job-store patterns, registry check_fn.

## 9. Missing components (built in `aetheros_autonomy/`)
- AutomationDefinition runtime, durable virtual-clock scheduler, trigger
  engine, file/repo/web watchers, autonomy levels, dry-run, digest,
  templates, NL builder + plan preview, recursion defense, global
  settings, emergency stop, safe mode.

## 10. Migration risks
- Touching `cron/` runtime risks breaking gateway ticks → bridge via lazy
  import, failure-safe, no cron code modified.
- Import cycles with swarm/gateway → lazy imports everywhere.
- Duplicating schedulers → single `Scheduler` class; cron remains the
  legacy path, autonomy is the new OS layer with optional cron mirror.
