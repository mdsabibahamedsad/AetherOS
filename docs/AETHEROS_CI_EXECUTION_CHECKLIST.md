# AetherOS Cross-Platform CI Execution Checklist
## For External Execution (GitHub Actions)

**Commit:** 4b715f534faeaa5ea3ab538b135ed26f45bf5641
**Date:** 2026-08-25
**Prepared by:** Local validation (Windows host)

---

## Prerequisites

- [ ] GitHub repository with Actions enabled
- [ ] Write permissions to trigger workflow_dispatch
- [ ] For Windows signing: Azure credentials (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID, AZURE_SIGNING_ENDPOINT, AZURE_SIGNING_ACCOUNT_NAME, AZURE_SIGNING_CERTIFICATE_PROFILE) as secrets/vars
- [ ] For iOS signing (optional): Apple Developer Team ID, certificates, provisioning profiles as secrets

---

## Workflow 1: Desktop Release (Linux + Windows + macOS)

**File:** `.github/workflows/desktop-release.yml`
**Trigger:** `workflow_dispatch` with inputs: `version` (e.g., "1.0.0"), `prerelease` (boolean)

### Jobs and Dependencies

```
validate-linux-config (ubuntu-latest)
    ↓
build-linux (ubuntu-latest) ──────────→ upload artifacts, create release
build-windows (windows-latest) ───────→ upload artifacts, create release
build-macos (macos-latest) ───────────→ upload artifacts, create release
```

### Execution Steps

1. Navigate to Actions → "AetherOS Desktop Release" → "Run workflow"
2. Enter version: `1.0.0`
3. Set prerelease: `true` (for initial validation)
4. Click "Run workflow"
5. Monitor all three build jobs

### Expected Outputs (Linux)

- **Artifacts:** `AetherOS-1.0.0-linux-x64.AppImage`, `AetherOS-1.0.0-linux-x64.deb`, `AetherOS-1.0.0-linux-x64.rpm`
- **Validation:** `linux-artifacts.sha256`, `linux-sbom.spdx.json`
- **Tests:** 695 renderer tests, 170 electron tests
- **Release:** GitHub Release with tag `v1.0.0` and Linux artifacts attached

### Expected Outputs (Windows)

- **Artifacts:** `AetherOS-1.0.0-win-x64.exe` (NSIS), `AetherOS-1.0.0-win-x64.msi`, `AetherOS-1.0.0-win-x64-portable.exe`
- **Validation:** `windows-artifacts.sha256`
- **Tests:** 695 renderer tests, 170 electron tests
- **Release:** GitHub Release with Windows artifacts attached

### Expected Outputs (macOS)

- **Artifacts:** `AetherOS-1.0.0-macOS-x64.dmg`, `AetherOS-1.0.0-macOS-x64.zip`, `AetherOS-1.0.0-macOS-x64.pkg`
- **Validation:** `macos-artifacts.sha256`
- **Tests:** 695 renderer tests, 170 electron tests
- **Release:** GitHub Release with macOS artifacts attached

### Verification Commands (post-build)

```bash
# Verify Linux artifacts
file AetherOS-1.0.0-linux-x64.AppImage
dpkg-deb --info AetherOS-1.0.0-linux-x64.deb
rpm -qip AetherOS-1.0.0-linux-x64.rpm
sha256sum -c linux-artifacts.sha256

# Verify Windows artifacts
# (on Windows) sigcheck -a AetherOS-1.0.0-win-x64.exe
sha256sum -c windows-artifacts.sha256

# Verify macOS artifacts
hdiutil verify AetherOS-1.0.0-macOS-x64.dmg
sha256sum -c macos-artifacts.sha256
```

---

## Workflow 2: iOS Build

**File:** `.github/workflows/ios-build.yml`
**Trigger:** `workflow_dispatch` with inputs: `version` (e.g., "1.0.0"), `prerelease` (boolean)

### Jobs and Dependencies

```
validate-ios-config (macos-latest)
    ↓
build-ios (macos-latest) ─────────────→ upload artifacts, create release
```

### Execution Steps

