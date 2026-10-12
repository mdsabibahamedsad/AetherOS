# AetherOS Update Security Model

## Threat Model

### Assets to Protect
1. **User Data** - Conversations, memories, configurations, credentials
2. **System Integrity** - Application code, runtime, dependencies
3. **Trust Chain** - Code signing certificates, update server keys
4. **Availability** - Continuous operation without forced downtime

### Adversaries
| Adversary | Capabilities | Motivation |
|-----------|--------------|------------|
| Network Attacker | MITM, DNS spoofing, BGP hijack | Inject malicious updates |
| Compromised CDN | Serve modified artifacts | Supply chain attack |
| Compromised Build | Inject malicious code at build time | Supply chain attack |
| Insider Threat | Access to signing keys | Targeted attacks |
| Malicious Update Server | Serve arbitrary manifests | Full control |

### Security Properties

| Property | Description |
|----------|-------------|
| **Authenticity** | Only authorized publisher can create valid updates |
| **Integrity** | Artifacts cannot be modified without detection |
| **Freshness** | Clients only accept newer versions (no downgrade) |
| **Authorization** | Updates only from configured channel |
| **Revocation** | Compromised releases can be blocked |
| **Auditability** | All updates traceable to source commit |
| **Recoverability** | Failed updates automatically rollback |

## Cryptographic Design

### Key Hierarchy

```
Root CA (Offline, Hardware Security Module)
  │
  ├── Update Server Signing Key (Online, HSM)
  │     └── Manifest Signatures
  │
  ├── Platform Code Signing Keys (Per-platform, HSM)
  │     ├── Windows: Authenticode (EV Certificate)
  │     ├── macOS: Developer ID Application + Notarization
  │     └── Linux: GPG Key for DEB/RPM, AppImageKit
  │
  └── Artifact Integrity Keys
        └── SHA-256 (manifest-embedded)
```

### Key Management

| Key | Storage | Rotation | Compromise Response |
|-----|---------|----------|---------------------|
| Root CA | Offline HSM | 5 years | Revoke all intermediates |
| Manifest Signing | Online HSM | 90 days | Revoke intermediate, rotate |
| Platform Signing | Per-platform HSM | 1 year | Platform-specific revocation |
| Build Keys | Ephemeral | Per build | SBOM attestation |

### Signature Algorithms

| Use Case | Algorithm | Parameters |
|--------|-----------|------------|
| Manifest | RSA-PSS-SHA256 | 4096-bit, MGF1-SHA256 |
| Manifest (alt) | Ed25519 | 256-bit |
| Windows Authenticode | RSA-SHA256 | 4096-bit, EV Cert |
| macOS Code Sign | RSA-SHA256 | 4096-bit, Developer ID |
| Linux DEB/RPM | RSA-SHA256 | 4096-bit, GPG |
| AppImage | RSA-SHA256 | 4096-bit, AppImageKit |
| Flatpak | Ed25519 | OSTree |

## Manifest Security

### Canonicalization
Before signing, manifests are canonicalized:
1. Remove `signature` field
2. Sort all object keys lexicographically
3. Serialize as compact JSON (no whitespace)
4. UTF-8 encode

### Verification Steps
1. Parse manifest JSON
2. Extract and decode `signature` field
3. Canonicalize manifest (without signature)
4. Verify signature using trusted public key
5. Check `protocolVersion` compatibility
6. Verify required fields present
7. Validate semantic version format
8. Check `minimumVersion` compatibility
9. Verify `channel` matches client configuration
10. Check `timestamp` within acceptable window (±24h)
11. Verify `releaseId` uniqueness (prevent replay)
12. Check `rollout.killSwitch` is false
13. Verify `security.classification` handling

### Anti-Replay
- `releaseId` must be unique (cryptographically random)
- Clients track seen `releaseId` values
- Server maintains published release registry

## Artifact Security

### Verification Chain
```
Manifest Signature
    │
    ├── Artifact SHA-256 (in manifest)
    │     │
    │     ├── Downloaded Artifact Hash
    │     │     │
    │     │     ├── Platform Signature (Authenticode/codesign/dpkg-sig)
    │     │     │     │
    │     │     │     ├── Publisher Certificate
    │     │     │     │     │
    │     │     │     │     ├── Certificate Chain
    │     │     │     │     │     │
    │     │     │     │     │     └── Root CA (Platform Trust Store)
    │     │     │     │
    │     │     │     └── Timestamp (RFC 3161)
    │     │     │
    │     │     └── Provenance Verification
    │     │           │
    │     │           ├── Builder Identity
    │     │           ├── Build Timestamp
    │     │           ├── Build Workflow
    │     │           └── SBOM Hash
```

