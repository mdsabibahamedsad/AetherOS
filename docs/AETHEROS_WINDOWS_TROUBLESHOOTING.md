# AetherOS Windows Troubleshooting

- App won't start: check `%LOCALAPPDATA%\aetheros\logs`; verify bundled
  `py/` runtime present; stale lock files after crash can be removed once
  no `AetherOS.exe` process remains.
- Backend unhealthy: renderer diagnostics center shows backend/IPC/storage
  health; copy the redacted diagnostics bundle before reporting.
- Protocol links (`aetheros://...`) do nothing: re-run installer to repair
  registration; Windows Settings > Apps > Default apps shows AetherOS.
- `.aetheros` files open elsewhere: reinstall restores associations; files
  are validated before import — opening never executes code.
- SmartScreen warning: expected for unsigned builds; verify SHA256 from
  the release before running (see SIGNING).
- Notifications missing: Windows Settings > Notifications > AetherOS.
- Legacy state: `%LOCALAPPDATA%\hermes` (if present) is never touched
  automatically; see MIGRATION doc.
