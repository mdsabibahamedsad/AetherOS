# AETHEROS Master 65 — macOS Audit

Environment note: this audit ran on Windows. All macOS-runtime claims
are BLOCKED — MACOS ENVIRONMENT unless they are source-verified
(configuration, scripts, CI definitions) or executed cross-platform
unit tests. Nothing is fabricated.

## 1–2. Architecture / runtime — PARTIAL

Electron 40 (`apps/desktop`), hardened windows verified in Master 64
(sandbox/contextIsolation/no-Node). mac builder: DMG/ZIP/PKG ×
x64+arm64, `hardenedRuntime: true`, `gatekeeperAssess: false`
(P1: enable post-signing), category developer-tools, bundle id from
`appId com.aetheros.aetheros`, `afterSign: notarize.cjs` (notarytool +
stapler, secret-gated).

## 3. Packaging — PARTIAL (config verified, execution blocked)

DMG/ZIP/PKG targets ×2 arch in `package.json#build.mac`. CI
(`desktop-release.yml` macos job) builds + asserts DMG + SHA256.
No artifact produced here: BLOCKED — MACOS ENVIRONMENT.

## 4–6. Signing / notarization / Apple Silicon — BLOCKED

No Developer ID here (BLOCKED — APPLE SIGNING CREDENTIALS); notarize
script exists but never executed here (BLOCKED — NOTARIZATION
CREDENTIALS). arm64+x64 targets declared; universal-binary
verification of nested components: UNVERIFIED. Intel retained in
targets (no silent drop).

## 7. Security — PARTIAL

Electron flags + TCC-by-design (no permission code claiming success).
`disable-library-validation` + `allow-unsigned-executable-memory` set
(standard Electron requirement; justification recorded in SIGNING doc —
P1 to re-minimize). No `get-task-allow` (correct for production).

## 8. Permissions (TCC) — MISSING → Category A model added

No TCC state model existed. Added `aetheros_platform/macos_tcc.py`
(states, request policy, degradation) + tests. Live permission flows:
BLOCKED — MACOS ENVIRONMENT.

## 9. Keychain — MISSING → Category A abstraction added

No macOS Keychain integration existed. Added
`aetheros_platform/macos_keychain.py` (service/account model, access
scope, no-plaintext-fallback) + tests with mock backend. Live
SecItem operations: BLOCKED — MACOS ENVIRONMENT.

## 10–11. Notifications / menu bar — PARTIAL

Electron Notification IPC exists (cross-platform); menu-bar status
item: MISSING (tray work in 64.1 was Windows-focused). Dock config via
builder defaults. Live verification: BLOCKED.

## 12–13. Login item / background — MISSING

No `SMAppService`/login-item code found. Documented in 64.1 background
doc (Windows-oriented). macOS login-item implementation: MISSING —
deferred (needs Mac testing); no fake setting added.

## 14. Filesystem — PARTIAL → paths module added

Home is `~/.aetheros` on macOS (no `~/Library` adoption — deliberate,
avoids migrating existing users). Added `macos_paths.py` mapping
CONFIG/DATA/CACHE/LOGS/RUNTIME/ARTIFACTS/BACKUPS to `~/Library/*`
conventions for new state + tests.

## 15–16. URL schemes / file associations — COMPLETE (config)

`aetheros://` + `.aetheros/.aethskill/.aethcfg` in builder config.
Inbound routing validation: UNVERIFIED live.

## 17–19. Computer use / AX tree — PARTIAL

macOS backend is `cua` (cua-driver exposes native AX markdown) per
`platform_caps.py` — better than Windows. Added `aetheros_computer/
ax.py` normalized schema + scopes + tests. Live AX runs: BLOCKED.

## 20–22. Screen capture / clipboard / windows — PARTIAL

Backend pipelines exist; TCC-gated capture has no bypass (policy).
Multi-display/Spaces/Stage Manager: UNVERIFIED.

## 23–24. Power / sleep-wake — PARTIAL

powerMonitor resume hooks exist in main; durable-state integration per
Master 61; live behavior UNVERIFIED.

## 25. Updater — MISSING channel

No electron-updater/Sparkle integration found; update-manifest
validator (64.1) is channel-agnostic and reusable. Live: BLOCKED.

## 26. Crash recovery — PARTIAL

Backend checkpoints exist; `crashReporter` not found in main.
UNVERIFIED live.

## 27–28. Backup / performance — see Masters 61/64.1

No mac numbers claimed. Bench harness is Windows-executed; Mac
figures BLOCKED — APPLE SILICON/INTEL HARDWARE.

## 29. CI — PARTIAL

macos build job exists (UNVERIFIED — not run here). New
`macos-platform.yml` added (UNVERIFIED until CI runs).

## 30. E2E — BLOCKED — MACOS ENVIRONMENT

Journeys defined in certification; none executed.

## Known blockers

Mac runner, Developer ID + notary creds, Apple Silicon + Intel
hardware, clean Mac VM, Store decision (NOT pursued — direct
Developer ID, see DISTRIBUTION doc).
