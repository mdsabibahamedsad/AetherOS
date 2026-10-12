# AetherOS Universal Auto-Update Architecture

## Overview

This document describes the architecture of the AetherOS Universal Continuous Update Platform, a production-grade update system supporting Windows, macOS, Linux, Web, iOS, and Android.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Update Manager                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │   Policy    │ │  Manifest   │ │  Verifier   │ │ Downloader│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ Windows  │ │  macOS   │ │  Linux   │
       │ Adapter  │ │ Adapter  │ │ Adapter  │
       └──────────┘ └──────────┘ └──────────┘
              │            │            │
              ▼            ▼            ▼
         ┌──────────┐ ┌──────────┐ ┌──────────┐
         │  NSIS/   │ │ DMG/PKG  │ │AppImage/ │
         │   MSI    │ │          │ │ DEB/RPM  │
         └──────────┘ └──────────┘ └──────────┘
```

## Core Components

### 1. Update Manager (`update-manager.ts`)
Central orchestrator coordinating the update lifecycle:
- State machine management
- Update checking with configurable intervals
- Download with progress tracking and resumption
- Installation coordination via platform adapters
- Rollback management
- History tracking

### 2. Platform Adapters (`platform-adapter.ts`)
Abstract interface with platform-specific implementations:
- **Windows** (`windows-adapter.ts`): NSIS/MSI installers with Authenticode verification
- **macOS** (`macos-adapter.ts`): DMG/PKG with code signing and notarization
- **Linux** (`linux-adapter.ts`): AppImage/DEB/RPM/Flatpak with package signatures
- **Web** (`web-adapter.ts`): Service Worker based updates
- **Mobile** (`mobile-adapter.ts`): App Store / Play Store coordination

### 3. Manifest System (`manifest-verifier.ts`, `types.ts`)
- Cryptographically signed manifests
- Artifact integrity verification (SHA-256)
- Publisher identity verification
- Rollout policy enforcement
- Security classification (normal/important/security-critical)

### 4. Semantic Versioning (`semver.ts`)
- Strict semver parsing and comparison
- Prerelease and build metadata support
- Range satisfaction checking
- Version increment utilities

### 5. Update Server (`update-server.ts`)
- Release creation and publishing
- Channel management (nightly/dev/alpha/beta/stable/enterprise)
- Rollout policies with percentage-based cohorts
- Emergency kill switch and rollback
- Artifact signing and provenance tracking

## Update Lifecycle

```
IDLE
  ↓ (periodic/manual check)
CHECKING
  ↓ (manifest fetched & verified)
AVAILABLE
  ↓ (auto or manual)
DOWNLOADING
  ↓ (progress tracking, hash verification)
VERIFYING
  ↓ (signature, hash, publisher)
STAGING
  ↓ (prepare for install)
READY_TO_INSTALL
  ↓ (user confirmation or auto)
INSTALLING
  ↓ (platform-specific install)
RESTARTING
  ↓ (health checks)
HEALTH_CHECK
  ↓ (all critical checks pass)
