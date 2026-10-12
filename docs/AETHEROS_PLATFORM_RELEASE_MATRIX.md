# AetherOS Platform Release Matrix

Master Prompt 34. Statuses are evidence-based from actual CI runs (2026-08-25).

Status vocabulary:

| Term | Meaning |
|---|---|
| `actual` | Verified in this repository/environment with recorded commands |
| `CI-PASS` | GitHub Actions job completed successfully with executable evidence |
| `CI-FAIL` | GitHub Actions job failed with recorded error evidence |
| `CI-CONFIGURED` | Workflow YAML valid, jobs defined, but not yet executed successfully |
| `BLOCKED_BY_ENVIRONMENT` | Source/config complete and validated statically; producing the artifact requires hardware/OS this environment lacks |
| `blocked-signing` | Artifact builds unsigned; signing requires real certificates/secrets |

## Master table

| Platform | Source | Build | Tests | Artifact | Hash | Signing | Provenance | Status |
|----------|--------|-------|-------|----------|------|---------|------------|--------|
| Windows desktop | actual (`apps/desktop`, Electron 40) | CI-FAIL (run 32806797641: renderer tests fail @aetheros/shared resolution) | CI-FAIL (same) | NOT-PRODUCED | NOT-GENERATED | blocked-signing | NOT-GENERATED | SOURCE-PASS / CI-CONFIGURED / CI-BUILD-FAIL / RELEASE-BLOCKED-SIGNING |
| Linux desktop | actual (same codebase; `build.linux` AppImage/deb/rpm; `electron/linux-session.cjs` capability gating) | CI-FAIL (run 32806797641: renderer tests fail @aetheros/shared resolution) | CI-FAIL (same) | NOT-PRODUCED | NOT-GENERATED | n/a (typically unsigned) | NOT-GENERATED | SOURCE-PASS / CI-CONFIGURED / CI-BUILD-FAIL |
| macOS desktop | actual (same codebase; `build.mac` DMG/ZIP/PKG) | CI-FAIL (run 32806797641: renderer tests fail @aetheros/shared resolution) | CI-FAIL (same) | NOT-PRODUCED | NOT-GENERATED | blocked-signing | NOT-GENERATED | SOURCE-PASS / CI-CONFIGURED / CI-BUILD-FAIL |
| iOS | actual (`apps/ios` XcodeGen project: SwiftUI app, 11 required screens, 5 XCTest files) | CI-PASS (run 32808054969: Xcode 26.6, iOS 26.5 simulator) | CI-FAIL (run 32808054969: Swift compilation error in test code) | NOT-PRODUCED | NOT-GENERATED | blocked-signing (Config.xcconfig placeholders) | NOT-GENERATED | SOURCE-PASS / BUILD-PASS / TEST-FAIL / CI-CONFIGURED |

## Regression baselines (this tree, 2026-08-25)

| Suite | Result | Command |
|---|---|---|
| Renderer (vitest) | 695/695 PASS (local) | `npm run test:ui` (apps/desktop) |
| Electron units (node --test) | 170/170 PASS (local) | `npm run test:desktop:platforms` |
| Python security | 351/351 PASS (local) | `python -m pytest tests/security` (venv) |
| Typecheck | PASS (local) | `npm run typecheck` |
| Lint | PASS (0 errors, 28 warnings) (local) | `npm run lint` |
| Entry JS size | ≤ 5 MB verified against current `dist/` build | see CI |

## Artifact verification

Recorded at commit `e3e9746` (latest CI runs).

| File | Size (B) | SHA-256 | Platform | Arch | Version |
|---|---|---|---|---|---|
| `apps/desktop/release/AetherOS-1.0.0-win-x64.exe` | 152,096,097 | `BB609665C6952267B4DDCA8391743C29E97DA6FA700FC019F0DF715B21C0CEB0` | Windows (NSIS installer) | x64 | 1.0.0 |
| `apps/desktop/release/AetherOS-1.0.0-win-x64.exe.blockmap` | 158,780 | `4B02BF05D29FCF312FBE5E8370A333D0658BAD75DEAEB44084D7E0A1638E2639` | Windows (delta blockmap) | x64 | 1.0.0 |

Linux/macOS/iOS artifact rows appear here ONLY after their CI jobs run and hashes are attached to a GitHub Release (`desktop-release.yml` / `ios-build.yml`). They must be genuine AppImage/deb/rpm binaries and iOS `.xcarchive` respectively — renamed Windows artifacts are forbidden.

