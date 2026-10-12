# AetherOS UX Architecture Map (Master Prompt 2, Phases 1–4)

## Audit method
Repository-wide inspection (not filename assumptions): route table
(`app/routes.ts`, 60+ routes), nav stores, shell (`app-shell`, sidebar,
topbar, statusbar, titlebar), palette (729-line real implementation),
agents/tasks/automation/memory/swarm/mcp/a2a/security views, composer +
session/draft/queue stores, gateway/IPC bridge, prompt overlays,
notifications, keybinds, i18n, terminal panes, files views, settings
tree, onboarding, themes, brand modules from Master Prompt 1.

## Findings (duplicates / dead ends / inconsistencies)
- FIXED this pass: 7 dead nav destinations opening bogus sessions
  (prior pass); palette now covers tasks/models/approvals/stop.
- Canonical IA exists (`navigation/canonical.ts`): Workspace / Execute /
  System / Build / Manage — sidebar `NAV_SECTIONS` corrected to it.
- Duplicate systems (documented, not force-merged): two automation
  surfaces, two workspace surfaces, two icon libs, two theme layers,
  two component libs (legacy `design-system/components` vs `ui/`).
- No placeholder screens found in primary flows; known fabricated
  surfaces unchanged (computer, research, marketplace, sync, devices,
  dashboard) — tracked, not faked over.
- Terminology: canonical already (Agent/Task/Workspace/Automation);
  "Bot" only in platform-credential labels (correct domain usage);
  "Hermes" only in technical identifiers (preserved for compatibility).

## Information architecture: current → target
CURRENT: 60+ flat routes, curated groups in canonical nav, palette as
backstop. TARGET: same registry, tightened — one automation surface, one
workspace surface, one component lib; concept model fixed at
HOME / AGI / WORKSPACE / TASKS / AGENTS / FILES / APPS / AUTOMATIONS /
TERMINAL / SYSTEM. No new top-level routes added by this phase.

## Global navigation model
Sidebar (canonical sections, collapsible) + topbar (intent field →
palette, New Chat, notifications hub) + statusbar (system truth) +
titlebar tools + ⌘K palette + deep links (`sessionRoute`, section query
params). Every destination resolves in `APP_ROUTES` (test-enforced for
sidebar; palette items navigate to registered paths only).

## OS shell architecture
`AppShell`: left nav rail, top intent bar, main pane context, right
inspector/terminal rails, statusbar, overlay layer (agents/cron/profiles/
settings/command-center as modal cards), portal notification stack,
prompt overlays (sudo/secret modals; approvals inline). Persistent,
calm, reversible: Esc/back/close always defined; silence never equals
consent (dismissal maps to refusal).
