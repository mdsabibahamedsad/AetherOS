# AETHEROS MASTER 78A — Build Environment

Measured: 2026-09-15 (UTC), on the build host itself. No values assumed.

| Component | Value | Source |
|---|---|---|
| Windows | Windows 11 Pro, 10.0.26200, x64-based PC | `systeminfo` |
| Architecture | x64 | `systeminfo` System Type |
| Node | v25.5.0 | `node --version` |
| npm | 11.8.0 | `npm --version` |
| Repo Python (`.venv`) | Python 3.12.13 | `.venv\Scripts\python.exe --version` (supported: bundle script allows 3.11–3.13) |
| System `python`/`python3` shims | BROKEN (Microsoft Store stub; `Python315\python.exe` missing) | `py --version` error text |
| `py` launcher payloads | 3.15 (default), 3.11, CPython 3.14.3, 3.12.13, 3.11.15 | `py -0` |
| `uv` | NOT on PATH | `uv --version` failed |
| Electron (installed) | 40.10.6 | `require('electron/package.json').version` |
| electron-builder (installed) | 26.8.1 | `require('electron-builder/package.json').version` |
| Declared `build.electronVersion` | 40.9.3 | `apps/desktop/package.json` line 167 — minor drift vs installed 40.10.6 |
| electron-builder tool cache | EMPTY (`%LOCALAPPDATA%\electron-builder\Cache` has no entries) | dir listing — NSIS/WiX binaries must download on first `--win` run |
| WiX / `light.exe` on PATH | ABSENT (expected; electron-builder vendors it) | `Get-Command` failed |
| Repo `.venv` size | ~287.6 MB | recursive measure (bundle-copy estimate) |
| Renderer `dist/` | ABSENT (not built) | dir listing |
| Desktop `build/` staging | ABSENT (bundled-python not staged) | dir listing |
| Root `node_modules` (workspace install) | PRESENT (`electron-builder.cmd`, `electron/dist/electron.exe`) | `Test-Path` True/True |
| Source commit | `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1` (`main`) | `git rev-parse HEAD` |
| Working tree | DIRTY (1422 modified paths) | `git diff --name-only` |
| Signing credentials | NONE in repo/env | no cert config; `SIGNING = BLOCKED / UNSIGNED` |
| Clean VM | NONE available on this host | `INSTALL = BLOCKED` (all installer-execution tests) |

Engine constraint: `apps/desktop` engines = `^20.19.0 || >=22.12.0`; host Node 25.5.0 satisfies the
`>=22.12.0` range. CI pins Node 22 — local/CI drift is recorded as a P1 caveat, not a blocker.
