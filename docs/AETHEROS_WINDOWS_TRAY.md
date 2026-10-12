# AetherOS Windows Tray

Nine actions (open, pause/resume automations, stop agents, approvals,
agent state, security, update check, quit) on typed `aetheros:*`
channels — the same command layer as the UI. Menu built purely from
live backend state (`electron/tray-menu.cjs`, 6 tests): backend-down
disables backend actions; pause/resume mutually exclusive; stop-all is
confirm-gated; tooltip/badges show real counts or nothing. Host wiring
(`electron/tray.cjs`): click-to-show, 15s refresh, cleanup on destroy.
Live tray: UNVERIFIED (no Electron binary here). Shell-restart/multi-
monitor/DPI behavior: UNVERIFIED. No fake status — unknown state renders
as "backend unavailable".