### Platform-Specific Verification

#### Windows
```powershell
# Authenticode verification
Get-AuthenticodeSignature -FilePath artifact.exe | Where-Object {$_.Status -eq 'Valid'}

# Certificate chain validation
$cert = (Get-AuthenticodeSignature artifact.exe).SignerCertificate
$cert.Verify() -and $cert.NotAfter -gt (Get-Date)
```

#### macOS
```bash
# Code signature verification
codesign --verify --deep --strict --verbose=2 artifact.app

# Notarization check
spctl --assess --type execute --verbose artifact.app

# Team identifier
codesign -d -vvvv artifact.app 2>&1 | grep "TeamIdentifier"
```

#### Linux (DEB)
```bash
# Package signature
dpkg-sig --verify package.deb

# Or GPG
gpg --verify package.deb.sig package.deb
```

#### Linux (RPM)
```bash
rpm --checksig package.rpm
# Should show: RSA sha256 OK
```

#### AppImage
```bash
./artifact.AppImage --appimage-signature
# Verify embedded signature block
```

### Hash Verification
```typescript
async function verifyHash(filePath: string, expectedSha256: string): Promise<boolean> {
  const buffer = await fs.readFile(filePath);
  const hash = crypto.createHash('sha256').update(buffer).digest('hex');
  return hash.toLowerCase() === expectedSha256.toLowerCase();
}
```

## Transport Security

### TLS Requirements
- **Minimum**: TLS 1.2
- **Preferred**: TLS 1.3
- **Cipher Suites**: TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256, TLS_AES_128_GCM_SHA256
- **Certificate**: Valid, non-expired, matching hostname
- **Validation**: Full chain validation, hostname verification

### Certificate Pinning
```typescript
const PINNED_HASHES = [
  'sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', // Primary
  'sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=', // Backup
];

function validatePinnedCert(cert: X509Certificate): boolean {
  const hash = 'sha256/' + btoa(
    crypto.createHash('sha256').update(cert.raw).digest()
  );
  return PINNED_HASHES.includes(hash);
}
```

### HSTS
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- Preload list submission for updates.aetheros.com

## Channel Security

### Channel Isolation
- Each channel has independent key rollout
- `nightly`/`dev` can use test keys
- `stable`/`enterprise` require production keys
- Cross-channel promotion requires re-signing

### Prerelease Handling
- `allowPrerelease: false` (default) blocks alpha/beta/nightly
- Enterprise channel requires explicit opt-in
- Channel mismatch = verification failure

## Revocation System

### Kill Switch
```json
{
  "rollout": {
    "percentage": 10,
    "killSwitch": true
  }
}
```
- Immediate effect on all clients
- Clients check kill switch before download
- Server-side: instant global stop

### Release Revocation
```json
{
  "status": "revoked",
  "revokedAt": "2026-01-15T10:00:00Z",
  "revocationReason": "Critical security vulnerability in v1.2.0"
}
```
- Clients check revocation status before install
- Revoked releases never installed
- Auto-rollback if already installed (on next check)

### Certificate Revocation
- OCSP stapling for code signing certificates
- CRL distribution points in certificates
- Short-lived certificates (90 days) for online signing

## Build Security

### Provenance
Every release includes:
```json
{
  "provenance": {
    "builder": "github-actions",
    "buildTimestamp": "2026-01-15T10:00:00Z",
    "buildWorkflow": ".github/workflows/release.yml@refs/heads/main",
    "buildInvocationId": "github-actions-run-12345",
    "dependencies": [
      { "name": "electron", "version": "40.10.6", "hash": "sha256:..." }
    ],
    "sbomHash": "sha256:...",
    "slsaLevel": 3
  }
}
```

### SLSA Compliance
- **Level 1**: Build scripted, provenance generated
- **Level 2**: Hosted build service, tamper-resistant
- **Level 3**: Hardened build, non-falsifiable provenance
- **Level 4**: Hermetic, reproducible, two-party review

### SBOM
- Format: CycloneDX 1.5+ / SPDX 2.3+
- Includes: Direct + transitive dependencies
- Linked to release via `sbomHash` in manifest
- Published to transparency log

## Client Security

