# AetherOS Windows Update

Current state (honest): there is NO electron-updater channel. What exists:

1. Passive git-remote check (`electron/update-remote.cjs`, unit-tested):
   compares the origin remote against the official HTTPS repo without auth
   prompts (FIDO2-safe). Informational only.
2. NSIS `differentialPackage: true` for smaller downloads when CI publishes
   full installers per release.

Missing and NOT claimed: signed update metadata, HTTPS manifest with
hashes, staged rollout, channels (stable/beta/nightly), download resume,
rollback, restart-safe apply. Any in-app "update available" surface must
link to the published release artifacts, never silently install.
Update/rollback matrix: BLOCKED — ENVIRONMENT (no packaged builds, no VM).
`verifyUpdateCodeSignature: false` is set — must be revisited when a
signed channel exists.
