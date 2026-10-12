# AETHEROS MASTER 13 — AUTOMATION FINAL REPORT

Date: 2026-08-23 · Companion to `AETHEROS_MASTER_13_AUTOMATION_AUDIT.md` (Phase 0).

---

## 0. Architecture Verdict

Master 13 was built **on top of** the production spine (cron scheduler + JSON
job store + worker pools + delivery routing), never beside it. There is exactly
one scheduler (`cron/`), one durable queue per purpose (cron `jobs.json`,
kanban SQLite), one event-trigger bus (`automation/events.AutomationBus`), and
one workflow engine whose every step executes through
`cron.scheduler.run_job` — so injection scanning, toolset denylists, resource
limits and provider fallback apply identically to scheduled and workflow work.
The unwired Phase-16 package (`aetheros_automation/*`) was deliberately **not**
wired; it remains a library to borrow from.

```
USER ── aetheros automation CLI · cronjob tool · /blueprint /suggestions
   │
AUTOMATION API (cron/jobs.py store — additive Master-13 fields)
   ├── SCHEDULER  cron/scheduler.py tick() (60s, .tick.lock)
   │     estop gate → breaker gate → due selection → pools → run_job
   └── EVENT BUS  automation/events.py → dispatcher.py pump
         file watcher · webhook.received · app lifecycle events
         (dispatch = stamp next_run_at ⇒ same guarded path as schedules)
                        │
              WORKFLOW ENGINE automation/workflow_engine.py
                DAG · conditions · approvals · retries · checkpoints
                        │
        MASTER 11 delegation · MASTER 12 tools/MCP · MASTER 7 security
```

## 1–5. Scheduler / Event / Workflow / Worker / Queue architecture

- **Scheduler**: `tick()` every 60 s from the gateway ticker thread;
  at-most-once via `advance_next_run()` under the jobs-file lock *before*
  dispatch; cross-process `.tick.lock`; parallel pool + sequential (workdir)
  pool; `atexit` shutdown.
- **Events**: `AutomationEvent{event_id,event_type,source,timestamp,payload,
  trust}`; bounded history (512), TTL dedup (1 h), payload cap (4 kB).
  External payloads are untrusted input used solely for filter matching.
- **Workflows**: versioned DAGs (`steps`, `depends_on`, structured
  `condition`s, `approval_required`, per-step `attempts`/`on_failure`,
  `concurrency ≤ 4`); Kahn topo sort rejects cycles; runs snapshot
  `definition_version` (in-flight runs finish their starting version).
- **Workers**: existing cron pools + kanban dispatcher (heartbeats, stale
  reclaim, failure-limit auto-block) + delegate_task children. No new pool
  was created.
- **Queues**: cron job store and kanban board only. The event "queue" is the
  bus's bounded history plus `next_run_at` stamping — no second queue exists.

## 6–8. Persistence / Checkpoints / Recovery

- Automations persist as additive fields on `jobs.json` records
  (`definition_version`, `timezone`, `missed_policy`, `resource_limits`,
  `breaker`, `trigger`, `workflow`, `failure_streak`, `breaker_opens*`,
  `quarantined*`, `last_triggered_at`) — backward compatible, tolerant loader.
- Workflow runs persist one JSON per run under `~/.aetheros/automation/runs/`;
  checkpointed **only at step milestones**; resume skips `done` steps
  (idempotency at step granularity); cancellation flag is monotonic across
  processes and re-checked between steps.
- Approvals persist under `~/.aetheros/automation/approvals/<id>.json`;
  expired ⇒ denied by construction (never silently executes).

## 9–11. Retry / Fallback / Notifications

- Step retries: `attempts` (≤10) × error classification
  (`automation/errors.py`: transient/network/resource retryable; auth/
  permission/security **never** retried) with jittered backoff.
- Automation-level circuit breaker: N consecutive failures open cooldown;
  repeated openings quarantine until `aetheros automation recover`.
  Quarantine notices always deliver (critical); cooldown notices honor prefs.
- Provider fallback chains unchanged (per-job model/provider/base_url +
  `fallback_model` inheritance).
- Notification preferences: allowlist w/ trailing-`*` globs, quiet hours
  (midnight wrap), priority floor — wired into workflow notices and breaker
  opens via `should_notify()`; critical events unbypassable.

## 12. Background agents

delegate_task (sync, capped, non-durable by contract), cron-spawned agents
(`skip_memory=True` invariant intact), kanban profile workers. Emergency stop
blocks all new dispatch (scheduler *and* dispatcher check it); safe mode
suppresses external deliveries while still executing locally.

## 13. MCP Tasks integration

