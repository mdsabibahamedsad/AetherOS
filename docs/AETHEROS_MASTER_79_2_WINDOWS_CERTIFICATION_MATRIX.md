# AETHEROS Master 79.2 — Windows Certification Matrix

Commit: `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1` (tree DIRTY locally).
CI workflow: `.github/workflows/windows-desktop-certification.yml` (created, NOT yet executed — `gh` auth invalid on dev host).
Status rules (§36): PASS = actually executed OK; FAIL = executed and failed; BLOCKED = required env unavailable; UNVERIFIED = evidence insufficient.

## CATEGORY A — CI-executable headless tests

| ID | Test | Environment | Artifact | Execution Type | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| 79.2-A01 | Artifact hash verification (3 hashes) | dev host (dirty) | NSIS/MSI/portable | headless static | match §3 baseline | all 3 match | PASS (host-side; CI re-verifies) | EVIDENCE/hashes.txt |
| 79.2-A02 | release:validate-artifacts | dev host | dist-packaged | headless static | VALID | VALID exit 0 | PASS (host-side; CI re-runs) | EVIDENCE/validate-artifacts.log |
| 79.2-A03 | Projected-path length validation | dev host | win-unpacked + bundled-python | headless static | 35061 files, ≤6 absolute-only warnings | 35061, 6 absolute-only | PASS | EVIDENCE/path-lengths.log |
| 79.2-A04 | Path guard tests | dev host | scripts | headless unit | 9/9 | 9/9 | PASS | EVIDENCE/path-guard-tests.log |
| 79.2-A05 | MSI ProductCode/ProductVersion/Name/UpgradeCode | dev host | MSI | headless metadata | GUID + 1.0.0.x + AetherOS | `{77035F50-…}`, 1.0.0.0, AetherOS, UpgradeCode matches pkg | PASS | EVIDENCE/msi-properties.txt |
| 79.2-A06 | Authenticode status | dev host | all 3 | headless metadata | honestly recorded | NotSigned x3 | PASS (status=UNSIGNED) | EVIDENCE/authenticode.txt |
| 79.2-A07 | Packaged file inspection (win-unpacked layout, exe version) | dev host | win-unpacked | headless static | AetherOS.exe + resources + branding | present; ProductName=AetherOS, FV=40.9.3 | PASS | matrix §notes |
| 79.2-A08 | Renderer title source | dev host | index.html source | headless static | `<title>AetherOS</title>` | present | PASS (fix intact) | EVIDENCE/title-source.txt |
| 79.2-A09 | Packaged renderer title | dev host | dist/index.html + asar | headless static | AetherOS after rebuild | dist stale (Aetheros); asar mixed | OLD_ARTIFACT_KNOWN_ISSUE (not PASS) | EVIDENCE/title-source.txt |
| 79.2-A10 | Host launch probe | dev host (dirty, non-admin) | win-unpacked exe | headless process | starts | started, kill-after-probe, clean | INFORMATIONAL (not runtime PASS) | EVIDENCE/host-launch-probe.txt |
| 79.2-A11 | Electron unit regression (17 files) | dev host | source | headless unit | 176/176 | 176/176 | PASS (host-side; CI re-runs) | EVIDENCE/electron-tests.log |
| 79.2-A12 | Static security audits | dev host | source | headless static | recorded | audit 50/100 exit 0; secrets exit 1 (fixture hits); deps 32 vulns | EXECUTED (triage pending; NOT a gate PASS) | EVIDENCE/security-static.txt |
| 79.2-A13 | Renderer unit tests (vitest) | CI windows-latest | source | headless unit | green | not executed (no CI run yet) | UNVERIFIED (CI step exists in workflow) | workflow `REGRESSION — renderer unit tests` |
| 79.2-A14 | SBOM spdx-json | CI windows-latest | dist-packaged | CI tool | generated | not executed (no CI run yet) | BLOCKED (pending CI run; step exists) | workflow `REGRESSION — SBOM` |
| 79.2-A15 | Build provenance attestation | CI windows-latest | 3 artifacts | CI tool | attested | not executed (no CI run yet) | UNVERIFIED (step exists) | workflow `attest-build-provenance` |

## CATEGORY B — CI-executable installer/runtime tests (require CI run)

