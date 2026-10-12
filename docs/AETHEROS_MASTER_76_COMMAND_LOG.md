# AetherOS Master 76 Command Log (UTC 2026-09-12, win32-x64, start commit 2bdfbfd)

Env record: 01-environment/env.json. Pre-existing dirty tree (~2320 entries);
Master 76 touched only files listed in the stability report.

| Time | Command | Exit | Result |
|---|---|---|---|
| — | npm run typecheck (apps/desktop) | 0 | ZERO errors (was 100+) |
| — | npm run test:ui -- --run (full) | 1 | 808 pass / 3 fail (pre-existing themes) → vitest-final-76.log |
| — | npm run test:desktop:platforms | 0 | 176/176 (incl. new webview test) → electron-final-76.log |
| — | wrapper: test_cmd_update + autostash + malformed_guard + check + interrupted | 0 | 80 + 34 + prior greens |
| — | wrapper: test_backup + backup_restore | 0 | 113/113 (3 fixed) |
| — | wrapper: recovery_suite + batch_checkpoint | 0 | 29/29 |
| — | wrapper: tests/security + curator_backup | 0 | 376/376 |
| — | node --test hardening.test.cjs | 0 | 12/12 |
| — | npm run build (apps/desktop) | 0 | tsc -b + vite 14.53s → renderer-build.log |
| — | npm run builder -- --dir (+NSIS/MSI/portable) | 0 | 3 installers + unpacked → electron-builder-dir.log |
| — | Get-AuthenticodeSignature installer | 0 | NotSigned (evidence of unsigned state) |
| — | unpacked AetherOS.exe launch, 25s | 0 | window "Aetheros", responding, alive |
| — | blockmap gunzip inspection | 0 | v2, 8953 chunks, well-formed |
| — | npm sbom | FAIL | ESBOMPROBLEMS (workspace state) → lockfile-SBOM instead (1030 pkgs) |
| — | npm run quality:a11y | 0 | 3/4, reduced-motion gap → accessibility-report.md |
| — | node --check main/hardening.cjs, release .mjs scripts | 0 | OK |
| — | node t76perf.mjs (×2) | 0 | perf-micro.json (labeled micro, not prod) |
| — | git grep secret patterns | 0 | clean (placeholders only) |

No secrets in any command. Junction proof farm (C:\t76root) and TEMP helpers
removed after use. dist-packaged/ kept as untracked build output (hashes recorded).
