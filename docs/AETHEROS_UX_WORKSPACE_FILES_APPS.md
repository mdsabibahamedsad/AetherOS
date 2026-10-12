# Workspaces, Files, Apps (Phases 12–14)

## Workspace model
Profiles are the workspace boundary (isolated home dirs, per-profile
gateways/sockets, switcher + ordering + colors); projects add
project-level context; workspace-manager/smart-workspace add shortcuts
and notes. Resume = profile + recent session + draft restore (composer
draft stash survives navigation). Target: one workspace surface merging
profiles ⊕ workspace-manager; until then both stay functional, canonical
nav exposes Workspaces once.

## File system UX
Files view: browse/search/preview/rename/move/copy/delete with honest
empty/error states. AGI file actions are contextual suggestions that
route to the real composer (same draft handoff as Home intent), e.g.
select files → summarize/explain/organize — suggestions, not fake
execution. Terminal ↔ files ↔ agents ↔ tasks move via shared cwd/session
context, not duplicated state.

## Application model
Every view inherits the shell + design language (no SaaS-skin apps):
consistent headers (`PageShell`), status/empty/error patterns, palette
presence, settings deep-links. Launcher = palette + Home suggestions
(apps/files/people/agents/commands/workspaces/recents). App lifecycle =
routes + overlay cards + persistent panes; permissions per toolset/MCP/
A2A trust (Security center). No window-manager simulation: panes, sheets,
and session windows cover windowing needs; a toy desktop is explicitly
rejected.

## Notifications (Phase 16)
`store/notifications` + portal `NotificationStack`: kinds
info/success/warning/error (mapped to INFO/SUCCESS/WARNING/ACTION/
CRITICAL presentation), error summarization (no raw stack traces),
action buttons = deep-links, overflow grouping with expand + clear-all,
haptics per severity, sticky errors/warnings (no timeout), auto-dismiss
only for info/success. Ranked, actionable, never spam.
