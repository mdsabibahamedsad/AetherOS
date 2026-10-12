# AetherOS macOS Installation / Update / Signing / Notarization / Distribution

Install: DMG primary (background, Applications shortcut, branding),
ZIP + PKG built in CI (`desktop-release.yml` macos job + SHA256).
Requires Developer ID Application signature + notarytool notarization
+ staple + `spctl` Gatekeeper check — NONE executed here (BLOCKED —
APPLE SIGNING/NOTARIZATION CREDENTIALS). `gatekeeperAssess: false`
must be enabled once signing lands (P1).

Update: no live channel (no Sparkle/electron-updater integration);
channel-agnostic manifest validator from 64.1 applies. Rollback =
previous signed artifact reinstall + snapshot discipline.
Distribution: direct Developer ID download ONLY. App Store NOT pursued:
sandbox would break agent execution, filesystem, computer-use, MCP/A2A
(see SANDBOX decision); no submission, no claim.