### Update Manager Hardening
- Runs in main process (not renderer)
- IPC validation for all renderer requests
- No arbitrary code execution from update metadata
- Release notes treated as untrusted (sanitized display)

### IPC Security
```typescript
// Renderer → Main IPC validation
ipcMain.handle('update:install', async (event, options) => {
  // Validate sender
  if (!isTrustedSender(event.sender)) throw new Error('Unauthorized');
  
  // Validate options schema
  const validated = InstallOptionsSchema.parse(options);
  
  // Check permissions
  if (!await hasInstallPermission()) throw new Error('Permission denied');
  
  return updateManager.installUpdate(validated);
});
```

### Data Protection
- Update configs encrypted at rest (OS keychain/DPAPI)
- No secrets in update artifacts
- Telemetry opt-in, minimal data

## Server Security

### Update Server Hardening
- Minimal attack surface (manifest + artifact serving only)
- No database (static files + signed metadata)
- Read-only artifact storage
- Rate limiting + DDoS protection
- Audit logging all requests

### Signing Service
- Isolated from public network
- HSM-backed key operations
- Quorum authorization for key use
- Audit trail all signing operations

### Artifact Storage
- Immutable object storage (S3/GCS with Object Lock)
- Content-addressed URLs (SHA-256 in path)
- No overwrite/delete for published artifacts
- Cross-region replication

## Incident Response

### Compromise Detection
1. Anomalous download patterns
2. Signature verification failures reported
3. Telemetry health check failures
4. External security reports

### Response Procedures

| Severity | Response Time | Actions |
|----------|---------------|---------|
| Critical (active exploit) | < 1 hour | Kill switch, revoke release, emergency patch |
| High (vulnerability found) | < 4 hours | Revoke affected, prepare patch, notify |
| Medium (potential issue) | < 24 hours | Investigate, prepare mitigation |
| Low (defense in depth) | < 1 week | Schedule fix, update docs |

### Recovery
1. Identify scope of compromise
2. Revoke compromised keys/releases
3. Rotate keys from offline root
4. Rebuild from clean source
5. Re-sign with new keys
6. Publish with emergency channel
7. Monitor rollout health
8. Post-incident review

## Compliance

### Standards Alignment
- **NIST SP 800-53**: CM-11 (User-Installed Software), SI-7 (Software Integrity)
- **NIST SP 800-190**: Application Container Security (for containerized components)
- **SLSA**: Supply Chain Levels for Software Artifacts
- **in-toto**: Software Supply Chain Integrity
- **Sigstore**: Transparency log for signatures

### Audit Requirements
- All signing operations logged
- Key access logged
- Release publication logged
- Rollout changes logged
- Retention: 7 years minimum

## Secure Development Practices

### Code Review Requirements
- All update-related code: 2 approvals required
- Security team review for crypto changes
- Threat model update for architecture changes

### Dependency Management
- Pinned dependencies with hashes
- Automated vulnerability scanning (Dependabot/GitHub Advisory)
- No unpinned `latest` tags in production builds
- License compliance verification

### Testing Requirements
- Unit tests for all verification logic
- Integration tests with known-good/bad artifacts
- Fuzzing for parser/verifier code
- Annual penetration test of update system

## Incident Runbooks

### Runbook: Malicious Artifact Detected
1. Activate kill switch for affected release
2. Revoke release on server
3. Identify affected clients via telemetry
4. Push emergency notification
5. Investigate build pipeline compromise
6. Rotate signing keys if build compromised
7. Rebuild from clean source
8. Publish emergency fix

### Runbook: Signing Key Compromise
1. Revoke intermediate certificate
2. Activate backup key from offline root
3. Re-sign all active releases
4. Update client trust anchors (if root rotated)
5. Monitor rollout for verification failures
6. Post-incident key rotation review

### Runbook: Update Server Compromise
1. Take server offline
2. Activate backup update server
3. Verify artifact integrity from backup
4. Rotate server TLS certificates
5. Audit all served manifests
6. Rebuild server from clean image
7. Restore service with new keys

## Security Testing

### Automated
- SAST on every PR (CodeQL, Semgrep)
- Dependency scanning (OSV, GitHub Advisory)
- Container scanning (Trivy)
- Secret scanning (GitLeaks, TruffleHog)

### Manual
- Annual penetration test
- Annual red team exercise (Master 72)
- Supply chain attack simulation
- Key compromise tabletop exercise

### Continuous
- Signature verification in CI
- Reproducible build verification
- Provenance attestation verification
- SBOM completeness check