# AETHEROS MASTER 58362 — Changed Files (non-git tree; list by hand)

## Source fixes
1. `apps/desktop/src/app/tasks/index.tsx`
   - Action-task ids now use the store key (`action:${key}`) instead of
     `status.name` (duplicate-React-key collisions fixed).
   - `lastRun` passes the raw timestamp to `formatTimestamp` (was pre-formatted
     with `toLocaleString()`, which parsed back to `—`).
   - Active partition excludes settled ids via new exported `partitionActiveTasks`
     (`success` no longer double-counted in Active + Completed).
2. `apps/desktop/src/app/shell/statusbar-controls.tsx`
   - Both button renderers (menu trigger + action) now set `aria-label` (from
     string `label`, else tooltip `title`) and pass through `title`.
3. `apps/desktop/src/app/shell/left-sidebar.tsx`
   - Collapsed icon-only nav buttons get `aria-label={section.label}`.
   - `navIdForPathname` exported (regression-test seam); view table refactored
     from switch to a `Record` lookup (identical mapping, fewer lint warnings).
4. `apps/desktop/src/app/command-palette/index.tsx`
   - Focus restoration: opener element captured on open, re-focused on close
     (matches activity-drawer contract). Added missing `useRef` import.
5. `apps/desktop/src/app/mcp-manager/index.tsx`
   - Import now persists via `persistServers` (with rollback + honest toast);
     added `serversRef` live mirror for the async file-input callback.
   - Health filter gains the `unknown` option (previously all default servers
     vanished under any health filter).
6. `apps/desktop/src/app/models/index.tsx`
   - Removed dead `getEnvVars` query (fetched, never read).
   - Added loading (`role="status"`) and error (`role="alert"` + Retry) shells.
7. `apps/desktop/src/app/projects/index.tsx`
   - Both dead `Open Folder` buttons now open a real folder picker
     (`selectPaths({directories:true})`), set the workspace cwd, toast, and
     navigate to chat (next message creates the session there).
8. `apps/desktop/src/app/resource-manager/index.tsx` + `store/resource-manager.ts`
   - Deleted the `Math.random()` poller and hardcoded processes/disks/network.
   - Metrics mirror real `$systemStats` (CPU/memory/GPU) while Live is on;
     threshold alerts fire on real values; paused/waiting states announced.
   - Processes/disks/network tabs render honest "not reported" empty states.
   - New `clearAlerts()`; Trash button actually clears (was toast-only) and has
     `aria-label="Clear alerts"`.
   - Description corrected to "Live system metrics from the desktop backend".
9. `apps/desktop/src/app/automation/canvas/workflow-canvas.tsx`
   - Removed `onClick={() => {}}` no-op (panning/selection handled by mouse handlers).
10. Jarvis Mode `aria-label` additions (icon-only buttons):
    - `command-bar/command-bar.tsx`: attach, send.
    - `command-center/command-input.tsx`: send.
    - `mission-nav/mission-nav.tsx`: nav items (label), collapse toggle.
    - `panels/left-panel.tsx`, `panels/right-panel.tsx`: panel toggles.
    - `panels/projects-view.tsx`: per-project open (`Open project ${name}`).
    - `automation/automation-dashboard.tsx`: refresh.
    - `agents/agent-manager.tsx`: remove (`Remove ${name}`).
    - `notifications/notification-center.tsx`: toast dismiss.

## New regression tests
- `app/shell/left-sidebar.test.ts` (5 tests: exact routes, session→chat,
  non-nav mapping, overlay null, overlay-with-entry highlight).
- `app/tasks/tasks-partition.test.ts` (2 tests: settled exclusion, empty settled).
- `store/resource-manager.test.ts` (2 tests: `clearAlerts`, `updateMetric` history).

## Untouched (by policy)
Backend, Electron main/preload/IPC, signing/updater/release, theme default
(light contract preserved), routes, dependencies.
