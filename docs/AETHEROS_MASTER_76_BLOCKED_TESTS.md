# AetherOS Master 76 Blocked Tests

## Signing/notarization/attestation runs
What: sign-windows, stapler validate, `gh attestation verify`, SBOM-vs-binary.
Why: no credentials/artifacts-in-CI. Infra: EV cert, Apple ID + macOS runner,
store accounts, CI OIDC. Owner: release eng. Impact: P0 — no trusted release.

## Device install/update/rollback (P01–P25 on hardware)
Why: no lab, no clean VMs, no signed builds. Infra: device lab. Owner:
release/QA. Impact: P0.

## Full python suite green
Why: 36k tests exceed local time budget; 24 pre-existing raw-collection
errors. Infra: CI runners + time. Owner: QA/infra. Impact: P1.

## Fleet telemetry / monitoring / incident / recovery drills / staging
Why: nothing deployed. Infra: staging/prod. Owner: SRE. Impact: P1.

## Perf on prod bits / a11y AT pass / legal review
Why: no lab/users/counsel. Infra: perf lab, AT tooling, counsel. Impact:
P1/P2. Note: a11y static 3/4 executed (reduced-motion gap recorded, P2).

## Theme value drift (3 tests)
Why: token values vs assertions disagree; needs UX design decision, not a
drive-by edit. Owner: UX. Impact: P3.
