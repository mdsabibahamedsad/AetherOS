# AETHEROS Master 81 — Final Certification (§80/§87/§98)

**WINDOWS_RC_BLOCKED** — stopped at exact gate A01 (RELEASE_SOURCE_NOT_CLEAN).
**PRODUCTION_RELEASE_BLOCKED** (§96).

## §87 gate table (no blank cells)

| Gate | Status | Evidence |
|---|---|---|
| Clean Git tree | FAIL (2783 paths; user chose block-and-report) | M81/02, M81/10, M81/11 |
| Node 22 | PASS (v22.12.0 bootstrapped, SHA-verified) | M81/03 |
| npm ci | NOT_RUN (belongs to clean-tree run) | RC report §11 |
| Lockfile immutable | NOT_RUN | — (guards T8 mechanism stands) |
| Master 80 guards | PASS (19/19 under Node 22) | M81/05 |
| Clean output | FAIL (A10, historical artifacts present) | M81/04 |
| Fresh NSIS | NOT_RUN | gate STOP A01 |
| Fresh MSI | NOT_RUN | gate STOP A01 |
| Fresh Portable | NOT_RUN | gate STOP A01 |
| Artifact completeness | NOT_RUN | gate STOP A01 |
| Source binding | NOT_RUN | gate STOP A01 |
| SHA-256 | NOT_RUN (historical hashes stay HISTORICAL) | §14 |
| Manifest | NOT_RUN | — |
| Packaged branding | NOT_RUN | — |
| Developer-path independence | NOT_RUN | — |
| Backend independence | NOT_RUN | — |
| Headless runtime | NOT_RUN | — |
| CI workflow executed | NOT_RUN (auth invalid) | M81/09 |
| CI build | NOT_RUN | — |
| CI tests | INFORMATIONAL (local suites under Node 22: guards 19/19, Electron 176/176, renderer 808/811) | M81/05–07 |
| CI artifact round-trip | NOT_RUN | — |
| Clean Windows environment | BLOCKED (no Sandbox/VM) | §76 |
| NSIS install | BLOCKED | VM |
| MSI install | BLOCKED | VM |
| Portable runtime | BLOCKED | VM |
| IPC | BLOCKED | VM |
| Backend | BLOCKED | VM |
| Shutdown | BLOCKED | VM |
| Uninstall | BLOCKED | VM |
| Reinstall | BLOCKED | VM |
| Authenticode | N/A (no new artifacts) / SIGNING=BLOCKED | — |
| SBOM | BLOCKED | — |
| Provenance | UNVERIFIED | — |
| Attestation | UNVERIFIED | — |

## §86 artifact table

| Artifact | Built in Master 81? | Source-bound? | SHA-256 | Runtime | Install | GUI | Status |
|---|---|---|---|---|---|---|---|
| NSIS | NO | NO | HISTORICAL b86b22f7… (NOT an RC hash) | NOT_RUN | BLOCKED | BLOCKED | HISTORICAL |
| MSI | NO | NO | HISTORICAL 1069fc6d… (NOT an RC hash) | NOT_RUN | BLOCKED | BLOCKED | HISTORICAL |
| Portable | NO | NO | HISTORICAL 214d4255… (NOT an RC hash) | NOT_RUN | N/A | BLOCKED | HISTORICAL |

## §88 test counts (exact)

Master-80 guards 19/19 (Node 22) · Path guards 9/9 · Electron 176/176 (Node 22) ·
Renderer 808/811 under Node 22 (3 pre-existing fails, identical under 25) ·
CI jobs 0/7 executed · VM tests 0/X.

## §89 environment record

Windows Pro 26200 25H2 x64 non-admin · system Node v25.5.0/npm 11.8.0 ·
canonical Node v22.12.0 portable (SHA-verified) · Python 3.12 venv · Git 2.53.0 ·
Electron pin 40.9.3 / dev 40.10.6 · builder 26.8.1 · CI runner: none · VM: none.

## Master-80 non-regression (§92)

No guard weakened. New files: root `.github/workflows/windows-desktop-certification.yml`
(promoted, 7-job, YAML-valid); M81 evidence (11) + RC report + this cert. Removed:
nested inert workflow copy (untracked). Source/build logic: untouched.