Capability-sniffing adapter (`automation/mcp_tasks.py`): state mapping
(preserving raw MCP record), bounded backoff polling, cancellation returning
`unsupported` when the server lacks `tasks/cancel`. Opt-in by design — hosts
pass client callables; internal run store stays authoritative. Wiring into
`tools/mcp_tool.py` transports is future work (documented extension points).

## 14–16. Security / Resource controls / Cross-platform

- Security: two-tier prompt-injection scanning incl. assembled runtime
  prompts; protected toolset denylist; fail-closed trigger trust model
  (`allow_untrusted` opt-in); file watchers confined to configured roots with
  symlink-swap re-validation; webhook HMAC/signature/replay/rate/idempotency
  stack; script sandbox; secrets never stored in automation definitions.
- Resources: per-run wall-clock + turn limits, per-automation breaker, global
  dispatch rate cap (30/min default), per-trigger cooldown, global parallelism
  knobs (`max_parallel_jobs`, `max_concurrent_children`), notification-rate
  breakers in process registry.
- Cross-platform: fcntl/msvcrt locking both exercised; `tzdata` pinned for
  Windows zoneinfo; this verification cycle executed natively on Windows.

## 17–18. Testing / Performance

- Suites: `tests/automation/` (13 files incl. new
  `test_notification_gate_and_conflicts.py`),
  `tests/tools/test_cronjob_tool_automation_fields.py` (+20 tests this pass),
  plus cron/tool/webhook/approval suites green.
- Regression discipline: baseline before changes = 13 failed / 652 passed;
  after = identical 13 failures (pre-existing Windows-only artifacts:
  POSIX 0600/0700 permission assertions, bash-script tests, tilde expansion)
  with 672 passed — zero regressions introduced.
- Performance characteristics are structural, not benchmarked here: dispatch
  adds one O(jobs) filter pass per event (rate-capped); workflow overhead =
  one JSON write per step milestone; scheduler latency unchanged (60 s tick).

## 19–20. Remaining risks & limitations (honest)

1. **MCP Tasks transport wiring** — adapter exists, not bound to live MCP
   sessions yet.
2. **Desktop automations dashboard** (Phase 64 UI) — CLI/`runs` timeline
   shipped; React dashboard panel not built.
3. **Natural-language → workflow compiler** (Phases 65–66) — `/blueprint`
   templates + conversational `cronjob` covers most cases; no dedicated NL
   planner.
4. **Sleep/wake & OS network events** (Phase 16) — no platform listeners;
   startup/shutdown covered, wake detection is not.
5. **Batching** (Phase 81) — debounce/coalesce exists per path; explicit
   "process N files in one run" aggregation does not.
6. **Full-repo regression** — verified the touched subsystems (~700 tests);
   the complete 17k-test suite should ride the normal CI pipeline.
7. Webhook generic-HMAC replay window relies on optional sender timestamps
   (pre-existing documented gap, unchanged).

## Checklist deltas closed in this pass

| Gap | Fix |
|---|---|
| Master-13 fields unreachable from agent surface | `cronjob` tool: `timezone`, `missed_policy`, `resource_limits`, `breaker`, `trigger` (create/update, fail-closed) |
| Notification preferences defined but unused | Wired into `_deliver_workflow_notice` + breaker-open notice; critical events made unbypassable |
| Critical events could be silenced by allowlist | `should_notify()` re-ordered to match its own contract |
| Conflict detection missing | New `automation/conflicts.py` (duplicate schedule / workdir overlap / event fanout), surfaced in `automation dryrun` |

Everything else on the Master-13 completion list was already implemented and
verified during this audit: universal automation object & lifecycle states,
one-time/recurring/cron/timezone/DST/missed-policy scheduling, event bus +
filters + trigger security, webhooks with replay protection, file watchers,
application/system(startup) events, versioned DAG workflows with conditional
branching, approval gates with timeout-expiry, parallel/sequential execution,
retry/failure policies, circuit breaker + quarantine, pause/resume/cancel/
emergency-stop/safe-mode/dry-run, durable run state with checkpoint/resume,
history retention pruning, and the `aetheros automation` control plane
(status/list/show/dryrun/estop/policy/limits/recover/trigger/events/approve/
deny/runs/cancel).

## Core principle — upheld

Every autonomous capability added is explicit (declared trigger or schedule),
bounded (cooldowns, rate caps, breakers, limits), observable (bus history,
`runs`, `events`, notices), cancellable (run flags, estop), recoverable
(checkpoints, missed policies), and user-controlled (approvals, preferences,
quarantine recovery). AetherOS automation remains work execution under user
authority — not uncontrolled autonomy.
