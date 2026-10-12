# AETHEROS MASTER 58361 — Changed Files

Repo is not a git checkout (`fatal: not a git repository`); list compiled by hand.

1. `apps/desktop/src/app/shell/app-shell.tsx`
   - Removed duplicate `components/command-palette/CommandPalette` import + mount.
     Canonical palette = `app/command-palette` mounted in `DesktopController` overlays.
     Added comment guarding against re-adding a second copy.
2. `apps/desktop/src/app/shell/left-sidebar.tsx`
   - Added `navIdForPathname()` (exact route match → `appViewForPath` view table;
     session routes map to Chat). Active highlight now derives from
     `location.pathname`; effect syncs `$activeNavSection` for overlay views.
     Removed `void location`.
3. `apps/desktop/src/app/shell/topbar.tsx`
   - Added workspace/profile pill (`$activeProfile`, Codicon `account`) → `/profiles`.
4. `apps/desktop/src/app/home/index.tsx`
   - Added `stashAndGo()`: stashes non-empty composer text via `stashSessionDraft`
     before navigating to `/files` (attach) or `/jarvis` (voice).
5. `apps/desktop/src/app/shell/context-panel.tsx` — DELETED (unimported permanent
   Context rail; zero importers confirmed by grep).
6. `apps/desktop/src/themes/context.tsx` — NO NET CHANGE (dark-default attempt
   reverted to preserve `profile-theme.test.ts` light-default contract).

Backend, Electron main/preload, IPC, signing/updater/release infra: untouched.
