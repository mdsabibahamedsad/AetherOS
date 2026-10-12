# AetherOS Update Platform Matrix

Companion to `AETHEROS_UPDATE_PLATFORM_MATRIX.json` (machine-readable source
of truth). One logical update protocol; platform-native installers.

## Windows

| Topic | Value |
|---|---|
| Architectures | x64 (production), arm64 (planned) |
| Packaging | NSIS (primary), MSI (enterprise), portable (no auto-update) |
| Updater | NSIS/MSI installer, `verifyUpdateCodeSignature: false` is build-only; production verifies Authenticode |
| Signing | EV code signing via Azure Trusted Signing (`apps/desktop/scripts/release/sign-windows.mjs`); missing creds = SIGNING=BLOCKED |
| Rollback | Previous-version installer retained in backup path; health-gated revert |
| Limitations | Per-machine install needs admin/UAC; no delta updates; metered-network policy enforced client-side |

## macOS

| Topic | Value |
|---|---|
| Architectures | arm64 (Apple Silicon), x64 (Intel), universal builds supported |
| Packaging | DMG (primary), ZIP, PKG |
| Updater | Signed DMG/PKG apply with notarization staple check |
| Signing | Developer ID + `xcrun stapler validate` gate (`verify-notarization.mjs`); non-mac runner = macOS=BLOCKED unless explicitly skipped for local dev |
| Rollback | Prior app bundle in backup path; crash-loop guard triggers revert |
| Limitations | Notarization requires Apple credentials + macOS runner |

## Linux

| Topic | Value |
|---|---|
| Architectures | x64 (production), arm64 (planned) |
| Packaging | AppImage (application-level update), deb (APT repo), rpm (DNF repo), Flatpak |
| Updater | AetherOS Update Service → repository metadata → platform package manager; AppImage via staged swap + exec-bit preserve |
| Signing | deb/rpm repository + package signatures; AppImage SHA-256 + RSA artifact signature |
| Rollback | deb/rpm via package manager history where supported; AppImage via retained previous file |
| Limitations | Privileged installs require sudo/polkit — never silent; Electron autoUpdater is NOT used as the Linux story |

## Web

| Topic | Value |
|---|---|
| Packaging | Immutable versioned build artifacts + service worker |
| Updater | Version-mismatch detection → notify → graceful refresh; active sessions never broken |
| Signing | TLS + subresource integrity on immutable assets |
| Rollback | Previous deployment retained; instant redeploy of prior version |

## Mobile (iOS / iPadOS / Android)

| Topic | Value |
|---|---|
| Distribution | App Store / Play (public); approved enterprise distribution (private) |
| Updater | OS store mechanisms only — no self-modification on iOS; Play in-app updates where applicable |
| Rollback | Store-staged rollout halt + previous-track promotion |

## Cross-cutting guarantees (all platforms)

- Manifest RSA signature over **recursively canonicalized** JSON (all nested
  fields covered) + per-artifact RSA signature + SHA-256. No custom crypto.
- HTTPS-only artifact URLs in production; downgrade forbidden by default;
  revoked/kill-switched releases refused.
- Every desktop install: pre-activation backup → 8-gate health check →
  automatic rollback on failure; crash-loop guard (3 crashes/10 min) reverts.
- Failure taxonomy: NETWORK_FAILURE, MANIFEST_INVALID, SIGNATURE_INVALID,
  HASH_MISMATCH, UNSUPPORTED_PLATFORM, INSUFFICIENT_DISK, PERMISSION_DENIED,
  INSTALL_FAILURE, MIGRATION_FAILURE, HEALTH_CHECK_FAILURE, CRASH_LOOP,
  ROLLBACK_FAILURE.
