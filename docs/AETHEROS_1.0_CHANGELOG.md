# AetherOS 1.0 Changelog (evidence-backed only)

## 1.0.0 (source 2bdfbfd — NOT RELEASED, production blocked)
- Universal auto-update: state machine, resumable downloads, RSA manifest +
  artifact verification, health-gated install, auto-rollback, crash-loop guard,
  versioned migrations (Master 70.5 evidence: 37 tests).
- Update service: channels, staged rollout, kill switch, revocation,
  previous-known-good (tested in-process).
- Beta release ops: RC freeze, rollout gates, signed flags, redacted bundles
  (Master 74 evidence: 46 tests + gate proofs).
- Fixed: manifest canonicalization (B74-001), CI pipeline doc→real workflow
  (B74-002), adapter wiring + Linux braces (B74-003).
- Known-open: design-system typecheck (B74-004), CLI updater mock bug (P1-1),
  theme tests (P3), no signing/device/fleet infra (P0-1/2/3, P1-2/3).