COMPLETE
```

### Failure Recovery
Any failure state transitions to `ROLLBACK` → `ROLLED_BACK` preserving user data.

## Security Model

### Artifact Verification Chain
1. **Manifest Signature** - Ed25519/RSA signature over canonicalized manifest
2. **Artifact Hash** - SHA-256 verified against manifest
3. **Artifact Signature** - Platform-specific (Authenticode, codesign, dpkg-sig, RPM)
4. **Publisher Verification** - Certificate chain validation
5. **Provenance** - Build metadata, SBOM hash, commit reference

### Transport Security
- HTTPS only for all update communications
- Certificate pinning for update server
- No secrets in client binaries

### Rollout Safety
- Percentage-based gradual rollout
- Cohort-based targeting
- Emergency kill switch
- Release revocation support

## Configuration

```typescript
interface UpdateConfig {
  enabled: boolean;                    // Master enable/disable
  channel: ReleaseChannel;             // nightly/dev/alpha/beta/stable/enterprise
  checkInterval: number;               // Milliseconds between checks
  downloadAutomatically: boolean;      // Background downloads
  installOnQuit: boolean;              // Install pending on quit
  allowPrerelease: boolean;            // Include pre-releases
  meteredNetworkPolicy: 'allow'|'wifi-only'|'block';
  autoUpdateOnRestart: boolean;        // Check on startup
  verifySignature: boolean;            // Enforce signature verification
  requireAdminForInstall: boolean;     // Require elevation
}
```

## State Definitions

| State | Description |
|-------|-------------|
| `IDLE` | No update activity |
| `CHECKING` | Contacting update server |
| `AVAILABLE` | Update ready to download |
| `DOWNLOADING` | Downloading artifact |
| `VERIFYING` | Verifying integrity/signature |
| `STAGING` | Preparing for installation |
| `READY_TO_INSTALL` | Awaiting user/auto trigger |
| `INSTALLING` | Running platform installer |
| `RESTARTING` | Application restarting |
| `HEALTH_CHECK` | Post-install validation |
| `COMPLETE` | Update successful |
| `FAILED` | Update failed |
| `ROLLBACK` | Reverting to previous version |
| `ROLLED_BACK` | Rollback complete |
| `BLOCKED` | Update blocked by policy |

## Platform-Specific Details

### Windows
- **Packaging**: NSIS (primary), MSI (enterprise)
- **Verification**: Authenticode via `signtool`/`Get-AuthenticodeSignature`
- **Installation**: Silent `/S` (NSIS) or `/qn` (MSI)
- **Rollback**: Previous version installer from backup
- **Elevation**: UAC via `runas` or installer manifest

### macOS
- **Packaging**: DMG (primary), PKG (enterprise), ZIP
- **Verification**: `codesign --verify`, `spctl --assess` (notarization)
- **Installation**: DMG mount + copy, or `installer -pkg`
- **Rollback**: App bundle swap from backup
- **Elevation**: `AuthorizationExecuteWithPrivileges` / SMJobBless

### Linux
- **Packaging**: AppImage, DEB, RPM, Flatpak
- **Verification**: `dpkg-sig`, `rpm --checksig`, Flatpak OSTree
- **Installation**: Package manager (`apt`, `dnf`, `flatpak`) or AppImage replace
- **Rollback**: Package manager reinstall or AppImage swap
- **Elevation**: `sudo` / PolicyKit

### Web
- **Mechanism**: Service Worker + Cache API
- **Verification**: Subresource Integrity + Content-Security-Policy
- **Update**: SW registration + `skipWaiting` + page reload
- **Rollback**: Server-side redeploy previous version

### Mobile
- **iOS**: App Store only (TestFlight for beta)
- **Android**: Play Store (In-App Updates API) or enterprise distribution
- **Verification**: Platform store signatures

## CI/CD Integration

### Release Pipeline
```
source change
  ↓
tests → typecheck → lint → security
  ↓
build → package (all platforms)
  ↓
sign (code signing)
  ↓
hash (SHA-256)
  ↓
SBOM (CycloneDX)
  ↓
provenance (SLSA)
  ↓
publish artifacts (CDN/object storage)
  ↓
publish manifest (signed)
  ↓
canary rollout (internal → alpha → beta)
  ↓
validation (health checks, telemetry)
  ↓
