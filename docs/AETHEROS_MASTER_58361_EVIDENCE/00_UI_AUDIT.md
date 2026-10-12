# AETHEROS MASTER 58361 — UI Audit (evidence, 2026-10-12)

Scope: `aetheros/apps/desktop/src` (Electron + React + nanostores renderer).
Method: direct file inspection (entry, routes, shell, stores, theme, IPC).

## Entry / shell
- `src/main.tsx` → `QueryClient + I18n + Theme + HashRouter` → `app/desktop-controller.tsx`.
- `app/shell/app-shell.tsx`: `TitlebarControls + TopBar + LeftSidebar + PaneShell + StatusbarControls`,
  plus `ActivityDrawer`, `KeybindPanel`, `NotificationStack`, `CommandPalette` mount (see fix F-1).
- `app/desktop-controller.tsx`: owns `Routes`, chat session state, gateway boot, overlays
  (settings/command-center/agents/cron/profiles as overlay views), panes
  (chat-sidebar, file-browser, preview, terminal).

## Findings (before this pass)
1. **F-1 DUPLICATE palette mount (fixed).** `$commandPaletteOpen` was subscribed by TWO
   palettes: `components/command-palette/CommandPalette.tsx` (mounted in `AppShell`) and
   `app/command-palette/index.tsx` (mounted in `DesktopController` overlays). Opening the
   palette rendered both. Canonical = `app/command-palette` (routes, sessions, settings
   fields, themes, nested pages). Removed the `AppShell` mount.
2. **F-2 Sidebar highlight not route-driven (fixed).** `LeftSidebar` read only the
   `$activeNavSection` atom set on click (`void location`). Refresh, deep link,
   back/forward, and session routes left the highlight stale. Now derived from
   `location.pathname` via `appViewForPath` + exact-route match, atom synced by effect.
3. **F-3 No workspace selector in header (fixed).** `TopBar` had status popover, model
   pill, new-chat, notifications, activity — but no workspace/profile affordance despite
   first-class profile support (`store/profile.ts`). Added profile pill → `/profiles`.
4. **F-4 Home draft loss (fixed).** `HomeView/IntentSection` kept composer text in local
   state; Attach-Files / Voice buttons navigated away and dropped it. Now stashes via
   `stashSessionDraft` before navigating.
5. **F-5 Dead permanent Context panel (fixed).** `app/shell/context-panel.tsx` (permanent
   `w-60` "Context" rail) was unimported dead code. Verified zero importers via grep,
   deleted. No permanent context/filesystem rail remains on Home. (The file-browser pane
   in `DesktopController` is `defaultOpen={false}`, `disabled={!chatOpen}` — chat-scoped.)
6. **F-6 Dark-default proposal REJECTED.** Changing `normalizeMode` fallback to `dark`
   broke the behavior-contract test `profile-theme.test.ts` (`fallback: 'light'`).
   Reverted; light remains the default, dark fully supported (Shift+X, palette).
   Recorded as intentional-design deviation, not a regression.

## Already-conforming (verified, not reworked)
- Sidebar groups (`store/navigation.ts`): Workspace / AI / Work / System / More — matches §5.
- Home (`app/home/index.tsx`): single wordmark, greeting, canonical composer path
  (`stashSessionDraft` → `/` chat runtime), quick actions with real routes, live
  Active Work / Recent / health / model / automations sections, honest empty states.
- `ActivityDrawer`: closed by default (`atom(false)`), focus trap + Esc + focus restore.
- Jarvis exit: `jarvis-status-bar.tsx` "Exit Jarvis" → `/home`, tasks preserved
  (no teardown); Esc cancels pipeline/voice only; voice pills render only on live
  `$voiceState` (`LISTENING`/`SPEAKING`).
- Command palette (`app/command-palette`): real routes/sessions/settings-fields/themes.
- Design tokens: `design-system/tokens/*` + `css-variables.css` + `--aether-*` aliases;
  single Codicon library; `BRAND_WORDMARK` single source.
- Reduced motion: `@media (prefers-reduced-motion: reduce)` zeroes durations/animations.
- Electron security: no change to main/preload/IPC; renderer uses narrow
  `window.aetherosDesktop` bridge only.
