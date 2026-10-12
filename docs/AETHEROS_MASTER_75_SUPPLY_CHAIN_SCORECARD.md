# AetherOS Master 75 Supply-Chain Scorecard — 1.0.0

| Item | Status | Evidence |
|---|---|---|
| signing | BLOCKED | no creds; tooling fails closed (proven Master 74) |
| SBOM | BLOCKED (prod) | RC/pipeline enforcement implemented; no packaged SBOM generated |
| provenance | IMPLEMENTED | RC records + attest-build-provenance in CI; no live run verified |
| attestation | UNVERIFIED | `gh attestation verify` never executed (no artifacts) |
| verification | IMPLEMENTED | verify-manifest/canary gates; red-team green |
| key management | BLOCKED | no production keys exist to manage/rotate |
| release integrity | IMPLEMENTED | immutability enforced by rc-manifest (proven); no prod release yet |
| lockfiles | PRESENT | uv.lock, package-lock, pnpm-lock committed |
| registry trust | PARTIAL | SHA-pinned GH Actions; npm audit not run here (no network claim) |
| dependency licenses | PARTIAL | 80 desktop direct deps, no name-flagged copyleft; transitive audit UNVERIFIED |
| secret hygiene | PASSED | scan clean (placeholders in tests only) |
