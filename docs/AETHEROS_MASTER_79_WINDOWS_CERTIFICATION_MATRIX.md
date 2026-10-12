# AETHEROS MASTER 79 — Windows Certification Matrix

Actual HEAD: `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1` (DIRTY).
Environment: dev host (NOT clean) for PASSED rows; clean VM/Sandbox: UNAVAILABLE.
Artifact hashes verified on host against Master 78A baselines (see
`AETHEROS_MASTER_79_EVIDENCE/checksums/W79-001-host-hashes.md`).

| Test ID | Artifact | Environment | Operation | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|---|---|
| W79-001 | NSIS+MSI+Portable | dev host | hash/size verification | match 78A baselines | all 3 match (195891460 / 203137784 / 162205111) | PASSED | EVIDENCE/checksums/W79-001-host-hashes.md |
| W79-002 | NSIS | clean VM | clean install | installs, exit 0 | no VM/Sandbox available | BLOCKED | BLOCKED_TESTS.md |
| W79-003 | NSIS | clean VM | first launch | process+GUI+renderer | no VM | BLOCKED | — |
| W79-004 | NSIS | clean VM | GUI smoke (Home/Agent/Settings/close) | observed nav | no VM | BLOCKED | — |
| W79-005 | NSIS | clean VM | IPC safe channels | req→preload→main→resp | no VM | BLOCKED | — |
| W79-006 | NSIS | clean VM | backend health | packaged backend responds | no VM | BLOCKED | — |
| W79-007 | NSIS | clean VM | Settings | loads, non-destructive pref | no VM | BLOCKED | — |
| W79-008 | NSIS | clean VM | shutdown | no orphans | no VM | BLOCKED | — |
| W79-009 | NSIS | clean VM | uninstall | files/shortcuts/registry removed, user data per policy | no VM | BLOCKED | — |
| W79-010 | NSIS | clean VM | reinstall | install+launch+smoke | no VM | BLOCKED | — |
| W79-011 | MSI | clean VM | clean install (GUI + msiexec /i + log) | exit 0 | no VM; static ProductCode {77035F50-600E-49B1-851F-6E004FDBC134} only | BLOCKED | EVIDENCE/windows/msi/msi-static-metadata.md |
| W79-012 | MSI | clean VM | first launch | process+GUI+renderer | no VM | BLOCKED | — |
| W79-013 | MSI | clean VM | GUI smoke | observed nav | no VM | BLOCKED | — |
| W79-014 | MSI | clean VM | IPC | req→resp | no VM | BLOCKED | — |
| W79-015 | MSI | clean VM | backend | packaged backend responds | no VM | BLOCKED | — |
| W79-016 | MSI | clean VM | Settings | loads | no VM | BLOCKED | — |
| W79-017 | MSI | clean VM | shutdown | no orphans | no VM | BLOCKED | — |
| W79-018 | MSI | clean VM | uninstall (Apps/msiexec /x) | removed, log captured | no VM | BLOCKED | — |
| W79-019 | MSI | clean VM | reinstall | install+launch+smoke | no VM | BLOCKED | — |
| W79-020 | MSI | clean VM | silent install (/qn /norestart) | exit 0 + verified product | no VM; contract applicability unverified | BLOCKED | — |
| W79-021 | Portable | clean env | launch, no install | process+GUI | no VM | BLOCKED | — |
| W79-022 | Portable | clean env | GUI smoke | observed nav+close | no VM | BLOCKED | — |
| W79-023 | Portable | clean env | IPC/backend | responds | no VM | BLOCKED | — |
| W79-024 | Portable | clean env | shutdown/restart | clean, no corruption | no VM | BLOCKED | — |
| W79-025 | all | clean env | developer-path independence | launches outside D:\hermes-agent-main | no VM | BLOCKED | — |
| W79-026 | all | clean env | normal-user launch | works non-admin (NSIS perMachine=true → UAC expected) | no VM | BLOCKED | — |
| W79-027 | all | clean env | orphan process check | none after close | no VM | BLOCKED | — |
| W79-028 | all | dev host (static) | long-path runtime regression (elevenlabs) | imports load from packaged py | guard FAILS on absolute checkout paths (6 files >240); runtime import UNVERIFIED | FAILED (guard) / BLOCKED (runtime) | EVIDENCE/failures/path-length-guard.md |
| W79-029 | all | dev host (static) | artifact parity (version/electron/assets/backend/icons) | same payload | version 1.0.0 + electron 40.9.3 + backend/py/resources consistent; validator manifest cross-check INVALID (stale M78 manifest, P1) | FAILED (manifest) / BLOCKED (runtime parity) | EVIDENCE/failures/validate-artifacts-manifest-mismatch.md |
| W79-030 | all | dev host | Authenticode status | record honestly | NotSigned ×3 (expected, unsigned-by-design local build) | PASSED (status recorded; NOT a trust pass) | EVIDENCE/windows/security/authenticode-status.md |
| W79-031 | repo | dev host | clean-tree verification | empty if release requires clean | DIRTY (~2755 paths, 1422 files in diff stat) → release-from-clean BLOCKED | FAILED (dirty = release blocker) | WINDOWS_TEST_ENVIRONMENT.md |
| W79-032 | build | dev host (static) | Electron version parity | explain 40.9.3 vs 40.10.6 | packaged pin 40.9.3 intentional (build.electronVersion); dev ^40.10.6 — documented, no runtime proof | PASSED (documented) | FINAL_TEST_REPORT.md §67 |
| W79-033 | build | dev host (static) | Node version parity | local vs CI vs release | local 25.5.0 vs CI 22 — documented P1 reproducibility gap | PASSED (documented) | WINDOWS_TEST_ENVIRONMENT.md |
| W79-034 | repo | dev host | Master 70 regression (electron platform tests) | 176/176 | 176/176 PASS | PASSED | EVIDENCE/windows/logs/electron-platform-tests.md |
| W79-035 | repo | dev host (static) | security regression (IPC/preload/sandbox/nav) | boundaries hold | static: contextIsolation=true, nodeIntegration=false, sandbox=true (main.cjs + hardening.cjs); live IPC/security tests BLOCKED | PASSED (static) / BLOCKED (live) | FINAL_TEST_REPORT.md §70 |

## Score

- Executed (host): 8 (W79-001, 028-guard, 029-manifest, 030, 031, 032, 033, 034, 035-static = counted as 8 matrix rows incl. partials)
- Passed: 5 (001, 030-recorded, 032, 033, 034) + 035-static
- Failed: 3 (028-guard, 029-manifest, 031-dirty)
- Blocked: 27 (all clean-environment operational tests)
- Unverified: SmartScreen, Defender behavior, SBOM, provenance attestation, update (NOT_IMPLEMENTED, unchanged)
