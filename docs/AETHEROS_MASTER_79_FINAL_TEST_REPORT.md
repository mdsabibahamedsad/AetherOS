# AETHEROS MASTER 79 — Final Test Report

HEAD: `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1` (DIRTY, ~2755 paths).
Prompt-quoted commit `...c2bfb159...` differs by one hex char; actual HEAD governs.
Environment: dev host, NOT clean (source checkout + Node + venv present);
clean VM/Sandbox UNAVAILABLE. All clean-env operational tests BLOCKED.

## Artifact verification (W79-001) — PASSED (host)

All three Windows artifacts byte-match Master 78A baselines: NSIS
195891460 / b86b22f7…f9278; MSI 203137784 / 1069fc6d…5b031b; portable
162205111 / 214d4255…43cfe3c. install-stamp commit == HEAD (dirty, local).

## NSIS (W79-002–010) — BLOCKED

No install/launch/smoke/IPC/backend/Settings/shutdown/uninstall/reinstall
executed (no VM). Static only: perMachine=true → UAC EXPECTED;
deleteAppDataOnUninstall=false → user-data preservation is policy.

## MSI (W79-011–020) — BLOCKED

No msiexec operations executed. Static: ProductCode
`{77035F50-600E-49B1-851F-6E004FDBC134}` (read-only COM query). Silent-install
contract applicability unverified → W79-020 BLOCKED (not NOT_APPLICABLE by fiat).

## Portable (W79-021–024) — BLOCKED

No launch executed. VersionInfo: ProductName=AetherOS, 1.0.0.

## IPC / Backend / GUI / Settings (live) — BLOCKED

No renderer, no IPC channel, no backend health check executed live.
INSTALLER_EXIT_0 ≠ APPLICATION_WORKS is respected: nothing is inferred.

## Runtime (§44–§56)

- Packaged-runtime-only, localhost-dependency, path-independence, user-profile,
  UAC-behavior, process-tree, orphan, crash, event-log checks: all BLOCKED (no VM).
- Long-path (W79-028): path-length guard FAILS (6 absolute paths >240,
  elevenlabs/mistralai, checkout-prefix-inflated); MSI built OK so WiX staging
  coped; runtime import UNVERIFIED → P1.
- Window title (§61): main.cjs titles correct ('AetherOS'); `index.html:11`
  `<title>Aetheros</title>` is the likely renderer-title defect → P1 cosmetic,
  NOT fixed here (no-rebuild rule).

## Security (§57–§60, §70)

- Authenticode (W79-030): NotSigned ×3, recorded honestly; no trust claimed.
- SmartScreen: UNVERIFIED / EXPECTED WARNING. Defender on clean VM: UNVERIFIED.
- Static hardening: contextIsolation=true, nodeIntegration=false, sandbox=true
  (main.cjs + hardening.cjs). Live security regression BLOCKED.

## Build parity (§66–§67)

- Node: local 25.5.0 vs CI 22 → P1 reproducibility gap, documented.
- Electron: dev ^40.10.6 vs packaged pin 40.9.3 (build.electronVersion) →
  intentional pin, documented.
- electron-builder ^26.8.1.

## Regression (§69–§70)

- W79-034: `test:desktop:platforms` 176/176 PASS (host).
- W79-029 validator: INVALID (stale M78 manifest, P1 provenance gap — not corruption).
- Full pytest suite: NOT run (out of scope for desktop phase; no claim made).

## SBOM / Provenance / Update (§86–§88)

SBOM: BLOCKED/UNVERIFIED (CI-only, CI not executed). Provenance: local source
binding YES (stamp==HEAD, dirty caveat); CI provenance/attestation: NONE —
no claim. UPDATE = NOT_IMPLEMENTED (unchanged).

## Failures

1. Stale M78 manifest vs rebuilt artifacts (P1 provenance).
2. Path-length guard FAIL on checkout-absolute paths (P1).
3. Dirty tree ~2755 paths (release-from-clean blocker, P0 for production release).

## Release-readiness answers (§99)

1–7 NSIS install/launch/UI/IPC/backend/uninstall/reinstall: UNVERIFIED (blocked).
8–14 MSI incl. reinstall: UNVERIFIED (blocked). 15–18 Portable: UNVERIFIED.
19 Hashes: YES, all correct. 20 Source-bound: YES locally (dirty caveat); CI: NO.
21 P0: YES — absence of clean-env evidence is itself certification-blocking
per §94 (plus dirty-tree release blocker). 22 Signing: NO. 23 SBOM: NO.
24 Provenance (CI/attestation): NO. 25 Update: NOT_IMPLEMENTED.
