# AetherOS Execution Architecture (Master Prompt 5)

## Architecture (as built)
AGI → TASK → PLAN → POLICY CHECK (approval gates) → PERMISSION CHECK
(server-side scopes) → EXECUTOR (agent runtime / cron / automation
runners — the existing engines, no duplicates) → TOOL (terminal,
filesystem, browser, MCP, apps, APIs) → OBSERVATION (stream, exit
codes, tool results) → VALIDATION (tool-reported only) → RESULT
(artifacts + notifications). Sandboxing/resource/network boundaries are
backend-owned; the renderer never executes anything directly (verified:
zero `child_process`/spawn/exec in `src/` — all terminal/fs IO goes
through typed `aetheros:*` IPC to the main process).

## Tool registry (`lib/tool-registry.ts`, tested)
Canonical advisory catalog: name → capabilities
(read/write/execute/network/browser/communicate/delete/system/admin) +
risk tier + environments (workspace/sandbox/system) + assumed timeout.
Joined with live `ToolsetInfo` (enabled/configured/tools) and shown as
capability + risk badges on every Skills toolset row. Unknown toolsets
fall back to medium/caution. Enforcement stays server-side — badges are
visibility, not control.

## Capability & risk models
Capabilities from actual toolsets; risk: LOW (workspace reads/search),
MEDIUM (project writes, config, automation), HIGH (terminal/code-exec,
messaging, MCP, system mutation), CRITICAL/DESTRUCTIVE (admin,
credentials, privilege). Confirmation mirrors risk
(`confirmationForTier`, Master Prompt 4). No per-tool schema invention:
granularity stops where backend metadata stops.

## Permission model
USER + AGENT + TASK + TOOL + RESOURCE + ACTION + SCOPE, evaluated
server-side per call; renderer shows scope at the gate (session/task/
workspace phrasing matches the `approval.respond` contract:
once/session/always/deny). Least privilege by default; "Allow all" never
offered (the permanent allow goes through its own confirm step).

## Timeouts, retry, idempotency
Registry carries assumed timeouts; transient network/rate-limit retries
belong to runners; destructive/external/financial actions are never
auto-retried. File writes via checkpoints (`/rollback` lists/restores
filesystem checkpoints — real mechanism, surfaced, not claimed atomic).
Rollback is offered only where checkpoints/git exist; otherwise the UI
says what is recoverable and what is not.

## Filesystem / terminal / browser / MCP / apps / APIs
- Filesystem: read/write/create/rename/move/copy/delete/list/search/stat
  through tool + file views; scope validation, traversal protection, and
  audit logging are backend-owned and unchanged.
- Terminal: command + cwd + env + timeout + stdout/stderr + exit code +
  duration + cancel via PTY IPC; output virtualized/collapsible, never
  dumped wholesale; secrets redacted before display/persistence.
- Browser: webview partition + automation client; login/purchase/submit
  class actions require confirmation; no silent consequential submits.
- MCP: manager shows trust/permissions/health from real config; servers
  are never auto-trusted; tool provenance shown where reported.
- Apps/APIs: same gateway RPC contract (endpoint/method/scope/timeout/
  retry/error), secrets never rendered.

## Background, queues, recovery
Cron runners + background sessions persist state, logs, artifacts,
errors; survival across reload/restart is backend-owned and surfaced
honestly (Live/Paused/Disconnected, never fake-live). Partial success
reports counts ("8 of 10"), never "Completed" on failure.

## History & audit
Execution timeline (Agents overlay) + Security audit + automation/cron
run history + notification trail = searchable operational history
(task/agent/tool/timestamp/result/approval/artifact). No reasoning
content anywhere.
