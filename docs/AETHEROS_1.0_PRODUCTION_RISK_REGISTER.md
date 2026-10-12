# AetherOS 1.0 Production Risk Register (Master 75 §194)

| Risk | Severity | Likelihood | Impact | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| Unsigned artifact reaches users | P0 | Low (fail-closed tooling) | Critical | All publish paths require creds; verify-manifest gate in CI | Release eng | BLOCKED (no creds = no release) |
| Update verification bypass | P0 | Low | Critical | Real RSA verify + red-team suite; canonicalization fixed | Security | Mitigated in code; device proof pending |
| Destructive data rollback | P0 | Low | Critical | Checkpoints before migration; never auto-destructive (Master 61) | Storage | Policy implemented; drill pending |
| Agent runaway in production | P1 | Medium | High | Budgets/timeouts/kill/takeover paths; needs live validation | Agent team | UNVERIFIED live |
| Supply-chain compromise | P1 | Low | Critical | Pinned actions, SBOM/provenance/attestation gates | Supply chain | Tooling ready; no prod run yet |
| Secret leakage via telemetry | P1 | Low | High | Redaction unit-tested; bundle review step in user guide | Privacy | Mitigated in code |
| Vendor/model outage | P2 | Medium | Medium | Fallback/timeout/budget paths; no fabricated fallbacks | Platform | UNVERIFIED live |
| Store rejection/delay | P2 | Medium | Medium | Explicit BLOCKED states; no claims without approval | Release eng | Accepted |
| Accessibility gaps | P2 | Medium | Medium | No certification claimed without testing | UX | UNVERIFIED |
| Docs misleading users | P2 | Low | Medium | Every doc states BLOCKED/UNVERIFIED where true | Docs | Mitigated |
