# AGI, Task & Agent Models (Phases 7–11, 27)

## AGI interaction loop (the heart)
Ask → understand → propose plan → approve when necessary → execute →
visible progress → result → continue from context. Implemented pieces:
Home intent input hands text to the real composer as a new-session draft
(no fake execution); chat runs conversation; sessions carry tasks;
subagent trees + `AgentCard` expose operational status (current action,
tool, progress, blockers, result) — never chain-of-thought.

## Conversation ≠ Task ≠ Agent ≠ Result
- Conversation: chat transcript (session).
- Task: first-class object (`/tasks`: cron jobs + desktop action tasks
  with open/pause/resume/cancel semantics where the backend honors them).
- Agent execution: subagent tree per session (`AgentCard` header:
  status, done/total, current tool, model, tokens, files; Inspect/Stop).
- Result: artifacts with provenance + notification deep-links.
Statuses: IDLE / THINKING / PLANNING / RUNNING / WAITING /
NEEDS_APPROVAL / BLOCKED / COMPLETED / FAILED / PAUSED / CANCELLED map
onto subagent + session + cron states; multi-agent shows one status per
worker plus delegation grouping (no orchestration internals).

## Context model (new: `lib/context-model.ts`, tested)
GLOBAL → WORKSPACE (profile) → APP (view) → TASK (session) → AGENT
(active count) → ACTION (current tool). Pure derivation from existing
stores; layers omitted when unknown. Consumers: Home shows
"Using context from: …" (no silent memory injection); palette stop
resolves "active session" from the same chain. Voice/keyboard/click
share it — one scope for "this".

## Task Center
`/tasks` unifies scheduled + action tasks with status, owner/agent,
timing, and result navigation; approvals surface via Security with
WHAT/WHY/SCOPE/RISK/CONSEQUENCE and ALLOW/DENY/ONCE/FOR-TASK scoping
where the backend honors it (sudo/secret modals; inline tool approval;
dismissal = refusal, never consent).
