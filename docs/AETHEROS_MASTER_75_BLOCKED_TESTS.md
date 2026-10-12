# AetherOS Master 75 Blocked Tests (Master 75 §132)

## Full python suite (F08)
- Test: `bash scripts/run_tests.sh tests/` (36,234 collected).
- Reason: exceeded 10-minute execution budget in this environment; raw pytest
  shows 24 pre-existing collection errors (import collisions).
- Required infra: CI runners with xdist + per-test isolation + time.
- Owner: QA / infra. Next: green CI run. Impact: P1 — no full-suite citation.

## Packaged install/update/rollback on devices (F09)
- Tests: P01–P25 golden journeys on hardware/VMs; clean-machine installs.
- Reason: no signed packaged builds exist (B74-004 + P0-1).
- Required infra: fixed tree, signing creds, device lab (Windows/mac/Linux,
  ARM, Android, iOS), TestFlight/Play access.
- Owner: release engineering. Next: build → sign → device matrix. Impact: P0.

## Signing / notarization / attestation runs (F10)
- Tests: sign-windows, stapler validate, `gh attestation verify`, SBOM-vs-artifact.
- Reason: no credentials, no artifacts.
- Required infra: EV cert, Apple ID + macOS runner, store accounts.
- Owner: release engineering. Next: provision + run update-release.yml. Impact: P0.

## Fleet telemetry / monitoring / incident drill
- Reason: no deployment exists to observe.
- Required infra: staging/prod + telemetry pipeline.
- Owner: SRE. Next: deploy beta env first. Impact: P1.

## Performance measurements
- Reason: no packaged build or perf lab run.
- Required infra: perf lab + Master 71 harness on prod bits.
- Owner: performance. Next: measure on RC. Impact: P1.

## Accessibility certification
- Reason: no assistive-tech test pass performed.
- Required infra: manual AT testing. Next: targeted pass. Impact: P2 (no
  certification claimed).
