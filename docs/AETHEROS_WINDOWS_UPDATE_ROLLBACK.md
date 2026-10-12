# AetherOS Windows Update & Rollback

States: CHECKING → AVAILABLE → DOWNLOADING → VERIFYING → READY →
INSTALLING → RESTART_REQUIRED → COMPLETED / FAILED → ROLLING_BACK →
ROLLED_BACK. Validator (`electron/update-manifest.cjs`, 6 tests)
rejects: non-HTTPS artifacts, bad SHA256, non-semver, unknown channel/
publisher/schema, downgrades, below-minimum currents, empty signatures.

Rollback: pre-update snapshot (version, state/schema generations,
update ID, artifact hash); health check post-install; on failure
reinstall previous build — app-only when user data changed since the
snapshot (never blindly restore stale data). Channels: STABLE + BETA
recommended (metadata per channel); NIGHTLY optional. Live
download/install/rollback: UNVERIFIED (no packaged builds, no VM).
`verifyUpdateCodeSignature: false` must be revisited with signing.