## CI Run Evidence (2026-08-25)

### Linux (desktop-release.yml, run 32806797641)
- **Workflow**: AetherOS Desktop Release
- **Run ID**: 32806797641
- **Commit SHA**: e3e9746 (HEAD at time of run)
- **Runner**: ubuntu-latest (ubuntu-24.04)
- **Status**: Validate Linux Packaging Config ✅ PASS | Build Linux ❌ FAIL (renderer tests)
- **Tests**: Renderer tests failed - @aetheros/shared module resolution (TypeError: resolvePlatform is not a function)
- **Artifacts**: None produced
- **Hashes**: None generated

### macOS (desktop-release.yml, run 32806797641)
- **Runner**: macos-latest (macOS 26, arm64)
- **Status**: Build macOS ❌ FAIL (renderer tests)
- **Tests**: Renderer tests failed - @aetheros/shared module resolution (TypeError: resolvePlatform is not a function)
- **Artifacts**: None produced
- **Hashes**: None generated

### Windows (desktop-release.yml, run 32806797641)
- **Runner**: windows-latest (Windows Server 2025)
- **Status**: Build Windows 🔄 RUNNING (renderer tests in progress at last check)
- **Tests**: Renderer tests expected to fail - same @aetheros/shared resolution issue
- **Artifacts**: Not yet produced
- **Hashes**: None generated

### iOS (ios-build.yml, run 32808054969)
- **Workflow**: AetherOS iOS Build
- **Run ID**: 32808054969
- **Commit SHA**: e3e9746
- **Runner**: macos-latest (macOS 26, arm64, Xcode 26.6, iOS 26.5)
- **Status**: Validate iOS Project Config ✅ PASS | Build iOS app ✅ PASS | Run iOS unit tests ❌ FAIL
- **XCTest Result**: Swift compilation error - "Missing argument label 'message:' in call" in test code (AppStateTests.swift, DeepLinkTests.swift)
- **Tests Passed**: 0/0 (compilation failed before test execution)
- **Artifact**: Not produced (test step failed before archive step)
- **Hash**: None generated

### iOS (ios-build.yml, run 32807726935)
- **Run ID**: 32807726935
- **Status**: Validate iOS Project Config ✅ PASS | Build iOS app ✅ PASS | Run iOS unit tests ❌ FAIL (same Swift compilation error)

## Capability registry (Phase 5)

Single source of truth: `apps/shared/src/platform-capabilities.ts`
(consumed by desktop via `@aetheros/shared`; mirrored in Swift by
`apps/ios .../MobileCapability.swift`; mirrored for Linux sessions by
`electron/linux-session.cjs`). Contract tests:
`apps/desktop/src/lib/platform-capabilities.test.ts`.

| Capability | Windows | macOS | Linux X11 | Linux Wayland | iOS |
|---|---|---|---|---|---|
| browser | native | native | native | native | backend-mediated |
| terminal | native | native | native | native | backend-mediated |
| filesystem | native | native | native | native | unsupported |
| computerUse | native | native | native | unsupported | backend-mediated |
| notifications | native | native | native | native* | native |
| tray | native | native | native | limited* | unsupported |
| agentControl | native | native | native | native | native |
| taskSubmission | native | native | native | native | native |
| planPreview | native | native | native | native | native |
| confirmations | native | native | native | native | native |

\* Per-session nuance (WSLg/X11-forwarded/headless) lives in
`linux-session.cjs CAPABILITY_MATRIX`, which remains the runtime authority;
the shared registry mirrors its Wayland row.

## What each status upgrade requires

- **Linux → BUILD-PASS**: one successful `desktop-release.yml` ubuntu job attaching `AetherOS-*-linux-x64.{AppImage,deb,rpm}` + SHA-256 manifest.
- **macOS → BUILD-PASS**: one successful `desktop-release.yml` macos-latest job attaching `AetherOS-*-macOS-*.{dmg,zip,pkg}` + SHA-256 manifest.
- **iOS → TEST-PASS**: one successful green `xcodebuild test` run in `ios-build.yml` (requires fixing Swift test compilation error).
- **iOS → RELEASE-PASS**: Apple Developer credentials as GitHub secrets, signed archive, TestFlight upload record.
- **Windows → PRODUCTION-CERTIFIED**: Authenticode signature verification passing on the native verifier job (`sign-verify`), plus installer smoke test records.