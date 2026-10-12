# AetherOS Master 78 — Distribution Audit

Date (UTC): 2026-09-13
Source commit: `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1` (actual `git rev-parse HEAD`;
the phase brief cites `...c2bfb...` which is a one-character transcription error for `...c2beb...`)
Version: `1.0.0`
Host: Windows 11 dev machine, Node v25.5.0, npm 11.8.0, Python 3.11.15
Linux env: WSL2 Ubuntu 24.04.4 LTS (x64, kernel 6.18.33.2-microsoft-standard-WSL2),
Node v24.14.1, Python 3.12.3, WSLg (Wayland `wayland-0` + X11 `:0`) present,
`dpkg-deb` / `rpm` / `fakeroot` / `file` present, GitHub network reachable.
Status legend: IMPLEMENTED / TESTED / PASSED / FAILED / BLOCKED / UNVERIFIED /
NOT_IMPLEMENTED / NOT_APPLICABLE / CONFIG_VALID / ARTIFACT_BLOCKED

## 1. Topology (verified on disk)

- Git root: `D:\hermes-agent-main` (workflows live at `.github/workflows/`, NOT under `aetheros/`).
- App root: `aetheros/` (npm workspaces `apps/*`, `ui-tui`).
- Desktop app: `aetheros/apps/desktop` (`name: aetheros`, `productName: AetherOS`, `version: 1.0.0`).
- electron-builder 26.8.1 (resolved from `aetheros/node_modules`), packaged Electron pin 40.9.3,
  dev `electron@^40.10.6` (hoisted at `aetheros/node_modules`).
- Canonical installer output: `apps/desktop/dist-packaged/` (matches `build.directories.output`).
- `apps/desktop/dist/` = Vite renderer output (NOT distributable).
- `apps/desktop/release/` = STALE previous-generation output (win-unpacked mtime 2026-09-03,
  `__msi-x64` mtime 2026-08-03, blockmap mtime 2026-07-27; effective-config says `output: release`).
  No current installers. Retained for forensics; must never be published.
- `apps/desktop/build/` = staging (`bundled-python/{py,backend}`, `native-deps`, `install-stamp.json`,
  `installer/`). `build/install-stamp.json` pins commit `2bdfbfd...` (dirty=true, local, 2026-09-13).
- `dist-packaged/` on-disk inventory (2026-09-13, BEFORE Master 78 rebuilds):
  `AetherOS-1.0.0-win-x64.exe` (195,739,994 B, 2026-09-13 — Master 77 fresh NSIS),
  `AetherOS-1.0.0-win-x64.exe.blockmap` (202,557 B, 2026-09-13),
  `AetherOS-1.0.0-win-x64.msi` (196,571,899 B, 2026-08-22 — LEGACY),
  `AetherOS-1.0.0-win-x64-portable.exe` (187,240,131 B, 2026-08-22 — LEGACY),
  `win-unpacked/`, `__msi-x64/`, `builder-debug.yml`.
- No Linux artifacts on disk. No `latest.yml` feed. No SBOM/provenance files. No macOS artifacts.

## 2. electron-builder configuration (source: `apps/desktop/package.json` `build` section)

- `appId com.aetheros.aetheros`, `executableName AetherOS` (win) / `aetheros` (linux),
  `artifactName AetherOS-${version}-${os}-${arch}.${ext}` — CONFIG_VALID.
- `extraResources`: install-stamp, native-deps, icon.ico, license.txt,
  `build/bundled-python/py → py`, `build/bundled-python/backend → backend` — this is the
  WiX long-path vector (§9).
- win targets: nsis + msi + portable, x64 only. ARM64 NOT_IMPLEMENTED (not declared; no claim made).
- linux targets: AppImage + deb + rpm, x64 only. `maintainer`, `synopsis`, `description`,
  `category: Development` set. No `deb.depends` overrides (defaults apply — see §17).
- mac targets: dmg + zip + pkg, x64 + arm64 (out of scope for this phase).
- `publish`: ABSENT on all platforms → UPDATE = NOT_IMPLEMENTED (all platforms).
- NSIS: `differentialPackage: true` (blockmap emitted, unconsumed), perMachine, GUID pinned.
- MSI: `upgradeCode` pinned, `warningsAsErrors: false`, perMachine.
- Signing flags: `signAndEditExecutable: false`, `verifyUpdateCodeSignature: false` → UNSIGNED.
- Hooks: `beforeBuild` (return false — skip node_modules collect), `beforePack`
  (wipe stale `appOutDir` — idempotency fix), `afterPack` (Windows exe identity stamp, best-effort),
  `afterSign` → notarize (mac path).

## 3. Build graph

`npm run build` = assert-root-install → write-build-stamp → stage-native-deps →
bundle-python (copies activated `.venv` → `build/bundled-python/py`, stages backend,
strips tests/pyc, smoke-tests bundled interpreter) → `tsc -b` → `vite build` → assert-dist-built.
`npm run dist:win[:nsis|:msi]` / `dist:linux` = build → electron-builder.
Package manager: `npm ci` (lockfiles at `aetheros/` and `apps/desktop/`). pnpm remnants unused.