1. Navigate to Actions → "AetherOS iOS Build" → "Run workflow"
2. Enter version: `1.0.0`
3. Set prerelease: `true` (for initial validation)
4. Click "Run workflow"
5. Monitor build and test jobs

### Expected Outputs

- **Build:** Unsigned `.xcarchive` at `AetherOS.xcarchive`
- **Tests:** All XCTest targets passing (expected ~15-20 tests across 5 test files)
- **Artifact:** `aetheros-ios-unsigned.tar.gz` (compressed archive)
- **Validation:** `ios-artifacts.sha256`, `TestResults.xcresult`
- **Release:** GitHub Release with tag `v1.0.0` and iOS artifacts attached, labeled "UNSIGNED CI BUILD"

### Test Coverage Areas (from AetherOSTests/)

- `APIClientTests.swift` - Request building, headers, idempotency, capabilities decoding, run status mapping
- `APIErrorTests.swift` - HTTP status mapping, timeout mapping, error message sanitization, connection state machine, plan step parsing
- `AppStateTests.swift` - HTTPS enforcement, error sanitization
- `DeepLinkTests.swift` - Known hosts, query parameters, rejection of unknown/illegal URLs
- `OfflineQueueTests.swift` - Backoff policy, failure recording, client error handling, max attempts, UI state mapping, idempotency keys

### Verification Commands (post-build)

```bash
# Verify archive structure
tar -tzf aetheros-ios-unsigned.tar.gz | head -20

# Verify bundle identifier
/usr/libexec/PlistBuddy -c "Print :ApplicationProperties:CFBundleIdentifier" AetherOS.xcarchive/Info.plist
# Expected: com.aetheros.mobile

# Verify version
/usr/libexec/PlistBuddy -c "Print :ApplicationProperties:CFBundleShortVersionString" AetherOS.xcarchive/Info.plist
# Expected: 1.0.0

# Verify SHA-256
sha256sum -c ios-artifacts.sha256
```

---

## Post-Execution Evidence Collection

After both workflows complete successfully, record:

### Linux CI Evidence
- [ ] Workflow Run ID: `__________`
- [ ] Commit SHA: `4b715f534faeaa5ea3ab538b135ed26f45bf5641`
- [ ] Runner: `ubuntu-24.04` (or similar)
- [ ] Duration: `__________`
- [ ] Renderer tests: `695/695 PASS`
- [ ] Electron tests: `170/170 PASS`
- [ ] Artifact names: `AetherOS-1.0.0-linux-x64.{AppImage,deb,rpm}`
- [ ] Artifact SHA-256 hashes: (from `linux-artifacts.sha256`)
- [ ] SBOM generated: `linux-sbom.spdx.json`
- [ ] Release created: `v1.0.0` with Linux artifacts

### Windows CI Evidence
- [ ] Workflow Run ID: `__________`
- [ ] Commit SHA: `4b715f534faeaa5ea3ab538b135ed26f45bf5641`
- [ ] Runner: `windows-latest`
- [ ] Duration: `__________`
- [ ] Renderer tests: `695/695 PASS`
- [ ] Electron tests: `170/170 PASS`
- [ ] Artifact names: `AetherOS-1.0.0-win-x64.{exe,msi,portable.exe}`
- [ ] Artifact SHA-256 hashes: (from `windows-artifacts.sha256`)
- [ ] Release created: `v1.0.0` with Windows artifacts

### macOS CI Evidence
- [ ] Workflow Run ID: `__________`
- [ ] Commit SHA: `4b715f534faeaa5ea3ab538b135ed26f45bf5641`
- [ ] Runner: `macos-latest`
- [ ] Duration: `__________`
- [ ] Renderer tests: `695/695 PASS`
- [ ] Electron tests: `170/170 PASS`
- [ ] Artifact names: `AetherOS-1.0.0-macOS-x64.{dmg,zip,pkg}`
- [ ] Artifact SHA-256 hashes: (from `macos-artifacts.sha256`)
- [ ] Release created: `v1.0.0` with macOS artifacts

