# AetherOS Master 63 — Desktop UX Audit

Date: 2026-09-10 (UTC). Scope: `apps/desktop/src` + `apps/desktop/electron`.
Method: direct file reads plus a targeted sub-agent sweep for fabricated/
decorative UI. Every verdict cites file + line evidence. No claim below is
based on screenshots or reproduction prose — only on current source.

## Shell, transport, and state (functional)

- Renderer entry `src/main.tsx`; routes `src/app/routes.ts` (60+ registered
  routes, `APP_ROUTES` table, overlay-view set, deep-link helpers
  `sessionRoute` / `routeSessionId` / `appViewForPath`).
- IPC boundary `electron/preload.cjs`: typed `invoke` surface only
  (`aetheros:api`, terminal, settings, updates, logs, …). No arbitrary
  renderer→IPC channel. `electron/main.cjs` + `hardening.cjs` own isolation.
- Gateway access: `src/aetheros.ts` (`AetherosGateway`, `listSessions`,
  `listAllProfileSessions`, config/env/skills/tools/model/cron/profile
  helpers) over `window.aetherosDesktop.api`; live sockets in
  `src/store/gateway.ts` (primary + per-profile secondaries) and
  `src/store/session.ts` (`$gatewayState`, `$sessions`, `$workingSessionIds`).
- Command palette `src/app/command-palette/index.tsx`: real — server-backed
  sessions/config/MCP/archived search via react-query, real navigation
  actions, theme/mode pages. Gap at audit time: no agent/task/approval/model
  actions and no global stop (addressed next phase — palette still never
  fakes: every item executes).
- Emergency stop `src/lib/emergency-stop.ts`: REAL — `session.active_list` →
  per-session `session.interrupt`, plus `process.stop`,
  `automation.stop_all`, `swarm.stop`, per-leg reporting. (Had two
  pre-existing `curly` lint errors, fixed in Master 63.)

## Design system (real, but naming was fragmented)

- Tokens exist and are complete: `src/design-system/tokens/` (color, spacing,
  typography, radius, elevation, motion, breakpoints, zIndex, opacity,
  density) + generated `css-variables.css` with light/dark/density/reduced-
  motion. Primitives in `src/components/ui/` (~40 components).
- Gap fixed in Master 63: no canonical `--aether-*` public naming (§4 of the
  brief). Added as aliases onto the mode-aware `--color-*` store so
  light/dark follow automatically.

## Per-area verdicts

| Area | Verdict | Evidence |
|---|---|---|
| Home (`src/app/home/index.tsx`) | Was **partially fake** — fixed | `ActiveTasksCard` hardcoded `0 running`; `ActivitySection` placeholder text; `AutomationsSection` static copy, never read `$cronJobs`. Rewritten: live atoms + Inspect/Stop/Review actions + offline states |
| Agents (`src/app/agents/`) | Functional | Live `$activeSessionId` + `$subagentsBySession` tree, honest empty state |
| Tasks (`src/app/tasks/`) | Functional | Merged `$cronJobs` + `$desktopActionTasks`, honest empty state |
| Computer (`src/app/computer-usage/ComputerUseView.tsx`) | **Partially fake — NOT fixed this phase** | Hardcoded `securityIndicators`; `actionTimeline` never populated; header Pause/Stop without `onClick`; `// In a full impl, this would IPC`; screen-preview placeholder. Documented as known issue / blocker |
| Browser (`src/app/browser-workspace/`) | Functional | Real `<webview partition="persist:aetheros-browser">` + tab store actions |
| Research (`src/app/knowledge/`) | **Local-only mock — NOT fixed this phase** | Zero gateway/IPC imports; `mockResults` substring filter with synthetic scores; hardcoded agent names in `handleGenerate`. Documented as known issue |
| Memory (`src/app/memory/`) | Functional | All reads via `requestGateway` (`memorySearch/Timeline/Project/Health/Explain/Forget`); honest unavailable state |
| Automation center (`src/app/automation-center/`) | Functional | `automationSearch/Runs/Health/Preview/Run/Enable/Disable/Delete/Build/StopAll` via gateway; honest unavailable state |
| Swarm (`src/app/swarm-center/`) | Functional | `swarmStart/Status/Events/Trace/Stop/Approve` via gateway; honest unavailable state |
| Models (`src/app/models/` → provider/model managers) | Functional | `getEnvVars` / `getGlobalModelOptions` / OAuth; hydrates `provider-manager` + session atoms |
| MCP manager (`src/app/mcp-manager/`) | Was **fake** — fixed | `SAMPLE_SERVERS` (Filesystem/GitHub/Postgres/… with `2026-07-21` timestamps); `setTimeout(1500)` + `Math.random()` latency. Rewired to `mcp_servers` in live gateway config; health `unknown` until a real probe exists; add/toggle/remove persist via `/api/config` with rollback on failure |
| Agent network / A2A (`src/app/agent-network/`) | Functional | `networkList/Tasks/Discover/Verify/Trust/Block/Revoke/Connect` via gateway; untrusted-until-verified copy |
| Marketplace (`src/app/marketplace/`) | **Fake — NOT fixed this phase** | `SAMPLE_PLUGINS` + fake `setTimeout` install progress. Real backend exists (`/api/plugins/marketplace/*` in `aetheros_cli/web_server.py`); wiring is deferred work. Documented as blocker |
| Agent marketplace (`src/app/agent-marketplace/`) | Functional | `marketSearch/Agent/Service/Transactions/Budget/Policy` via gateway |
| Artifacts (`src/app/artifacts/`) | Functional | Scans 30 sessions via `listAllProfileSessions` + `getSessionMessages`; real `openExternal` |
| Dashboard activity (`src/app/dashboard/`) | **Partially fake — NOT fixed this phase** | `simulateDashboardData()` hardcoded CPU/mem/disk; two buttons without `onClick`. Documented as known issue |
| Security center (`src/app/security-center/`) | Functional shell over local stores | Integrity check reads live gateway + logs; never claims Secure without checks; approvals tab reads `$allApprovalRequests` (real parked gateway prompts) |
| Devices (`src/app/devices/` + `src/store/devices.ts`) | **Fake — NOT fixed this phase** | Single hardcoded `CURRENT_DEVICE` (`192.168.1.100`); `refreshDevices()` no-op; non-reactive read. Documented as known issue |
| Sync (`src/app/sync-dashboard/` + `src/store/sync.ts`) | **Fake — NOT fixed this phase** | Local atoms; `setTimeout(2000)` + `Math.random()` fake sync success. Documented as blocker-adjacent known issue |

## Navigation / IA finding

60+ routes with no curated product IA: every internal subsystem was a
peer of Home/Tasks/Security. Fixed with `src/navigation/canonical.ts`:
5 groups (Workspace / Execute / System / Build / Manage), primary ≤ 12,
every entry resolves against `APP_ROUTES` (test-enforced).

## Accessibility / motion / performance baseline

- Tokens already carry `prefers-reduced-motion` zeroing, density levels,
  focus-ring tokens, z-index scale. New components use `role="status"` /
  `role="alertdialog"`, visible focus, keyboard-operable native buttons.
- No new render loops introduced; Home reads existing atoms (no polling);
  MCP loads config once per mount. No performance measurements were taken
  this phase — see certification for the honest verdict.
