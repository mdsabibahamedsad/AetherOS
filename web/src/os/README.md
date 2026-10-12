# AetherOS Shell — Web Dashboard Binding

The web dashboard is an AetherOS operating-environment surface, not an admin panel.
This directory (`src/os/`) holds the OS chrome; canonical product IA lives in the
desktop app (`apps/desktop/src/navigation/canonical.ts`); this package binds it to
dashboard routes.

## Information architecture

`ia.ts` classifies every built-in route into one OS domain:

HOME → `/home` · SEARCH (overlay, Ctrl+K) · LAUNCHER (`/launcher` + overlay) ·
WORKSPACES (`/workspaces`, profile-anchored) · AGI (`/chat`, `/sessions`, `/tasks`,
`/agent-hub`, `/memory-viewer`, `/intelligence`) · APPLICATIONS (`/files`, `/live`,
`/cron`, `/skills`) · SYSTEM (`/system`, notifications, `/security`, `/sync`,
`/models`, `/config`) · DEVELOPER (`/marketplace*`) · ACCOUNT (`/profiles`, `/pairing`)

Existing routes are preserved — `ia.ts` only classifies them. Deep links:
`osLink.task/agent/file/session/setting/workspace`.

## Shell pieces

- `store.ts` — zustand: overlay, boot/onboard/lock, offline, active workspace
  (persisted to localStorage; workspace mirrors the backend profile scope).
- `chrome.tsx` — `OsTopBar` (wolf, workspace context, search entry, launcher,
  live task/agent counts polled from the orchestrator API, notifications/quick
  settings/system) + `OsDrawers` (real data only: failing tasks, sync state).
- `UniversalSearch.tsx` — Ctrl+K fuzzy palette over apps + actions (`lib/fuzzy`).
- `Launcher.tsx` — application launcher overlay bound to `/launcher`.
- `WolfMark.tsx` — the ONE primary brand mark. No competing logos.
- `states.tsx` — shared Empty / Loading / Error / Offline / Permission states.
- `lifecycle.tsx` — `BootScreen`, `OnboardingFlow` (progressive disclosure),
  `LockScreen` (privacy-safe; auth stays backend-enforced).

## Pages

- `pages/HomePage.tsx` — greeting, workspace context, active tasks (orchestrator
  plans), agents, recent sessions/files, system links. Honest empty states.
- `pages/WorkspacesPage.tsx` — profile list from `/api/profiles`, switch/clear.
- `pages/LauncherPage.tsx` — deep-link that opens the launcher overlay.
- `TaskTimeline.tsx` — structured execution timeline + verification framing for
  `TaskDetailPage` ("Timeline" tab), derived strictly from real plan + event
  records. Backend contract: `agent/operating_layer.py`
  (intent → plan → guard → verify → result; completion requires passing checks).

## Polish layer (Prompt 9)

- `os.css` — single token binding for the OS chrome (`--os-surface/border/
  text/accent/radius/z`, motion durations, focus rings). Overlays, states,
  buttons, and pages consume theme CSS variables with dark-first fallbacks,
  so light/inverted dashboard themes propagate. Includes
  `prefers-reduced-motion`, coarse-pointer (44px targets), and
  `forced-colors` support.
- `overlay.tsx` — `useOverlayBehavior`: Escape closes, background scroll
  locks, focus is trapped while open and returned to the invoker on close.
  Used by search, launcher, and all drawers. No keyboard traps.

## Rules

- Real data only. No fabricated tasks, agents, activity, or telemetry.
- `HERMES_*` identifiers (`window.__HERMES_BASE_PATH__`, `HERMES_BASE_PATH`) are
  technical compatibility shims — never rename them.
- No user-facing "Hermes" branding remains in this package (verified).
- Favicon is the wolf (`public/wolf-favicon.svg`); `.ico` kept as fallback.