| ID | Test | Environment | Artifact | Execution Type | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| 79.2-B01 | NSIS silent install (/S) | CI windows-latest (disposable, admin) | NSIS | real install, headless | exit 0 + files present | not executed | BLOCKED (pending CI run; step exists) | workflow → ci-evidence/nsis-install.txt |
| 79.2-B02 | NSIS-installed launch probe | CI windows-latest | installed app | real process, headless | HEADLESS_RUNTIME_PASS | not executed | BLOCKED (pending CI run) | workflow → nsis-runtime.txt |
| 79.2-B03 | NSIS uninstall (/S) | CI windows-latest | installed app | real uninstall, headless | files removed | not executed | BLOCKED (pending CI run) | workflow → nsis-uninstall.txt |
| 79.2-B04 | MSI install (msiexec /qn + /L*v) | CI windows-latest | MSI | real install, headless | exit 0/3010 + log | not executed | BLOCKED (pending CI run) | workflow → msi-install.log |
| 79.2-B05 | MSI-installed launch probe | CI windows-latest | installed app | real process, headless | HEADLESS_RUNTIME_PASS | not executed | BLOCKED (pending CI run) | workflow → msi-runtime.txt |
| 79.2-B06 | MSI uninstall (msiexec /x + /L*v) | CI windows-latest | MSI | real uninstall, headless | exit 0/3010 + log | not executed | BLOCKED (pending CI run) | workflow → msi-uninstall.log |
| 79.2-B07 | Portable launch probe | CI windows-latest | portable | real process, headless | HEADLESS_RUNTIME_PASS | not executed | BLOCKED (pending CI run) | workflow → portable-runtime.txt |
| 79.2-B08 | Packaged-backend independence | CI windows-latest | installed/portable | real process | no dev-server use | not executed | BLOCKED (pending CI run; probes exist in B02/B05/B07 — processes launch from installed layout only) | — |
| 79.2-B09 | IPC smoke (packaged) | CI windows-latest | installed app | real IPC | exercised | cannot run headless (renderer GUI needed) | BLOCKED (VM_REQUIRED even after CI) | §22 |

## CATEGORY C — GUI/interactive/VM-only tests

| ID | Test | Environment | Artifact | Execution Type | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| 79.2-C01 | GUI navigation / visual rendering | clean VM + interactive session | any | human/visual | verified UI | not executed | BLOCKED (VM_REQUIRED) | BLOCKED_TESTS |
| 79.2-C02 | Settings UI interaction | clean VM | installed app | human/visual | verified | not executed | BLOCKED (VM_REQUIRED) | BLOCKED_TESTS |
| 79.2-C03 | Visual smoke + screenshots/video | clean VM | installed app | human/visual | captured | not executed | BLOCKED (VM_REQUIRED) | BLOCKED_TESTS |
| 79.2-C04 | Interactive UAC behavior (per-machine NSIS/MSI) | clean VM, standard user | NSIS/MSI | human | observed prompt/elevation | not executed | BLOCKED (VM_REQUIRED) | BLOCKED_TESTS |
| 79.2-C05 | Real desktop user workflow | clean VM | installed app | human | end-to-end | not executed | BLOCKED (VM_REQUIRED) | BLOCKED_TESTS |
| 79.2-C06 | Interactive uninstall verification | clean VM | installed app | human | observed | not executed | BLOCKED (VM_REQUIRED) | BLOCKED_TESTS |

## No-false-equivalence attestations (§38)

- CI runner ≠ GUI VM. Stated in workflow header, CI cert doc, and final cert.
- Process launched ≠ GUI passed. Probes assert HEADLESS_RUNTIME_PASS only.
- Installer exit 0 ≠ application passed. Install and runtime are separate IDs.
- Static IPC analysis ≠ IPC pass. 79.2-B09 stays BLOCKED.
- Headless Electron startup ≠ visual UI pass. Category C untouched by CI.

Notes: win-unpacked layout verified (`AetherOS.exe` 213946368 bytes, resources/{app.asar,backend,py,native-deps}). MSI ProductCode `{77035F50-600E-49B1-851F-6E004FDBC134}` is electron-builder-generated (package.json pins only `upgradeCode` + nsis `guid`); recorded, not modified.
