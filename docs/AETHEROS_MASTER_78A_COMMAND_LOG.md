# AETHEROS MASTER 78A — Command Log (abridged, exit codes + timestamps)

Host: Windows 11 Pro x64. All commands executed for real; logs in `docs/AETHEROS_MASTER_78A_EVIDENCE/`.

| # | Command (cwd) | Exit | Result |
|---|---|---|---|
| 1 | `npm run typecheck` (apps/desktop) | 0 | PASS |
| 2 | `npm run build` (apps/desktop) | 1 | FAIL F-01 (missing @vitejs/plugin-react) |
| 3 | `npm install --no-audit --no-fund` (repo root) | 0 | +100 packages |
| 4 | `npm run build` (apps/desktop) | 0 | PASS (bundle 270.7MB, smoke pydantic 2.13.4, vite 8.40s) |
| 5 | `npm run test:desktop:platforms` | 0 | 176/176 PASS |
| 6 | `npm run dist:win:validate-paths` | 1 | FAIL F-02 (1 offender, 246 chars) — recorded, MSI-gating |
| 7 | `npm run builder -- --win nsis` | 0 | NSIS installer built (09:21) |
| 8 | verify NSIS (Get-Item/hash/version) | 0 | 195891460 B, b86b22f7…, 1.0.0 |
| 9 | `npm run builder -- --win portable` | 0 | portable built (09:26) |
| 10 | verify portable + Authenticode | 0 | 162205111 B, 214d4255…, 1.0.0, NotSigned |
| 11 | guard from `X:\` (subst) | 0 | VALID 33904 files (short spelling) |
| 12 | `npm run builder -- --win msi` (from X:) | 1 | FAIL F-03 LGHT0103 — subst canonicalized to D:\ |
| 13 | robocopy → `D:\hb\` + junction node_modules | 0/1(rc1=ok) | verbatim staging |
| 14 | `node electron-builder/out/cli/cli.js --win msi` (cwd D:\hb) | 0 | MSI built (09:39) |
| 15 | Move MSI → dist-packaged + hash verify | 0 | hash identical 1069fc6d… |
| 16 | MSI Property-table read (COM) | 0 | ProductName=AetherOS, ProductVersion=1.0.0.0 |
| 17 | win-unpacked launch probe (25s, --no-sandbox) | 0 | alive+responding, HWND set, title "Aetheros", 0 orphans |
| 18 | `validate-artifacts.mjs --manifest <78A manifest>` | 0 | VALID, 7 entries cross-checked |
| 19 | cleanup `__msi-x64`, `D:\hb` | 0 | removed |

Evidence files: build.log, build-2.log, npm-install.log, electron-tests.log, validate-paths.log,
nsis-build.log, portable-build.log, msi-build.log, msi-build-short.log, validate-artifacts.log.
