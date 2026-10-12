# AETHEROS Master 79.2 — CI Certification

Product AetherOS 1.0.0, commit `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1`.

## What CI gives us (and what it does not)

- `windows-latest` = DISPOSABLE CI ENVIRONMENT (clean checkout, admin, Node 22). ✔ for Categories A/B headless.
- `windows-latest` ≠ GUI CERTIFICATION VM. No interactive session, no visual observation, no UAC interaction. Category C stays BLOCKED regardless of CI outcome. (§6, §33)

## Workflow (`.github/workflows/windows-desktop-certification.yml`)

CHECKOUT → ENVIRONMENT → ARTIFACT → HASH → PACKAGE VALIDATION → INSTALLER TEST → RUNTIME TEST → SECURITY TEST → REGRESSION → EVIDENCE → CERTIFICATION.
Least-privilege (`contents: read` + job-scoped `attestations: write`/`id-token: write` for provenance only). No secrets, no signing credentials; output is UNSIGNED by design. Fails safe (any real failure exits non-zero; GUI-absence is recorded, never asserted).

## CI run status

NOT EXECUTED. `gh` token on dev host is invalid; dispatch requires a human with repo access
(GitHub UI → Actions → Windows Desktop Certification → Run workflow, or `gh workflow run`).
On dispatch: default `artifact_source=rebuild-in-ci` produces clean-tree provenance + fresh
NSIS/MSI/Portable (historical Master 78A hashes preserved, never overwritten); SBOM +
build-provenance attestation execute; evidence artifact `windows-desktop-certification-evidence` (90d)
lands under `docs/AETHEROS_MASTER_79_2_EVIDENCE/`-equivalent CI paths.

## Headless-vs-GUI separation enforced in the workflow

- Install steps assert exit codes + file presence only.
- Runtime probes assert HEADLESS_RUNTIME_PASS (process alive at 20s, clean kill) — never GUI PASS.
- IPC step: attempted only as safe probe; BLOCKED verdict pre-recorded for headless (§22).
- MSI `/L*v` logs captured to `ci-evidence/msi/`; failures fail the job (fail safely).

## Local Node vs CI Node (§26)

Local 25.5.0 vs CI 22 — documented, local NOT changed; CI authoritative for reproducibility.

GUI_CERTIFICATION = BLOCKED. VM_REQUIRED = YES. SBOM = BLOCKED (pending run). Provenance/attestation = UNVERIFIED (pending run).