stable rollout (gradual)
```

### Release Gates
- All tests pass
- Type checking clean
- Security audit clean
- Signing successful
- Artifact hashes recorded
- SBOM generated
- Provenance attested
- Manifest valid
- No critical security issues
- No P0 performance regressions (Master 71)

## Data Structures

### Update Manifest
```json
{
  "product": "AetherOS",
  "version": "1.2.0",
  "channel": "stable",
  "releaseId": "abc123...",
  "commit": "def456...",
  "platforms": {
    "win32-x64": { "sha256": "...", "url": "...", "size": 123456, "signature": "..." }
  },
  "minimumVersion": "1.0.0",
  "releaseNotes": "...",
  "security": { "classification": "normal" },
  "rollout": { "percentage": 10, "startDate": "..." },
  "protocolVersion": 1,
  "timestamp": "2026-01-15T10:00:00Z",
  "signature": "base64..."
}
```

### Artifact Provenance
```json
{
  "builder": "github-actions",
  "buildTimestamp": "2026-01-15T10:00:00Z",
  "buildWorkflow": "release.yml",
  "dependencies": [
    { "name": "electron", "version": "40.10.6", "hash": "..." }
  ],
  "sbomHash": "sha256:..."
}
```

## Error Codes

| Code | Description | Recoverable |
|------|-------------|-------------|
| `NETWORK_FAILURE` | Network error during check/download | Yes |
| `MANIFEST_INVALID` | Manifest structure invalid | No |
| `SIGNATURE_INVALID` | Signature verification failed | No |
| `HASH_MISMATCH` | Artifact hash mismatch | No |
| `UNSUPPORTED_PLATFORM` | No artifact for platform | No |
| `INSUFFICIENT_DISK` | Not enough disk space | Yes |
| `PERMISSION_DENIED` | Elevation required/denied | Yes |
| `INSTALL_FAILURE` | Installer returned error | Maybe |
| `MIGRATION_FAILURE` | Data migration failed | No |
| `HEALTH_CHECK_FAILURE` | Post-install checks failed | Yes (rollback) |
| `CRASH_LOOP` | Repeated crashes post-update | Yes (auto-rollback) |
| `ROLLBACK_FAILURE` | Rollback failed | No |
| `REVOKED_RELEASE` | Release revoked by server | No |
| `DOWNGRADE_FORBIDDEN` | Downgrade not allowed | No |

## Testing Strategy

### Unit Tests
- Semver parsing/comparison
- Manifest verification
- Hash verification
- Signature verification (mocked)
- State machine transitions

### Integration Tests
- Check → Download → Verify → Stage → Install → Health Check
- Rollback scenarios
- Interrupted download recovery
- Corrupted artifact rejection
- Invalid signature rejection

### Platform Tests
- Windows: NSIS/MSI install/upgrade/uninstall
- macOS: DMG/PKG install with Gatekeeper
- Linux: DEB/RPM/AppImage/Flatpak
- Web: SW update cycle
- Mobile: Store coordination (mock)

### Security Tests
- Malicious manifest rejection
- Modified artifact rejection
- Downgrade attack prevention
- Revoked release rejection
- MITM attempt detection

### Chaos Tests
- Interrupted download (network kill)
- Process kill during install
- Machine reboot during install
- Disk full during download
- Clock skew

## Rollback Strategy

### Pre-Install Snapshot
```
recordPreUpdateSnapshot({
  currentVersion: "1.1.0",
  stateGeneration: 42,
  schemaGeneration: 7,
  updateId: "abc123",
  artifactHash: "sha256:...",
  recordedAt: "2026-01-15T10:00:00Z"
})
```

### Rollback Decision
```typescript
rollbackDecision({
  snapshot,
  healthCheckPassed: false,
  userDataChangedSince: true
})
// Returns: { action: 'rollback-app-only', reason: '...', restoreVersion: '1.1.0' }
```

## Monitoring & Telemetry

### Metrics
- `update_checks_total` - Check attempts
- `update_available_total` - Updates found
- `update_download_success_total` / `update_download_failure_total`
- `update_install_success_total` / `update_install_failure_total`
- `update_rollback_total`
- `update_duration_seconds` - Per phase

### Health Checks
- Process launch
- IPC connectivity
- Backend connectivity
- Storage access
- Config integrity
- Update subsystem self-check

## File Structure

```
apps/desktop/src/updater/
├── types.ts                 # Core type definitions
├── semver.ts                # Semantic versioning
├── manifest-verifier.ts     # Manifest verification
├── platform-adapter.ts      # Adapter interface
├── update-manager.ts        # Main orchestrator
├── update-store.ts          # Nanostores state
├── ipc-handlers.ts          # Main process IPC
├── UpdateUI.tsx             # React UI components
├── platforms/
│   ├── windows/windows-adapter.ts
│   ├── macos/macos-adapter.ts
│   ├── linux/linux-adapter.ts
│   ├── web/web-adapter.ts
│   └── mobile/mobile-adapter.ts
services/update/
├── update-server.ts         # Update server implementation
```

## Integration Points

- **Master 61**: Durable state checkpoints before migrations
- **Master 60**: Identity, authorization, secrets, audit
- **Master 63**: Design system, accessibility, dark mode
- **Master 70**: E2E update journeys (U01-U10)
- **Master 71**: Performance benchmarks for update operations
- **Master 72**: Security red team testing
- **Master 73**: Signing, SBOM, provenance integration