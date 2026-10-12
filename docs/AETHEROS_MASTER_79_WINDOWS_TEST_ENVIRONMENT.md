# AETHEROS MASTER 79 — Windows Test Environment

> Master 79 clean-environment requirement (§7–§9): a genuinely clean Windows
> environment (full VM preferred, Windows Sandbox acceptable with explicit
> documentation). This file records the ACTUAL environment available for
> Master 79 execution. No clean VM or Sandbox was available: all
> clean-environment install/launch/smoke/uninstall/reinstall tests are
> BLOCKED (see `AETHEROS_MASTER_79_BLOCKED_TESTS.md`). Host-side static
> verification (artifact identity, signatures, validators, unit regression)
> was executed instead and is recorded honestly.

## Actual HEAD

- `git rev-parse HEAD` → `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1`
- NOTE: differs by one hex char from the commit printed in the Master 79
  prompt (`...c2bfb159...` vs actual `...c2beb159...`). The prompt value is
  treated as a transcription error; all artifact identity claims use the
  ACTUAL HEAD above.
- `install-stamp.json` commit in `win-unpacked/resources/` matches ACTUAL
  HEAD (`2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1`, `dirty=true`,
  `builtAt=2026-09-15T03:17:22.339Z`, `source=local`). HEAD binding: YES,
  with dirty-tree caveat (unchanged from Master 78A).
- Tree state: DIRTY. `git status --short` reports ~2755 changed paths
  (1422 files changed per `git diff --stat`). No destructive git commands
  were run (§96 respected).

## Host (where host-side verification ran — NOT a clean environment)

| Field | Actual |
|---|---|
| `systeminfo` OS Name | Microsoft Windows 11 Pro |
| `systeminfo` OS Build | 10.0.26200 Build 26200 |
| `Get-ComputerInfo` product | Windows 10 Pro, version 2009, HAL 10.0.26100.1 (reporting API disagrees with systeminfo; both recorded verbatim) |
| Architecture | x64-based PC |
| Administrator | False (non-elevated shell) |
| Windows Sandbox (`System32\WindowsSandbox.exe`) | NOT PRESENT (`Test-Path` → False) |
| Hyper-V / VM platform | No snapshot-capable VM available in this session |
| Snapshot identifier | N/A — no VM |
| Network | ENABLED (required for tool downloads already cached; no untrusted browsing) |
| Test user | Dedicated test account NOT provisioned — no clean-user testing performed (BLOCKED) |
| Date/time | 2026-09-15T10:12+06:00 (UTC+6, Asia/Almaty wall clock; process TZ UTC per test wrapper) |
| Display resolution / DPI / GPU | NOT RECORDED — no GUI test executed, no values fabricated |
| Dev-machine contamination (§9/§45) | PRESENT — this host contains the `D:\hermes-agent-main\aetheros` source checkout, Node v25.5.0 + npm 11.8.0, repo venv Python 3.12.13. It is therefore explicitly NOT a clean environment and CANNOT certify clean install/uninstall/reinstall (§95). |

## Clean-environment verdict

- Full Windows 11 VM with snapshot/restore: UNAVAILABLE → BLOCKED.
- Windows Sandbox: executable absent, feature query requires elevation
  (unavailable, non-admin shell) → BLOCKED.
- Clean snapshot identifier: NONE.
- Consequence per §94: final certification MUST be
  `AETHEROS_WINDOWS_DESKTOP_BLOCKED` regardless of host-side results.

## Registry / install state on host (pre-test)

- `HKCU/HKLM ...\Uninstall\*` entries matching `Aether`: NONE (no AetherOS
  installed on host).
- Windows Defender threat detections query: no output / not elevated; no
  block/quarantine event fabricated. Defender behavior in a clean VM is
  UNVERIFIED.

## Toolchain versions observed on host

- Node: v25.5.0 | npm: 11.8.0 (local)
- CI Node (`.github/workflows/desktop-release.yml`, `setup-node`): 22
- Python: system `python` not on PATH; repo `.venv` Python 3.12.13
- electron-builder: `^26.8.1` (apps/desktop/package.json devDependencies)
- Electron dev pin: `^40.10.6`; packaged pin (`build.electronVersion`): `40.9.3`
