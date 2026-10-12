# Artifacts, Results, Memory, Integrations (Master Prompt 4)

## Artifact model
First-class objects from session-message collection (`ArtifactsView`):
type, location, creator session, task link, kind filters, counts,
preview/download/open via real handlers. Result view separates ACTIVITY
(result list) from RESULT (summary + artifacts + next actions:
open/review/continue).

## Memory / context
Session context (scope line, drafts) vs saved preferences (Memory center
with inspect/edit/delete/retract/scope) — visually and mechanically
separate. Continuation ("Now optimize it") retains session context and
states it.

## Integrations (all route through existing real surfaces)
- Workspace: profiles + projects + drafts; palette/Home deep-links.
- Files: composer attachments + file views; AGI suggestions route to
  composer, never fake-execute.
- Terminal: PTY panes share cwd/session context; agent terminal tool use
  summarized, raw output inspectable.
- Notifications: completion/approval/failure deep-link to context.
- Automation: successful workflows → cron/automation-center (trigger →
  actions → permissions → result) where backends allow.
- Developer mode: logs, raw tool output, timelines, model/provider info
  behind inspect surfaces (progressive disclosure intact).

## Streaming / long-running / mobile
Incremental rendering over existing virtualized threads; no scroll
hijack; long tasks leave conversation (Task Center/notification/
workspace resume); mobile prioritizes intent/status/approval/results
with collapsed execution detail. Reduced-motion and live-region rules
hold for streaming content.
