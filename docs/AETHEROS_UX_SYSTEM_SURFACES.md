# System Surfaces: Automation, Memory, Terminal, Settings, System Center (Phases 17–22)

## Approvals & permissions (Phase 17 — verified, kept)
WHAT/WHY/SCOPE/RISK/CONSEQUENCE on every gate; ALLOW/DENY/ONCE/FOR-TASK
where honored; dangerous consequences never hidden; no dark patterns.
Plumbing: session-keyed parked prompts (`store/prompts`), sudo/secret
modals, inline tool approval, dismissal→refusal. Palette + Home link to
the same Security surface — one approval truth.

## Automation (Phase 18)
Represented TRIGGER → CONDITIONS → ACTIONS → RESULT (automation-center
+ cron + canvas builder + history). Users see when it runs, what it
does, which permissions it uses, what happened, failure + retry. STOP
ALL halts automations via the real `automation.stop_all` leg.

## Memory & context (Phase 19)
Understandable concepts only: current/session context, workspace
(profile) context, saved preferences, provenance. Memory center exposes
inspect/edit/delete/retract/scope; Home states intent scope explicitly.
No "AI knows everything" mystery, no raw mechanism exposure.

## Terminal (Phase 20)
Native PTY panes (persistent, flippable, takeover-aware) keep full
power-user conventions; AI enters via composer draft + agent tool use,
not a chatbot skin. Shares cwd/session context with files/agents/tasks.

## Settings (Phase 21)
Organized by mental model (config sections + providers/keys/gateway/MCP/
sessions/about/developer/advanced/multimodal/accessibility), searchable,
every field labeled with explanation + default + predictable effect.
Palette deep-links to sections and individual fields.

## System Center (Phase 22)
Command Center + Home + statusbar + diagnostics: health, agents, tasks,
network, storage, automations, permissions, updates, security,
notifications — consumer-calm, one status language (`GlobalStatusIndicator`:
Operational / degraded-count / Offline), never an admin dashboard.
Onboarding teaches the mental model (invoke AGI, tasks, approvals,
workspaces, search, shortcuts) and stays fast.
