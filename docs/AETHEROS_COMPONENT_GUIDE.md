# AetherOS Component Guide

Public UI components shipped or referenced by Master 63. Location:
`apps/desktop/src`. Each entry: purpose, props/state contract, a11y,
and what backs it (real state source or documented gap).

## Global

### `GlobalStatusIndicator` (`components/system-status/global-status.tsx`)

Subtle system status (§109). Derives `operational | degraded | offline`
from `$gatewayState` + `$healthStatus`: offline unless the gateway is
open/connected; `Connecting` when no health report has arrived (never
fake green); degraded count from non-running services. `role="status"`,
color + text (never color alone).

### `StopAllAgentsButton` (same file)

Global emergency stop (§56, §180). Disabled while offline with an honest
tooltip. Two-step confirm (Cancel / Stop all agents); drives
`emergencyStopAll` (`session.interrupt` per live session, `process.stop`,
`automation.stop_all`, `swarm.stop`); per-leg failures surface via
`notifyError` with leg detail. `role="alertdialog"` on confirm.

### `useGlobalStatus()` (same file)

Headless hook returning `{ level, label, degradedSystems }` for chrome
integration (titlebar/sidebar wiring is deferred — Home header is the
current consumer).

## Home (`app/home/index.tsx`)

Composed of `AttentionSection` (ranked approvals/running, Review/Open
Tasks actions), `ActiveWorkSection` (live `$sessions` ×
`$workingSessionIds` with Inspect → `sessionRoute(id)` and Stop →
`session.interrupt`), `SystemHealthBody` (CPU/memory/status from
`$systemStats`/`$healthStatus`, skeletons while unknown),
`ModelBody` (current model + session tokens + Switch Model), and
`AutomationsBody` (live `$cronJobs` counts + list, or an honest empty
state with Create Automation). Offline renders `Unavailable` per panel
plus a gateway-offline banner; actions disable with reasons.

## Navigation (`navigation/canonical.ts`)

`CANONICAL_NAV`: 5 groups, stable kebab-case ids, codicon names,
`primary | secondary | advanced` visibility, real `APP_ROUTES` paths.
`canonicalNavEntry(id)`, `primaryNavEntries()`. Tested:
route-resolution (no dead destinations), id uniqueness/shape, primary
surface ≤ 12.

## Primitives (`components/ui/`)

Button, IconButton patterns, Input, Textarea, Select, Combobox patterns,
Tabs, Dialog, Drawer (Sheet), Popover, Tooltip, Toast (notifications
store), Banner, Card, Panel, Table, List, Tree, Timeline, Graph, Badge,
Status (StatusDot), Progress, Command (palette), Inspector patterns,
SplitPane, Sidebar, Topbar, Breadcrumb, EmptyState, ErrorState, Skeleton,
SearchField, LogView, Codicon. Consume `--aether-*` tokens; expose typed
props + loading/disabled/error + keyboard + accessible names.

## Domain cards (to build on primitives, not beside them)

AgentCard, TaskCard, ApprovalCard, ArtifactCard, ResearchCard, MemoryCard,
ToolCard, ModelCard, SecurityCard — build these from Card + Badge +
StatusDot + `--aether-*` when rewiring computer/research/marketplace/
sync/devices/dashboard. Do not introduce competing card/badge/dialog
systems (§79, §152).

## Do / Don't

- Do: `Unavailable` / `Not configured` with cause + next action; skeletons
  for genuinely-loading state; confirm destructive scope before acting
  (affected counts, irreversibility stated).
- Don't: sample-data constants (`SAMPLE_*`), `setTimeout`/`Math.random`
  latency or progress, buttons without handlers, red for non-risk,
  color-only status, emoji status.
