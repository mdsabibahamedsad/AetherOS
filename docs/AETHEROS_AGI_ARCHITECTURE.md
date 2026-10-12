# AetherOS AGI Architecture (Master Prompt 4)

## Architecture map (mapped to the real repository)
USER → composer input (text/voice/draft) → intent (chat message or
stashed draft) → context resolution (`lib/context-model.ts`:
profile/view/session/agents/tool) → task creation (session, cron job,
action task) → planning (subagent delegation tree) → policy/permission
check (approval gates: inline tool approval, sudo/secret modals, parked
session-keyed prompts) → agent selection (main + subagents) → tool
selection (toolsets, MCP, terminal, browser) → execution (gateway
`prompt.submit`, streaming) → observation (stream entries, tool results)
→ verification (tool exit codes, test output — only what tools report)
→ artifact (message attachments, files) → result (summary + deep-link
notification) → USER (continue from retained session context).

No layer is faked; layers without backend signal render as Unknown, not
as guesses.

## Intent model
Inputs: text, voice (same composer), stashed drafts (Home/files
suggestions), selected files/text (composer attachments), current app /
workspace / task / terminal context (context chain). "Fix this" resolves
via the visible scope line — never silent memory injection.

## Context model
`lib/context-model.ts` (tested): GLOBAL → WORKSPACE → APP → TASK →
AGENT → ACTION. Consumers: Home scope line, palette stop target.
Memory surfaces stay separate: session context vs saved preferences are
visually distinct (Memory center vs scope line).

## Autonomy model (only implemented controls)
- supervised (default): approvals gate dangerous tools; clarify parks
  questions per session (human takeover path).
- autonomous: per-session YOLO or global YOLO (`approvals.mode`);
  statusbar zap shows effective state; `/yolo` command; shift toggles
  scope. No guided-plan mode exists — none claimed.
- Confirmation mirrors policy: low none / medium inline / high explicit /
  destructive strong (`confirmationForTier`, tested).

## AGI state system (canonical, `lib/agi-states.ts`)
Task: draft/queued/planning/waiting_for_approval/running/paused/blocked/
verifying/completed/failed/cancelled/unknown. Agent lifecycle:
created/initializing/ready/planning/running/waiting/needs_approval/
completing/completed/blocked/failed/cancelled/paused/unknown — mapped
1:1 from `SubagentStatus`. Interrupt labels Cancelled (sessions have no
pause); cron pause is real and labeled Paused. One vocabulary everywhere.

## AGI visual language
Cyan/blue/violet restraint, `AgiActivityList` (✓/●/○/✕ + text),
`AgentCard`, `ExecutionTimeline`, StatusDot tones. No brains, particles,
HUD theater. Wolf only at identity moments.
