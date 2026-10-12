# AETHEROS MASTER 13 — PHASE 0 AUTOMATION AUDIT

Date: 2026-08-22 · Scope: full-repo scan for scheduling, queueing, background
execution, eventing, persistence, retry/recovery, notification, and service
infrastructure. **No code was modified.**

---

## Executive Summary

AetherOS already ships a **mature, production automation spine**:

| Spine component | Location | Maturity |
|---|---|---|
| Scheduler (tick loop, multi-format schedules, catchup, injection scanning) | `cron/scheduler.py`, `cron/jobs.py` | High — heavily hardened |
| Durable work queue + dispatcher | `aetheros_cli/kanban_db.py` (SQLite), dispatcher in gateway | High — heartbeats, reclaim, breaker |
| Sub-agent execution | `tools/delegate_tool.py` | High — sync, bounded, non-durable (by design) |
| Long-running background processes | `terminal(background=True)` watcher | High |
| Approval gates | `tools/approval.py` + `/approve` `/deny` | High |
| Webhook ingress | `gateway/platforms/webhook.py`, `msgraph_webhook.py` | Medium-high — signatures, rate limit, idempotency |
| REST/OpenAI API | `gateway/platforms/api_server.py` | High — idempotency cache, concurrency cap |

It also contains **two additional, partially-wired infrastructure layers**
(`aetheros_automation/*` Phase-16 package, `aetheros_runtime/*`) plus scattered
task managers (`aetheros_intelligence/planning.py`, `agents/collaboration.py`,
`core/jarvis/engine.py`). Several of these duplicate spine capabilities at
lower quality and some violate repo policy (hardcoded `~/.aetheros` paths,
false durability claims). **Consolidation, not new parallel systems, is the
correct Master-13 strategy** — matching the preservation rules ("no duplicate
queues / workers / persistence").

---

## 1. Existing Schedulers

### 1.1 Production cron scheduler — `cron/scheduler.py` (~2,212 LOC)
- **Tick loop**: gateway calls `tick()` every 60 s from a background thread;
  cross-process safety via file lock `~/.aetheros/cron/.tick.lock`
  (fcntl on POSIX, msvcrt on Windows) — `_get_lock_paths()` (scheduler.py:230).
- **Execution pools**: persistent parallel `ThreadPoolExecutor`
  (`_get_parallel_pool`, scheduler.py:175) + single-worker sequential pool for
  env-mutating workdir jobs (`_get_sequential_pool`, scheduler.py:189);
  both shut down via `atexit` (scheduler.py:218).
- **Hardening**: 3-minute hard interrupt on cron sessions; catchup window =
  half the job period clamped 120 s–2 h; one-shot grace `ONESHOT_GRACE_SECONDS=120`
  (jobs.py:46); `[SILENT]` suppression marker; `wakeAgent:false` script gate
  (`_parse_wake_gate`, scheduler.py:1006); `no_agent` script-only watchdog mode
  (scheduler.py:1333).
- **Security**: two-tier prompt-injection scanner on create/update *and* the
  fully-assembled runtime prompt incl. skill content
  (`_scan_assembled_cron_prompt`, scheduler.py:1235; patterns in
  `tools/cronjob_tools.py`); pre-run scripts sandboxed to
  `AETHEROS_HOME/scripts/` with traversal/symlink escape rejection
  (`_run_job_script`, scheduler.py:891) and secret redaction of stdout/stderr;
  protected-toolset denylist always applied to spawned agents
  (`cronjob`, `messaging`, `clarify` + user denylist — scheduler.py:61);
  validated delivery platforms frozenset prevents env-var enumeration
  (scheduler.py:116); job `id` immutable + path-component validated
  (jobs.py:52–68); ContextVars isolate per-job session/delivery state
  (scheduler.py:1500–1534).
- **Delivery**: multi-target routing — `local`, `origin`, `all` token,
  `platform:chat[:thread]`, name resolution via channel directory; live-adapter
  path for E2EE rooms with standalone-HTTP fallback (`_deliver_result`,
  scheduler.py:658); native media attachment routing (scheduler.py:602).

### 1.2 Job store & schedule grammar — `cron/jobs.py` (~1,212 LOC)
- Persistence: `~/.aetheros/cron/jobs.json` (atomic replace, in-process
  threading lock, 0600 perms); outputs `~/.aetheros/cron/output/{job_id}/{ts}.md`.
- `parse_schedule()` (jobs.py:206) → `{kind: once | interval | cron}`:
  duration `"30m"|"2h"|"1d"`, `"every X"` recurring, 5/6-field cron
  expressions (optional `croniter` dep), bare ISO timestamps.
- Job fields include: `id, name, prompt, schedule, skills[], model, deliver,
  origin{platform,chat_id,thread_id}, script, context_from[], workdir,
  enabled, state(scheduled|paused), no_agent, enabled_toolsets, max_turns…`.

### 1.3 Secondary schedulers (NOT part of the production spine)
- `aetheros_automation/communications/scheduler.py` — `MessageScheduler`;
  **unwired** (no caller in live paths).
- `apps/desktop/dist-packaged/.../cluster/scheduler.py` — packaged desktop
  backend copy only, not repo-runtime code.

## 2. Existing Workers
- **Kanban dispatcher** (`aetheros_cli/kanban.py`, runs inside gateway via
  `kanban.dispatch_in_gateway`): every ~60 s — reclaim stale claims, promote
  ready tasks, atomic claim, spawn assigned profiles. Auto-blocks tasks after
  `kanban.failure_limit` (default 2) consecutive non-success attempts.
  Board isolation via pinned `AETHEROS_KANBAN_BOARD`; soft tenant namespace.
- **Cron worker pools**: see §1.1.
- **Gateway background processors**: each adapter's
  `_process_message_background` (`gateway/platforms/base.py`) with the two
  sequential message guards (base queue + runner intercept).
- **Background-process watcher**: `terminal(background=true,
  notify_on_complete=true)` completion watcher triggers new agent turns;
  verbosity via `display.background_process_notifications`
  (`all|result|error|off`).
- `batch_runner.py` — parallel batch processing entrypoint.

## 3. Existing Queues
- **Kanban SQLite board** (`aetheros_cli/kanban_db.py`) — the durable queue.
  Schema includes `idempotency_key`, `worker_pid`, `last_heartbeat_at`,
  `max_runtime_seconds`, `max_retries`, `current_run_id`,
  `workflow_template_id`, `current_step_key`, `tenant`, `result`,
  `last_failure_error`, `goal_mode/goal_max_turns`, `skills`.
- **Gateway pending-message queue**: `base.py::_pending_messages` while a
  session is active.
- `aetheros_runtime/execution_queue.py` — exists; in-memory quality tier.
- ⚠ `core/task_queue.py` — **claims durable but does not persist**; must never
  be wired into live paths without fixing or deleting.

## 4. Existing Timers
- Threading pools with `atexit` shutdown (cron).
- Per-adapter `asyncio.create_task` loops (heartbeat/reconnect/polling).
- Feishu drainer thread queuing inbound events until the loop is ready.
- No generic timer service; all timing is owned by the components above.

## 5. Existing Event Systems
- **In-process EventBus**: `aetheros_automation/orchestrator/events.py` —
  sync pub/sub, wildcard `*` handlers, 1000-entry bounded history,
  `get_history(event_filter, limit, since)`. ⚠ `wait_for()` calls
  `run_until_complete` — returns `{}` whenever a loop is already running
  (i.e., always, in gateway/TUI contexts). Not wired to the cron/kanban spine.
- **Plugin lifecycle hooks** (`aetheros_cli/plugins.py` ctx):
  `pre_tool_call`, `post_tool_call`, `pre_llm_call`, `post_llm_call`,
  `on_session_start`, `on_session_end` — invoked from `model_tools.py` /
  `run_agent.py`. Discovery pitfall: requires `import model_tools` first.
- **Gateway hooks**: `gateway/builtin_hooks/` extension point (none shipped);
  hook emission gated on `GATEWAY_KNOWN_COMMANDS`.
- **Message deduplication**: `MessageDeduplicator`
  (`gateway/platforms/helpers.py`) used by dingtalk/slack/wecom/weixin/matrix;
  Feishu persists seen-IDs across restarts (`feishu_seen_message_ids.json`);
  Matrix startup-replay window guard.
- **Platform webhooks** (inbound events): see §12/§15.

## 6. Existing Persistence
| Store | Path | Tech |
|---|---|---|
| Sessions/search | SessionDB (`aetheros_state.py`) | SQLite + FTS5 |
| Cron jobs | `~/.aetheros/cron/jobs.json` | JSON, atomic write, lock |
| Cron outputs/history | `~/.aetheros/cron/output/{job_id}/*.md` | files |
| Kanban board | profile kanban DB (`aetheros_cli/kanban_db.py`) | SQLite |
| Skill usage/curator | `~/.aetheros/skills/.usage.json` + `.archive/` + tar.gz backups | JSON/tar |
| Agent checkpoints | `checkpoints.*` config (run_agent) | git-based |
| Orchestrator state | `aetheros_automation/orchestrator/store.py`, `checkpoint.py`; `undo/checkpoints.py` | JSON stores (mixed quality) |
| Feishu dedup state | `feishu_seen_message_ids.json` | JSON |

All spine stores are profile-aware via `get_aetheros_home()`. The Phase-16
package has instances of hardcoded `~/.aetheros` — policy violation to fix if
touched (see §15).

## 7. Existing Retry Systems
- Kanban: `max_retries`, heartbeat-based stale reclaim, `failure_limit`
  auto-block (**de-facto circuit breaker**).
- Provider layer: `fallback_model` chain, credential-pool cooldowns.
- Platform sends: Slack 429 retry (<2 attempts), Weixin rate-limit circuit
  breaker with cooldown window, Signal rate-limit error typing.
- Phase-16 duplicates: `recovery/retry.py` (backoff+jitter),
  `recovery/fallback.py`, `orchestrator/recovery.py` — parallel abstractions
  overlapping §7 items above.
- Cron: **no retry-on-failure today** (next occurrence is the retry); no
  consecutive-failure breaker on the job level.

## 8. Existing Background Execution
- `delegate_task` — synchronous sub-agents (single + parallel batch, capped by
  `delegation.max_concurrent_children=3`, depth ≤2, child timeout). Explicitly
  **not durable** — AGENTS.md directs long-running work to cron/background
  terminal instead.
- Cron jobs — durable, survive restart (store-driven).
- Background terminal processes — durable-ish (process outlives turn; watcher
  notifies).
- Orchestrator `ExecutionEngine`/SubAgentManager — Phase-16 layer; not part of
  shipped flows.

## 9. Existing Notifications
- Cron result delivery to 19+ platforms (+ plugin `cron_deliver_env_var`),
  wrap_response framing, MEDIA extraction, silent marker.
- Background-process notifications with severity filtering.
- `send_message_tool` for agent-initiated messages.
- `aetheros_runtime/notifications.py::publish` — desktop notification helper
  (`task.finished` etc.), in-memory tier.
- **Missing**: unified notification engine (preferences, quiet hours, priority
  thresholds, channel fan-out for lifecycle events like WAITING_APPROVAL).

## 10. Existing Service Integration
- Windows: `schtasks` wrapper (`gateway_windows.py`) registers gateway startup.
- Linux/systemd: `plugins/kanban/systemd/hermes-kanban-dispatcher.service`
  (standalone dispatcher deployment; marked deprecated in favor of
  dispatch-in-gateway).
- macOS: none dedicated (launchd absent) — gateway runs as user process.
- Installer/service architecture must not be replaced (preservation rule).

## 11. Existing Automation APIs
- **Model tool**: `cronjob` (`tools/cronjob_tools.py`) — create/update/list/
  pause/resume/remove with create-time injection scanning; explicit schedule
  strings required (nothing silently recurring).
- **CLI**: `aetheros cron {list,add,edit,pause,resume,run,remove}`;
  `/cron` slash command; kanban verb suite (`init … gc`).
- **REST**: `aetheros_cli/web_server.py` (cron targets endpoint ~line 3320,
  tasks listing ~3066, PTY bridge); OpenAI-compatible
  `gateway/platforms/api_server.py` with `Idempotency-Key` support
  (LRU+TTL cache, lines 621/1950/2996) and `_MAX_CONCURRENT_RUNS` cap
  (line 3645, returns `rate_limit_exceeded`).
- Phase-16: `aetheros_automation/web/api.py`, `orchestrator/api.py` (desktop
  Task-Orchestrator workspace `/task-orchestrator`).

## 12. Existing MCP Tasks Integration
**None.** Repo-wide search finds no `tasks/get`, `tasks/update`,
`tasks/cancel` (MCP Tasks extension). An MCP client + catalog exist
(`tools/`, docs), and `aetheros_automation/mcp/server.py` exposes an MCP
server, but task-state normalization with MCP Tasks is greenfield.
Per Master-13 constraints this stays optional capability-detection based;
internal persistence remains authoritative.

## 13. Duplicate Systems (consolidation targets)
| Capability | Spine (keep) | Duplicates (consolidate/quarantine) |
|---|---|---|
| Task queue | kanban SQLite | `core/task_queue.py` (false durability), `aetheros_runtime/execution_queue.py` |
| Scheduler | cron/ | `communications/scheduler.py` (unwired) |
| Checkpoints | run_agent checkpoints; kanban step keys | `orchestrator/checkpoint.py`, `undo/checkpoints.py` (three-way split) |
| Retry/backoff | provider fallback + kanban retries | `recovery/retry.py`, `orchestrator/recovery.py` |
| Approvals | `tools/approval.py` + `/approve·/deny` | `orchestrator/approvals.py` |
| Task registries | SessionDB, kanban, cron store | in-memory `_tasks` dicts in ≥6 modules (`aetheros_runtime/agent_runtime.py:140`, `agents/collaboration.py:123`, `agent/multimodal/orchestration.py:232`, …) |
| Notifications | platform delivery + bg-process notifier | `communications/notification_manager.py`, `mobile/notifier.py` |

## 14. Missing Capabilities (gap list vs Master 13 phases)
1. **File watchers** (Phases 9/14) — zero filesystem-watch infrastructure.
2. **Normalized event bus bridged to the scheduler** (Phases 9–11, 15–17) —
   EventBus exists but is disconnected from cron/kanban; no trigger registry.
3. **MCP Tasks adapter** (Phases 55–58) — absent.
4. **Timezone/DST-aware schedules** (Phases 6–7) — `aetheros_time.now()` gives
   a global configured zone, but `parse_schedule()` has no per-job IANA zone
   field; croniter called without tz ⇒ wall-clock drift across DST for
   time-of-day schedules.
5. **Missed-schedule policies** (Phase 8) — fixed catchup heuristic; no
   SKIP/RUN_ON_START/RUN_NEXT_INTERVAL/CATCH_UP/ASK_USER selection.
6. **Automation-level circuit breaker & quarantine** (Phases 27, 94) — kanban
   has one; cron does not.
7. **Workflow DAG/versioning in the spine** (Phases 18–21) — kanban
   `workflow_template_id`/`current_step_key` is partial; no versioned DAG
   runner wired to delegation.
8. **Approval-gated steps inside workflows** (Phases 22–23) — approvals exist
   interactively; no durable WAITING_APPROVAL state for scheduled work.
9. **Emergency stop / safe mode / dry-run** (Phases 48–51) — per-session
   `/stop` exists; no global background kill-switch or simulation mode.
10. **Per-automation resource limits & cost caps** (Phases 30–32) — global
    max_turns only; kanban has max_runtime/max_retries columns to reuse.
11. **Notification preferences/quiet hours** (Phases 59–61).
12. **Execution-history timeline UI** (Phases 62–64, 71) — raw materials exist
    (cron output dir, kanban runs table) but no unified view/API.

## 15. Security Risks
1. **Hardcoded `~/.aetheros` paths in `aetheros_automation/**`** — breaks
   profiles (violates PR #3575 policy). Any wiring must route through
   `get_aetheros_home()`.
2. **Webhook replay**: Svix path enforces ±300 s timestamp tolerance
   (webhook.py:707–755); GitHub/GitLab/generic HMAC paths verify signature but
   carry **no timestamp**, so captured valid payloads replay indefinitely
   unless senders provide `Idempotency-Key` (1 h TTL cache). Documented gap.
3. **EventBus.wait_for** swallows errors under a running loop — an approval or
   trigger built on it would appear to "time out" silently.
4. **Untrusted payload → prompt**: webhook templates interpolate payload text
   directly (`_render_prompt`, webhook.py:761+). Cron-grade assembled-prompt
   injection scanning does **not** cover the webhook path.
5. **False-durability trap**: `core/task_queue.py` — wiring it in would lose
   tasks on restart while claiming otherwise.
6. **Process-global env mutation** in cron `run_job` (`TERMINAL_CWD`,
   `AETHEROS_CRON_SESSION`) — currently safe only because of pool discipline;
   new parallel paths must preserve that invariant.
7. Positives worth preserving: script sandbox + redaction, job-ID path guards,
   immutable fields, protected toolsets, scoped token locks, pairing, Twilio/
   Feishu/msgraph signature validation, API concurrency caps.

## 16. Reliability Risks
- Crash window between job pickup and `mark_job_run` could double-fire a job
  after restart (small; file lock narrows it).
- No heartbeat/stall detection for cron pool threads (long jobs invisible).
- Restart recovery depends on gateway being up to tick; standalone CLI runs do
  not advance schedules.
- In-memory task registries (§13) evaporate on restart — acceptable while
  unwired, dangerous as growth paths.
- `atexit` pool shutdown waits (`wait=True`) — slow jobs delay interpreter
  exit.

## 17. Files Requiring Modification (Master-13 implementation map)
| Area | Files |
|---|---|
| Automation object + lifecycle + limits + breaker + quarantine | `cron/jobs.py` (schema v-additions, backward compatible), new `automation/model.py` |
| Scheduler semantics (missed-policy, tz/DST, dry-run, e-stop) | `cron/scheduler.py`, new `automation/schedule_policy.py` |
| Trigger registry + event bus bridge + filters | new `automation/triggers.py`, `automation/event_bus.py` (wraps/adapts `orchestrator/events.py`) |
| File watcher | new `automation/file_watcher.py` (stdlib polling first; optional watchdog dep, SHA-pinned per policy) |
| Webhook hardening (timestamped generic sigs, payload scan) | `gateway/platforms/webhook.py` |
| Workflow DAG/versioned runner over delegation | new `automation/workflow.py`, thin hooks in `tools/delegate_tool.py` (additive only) |
| MCP Tasks adapter (capability-detected) | new `automation/mcp_tasks.py` |
| Tool/UI surfaces | `tools/cronjob_tools.py` (schema additions), `aetheros_cli/web_server.py` (dashboard endpoints), `aetheros_cli/commands.py` + `cli.py`/`gateway/run.py` (new slash commands per registry pattern) |
| Config | `aetheros_cli/config.py` DEFAULT_CONFIG (`automation:` section), `_config_version` bump only if migrating |
| Tests | `tests/automation/…` (tz/DST, missed-policy, dedup, breaker, recovery, security) |

## 18. Files That Must Remain Untouched
`run_agent.py` (loop/cache invariants — additive params only, no behavior
change), `cli.py` core loop, `toolsets.py` `_HERMES_CORE_TOOLS` (no new core
tool), `model_tools.py` (discovery), `gateway/run.py` message guards,
`gateway/platforms/*` adapters (except webhook.py hardening above), memory
stack (`agent/memory_*`), curator, profiles machinery (`aetheros_constants.py`,
`aetheros_cli/main.py` profile override), installer/service registration,
and all MASTER 1–12 behavior contracts.

---

## Audit Verdict

Build Master 13 **on top of the cron + kanban + delegation spine** as a new
`automation/` layer that (a) extends the job schema additively, (b) adapts the
existing EventBus into the trigger source, (c) reuses kanban's
heartbeat/breaker/idempotency patterns, and (d) treats `aetheros_automation/*`
as a library to borrow from — not a second runtime. This satisfies every
"do-not-duplicate" rule while closing the gaps in §14.
