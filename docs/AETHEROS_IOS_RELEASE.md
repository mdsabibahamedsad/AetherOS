# AetherOS iOS Release

Status: **BLOCKED for production.** Source, tests, and CI scaffolding exist
(`apps/ios/`, `.github/workflows/ios-build.yml`), but no iOS build has ever
been executed (this repository was authored on Windows; Xcode requires
macOS). Nothing in this document may be upgraded from BLOCKED without
executable evidence.

## 1. Prerequisites

| Item | Status |
|---|---|
| Apple Developer account + Team ID | operator-provided — placeholders in `apps/ios/Config.xcconfig`; NEVER commit real values |
| App ID `com.aetheros.mobile` with Push Notifications capability | to be created by the operator |
| Provisioning profiles (dev + distribution) | via Xcode automatic signing once Team ID is set |
| macOS runner / Mac with Xcode 15.4+ | CI has `macos-latest`; local builds need a Mac |

Fabricating or committing any credential is prohibited.

## 2. Build & test

```bash
brew install xcodegen
cd apps/ios && xcodegen generate

# Simulator (no signing required):
xcodebuild -project AetherOS.xcodeproj -scheme AetherOS \
  -destination 'platform=iOS Simulator,name=iPhone 15' test

# Device development build (requires Team ID in Config.xcconfig):
xcodebuild -project AetherOS.xcodeproj -scheme AetherOS \
  -destination 'platform=iOS' build
```

CI: `.github/workflows/ios-build.yml` generates the project and runs the
XCTest suite unsigned on a macOS runner simulator (`CODE_SIGNING_ALLOWED=NO`
for the dev record). It produces NO signed archive by design.

## 3. Test evidence required before any readiness claim

- [ ] XCTest suite green on simulator (attach xcodebuild result bundle)
- [ ] Manual pass on simulator: connect to a real `api_server`, submit run,
      receive SSE events, resolve an approval through all four choices
- [ ] Offline matrix: airplane-mode submit → queued → retry on reconnect;
      UI shows only honest states
- [ ] Deep link matrix: each host routes; malformed/unknown dropped
- [ ] Keychain round-trip on device; token absent from logs/screenshots
- [ ] Accessibility audit: VoiceOver order on ConfirmationCard, Dynamic Type
      at largest sizes, 44pt touch targets, contrast in Light/Dark
- [ ] Real-device smoke test (iPhone, current iOS major)

## 4. Distribution ladder

1. **Development** — simulator + registered devices. Available now.
2. **Internal testing** — ad-hoc/TestFlight internal group. Requires Apple
   credentials.
3. **TestFlight** — external beta. Requires App ID, provisioning, and
   export-compliance answers.
4. **App Store** — full review. NOT claimed until 2–3 have real evidence.

Archive command (only when credentials exist):

```bash
xcodebuild -project AetherOS.xcodeproj -scheme AetherOS \
  -configuration Release -archivePath build/AetherOS.xcarchive archive
```

## 5. Notifications bridge (planned)

APNs delivery of approval/task events requires a backend component that does
not exist yet. The payload CONTRACT is fixed in
`docs/AETHEROS_CROSS_PLATFORM_API.md` §7 (event kind + IDs only, no secrets).
Do not ship push claims before the bridge exists and is tested.
