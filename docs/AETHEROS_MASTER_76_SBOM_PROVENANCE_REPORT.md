# AetherOS Master 76 SBOM / Provenance Report

## SBOM
`npm sbom` unusable here (workspace file: deps uninstalled in this view →
ESBOMPROBLEMS). Instead generated **lockfile-SBOM** from
apps/desktop/package-lock.json: **1030 packages** (607 dev), integrity hashes
preserved where locked, 2 unknown-license entries — both are the in-repo
`@aetheros/shared` workspace package (not third-party risk).
Evidence: 03-tests/lockfile-sbom.json. Scope honesty: this describes the
locked DEPENDENCY GRAPH, not installer binary contents. Binary SBOM +
drift check: BLOCKED (needs CI-packaged SBOM step). No template labeled
production.

## Provenance
Local-build provenance recorded (commit, builder host, tool versions,
artifact digests, honest non-SLSA scope): 03-tests/local-build-provenance.json.
SLSA/GitHub attestation: BLOCKED — no `gh`, no CI OIDC from this host, so
nothing generated and nothing "verified". `gh attestation verify` pattern
documented in runbook for the creds-backed run.

## Release integrity
RC immutability + manifest validation proven (Master 74). 1.0 manifests remain
honestly empty (no signed release exists).
