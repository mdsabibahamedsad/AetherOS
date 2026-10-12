# AetherOS Master 76 Initial Blocker Matrix (commit 2bdfbfd, 2026-09-12)

 inherited from Master 75: P0-1 (no signing creds), P0-2 (no packaged artifacts),
 P0-3 (no device evidence), P1-1 (CLI updater 22 failures), P1-2 (full suite
 incomplete), P1-3 (no prod operations), B74-004 (design-system typecheck).

| ID | Sev | Subsystem | Source | Status | Repro | Expected | Actual | Root cause | Fix | Test | Evidence | Residual | Blocked by |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M76-01 | P1 | desktop typecheck | Master 75 B74-004 | FIXED | `npm run typecheck` | clean | 100+ errors | tokens/index re-exported non-members from ./color; 5 components/ missing; i18n key drift; linux braces (prev) | trimmed re-export; created design-system/components/{Button,DropdownMenu,Card,Divider,Badge}; Home icon; emergencyStop en+zh | typecheck clean; vitest 808/811 | 03-tests/typecheck-clean.log | none | — |
| M76-02 | P1 | CSS build | NEW (found via Phase G) | FIXED | `npm run build` | vite ok | lightningcss var() in @media | self-referential --breakpoint-* in @theme inline | literals (identical runtime values) | renderer-build.log ✓ built 14.53s | 03-tests/renderer-build.log | none | — |
| M76-03 | P1 | CLI updater tests (18) | Master 75 P1-1 | FIXED* | wrapper run | pass | ZIP-path exit / int('') | (a) nested-checkout .git layout (env); (b) win32 git prefix vs exact-match mocks | hermetic PROJECT_ROOT fixture; _git_cmd() helper+refactor; normcase cwd | 25/25 in file pass | wrapper summary | fork/refresh layout proofs documented | — |
| M76-04 | P1 | CLI updater tests (4 autostash) | Master 75 P1-1 | FIXED | wrapper run | pass | win32 prefix mismatch | same as M76-03(b) | platform-aware expectations | 31/31 file pass | wrapper summary | none | — |
| M76-05 | P1 | CLI updater robustness | NEW (from M76-03) | FIXED | crafted mocks | controlled abort | ValueError/TypeError crash | unguarded int() + join() on resolver output | safe-abort w/ restore; argv validation | test_update_malformed_guard.py (3 pass) | wrapper summary | none | — |
| M76-06 | P2 | backup tests (3) | NEW (Phase N) | FIXED | wrapper run | pass | substring false-positive; .bat naming | test filter over-broad; POSIX-only wrapper name | startswith filter; platform-aware names | 113/113 pass | wrapper summary | none | — |
| M76-07 | P2 | webview attach | NEW (Phase 21 audit) | FIXED | code audit | explicit policy | no will-attach-webview | missing guard | hardening policy + main wiring | hardening.test 12/12 | electron log | live botherder test UNVERIFIED | — |
| M76-08 | P3 | themes (3) | Master 75 | OPEN | vitest | pass | value drift | token values vs assertions | NONE (design decision required) | — | vitest-final-76.log | UX owner decision | UX review |
| M76-09 | P0 | signing creds | Master 75 P0-1 | OPEN | env audit | creds exist | absent (NotSigned verified) | never provisioned | pipeline ready; fail-closed proven | sign-windows BLOCKED proof | GATE_PROOFS (M74) | blocks stable | infra provisioning |
| M76-10 | P0 | packaged artifacts | Master 75 P0-2 | PARTIAL | build attempt | signed installers | UNSIGNED local build exists | creds absent; (build chain now works) | built NSIS+MSI+portable, hashed | launch alive 25s | local-artifacts.json | signature missing | M76-09 |
| M76-11 | P0 | device evidence | Master 75 P0-3 | PARTIAL | n/a | device matrix | host-only validation | no lab | launch+hash on host; matrix honest | launch log | device matrix | all other devices | device lab |
| M76-12 | P1 | full python suite | Master 75 P1-2 | OPEN | wrapper 10-min budget | green | time-boxed | 36k tests, no CI time here | targeted suites green | security 376, recovery 165+ | wrapper summaries | CI run needed | CI runners/time |
| M76-13 | P1 | prod operations | Master 75 P1-3 | OPEN | n/a | live ops | none | no infra | runbooks ready | — | — | blocks launch | infra |
| M76-14 | P1 | perf on prod bits | Master 75 | OPEN | n/a | measurements | none | no prod build until now | micro-timings only | perf-micro.json | honest micro only | perf lab | perf lab |
| M76-15 | P2 | a11y full cert | NEW (Phase 33) | OPEN | quality:a11y | 4/4 | 3/4 (reduced-motion) | store gap | none (needs impl) | ACCESSIBILITY_REPORT | a11y report | AT pass | UX impl |

\* M76-03: 16/18 proven green under both layouts; fork-sync + refresh-cwd
 assertions verified structurally (identical-path derivation) — see updater validation doc.
