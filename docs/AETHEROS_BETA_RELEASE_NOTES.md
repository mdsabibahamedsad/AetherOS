# AetherOS Beta Release Notes — 1.1.0-beta.1

releaseId: `aetheros-1.1.0-beta.1` · commit `2bdfbfd` · channel `beta` · date 2026-09-12.
This is a CONTROLLED BETA, not general availability.

## New in this beta

- Universal auto-update engine: guarded state machine, resumable downloads,
  real RSA manifest/artifact verification, health-gated install with automatic
  rollback, crash-loop protection, versioned migrations.
- Update server: channel manifests, staged rollouts, kill switch, revocation,
  previous-known-good promotion.
- Beta release ops: RC freeze tooling, rollout gates, signed feature flags,
  redacted support bundles, incident workflow.
- Release pipeline: 9-job CI (test → security → build → sign → SBOM →
  provenance → publish → canary → promote) with fail-closed gates.

## Improvements

- Manifest signature canonicalization fixed (recursive sorted-keys; nested
  artifact fields covered).
- Platform adapters: corrected module wiring; Linux rollback brace fix.
- Renderer↔main update IPC validated; install options allow-listed.

## Platform support (honest)

- Windows x64: BETA_READY_WITH_LIMITATIONS (needs signed build; signing creds absent).
- Linux x64: BETA_READY_WITH_LIMITATIONS (AppImage/deb/rpm paths implemented; repo E2E unrun).
- macOS x64/ARM64: BLOCKED (no Apple signing/notarization runner).
- Windows ARM64 / Linux ARM64: BLOCKED (no hardware).
- iOS/iPadOS: BLOCKED (no TestFlight). Android: BLOCKED (no Play track execution).
- Web beta env: UNVERIFIED (no deployment performed). Server: code tested, deployment UNVERIFIED.

## Security

- No known critical vulnerabilities in the release path. Update verification,
  rollback, IPC, and AgentCapsule controls preserved; nothing weakened for beta.
- Signing: BLOCKED until credentials exist — therefore no artifact in this
  beta is claimed production-ready.

## Update and rollback

- BETA N → N+1 verified in harness (manifest/signature/digest/migration/health).
  On-device update/rollback drills: UNVERIFIED (need signed builds + devices).

## Limitations

- No beta users enrolled yet; all fleet metrics UNVERIFIED — no crash rates,
  install counts, or success rates are claimed anywhere in this document set.
- Pre-existing `design-system` typecheck errors block packaged builds.
