# AetherOS Desktop Security

## Security Philosophy

AetherOS Desktop follows a defense-in-depth approach:
1. **Sandboxing:** Renderer processes are sandboxed with context isolation
2. **Least Privilege:** Each component has only the permissions it needs
3. **Secure by Default:** Security features are enabled out of the box
4. **Defense in Depth:** Multiple layers of security controls

## Architecture Security

### Process Isolation
```
┌──────────────────┐     Restricted IPC      ┌──────────────────┐
│   Main Process   │ ◄──────────────────────► │ Renderer Process │
│  (Node.js)       │    (contextBridge)       │  (Chromium)      │
│  - File System   │                          │  - UI Rendering  │
│  - Native APIs   │                          │  - No Node.js    │
│  - OS Dialogs    │                          │  - Sandboxed     │
└──────────────────┘                          └──────────────────┘
```

### Key Protections
- **Context Isolation:** Renderer cannot access main process APIs directly
- **Node Integration Disabled:** No `require()` in renderer
- **Sandbox Enabled:** Chromium sandbox restricts renderer capabilities
- **CSP Headers:** Content Security Policy prevents XSS and data injection

### IPC Security
- All IPC channels must match the allowlist pattern
- Path arguments are validated to prevent traversal attacks
- Channel names are validated against regex patterns
- No wildcard channel handlers

## Code Signing

### macOS
- Apple Developer ID certificate (Developer ID Application)
- Notarization by Apple for Gatekeeper compatibility
- Hardened runtime with proper entitlements
- Entitlements restrict JIT, unsigned executable memory, and debugging

### Windows
- Authenticode certificate (Extended Validation recommended)
- Dual-signing (SHA-256 + SHA-1) for backward compatibility
- Timestamped signatures for longevity

### Linux
- GPG signatures for deb and rpm packages
- Checksum files for AppImage verification

## Data Security

### Storage
- **Tokens:** Encrypted using OS keychain (Win Credential Manager, macOS Keychain, Linux secret-service)
- **Configuration:** JSON files in app data directory
- **Cache:** Non-sensitive cached data in cache directory
- **Logs:** Application logs (no secrets written)

### Encryption
- Token encryption: AES-256-GCM via OS keychain
- Transport: TLS 1.3 for all network communication
- Local IPC: Unix domain sockets / named pipes (no encryption needed)

### Sensitive File Protection
- The following are never exposed to the renderer:
  - `.env` files
  - SSH keys (`id_rsa`, `id_ed25519`, etc.)
  - GPG keys
  - Token/key files

## Update Security

### Update Verification
- Updates downloaded over HTTPS
- Update package signature verification
- Checksum validation after download
- Certificate pinning for update server

### Auto-Update Channels
| Channel | Update Server | Signing | Distribution |
|---------|--------------|---------|-------------|
| Stable | production | Required | Full rollout |
| Beta | production | Required | Limited rollout |
| Nightly | staging | Optional | Developer use |

## Crash Reporting (Opt-in)

Crash reports contain:
- Stack trace at crash point
- System information (OS, architecture, memory)
- Application version
- **No personal data, no file contents, no credentials**

## Security Checklist for Deployment

### Pre-Deployment
- [ ] Verify code signing certificates are valid
- [ ] Run security audit: `node scripts/security/audit-security.mjs`
- [ ] Run dependency audit: `node scripts/security/audit-dependencies.mjs`
- [ ] Check for secrets in codebase: `node scripts/security/check-secrets.mjs`
- [ ] Verify CSP headers are configured
- [ ] Confirm sandbox is enabled
- [ ] Validate IPC allowlist

### Post-Deployment
- [ ] Verify code signature: `codesign -dvvv /Applications/AetherOS.app`
- [ ] Verify notarization: `spctl --assess --verbose /Applications/AetherOS.app`
- [ ] Check Windows Authenticode: `Get-AuthenticodeSignature AetherOS.exe`
- [ ] Verify Linux GPG signatures
- [ ] Run health check: `curl http://localhost:48765/health`

## Vulnerability Disclosure

### Reporting a Vulnerability
1. **Do NOT** create a public GitHub issue
2. Email: security@aetheros.dev
3. Encrypt with our PGP key (available on security.txt)

### Response Timeline
- **24 hours:** Acknowledgment of receipt
- **7 days:** Initial assessment and mitigation plan
- **30 days:** Fix deployed to affected versions
- **90 days:** Public disclosure after patch

## Related Documents
- [Security Audit Report](docs/SECURITY_AUDIT.md)
- [Dependency Audit Report](docs/DEPENDENCY_AUDIT.md)
- [Privacy Policy](PRIVACY.md)
- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)

## Version History
| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-Q3 | Initial security baseline for v1 release |
