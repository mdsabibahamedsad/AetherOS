# AetherOS Agent Operating Layer (Master Prompt 4)

## Agent model
Execution entities with identity (goal/model), capabilities (tools used),
permissions (gates passed), context (session), status (lifecycle),
output (summaries, files, artifacts). `AgentCard` renders exactly this —
operational info only, never chain-of-thought ("Researching
documentation", never "Thinking...").

## Multi-agent
Delegation tree (`buildSubagentTree`) + grouping + per-worker status;
`AgentCard` rolls up done/total, current tool, tokens, files.
Orchestration internals stay hidden; WHO/WHAT/STATUS/RESULT visible.

## Tool execution model
Tools are first-class: filesystem, terminal, browser, search, code exec,
APIs, MCP, apps, automation, comms, data. UI shows TOOL → ACTION →
RESULT at summary level (`summarizeAgentNodes`: current tool, counts);
raw payloads behind inspect/developer surfaces. No irrelevant dumps.

## Permissions & approvals
WHAT/WHY/SCOPE/RISK gates; ALLOW once / for-task / session / always /
deny per backend contract; dismissal = refusal; destructive = strong
confirmation (`confirm-dialog`, env-delete `window.confirm`). Thresholds
from policy, never hidden, never dark-patterned.

## Execution timeline (new: `ExecutionTimeline`, tested)
Node lifecycles → started + terminal events, time-ordered, in the Agents
overlay under the status card. Operational history (09:41 created →
approved → started → passed → prepared), not reasoning. Events without
timestamps dropped; empty → renders nothing.

## Interrupt / retry / recovery / takeover
- STOP = `session.interrupt` (palette, Home rows, AgentCard, STOP ALL
  legs); RESUME = `session.resume`; cron = pause/resume/trigger (all
  real). No backend pause for sessions → no Pause label on sessions.
- Failure shows WHAT/WHERE/WHY + real next actions (retry via resume or
  cron trigger, edit request as new draft, change permission via
  Security, open logs). No forced restarts.
- Takeover = parked clarify (choices inline) + sudo/secret modals +
  approval cards; ambiguous states offer choose/instruct/cancel. Never
  guesses on significant consequences.

## Verification honesty
Produced ≠ verified. "Verified" appears only from real tool signals
(exit codes, test output). No backend verified-flag exists — documented
as a backend gap, not papered over in UI.

## Background / concurrency / resources
Cron + background sessions are explicit ("Live · N running"); multi-task
status per task; system stats from real probes. Nothing implies
background execution the backend lacks.
