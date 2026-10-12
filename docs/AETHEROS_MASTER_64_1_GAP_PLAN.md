# Master 64.1 — Gap Closure Plan

Source of truth: Master 64 audit + certification (WINDOWS BETA READY).
Rule: close what is implementable + testable here (Category A); prepare
but honestly mark what needs external environment (Category B). No fake
implementations; no Electron rewrite; reuse `aetheros_platform/desktop/*`,
`aetheros_computer/*`, `aetheros_platform/observability/*`.

## CATEGORY A — implement + test now

| # | Gap | Implementation | Evidence |
|---|---|---|---|
| A1 | No capability registry | `aetheros_platform/windows_capabilities.py`: detectors (OS, admin, UIA dlls, Hello API presence, EventLog writability, signing state, msix) + `python -m` CLI dump | pytest file |
| A2 | Toast actions unvalidated | Action allowlist + validation (id/task/agent/auth/state/expiry binding) in `aetheros_platform/desktop/notifications.py` | pytest file |
| A3 | Tray unwired | `electron/tray-menu.cjs` pure menu builder from backend state + `electron/tray.cjs` guarded Electron wiring (live tray UNVERIFIED: no Electron binary) | node:test file |
| A4 | Startup model missing | `aetheros_platform/desktop/startup.py`: mode model, per-user Run-key mechanism (winreg, win32 only), audit record; live registration UNVERIFIED | pytest file |
| A5 | UIA tree missing | `aetheros_computer/uia.py`: UIElement schema, 6 capability scopes, provider interface, OCR-fallback provider, validation | pytest file |
| A6 | Event Log missing | Windows EventLog writer w/ structured fallback (`aetheros_platform/observability/`), stable IDs, secret redaction | pytest file |
| A7 | Update/rollback unvalidated | `electron/update-manifest.cjs`: manifest/hash/version/channel/publisher validator + rollback recorder | node:test file |
| A8 | No benchmarks | `scripts/windows_bench.py`: env capture + real timings, JSON output — EXECUTED here | output JSON |

## CATEGORY B — prepare, mark blocked

B1 signing pipeline (docs exist; creds BLOCKED). B2 clean-VM harness
(script + docs, execution BLOCKED). B3 Store/MSIX decision doc
(>>> direct NSIS/MSI primary; Store NOT pursued). B4 per-user installer
(doc decision; default NOT flipped untested). B5 CI `windows-platform.yml`
(UNVERIFIED until CI runs). B6 Hello biometrics (detection only).
B7 hardware benchmarks beyond bench harness (BLOCKED).

## Docs to produce

NATIVE_INTEGRATION, UI_AUTOMATION, TRAY, BACKGROUND_RUNTIME,
UPDATE_ROLLBACK, INSTALLER_E2E, DISTRIBUTION_DECISION, BENCHMARKS,
SECURITY_REGRESSION, 64_1_TEST_MATRIX, manifest update, 64_1 certification.

## Verdict rule

PRODUCTION READY only with P0 evidence (signed, clean-VM install/update/
rollback, E2E green). Otherwise BETA READY (expected) or BLOCKED.