### iOS CI Evidence
- [ ] Workflow Run ID: `__________`
- [ ] Commit SHA: `4b715f534faeaa5ea3ab538b135ed26f45bf5641`
- [ ] Runner: `macos-latest` (Xcode 16.0)
- [ ] Duration: `__________`
- [ ] XCTest results: `X/Y tests passed` (record exact counts)
- [ ] Artifact name: `aetheros-ios-unsigned.tar.gz`
- [ ] Artifact SHA-256 hash: (from `ios-artifacts.sha256`)
- [ ] Bundle ID verified: `com.aetheros.mobile`
- [ ] Version verified: `1.0.0`
- [ ] Release created: `v1.0.0` with iOS artifacts (labeled UNSIGNED CI BUILD)

---

## Regression Gate Verification (Local - Already Complete)

| Suite | Baseline | Local Result | Status |
|-------|----------|--------------|--------|
| Renderer (vitest) | 695/695 | 695/695 PASS | ✅ |
| Electron units | 170/170 | 170/170 PASS | ✅ |
| Python security | 351/351 | 351/351 PASS | ✅ |
| Typecheck | PASS | PASS | ✅ |
| Lint | 0 errors | 0 errors (28 warnings) | ✅ |
| Entry JS size | ≤ 5 MB | Not measured locally | ⚠️ CI only |

---

## Signing Status

| Platform | Signing Configured | Secrets Present | Status |
|----------|-------------------|-----------------|--------|
| Windows (Authenticode) | Yes (`signAndEditExecutable: false` in config) | ❌ Not in this env | BLOCKED |
| macOS (Notarization) | Yes (hardened runtime, entitlements) | ❌ Not in this env | BLOCKED |
| iOS (App Store) | Placeholders only (`Config.xcconfig`) | ❌ Not in this env | BLOCKED |

**Note:** Unsigned artifacts MUST NOT be promoted to production.

---

## Provenance (If Workflow Supports)

- [ ] SBOM generated (desktop-release.yml includes anchore/sbom-action)
- [ ] Artifact attestation (configured via `id-token: write`, `attestations: write`)
- [ ] Digest subjects recorded in SHA-256 manifests

---

## Blockers for Production Certification

1. **Linux artifacts not built** - Requires GitHub Actions ubuntu-latest runner
2. **iOS artifacts not built** - Requires GitHub Actions macos-latest runner with Xcode
3. **Windows signing** - Requires Azure Artifact Signing secrets
4. **macOS notarization** - Requires Apple Developer credentials
5. **iOS App Store signing** - Requires Apple Developer Team ID + certificates

---

## Next Steps

1. ✅ Workflows created and validated locally
2. ✅ Desktop regression tests pass locally (Windows host)
3. ⏳ **EXECUTE** `desktop-release.yml` on GitHub Actions (Linux, Windows, macOS)
4. ⏳ **EXECUTE** `ios-build.yml` on GitHub Actions (macOS + Xcode)
5. ⏳ Collect CI evidence (Run IDs, artifact hashes, test counts)
6. ⏳ Update `AETHEROS_CROSS_PLATFORM_EXECUTION_REPORT.md` with real evidence
7. ⏳ Update `AETHEROS_PLATFORM_RELEASE_MATRIX.md` with evidence-based statuses
8. ⏳ Create `AETHEROS_RELEASE_ARTIFACT_MANIFEST.json` with real values
8. ⏳ Determine final verdict (PRODUCTION_BLOCKED until Linux+iOS artifacts exist)

---

## Final Verdict Criteria

**PRODUCTION_CERTIFIED** = ALL of:
- [ ] Linux: BUILD-PASS + TEST-PASS + ARTIFACT-PASS + SHA-256 recorded
- [ ] Windows: BUILD-PASS + TEST-PASS + ARTIFACT-PASS + SHA-256 recorded + SIGNING verification
- [ ] macOS: BUILD-PASS + TEST-PASS + ARTIFACT-PASS + SHA-256 recorded
- [ ] iOS: TEST-PASS + ARTIFACT-PASS (unsigned) + SHA-256 recorded
- [ ] Shared contract tests pass
- [ ] No regressions vs baseline
- [ ] Provenance (SBOM + attestation) executed

**RELEASE_CANDIDATE** = Linux+iOS artifacts exist but signing incomplete

**PRODUCTION_BLOCKED** = Any mandatory evidence missing (current state)