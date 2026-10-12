# AETHEROS MASTER 79 — Windows Certification Matrix (Execution-3, 36 rows per §52)

HEAD: `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1` (DIRTY).
Env: dev host, NOT clean. Clean VM/Sandbox: re-checked 79.1-exec3, still UNAVAILABLE.
Baselines: NSIS 195891460 b86b22f7…f9278 | MSI 203137784 1069fc6d…5b031b | Portable 162205111 214d4255…43cfe3c — all re-verified on host this run.

| Test ID | §52 name | Result | Evidence / note |
|---|---|---|---|
| W79-001 | Artifact verification | PASSED | hashes re-computed, match; CURRENT manifest created (§7) |
| W79-002 | NSIS install | BLOCKED | no VM |
| W79-003 | NSIS launch | BLOCKED | no VM |
| W79-004 | NSIS GUI | BLOCKED | no VM |
| W79-005 | NSIS IPC | BLOCKED | no VM (static: contextIsolation/sandbox true) |
| W79-006 | NSIS backend | BLOCKED | no VM |
| W79-007 | NSIS settings | BLOCKED | no VM |
| W79-008 | NSIS shutdown | BLOCKED | no VM |
| W79-009 | NSIS uninstall | BLOCKED | no VM (policy deleteAppDataOnUninstall=false) |
| W79-010 | NSIS reinstall | BLOCKED | no VM |
| W79-011 | MSI install | BLOCKED | no VM; ProductCode {77035F50-600E-49B1-851F-6E004FDBC134} |
| W79-012 | MSI launch | BLOCKED | no VM |
| W79-013 | MSI GUI | BLOCKED | no VM |
| W79-014 | MSI IPC | BLOCKED | no VM |
| W79-015 | MSI backend | BLOCKED | no VM |
| W79-016 | MSI settings | BLOCKED | no VM |
| W79-017 | MSI shutdown | BLOCKED | no VM |
| W79-018 | MSI uninstall | BLOCKED | no VM |
| W79-019 | MSI reinstall | BLOCKED | no VM |
| W79-020 | MSI silent install | BLOCKED | no VM; enterprise-contract applicability unverified |
| W79-021 | Portable launch | BLOCKED | no VM |
| W79-022 | Portable GUI | BLOCKED | no VM |
| W79-023 | Portable IPC | BLOCKED | no VM |
| W79-024 | Portable backend | BLOCKED | no VM |
| W79-025 | Portable shutdown | BLOCKED | no VM |
| W79-026 | Developer-path independence | BLOCKED | no VM |
| W79-027 | Normal-user behavior | BLOCKED | no VM (UAC expected: perMachine=true) |
| W79-028 | Orphan-process validation | BLOCKED | no VM |
| W79-029 | Long-path runtime validation | PASSED-static / BLOCKED-live | guard VALID-projection (35061 files, max PROJ 218); live import UNVERIFIED |
| W79-030 | Artifact parity | PASSED-static / BLOCKED-live | version/electron/payload static match; M79 + CURRENT manifests VALID |
| W79-031 | Authenticode | PASSED-recorded | NotSigned ×3 (expected; NOT a trust pass) |
| W79-032 | Clean-tree verification | FAILED | DIRTY (1780M/13D/963??; §4 classes below) |
| W79-033 | Electron version parity | PASSED-documented | pin 40.9.3 intentional; dev ^40.10.6 |
| W79-034 | Node version/reproducibility | PASSED-documented | local 25.5.0 vs CI 22; CI authoritative (P1 gap) |
| W79-035 | Regression suite | PASSED | electron 176/176; guard tests 9/9; validator VALID; guard VALID |
| W79-036 | Security regression | PASSED-static / BLOCKED-live | hardening static OK; audit-security 12/24 (50/100); check-secrets heuristic 7724 keyword hits, no verified real secrets; live IPC/security BLOCKED; renderer IPC vitest unrunnable (no vitest binary) |

Score: Executed 9 rows (host) · Passed 7 (incl. static/recorded) · Failed 1 (W79-032 dirty) · Blocked 27 · Unverified: SmartScreen, Defender, SBOM, attestation, update(NOT_IMPLEMENTED).
