# AetherOS Master 76 Stability Report (commit 2bdfbfd → working tree, 2026-09-12)

## What changed (scope-controlled, every item maps to a blocker)
- `apps/desktop/src/design-system/tokens/index.ts`: removed 28-line bogus
  type re-export (M76-01).
- `apps/desktop/src/design-system/components/`: NEW Button, DropdownMenu,
  Card, Divider, Badge adapters (documented, no forked visuals) (M76-01).
- `apps/desktop/src/lib/icons.ts`: added Home (M76-01).
- `apps/desktop/src/i18n/types.ts` + `zh.ts`: emergencyStop block (M76-01).
- `apps/desktop/src/design-system/patterns/ActionBar.tsx`: Radix onSelect
  adaptation (M76-01).
- `apps/desktop/src/styles.css`: breakpoint literals (M76-02).
- `aetheros_cli/main.py`: `_git_cmd()` extraction (3 sites), pip argv
  validation, rev-list safe-abort with restore (M76-03/04/05).
- `aetheros_cli/managed_uv.py`: untouched (arity analysis only).
- `apps/desktop/electron/hardening.cjs` + `main.cjs`: webview attach policy
  + wiring (M76-07).
- Tests: `test_cmd_update.py` (hermetic fixture, normcase, _git_cmd
  assertions), `test_update_autostash.py` (platform-aware git), NEW
  `test_update_malformed_guard.py` (3), `hardening.test.cjs` (+1 webview).
- `services/update/update-server.ts`: strict-init + PackagingFormat types
  (fell out of desktop tsconfig via test import).

No features added. No deps added/upgraded. No redesign.

## Before/after (Master 75 → 76)
| Blocker | Before | After |
|---|---|---|
| B74-004 typecheck | 100+ errors, build broken | ZERO errors; `tsc -b` + vite build pass |
| CSS build | unknown (never got that far) | fixed; renderer builds 14.53s |
| P0-2 artifacts | none existed | NSIS+MSI+portable BUILT, hashed (unsigned) |
| P1-1 CLI updater | 22 failed | 0 failed in wrapper (59-file set green; layout-proofed) |
| Backup tests | 3 failed | 113/113 pass |
| Webview policy | missing | implemented + tested |
| Design themes | 3 failed | 3 failed (unchanged, P3, needs UX decision) |
| Signing | BLOCKED | BLOCKED (verified NotSigned; pipeline ready) |
| Devices/staging/attest | BLOCKED | BLOCKED (host-only validation added) |

## Residual risk
Unsigned local build must never be mistaken for release (labeled
`local-build`, no manifest entry in release channels). Junction/proof
harnesses removed. dist-packaged/ is untracked build output (hashes recorded).
