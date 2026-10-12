# AetherOS Master 77 — Install / Launch / Uninstall Tests

## Executed on Windows dev host (2026-09-13)

1. Unpacked binary presence: `dist-packaged/win-unpacked/AetherOS.exe` EXISTS, size > 0. PASS.
2. PE metadata: Product=AetherOS, Company=AetherOS. PASS with note: FileVer/ProdVer=40.9.3
   (Electron runtime version, not app 1.0.0 — P2 metadata follow-up).
3. Process-spawn probe: `AetherOS.exe --version` spawned a live process surviving >25s; no
   `--version` stdout contract exists in main.cjs, so the flag launches the app instead of
   printing. Process killed afterwards; host clean. Result: UNVERIFIED (spawn proves the binary
   loads, not that the GUI initializes).
4. NSIS/MSI installer execution on dev host: NOT ATTEMPTED (would mutate the dev machine and
   requires elevation + clean snapshot). BLOCKED → clean VM.

## Blocked (clean VM required) — Windows

Fresh install (NSIS + MSI separately) → launch → first-run init → renderer load → backend
connection → IPC init → filesystem/config init → uninstall → reinstall → upgrade/downgrade/repair.
See BLOCKED_TESTS for exact VM commands. Elevation: NSIS config is perMachine=true → expect UAC;
document the prompt, do not bypass it.

## Blocked (Linux runner/VM required)

AppImage launch (`chmod +x …AppImage`, `./…AppImage --version` where supported, then GUI smoke),
`dpkg -i …deb` / `apt install ./….deb` install → menu entry → launch → upgrade → uninstall,
`dnf install ./….rpm` (or `rpm -i`) equivalents. Desktop smoke (GNOME + KDE): icon, name,
launch action, no duplicate entries, StartupWMClass match.

## Smoke-test scope (post-install, all platforms)

Launch → login/auth → home → agent → task → computer → browser → research → memory →
automation → approval → artifact → settings → quit → relaunch. Only capabilities that exist in
1.0.0; backend must be the real bundled backend (no mocks in smoke). Agent-backend path:
UI → IPC → backend → agent runtime → model/tool gateway → result → UI. NOT executed (no installed
instance) — UNVERIFIED.
