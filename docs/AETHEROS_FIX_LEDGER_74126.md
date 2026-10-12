# Fix Ledger Entry — 2026-09-19 — MASTER PROMPT 74126

## Issues

1. MissionControl status bar permanently showed BACKEND running / GATEWAY
   disconnected: `$jarvisSystemStatus.gateway` was initialized to
   'disconnected' and no poller or subscriber ever wrote it, so the UI
   rendered a stale default regardless of the real socket state.
2. Jarvis commands executed a local simulation (`executePipeline` in
   `lib/jarvis/core/ai-core.ts`): random intent confidence, fixed delays,
   fake per-step progress, fabricated token counts and runtimes — never
   touching the gateway. `backend-bridge.ts` pointed at a dead
   `http://127.0.0.1:9789/api/jarvis/*` endpoint, and `background-services.ts`
   polled the same dead port.
3. MissionControl home (`orb` view) rendered only a decorative AiOrb +
   StatusRing — a giant empty center with no actions, no active-work state,
   no recent activity.
4. `aetheros:system:health` (main) reported only child-process aliveness,
   never verifying the backend HTTP handshake.
5. Intent confidence used Math.random, making identical inputs score
   differently on every call.

## Root causes

- Gateway state lived in `$gatewayState` (socket: idle/connecting/open/
  closed/error, owned by use-gateway-boot) while Jarvis status lived in a
  disconnected `$jarvisSystemStatus` atom with no bridge between them.
- `executePipeline` was a self-contained mock: no `activeGateway()` import,
  no `session.create`/`prompt.submit`, no event subscription.
- `HomeDashboard` in `mission-control.tsx` was orb-only by construction.
- Health handler never awaited `connectionPromise` nor fetched `/api/status`.

## Fixes

- `store/jarvis-mode.ts`: `JarvisGatewayState` lifecycle
  (starting/connecting/connected/degraded/disconnected/reconnecting/error/
  stopped), `$jarvisGatewayDetail`
  (latencyMs/lastHeartbeat/version/capabilities/error/reconnectAttempt, no
  credentials), `mapSocketToGatewayState()`, `$jarvisExecution` state machine
  (IDLE/SUBMITTED/PARSING/PLANNING/AWAITING_PERMISSION/EXECUTING/STREAMING/
  COMPLETED + FAILED/CANCELLED/TIMEOUT/UNAVAILABLE), `$jarvisCommandLog`
  real history. Intent confidence deterministic.
- `lib/jarvis/gateway-sync.ts` (new): subscribes to `$gatewayState`/
  `$connection`/`$healthStatus`, mirrors lifecycle into
  `$jarvisSystemStatus`; started by MissionControl + JarvisLayout, torn down
  on unmount (navigation never destroys sessions/sockets).
- `lib/jarvis/core/ai-core.ts`: real pipeline — local intent analysis, then
  `activeGateway()` guard (UNAVAILABLE + GatewayUnavailableError when not
  open), `session.create` + `prompt.submit`, streaming via `message.delta`/
  `tool.start`/`tool.complete`/`message.complete` with `session.info
  running:false` fallback, 180s timeout, Esc cancellation, real
  duration/tools/result persisted to `$jarvisCommandLog`; no delays, no
  random tokens.
- `mission-control.tsx`: functional HomeDashboard — compact orb header with
  live gateway/backend/model line, 8 quick actions routing to real
  MissionViews, Active Work from live `$sessions`/`$workingSessionIds`,
  Recent Sessions + Recent Commands from real atoms, GatewayBanner +
  ExecutionBanner with honest states and Cancel; `handleCommand` uses the
  real pipeline with honest gateway-unavailable messaging; SystemStatusPoller
  no longer fights the sync (15s model-only refresh).
- `electron/main.cjs` `aetheros:system:health`: async, now verifies process
  alive + cached backend `/api/status` handshake
  (latencyMs/version/reachable), structured services
  (python-runtime/backend-http/backend-handshake), overall
  healthy/degraded/unhealthy; gateway socket explicitly marked
  renderer-owned.
- `lib/background-services.ts`: removed dead `:9789` fetch + local-engine
  fallback init; backend state now derived from real health IPC.
- IPC audit: preload exposes only narrow `aetherosDesktop` methods (no raw
  ipcRenderer); `aetheros:api` validates paths via
  `validateApiRequestPath`; no `catch { return {success:true} }` in
  production paths — errors propagate to the renderer retry/re-auth logic.

## Files

- apps/desktop/src/store/jarvis-mode.ts
- apps/desktop/src/store/jarvis-lifecycle.test.ts (new)
- apps/desktop/src/lib/jarvis/gateway-sync.ts (new)
- apps/desktop/src/lib/jarvis/core/ai-core.ts
- apps/desktop/src/lib/jarvis/core/ai-core.test.ts (new)
- apps/desktop/src/lib/background-services.ts
- apps/desktop/src/app/jarvis-mode/layout/mission-control.tsx
- apps/desktop/src/app/jarvis-mode/layout/jarvis-layout.tsx
- apps/desktop/electron/main.cjs

## Verification

- `npm run typecheck` (tsc --noEmit): clean.
- `npx eslint` on all touched files: 0 errors.
- vitest: gateway-ws-url + gateway-events + gateway-connecting-overlay 18/18
  PASS; home + use-gateway-boot 7/7 PASS; new jarvis-lifecycle 5/5 PASS; new
  ai-core 3/3 PASS; session + composer + lib/jarvis + home 34/34 PASS.
- `node --test electron/backend-probes + gateway-ws-probe +
  connection-config`: 60/60 PASS.
- `npm run build` (tsc -b + vite build + assert-dist-built): PASS.
- Installed-app runtime test (Gateway/Backend/Home/Jarvis/sidebar/restart/
  failure-recovery): NOT TESTED in this session — requires
  `npx electron-builder --win --x64 --publish never`, install, and live
  launch.

## Status

CLOSED for source-level root causes (GATEWAY_DISCONNECTED sync,
JARVIS_COMMAND_PIPELINE real execution, HOME_DASHBOARD_UX functional
workspace, IPC audit, health handshake). Runtime certification remains open
pending installed-app test.
