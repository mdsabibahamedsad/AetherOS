# AETHEROS Master 80 — Final Certification (§79)

## Executive Summary

Master 80 replaced documentation-only release hygiene with executable enforcement.
The repository now has ONE canonical Windows release path that refuses dirty trees,
wrong toolchains, unclean outputs, stale artifacts, and branding drift — proven by
live runs that correctly FAIL on the current dirty/stale state, plus 19 regression
tests that fail forever on the historical failure modes. Full rebuild, CI run, VM,
signing, SBOM, and attestation remain not-run/blocked for stated capability reasons.

## Mission / Environment / Repository State

Mission per Master 80 prompt (build integrity, not packaging capability).
Env: Windows Pro 26200 non-admin, Node v25.5.0 / npm 11.8.0 (non-canonical),
Python 3.12 (.venv), no Sandbox/VM, gh token invalid. Repo: commit 2bdfbfd8…,
tree DIRTY (2777 porcelain paths). No product architecture changed.

## Build-System Audit

`docs/AETHEROS_MASTER_80_BUILD_SYSTEM_AUDIT.md` — every entrypoint/output/validator/
CI path inspected; legacy `build-all-installers.mjs` retired; toolchain resolved
(Node 22 / electron 40.9.3 pinned + dev ^40.10.6 documented / builder 26.8.1 exact).

## Root Causes (fixed)

No output ownership, no clean-tree gate, no toolchain gate, weak binding (recorded,
not failed), competing `release/` framework, manifest-per-phase confusion, unexecuted CI.

## Changes Made (files)

Created: `scripts/release/{release-config.cjs, release-guards.cjs, preflight-windows.mjs,
validate-windows-release.mjs, release-windows.mjs, windows-release-guards.test.cjs}`,
`docs/AETHEROS_MASTER_80_{BUILD_SYSTEM_AUDIT,BUILD_CONTRACT,REPRODUCIBILITY_REPORT,
TEST_MATRIX,EVIDENCE/*,FINAL_CERTIFICATION}.md`, updated `.github/workflows/
windows-desktop-certification.yml` (7-job DAG, YAML-validated).
Changed: `apps/desktop/package.json` (+7 `desktop:*` scripts), `scripts/
build-all-installers.mjs` (retired guard). Removed: none (history preserved).

## Canonical Build / Toolchain / Output / Artifact / Manifest / Hash Contracts

`docs/AETHEROS_MASTER_80_BUILD_CONTRACT.md` (single source of truth, §73).

## Regression Tests

`windows-release-guards.test.cjs`: 19/19 PASS (§57 T1–T10 + T11/T12 policy locks).
Path guard 9/9 PASS. Electron 176/176 PASS (unchanged). Preflight live: correctly
FAILs A01/A02/A10. Validator live: B05/B11/C01/C03/C09 PASS; B12/C07 correctly FAIL.

## Local / CI / VM Execution (§74–§76)

Local: all static gates executed; full rebuild NOT_RUN (blocked by design: dirty
tree + non-canonical Node; rebuilding would also destroy the only artifacts).
CI: NOT_RUN (gh auth invalid; exact dispatch documented). VM: BLOCKED (no capability).

## Signing / SBOM / Provenance / Attestation

UNSIGNED / BLOCKED / UNVERIFIED / UNVERIFIED — steps exist, none fabricated.

## Known Limitations / Remaining Blockers

Stale `dist/index.html` title (rebuild fixes); dirty tree (commit/clean fixes);
Node 25.5 local (use Node 22); dep-vuln triage scheduled (§42); L4 reproducibility
unclaimed; auto-update untouched (§52).

## Evidence Index

`docs/AETHEROS_MASTER_80_EVIDENCE/README.md` (12 files, all from real runs).

## §80 gate table

| Gate | Status | Evidence |
|---|---|---|
| Git clean enforcement | PASS (mechanism; live FAIL correct) | 01-preflight.json A01 |
| Toolchain lock | PASS (mechanism; live FAIL correct) | 01-preflight.json A02 |
| npm ci | PASS (contract+CI; local NOT_RUN by design) | contract §13, workflow `build` job |
| Lockfile immutability | PASS (mechanism + CI step) | guards T8, workflow preflight |
| Clean output | PASS (mechanism; live FAIL correct) | 01-preflight.json A10 |
| Stale artifact detection | PASS (mechanism; live FAIL correct) | 12-validation-status.json C07 |
| Artifact completeness | PASS | validator B05 |
| NSIS | PASS (gate; build NOT_RUN) | B05 + CI `build` job |
| MSI | PASS (metadata verified live) | validator B11 |
| Portable | PASS (gate; build NOT_RUN) | B05 + CI `build` job |
| Source binding | PASS (mechanism; live FAIL correct) | 12-validation-status.json B12 |
| SHA-256 | PASS | 08-hashes.json |
| Manifest | PASS (schema v1 + self-check) | 09-manifest.json |
| Packaged branding | PASS (mechanism; live FAIL correct) | 12-validation-status.json C07 |
| Path guard | PASS | 10-path-guard.log |
| Developer path independence | PASS | validator C09 |
| Runtime smoke | NOT_RUN (CI job exists) | workflow `runtime` job |
| Regression suite | PASS (19/19 + 9/9 + 176/176) | 05-guard-tests.log |
| CI workflow | PASS (YAML-valid, 7-job DAG) | parser output |
| Actual CI run | NOT_RUN (gh token invalid) | §75 |
| Clean VM | BLOCKED | §76 |
| Signing | BLOCKED (UNSIGNED) | sign-windows.mjs contract |
| SBOM | BLOCKED (step exists) | workflow `evidence` job |
| Provenance | UNVERIFIED | no attestation yet |
| Attestation | UNVERIFIED | no attestation yet |

No blank cells. No converted statuses (§80/§81).

## Certification

**BUILD_SYSTEM_HARDENED** (§78: contract exists, stale/dirty/toolchain/output/identity/
binding/regression/CI-valid/docs all present and exercised).
**PRODUCTION_RELEASE_BLOCKED** (signing, SBOM, provenance, attestation, clean VM,
CI run all outstanding).

## Next Step

On canonical Node 22 with a clean tree: `npm run desktop:release:windows:manifest`
→ dispatch `windows-desktop-certification.yml` → VM GUI → sign → SBOM/attest → release.
