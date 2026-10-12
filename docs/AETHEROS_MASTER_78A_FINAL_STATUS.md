# AETHEROS MASTER 78A — Final Status

- Version: 1.0.0 | Arch: x64 | Platform: windows
- Source commit: `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1` (`main`), BEFORE == AFTER.
  Working tree DIRTY (1422 paths; mostly CRLF noise + real deltas incl. uncommitted validate-paths
  wiring). Build stamp records `[DIRTY]`. Artifacts are HEAD_BOUND with that caveat.
- Environment: Win11 Pro 10.0.26200 x64; Node 25.5.0; npm 11.8.0; venv Python 3.12.13;
  Electron 40.9.3 (packaged) / 40.10.6 (dev); electron-builder 26.8.1. See build-environment doc.

## WINDOWS NSIS — BUILD: PASS
ARTIFACT: dist-packaged/AetherOS-1.0.0-win-x64.exe | SIZE: 195891460
SHA256: b86b22f74f1afaa74bc28a304ff13e5bb0b0a6ad8cc42e969d138c34e67f9278
HEAD_BOUND: YES (dirty-tree caveat) | INSTALL: BLOCKED (no clean VM) | LAUNCH: N/A (installer not executed)
SMOKE: BLOCKED | UNINSTALL: BLOCKED

## WINDOWS MSI — BUILD: PASS (via documented short-root fix)
ARTIFACT: dist-packaged/AetherOS-1.0.0-win-x64.msi | SIZE: 203137784
SHA256: 1069fc6d26ee71810a9131f1383413d51252a3f3ae99c357f054dd1e2a5b031b
HEAD_BOUND: YES (verbatim inputs, same commit; move hash-verified) | INSTALL: BLOCKED | LAUNCH: N/A
SMOKE: BLOCKED | UNINSTALL: BLOCKED

## WINDOWS PORTABLE — BUILD: PASS
ARTIFACT: dist-packaged/AetherOS-1.0.0-win-x64-portable.exe | SIZE: 162205111
SHA256: 214d425537eb8eea43ca6c3f78f48edc1ccce758817e3fb9425e52ca143cfe3c
HEAD_BOUND: YES | LAUNCH: NOT EXECUTED (installer-execution class; win-unpacked equivalent probed instead)
SMOKE: BLOCKED

## WIN-UNPACKED — BUILD: PASS (staged by packaging)
LAUNCH: PASS (PID observed, alive+responding at 25s, 4 children) | IPC: NOT VERIFIED | BACKEND: NOT VERIFIED
UI: GUI_VISIBLE (HWND=1312250, title "Aetheros", Responding=True; --no-sandbox) — no in-app interaction performed.

## SIGNING — BLOCKED / UNSIGNED (Get-AuthenticodeSignature = NotSigned; no certs)
## SBOM — NOT GENERATED (no SBOM tooling run this phase; CI has the step)
## PROVENANCE — commit recorded + dirty flag + build stamp; no sigstore attestation (CI-only)
## UPDATE — NOT_IMPLEMENTED (no update feed created; latest.yml is builder auto-output only)
## P0 — none remaining (F-01/F-02/F-03 resolved; F-04 explained)
## P1 — dirty-tree HEAD caveat; Node 25 vs CI Node 22 drift; window title "Aetheros" vs product "AetherOS";
  CI SBOM action pinned to mutable tag; packaged Electron 40.9.3 vs dev 40.10.6.
## BLOCKED — SIGNING; clean-VM INSTALL/LAUNCH/SMOKE/UNINSTALL/REINSTALL for all three targets;
  in-app IPC/backend/settings smoke.
## CHANGED FILES (by this run) — docs only + dist-packaged artifacts + npm-install reconciliation:
  docs/AETHEROS_MASTER_78A_*.md/.txt/.json + EVIDENCE logs; deleted legacy apps/desktop/release/;
  package-lock.json may have shifted via npm install (working tree was already dirty).
## EVIDENCE — docs/AETHEROS_MASTER_78A_EVIDENCE/ (10 logs) + checksums txt + manifest json + inventory md.