## 4. Native modules

Exactly one: `node-pty@1.1.0`. Staged prebuilds on disk: `win32-x64` ONLY.
Linux/macOS prebuilds ABSENT → Linux packaging must acquire a Linux node-pty binary
(rebuild/download) or the packaged terminal backend is broken on Linux. This is a P1 until
proven by a Linux smoke import.

## 5. Python bundle

`build/bundled-python/py` = full Windows `.venv` copy (13,768 files under
`dist-packaged/win-unpacked/resources/py`). Contains `elevenlabs` + `mistralai` SDKs with
auto-generated (Fern) endpoint type stubs — the WiX MAX_PATH offenders (§9). Both SDKs are
runtime-optional (lazy `ensure()` imports for TTS providers) but INSTALLED, and `elevenlabs`
eagerly imports its `types/` tree at package import → files cannot be deleted without breaking
`import elevenlabs`. Deletion is REJECTED as a fix.

## 6. CI workflows (`.github/workflows/`)

- `desktop-release.yml`: validate-linux-config → build-linux (AppImage+deb+rpm, SHA-256, SBOM via
  anchore, upload-artifact + gh-release) → build-windows (NSIS+MSI+portable) → build-macos.
  Gaps found this phase: (a) Windows `Verify artifacts exist` checks ONLY the `.exe`
  (MSI/portable absence would pass silently); (b) no MSI path-length guard; (c) no
  upload/download SHA cross-check (`artifact-integrity-check`); (d) `build-linux` has no
  path-length concern (Linux has no MAX_PATH) but shares `npm run dist:linux`. Fixed in §32–34.
- `desktop-build.yml`: matrix (linux/mac-x64/mac-arm64/win), upload path `dist-packaged/*` —
  CORRECT (fixed in Master 77). Linux system deps installed (`libgtk-3-dev`, …).
- `desktop-nightly.yml`: upload path `dist-packaged/*` — CORRECT (fixed in Master 77).
- `desktop-test.yml`, `desktop-security.yml`: present, unmodified.
- All fixes are CONFIG_VALID / UNVERIFIED until a CI run executes them.

## 7. Validators present

- `scripts/release/validate-linux-packaging.mjs` — static Linux config check (any host). VALID.
- `scripts/release/validate-artifacts.mjs` — dist-packaged naming/size/hash/manifest self-check. VALID.
- `scripts/test-desktop.mjs` — integration test (build+typecheck+lint+vitest+electron tests+listing).
- NEW this phase: `scripts/release/check-packaging-path-lengths.mjs` — early MAX_PATH guard (§46).

## 8. Master 77 baseline mapping (no cheating — restated as starting point)

- Windows NSIS: fresh 2026-09-13, HEAD-bound (install-stamp verified local). Must be REBUILT
  (Master 78 forbids reusing the Master 77 artifact).
- Windows MSI / portable: 2026-08-22 LEGACY_NON_HEAD_BOUND. Must be REBUILT.
- Linux AppImage/deb/rpm: ABSENT. WSL2 Ubuntu 24.04 now identified as real Linux env — attempt.
- Clean-VM install/launch: no VM available (no Hyper-V/VBox/VMware found; elevation unavailable
  to confirm Hyper-V) → stays BLOCKED unless a VM appears.
- Signing: UNSIGNED / BLOCKED (no certs). SBOM: BLOCKED unless CI runs. Update: NOT_IMPLEMENTED.
- Stale `release/`: retained, classified STALE — never published.

## 9. WiX LGHT0103 preview (full analysis in AETHEROS_MASTER_78_WIX_LGHT0103_ROOT_CAUSE.md)

44 files under `resources/py` exceed 200 chars absolute (pre-fix survey); exactly 1 file
reaches 262 (fatal ≥ 260) and 6 exceed the 240 guard budget from this checkout.
(`.../elevenlabs/text_to_speech/types/body_text_to_speech_streaming_with_timestamps_..._post_apply_text_normalization.py`).
WiX light (v3 toolchain via electron-builder) fails at MAX_PATH 260 → LGHT0103.
Primary fix: shorten the build workspace/staging prefix (SUBST drive) — zero runtime change.
Rejected: deleting SDK files (breaks `import elevenlabs`), renaming vendored files (breaks
package integrity), suppressing the error.

## 10. Search-index confirmation

`release/`, `dist/`, `dist-packaged/`, `win-unpacked`, `msi`, `portable`, `nsis`, `AppImage`,
`deb`, `rpm`, `electron-builder`, `wix`, `LGHT0103`, artifact upload/download, checksum/sha256,
SBOM, attestation, provenance — all traced to the files listed above. No second desktop app,
no mock installer, no duplicate packaging system found.
