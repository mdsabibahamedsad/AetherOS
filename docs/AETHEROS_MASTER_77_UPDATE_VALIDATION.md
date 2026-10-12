# AetherOS Master 77 — Update Validation

## Declared state (honest)

- WINDOWS_AUTO_UPDATE = NOT_IMPLEMENTED (no `publish` provider, no `electron-updater`).
- LINUX_AUTO_UPDATE = NOT_IMPLEMENTED (no AppImage update wiring, no deb/rpm repository).
- `electron/update-manifest.cjs` = pure offline manifest validator (unit-tested); it validates
  metadata objects, it does not download or apply anything.
- NSIS `differentialPackage: true` + `.blockmap` are emitted artifacts without a consumer feed.

No update manifest is published; no manifest points at nonexistent files (nothing is published at all).

## What was tested

- `validateManifest` unit tests (part of Electron suite): https enforcement, sha256 shape, semver,
  channel match, publisher match, downgrade rejection, minimumVersion gating. PASSED at unit level.
- Live check/download/verify/stage/install/restart/health/rollback: BLOCKED — there is no live
  update channel in 1.0.0, and destructive update tests must never run against production.

## Controlled update-test plan (for when a channel is implemented)

Fake update server → cases: no-update, new-update, invalid manifest, wrong hash, wrong signature,
wrong platform/arch, expired/revoked release, download failure, interrupted download, disk-full,
restart, health-failure → rollback to N. Rollback rule already encoded in `rollbackDecision`
(app-only rollback when user data changed since snapshot; full restore otherwise).

## Rollback status

`recordPreUpdateSnapshot` + `rollbackDecision` exist as pure logic (TESTED). End-to-end
N → N+1 → broken-launch → health-fail → rollback → N-healthy: BLOCKED (no channel, no VM).
