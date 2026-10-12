# AETHEROS Master 80 — Test Matrix (§56)

Commit `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1`, tree DIRTY, Node v25.5.0 (non-canonical).
Statuses: PASS / FAIL (gate correctly rejected a bad live state) / NOT_RUN / BLOCKED.

## A — Preflight (`preflight-windows.mjs --report` → 01-preflight.json)

| ID | Check | Status | Evidence |
|---|---|---|---|
| A01 | git clean | FAIL (correct: 2777 changed paths → RELEASE_BUILD_BLOCKED_DIRTY_TREE) | 01-preflight.json |
| A02 | canonical Node 22 | FAIL (correct: v25.5.0 → NODE_MAJOR_MISMATCH) | 01-preflight.json |
| A03 | npm available | PASS | 01-preflight.json |
| A04 | Electron pin 40.9.3 | PASS | 01-preflight.json |
| A05 | builder 26.8.1 repo-local | PASS | 01-preflight.json |
| A06 | lockfiles present | PASS | 01-preflight.json |
| A07/A08 | npm ci / lockfile gate | INFORMATIONAL (enforced by canonical build) | contract §13 |
| A09 | output path safe | PASS | 01-preflight.json |
| A10 | output initially clean | FAIL (correct: 10 entries → OUTPUT_DIRECTORY_NOT_CLEAN) | 01-preflight.json |
| A11 | path guard wired | PASS | 01-preflight.json |
| A12 | packaging identity | PASS | 01-preflight.json |

## B — Build (`validate-windows-release.mjs` live run → 12-validation-status.json)

| ID | Check | Status | Evidence |
|---|---|---|---|
| B01–B04 | unpacked/NSIS/MSI/portable builds | NOT_RUN (blocked by A01/A02 by design) | — |
| B05 | artifact set (3/3 + foreign noted) | PASS | validator output |
| B06–B10 | names/version/arch/ProductName/appId | PASS (structural) | validator output |
| B11 | MSI metadata (COM read) | PASS (ProductName/Version/Code/UpgradeCode) | validator output |
| B12 | source identity | FAIL (correct: dirty stamp → ARTIFACT_DIRTY_TREE) | 12-validation-status.json |
| B13/B14 | stale/unexpected rejection | PASS (mechanism; live stale caught at C07) | 12-validation-status.json |

## C — Integrity

| ID | Check | Status | Evidence |
|---|---|---|---|
| C01 | SHA-256 (3/3) | PASS | 08-hashes.json |
| C02/C03 | manifest + self-validation | PASS | 09-manifest.json |
| C04/C05/C06 | binding / buildId / toolchain | PASS (mechanism; binding correctly FAILs on dirty) | 09-manifest.json |
| C07 | packaged title | FAIL (correct: stale dist → PACKAGED_BRANDING_MISMATCH) | 12-validation-status.json |
| C08 | packaged metadata | PASS | validator output |
| C09 | developer-path screen | PASS (6 containers classified, 0 failing) | validator output |
| C10 | long-path guard | PASS (35061 + 9/9) | 10-path-guard.log |

## D — Runtime

D01–D08: NOT_RUN locally (release blocked by design); CI `runtime` job owns headless
probes (HEADLESS_RUNTIME_SMOKE, never GUI). G: all BLOCKED (VM_REQUIRED).

## E — CI

| ID | Check | Status | Evidence |
|---|---|---|---|
| E01 | workflow syntax | PASS (PyYAML parse; 7 jobs, DAG verified) | shell output |
| E02–E11 | clean checkout … upload | NOT_RUN (gh token invalid; dispatch required) | §75 |

## F — Release security

F01 signing availability: BLOCKED (UNSIGNED; `sign-windows.mjs` exits 1).
F02 signature validation: NOT_APPLICABLE (nothing signed).
F03 SBOM: BLOCKED (step exists). F04 provenance: UNVERIFIED. F05/F06 attestation: UNVERIFIED.

## Regression suite (§57): 19/19 PASS; path-guard 9/9 PASS; Electron 176/176 PASS (unchanged).
