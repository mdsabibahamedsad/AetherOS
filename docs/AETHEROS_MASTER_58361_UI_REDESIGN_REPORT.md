# AETHEROS MASTER 58361 — UI Redesign Report (2026-10-12)

## What this was
A targeted implementation pass on the existing Electron desktop app
(`aetheros/apps/desktop/src`). The audit found the app already substantially
conforms to the Master 58361 direction (grouped sidebar, command-center Home,
optional Activity drawer, functional palette, Jarvis exit + live voice states,
consolidated token system). Work focused on real gaps, not a rewrite.

## Implemented
1. **Removed duplicate command palette** (`app-shell.tsx`) — one canonical palette
   (`app/command-palette`, routes/sessions/settings/themes) instead of two stacked
   instances on the same open atom.
2. **Route-driven sidebar highlight** (`left-sidebar.tsx`) — active state follows
   `location.pathname` (refresh, deep links, back/forward, `/:sessionId` → Chat).
3. **Header workspace selector** (`topbar.tsx`) — profile pill → `/profiles`.
4. **Home draft preservation** (`home/index.tsx`) — Attach/Voice stash composer text
   via `stashSessionDraft` before navigating.
5. **Deleted dead permanent Context rail** (`app/shell/context-panel.tsx`,
   unimported) — no permanent context/filesystem rail on Home; file browser stays
   chat-scoped and closed by default.
6. Evidence bundle + Fix Ledger continuation (this report + `docs/AETHEROS_MASTER_58361_EVIDENCE/`).

## Deliberately not changed
- **Light default kept.** A dark-default switch broke the pinned
  `profile-theme.test.ts` light-fallback contract; reverted. Dark mode fully
  supported (Shift+X, palette). Needs a maintainer product decision, not a drive-by.
- No backend, Electron main/preload/IPC, signing, updater, or release changes.
- No routes added/removed; no features replaced with mocks; no new dependencies.

## Verification (executed, this session)
- `npm run typecheck`: CLEAN (twice).
- `npx vitest run`: **134 files / 891 tests PASS**, 0 fail.
- ESLint on touched files: remaining errors all pre-existing on untouched lines;
  added lines comply. Repo-wide lint debt predates this pass.
- Grep-verified: zero references to deleted panel; single desktop palette mount
  (+ Jarvis's own scoped palette, by design).
- NOT run (stated, not claimed): packaged-app validation, Python backend suite
  (untouched), screenshots, manual resize/screen-reader pass.

## Incomplete / blockers
- Packaged-app validation requires a build/install environment not used here.
- Pre-existing ESLint debt across the desktop tree.
- Live-gateway E2E (voice capture, Jarvis runs) still gateway-dependent per prior
  ledger entries; not re-verified.

## Final status
`AETHEROS_UI_REDESIGN_PARTIAL`
