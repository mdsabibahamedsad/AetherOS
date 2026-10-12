# AETHEROS Master 79.2 — Blocked Tests

Commit `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1`. Every BLOCKED item names its missing capability. Nothing is downgraded.

## P0 (certification-blocking)

| ID | Test | Missing capability | Unblocks when |
|---|---|---|---|
| 79.2-B01…B08 | CI installer/runtime execution (install, launch probes, uninstall, backend independence) | A completed run of `windows-desktop-certification.yml` on windows-latest (`gh` auth invalid on dev host; dispatch required) | CI run green + evidence uploaded |
| 79.2-B09 | Packaged IPC smoke | GUI renderer (headless CI cannot exercise IPC) | clean VM + packaged runtime IPC probe |
| 79.2-C01…C06 | All GUI/interactive/VM tests | clean Windows VM + interactive session (Sandbox/Hyper-V/VMware/VBox all unavailable; non-admin host) | VM provisioned, hashes re-verified in-VM, W79-002…W79-027 executed |
| Dirty-tree provenance | CI-clean build proof | Local tree DIRTY (2763 paths); local hashes ≠ clean-tree proof | CI rebuild from clean checkout |
| Signing/trust | Code-signing certificate | Artifacts UNSIGNED; no credentials in repo or workflow | cert acquired, signed, `signtool verify /pa /v` recorded |

## P1 (non-blocking, must be scheduled)

| ID | Test | Missing capability | Note |
|---|---|---|---|
| 79.2-A13 | Renderer vitest in CI | CI run | step exists in workflow |
| 79.2-A14 | SBOM spdx-json | CI run | step exists (anchore/sbom-action) |
| 79.2-A15 | Provenance attestation verification | CI run | step exists (attest-build-provenance v3); UNVERIFIED until inspected |
| 79.2-A12 triage | secrets-scanner fixture hits + dep vulns (32; 21 high, 1 critical) | security triage decision | static only; live half (W79-035) still needs VM |
| 79.2-A09 | Packaged renderer title | CI rebuild | OLD_ARTIFACT_KNOWN_ISSUE until rebuilt artifacts verified to contain AetherOS |

GUI_CERTIFICATION = BLOCKED. VM_REQUIRED = YES. (§33–§34)
