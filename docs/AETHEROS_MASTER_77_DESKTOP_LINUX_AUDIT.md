# AetherOS Master 77 — Desktop & Linux Distribution Audit

Date (UTC): 2026-09-13
Source commit: `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1`
Host: Windows (development machine, Node v25.5.0, npm 11.8.0)
Status legend: IMPLEMENTED / TESTED / PASSED / FAILED / BLOCKED / UNVERIFIED / NOT_APPLICABLE

## 1. Repository topology

- Repo root (workspace): `D:\hermes-agent-main\aetheros` (`package.json`, npm workspaces `apps/*`, `ui-tui`).
- Desktop app: `apps/desktop/` (npm workspace `aetheros`, productName `AetherOS`, version `1.0.0`).
- Shared lib: `apps/shared/` (`@aetheros/shared`, built via `tsc -p .`, aliased in vite config).
- Workflows: `D:\hermes-agent-main\.github\workflows\` (note: workflows live at the
  outer `hermes-agent-main` root, NOT under `aetheros/` — paths inside use `aetheros/...` prefix).
- Package manager: **npm** (`package-lock.json` at `aetheros/` and `apps/desktop/`; all CI
  jobs run `npm ci`). `pnpm-lock.yaml` / `pnpm-workspace.yaml` remnants exist but are NOT used
  by any workflow. Do not use pnpm/yarn here.

## 2. Desktop architecture

- Electron main: `apps/desktop/electron/main.cjs` (~6k LOC god-file — noted, out of scope for this phase).
- Preload: `electron/preload.cjs`. Hardening helpers: `electron/hardening.cjs`
  (path validation, secret-file blocklist, webview partition policy, API-path validation).
- Renderer: React 19 + Vite 8 (`vite.config.ts`, `base: './'`, single-chunk strategy documented).
- Linux session detection: `electron/linux-session.cjs` (pure, tested; x11/wslg/wayland/headless matrix).
- Update logic: `electron/update-manifest.cjs` (pure manifest validator) + `electron/update-remote.cjs`
  (remote canonicalization). No `electron-updater` dependency anywhere.
- Native module: exactly one — `node-pty@1.1.0`, staged via `scripts/stage-native-deps.cjs`
  into `build/native-deps/` → packaged as `resources/native-deps/` (fallback require in main.cjs).
- Bundled backend: Python runtime + backend staged by `scripts/bundle-python.cjs` into
  `build/bundled-python/{py,backend}` → `resources/{py,backend}`.

## 3. Linux architecture

- Same Electron app; no separate native codebase (correct — do not invent one).
- `build.linux` declares AppImage + deb + rpm, all x64-only, `executableName: aetheros`,
  `artifactName: AetherOS-${version}-linux-${arch}.${ext}`, maintainer/synopsis/description/category set.
- `electron/linux-session.cjs` capability matrix: x11=native across the board; wayland
  screen_capture/input_synthesis/window_management=`unsupported` BY DESIGN (no portal path yet);
  tray/clipboard=`limited`. Honest by construction.
- Static validator `scripts/release/validate-linux-packaging.mjs` — PASSED on Windows host.
- Native production (`npm run dist:linux`) requires a Linux runner (CI job exists).

## 4. Build graph

`npm run build` = assert-root-install → write-build-stamp → stage-native-deps →
bundle-python → `tsc -b` (shared + app) → `vite build` → assert-dist-built.
`npm run dist[:win|:linux|:mac]` = build → electron-builder.
Typecheck (`tsc -p . --noEmit`): PASSED. Electron platform tests (176): PASSED.

## 5. Packaging graph

electron-builder 26.8.1, `directories.output = dist-packaged` (current config).
Hooks: before-build / before-pack / after-pack (`scripts/*.cjs`), afterSign notarize (mac only path).
asar=true, `*.node` + prebuilds unpacked. NSIS differentialPackage=true.
No `publish` provider configured → no electron-updater feed (see §16).

## 6. Artifact output directories

- `apps/desktop/dist-packaged/` — CANONICAL output (matches `build.directories.output`).
- `apps/desktop/release/` — STALE output from a previous config generation
  (`release/builder-effective-config.yaml` says `output: release`; mtimes July 2026).
  Contains only `win-unpacked/` + blockmap + debug yml. No current installers.
- `apps/desktop/dist/` — renderer build output (not distributable).

## 7. Existing artifacts (verified on disk 2026-09-13)

`apps/desktop/dist-packaged/`:

| File | Size (bytes) | SHA-256 |
|---|---|---|
| AetherOS-1.0.0-win-x64.exe | 187414763 | 3147bcea…b06 (full in inventory JSON) |
| AetherOS-1.0.0-win-x64.msi | 196571899 | 6fe65eb4…f2f3 |
| AetherOS-1.0.0-win-x64-portable.exe | 187240131 | cce16c07…c9cf |
| AetherOS-1.0.0-win-x64.exe.blockmap | 194806 | 5497fbdb…c809 |

PE metadata of `win-unpacked/AetherOS.exe`: Product=AetherOS, Company=AetherOS,
FileVer/ProdVer=**40.9.3** (= packaged Electron runtime, NOT app version — P2 metadata note).
install-stamp in unpacked tree: commit 2bdfbfd (== HEAD), builtAt 2026-09-12T15:44:05Z, source=local.
Unpacked `AetherOS.exe --version` probe: process spawned and stayed alive >25s (explicitly killed
afterwards); no GUI/window confirmation on headless host → launch evidence is partial only.

## 8. Missing artifacts

- Linux AppImage / deb / rpm: ABSENT (no Linux runner on this host; CI job defined, never executed here).
- `latest.yml` / update feed: ABSENT (no publish provider — expected, see §16).
- SBOM / provenance files: ABSENT locally (CI job defines SBOM step; not executed here).
- macOS dmg/zip/pkg: ABSENT (no mac runner here).

## 9. Broken commands (found + fixed this phase)

1. `.github/workflows/desktop-build.yml` uploaded `aetheros/apps/desktop/release/*` — directory no
   longer produced → CI upload would fail (`if-no-files-found: error`). FIXED → `dist-packaged/*`.
2. `.github/workflows/desktop-nightly.yml` — same stale path. FIXED → `dist-packaged/*`.
3. `apps/desktop/scripts/test-desktop.mjs` inspected `release/` — reported zero artifacts on a healthy
   tree. FIXED → `dist-packaged/`.
4. New `release:validate-artifacts` initially rejected `*.exe.blockmap` (double-extension regex gap —
   caught by its own run, fixed, now VALID).

## 10. Dependency problems

- None blocking. `npm ci` state assumed from existing `node_modules`; full reinstall not re-run
  (avoid churning the tree; CI runs `npm ci` cleanly per workflow).
- Electron drift (P3): installed `electron@40.10.6` vs packaged `electronVersion 40.9.3`.
  Packaged runtime is pinned and verified (FileVer 40.9.3); dev dep floats on ^40.10.6.

## 11. Native module requirements

- `node-pty@1.1.0` only. Requires Electron-ABI rebuild for each Electron bump; staged copy exists
  under `build/native-deps/node-pty` with prebuilds. x64-only evidence → ARM64 claim NOT made.

## 12–13. Electron / electron-builder configuration

- `appId com.aetheros.aetheros`, `productName AetherOS`, `executableName AetherOS`
  (win/mac) / `aetheros` (linux). Protocols: `aetheros://`. File associations: `.aetheros`,
  `.aethskill`, `.aethcfg` (icon `assets/icon.ico`).
- Targets: win = nsis + msi + portable (x64); linux = AppImage + deb + rpm (x64);
  mac = dmg + zip + pkg (x64 + arm64).
- Icons on disk: `assets/icon.ico`, `assets/icon.icns`, `assets/icon.png` (1024×1024 single PNG).
  No size-specific Linux icon set — builder resizes the single PNG; acceptable, P2 polish only.

## 14–15. Linux / Windows target configuration

- Linux: category Development, maintainer set, per-target arch x64. No `deb.depends` overrides —
  default Electron dependency set applies; target-distro verification is BLOCKED (needs Linux runner).
- Windows: NSIS perMachine, GUID + MSI upgradeCode pinned, `deleteAppDataOnUninstall: false`
  (safe default), `signAndEditExecutable: false`, `verifyUpdateCodeSignature: false`.
  Signing: UNSIGNED (no CSC cert in this environment) → SIGNATURE = BLOCKED / UNSIGNED.

## 16. Updater configuration

- No `build.publish` section. No `electron-updater` dependency. `update-manifest.cjs` is a pure
  offline validator; the Help-menu "check for updates" path has no download/apply engine behind it
  on any platform. Therefore: WINDOWS_AUTO_UPDATE = NOT_IMPLEMENTED, LINUX_AUTO_UPDATE =
  NOT_IMPLEMENTED (declared honestly; a manifest validator is not an updater). NSIS
  `differentialPackage: true` + `.blockmap` are emitted but unconsumed without a feed.

## 17. CI configuration

- `desktop-release.yml` (validate-linux-config → build-linux → build-windows → build-macos): correct
  paths (`dist-packaged/`), SHA-256 + SBOM + release-upload steps. NOT executed from here (needs runners).
- `desktop-build.yml` / `desktop-nightly.yml`: stale upload path, FIXED this phase (unexecuted — fix is
  by inspection, CI run required to prove green).
- `desktop-test.yml`, `desktop-security.yml`: exist; not modified.

## 18. Platform matrix (honest)

| Platform | x64 artifact | ARM64 artifact | Build | Install | Launch | Update |
|---|---|---|---|---|---|---|
| Windows | IMPLEMENTED (exe/msi/portable 1.0.0) | NOT_APPLICABLE (not declared) | PASSED (artifact validates) | BLOCKED (needs clean VM) | UNVERIFIED (process-spawn only) | NOT_IMPLEMENTED |
| Linux | BLOCKED (no runner) | NOT_APPLICABLE | BLOCKED | BLOCKED | BLOCKED | NOT_IMPLEMENTED |
| macOS | ABSENT (no runner) | ABSENT (no runner) | BLOCKED | BLOCKED | BLOCKED | NOT_IMPLEMENTED |

## 19. Test matrix (executed this phase, Windows host)

- `npm run typecheck` → PASSED (exit 0).
- `npm run test:desktop:platforms` → 176/176 PASSED.
- `npm run dist:linux:validate` → VALID (exit 0).
- `npm run release:validate-artifacts` (new) → VALID (exit 0).
- `vitest run` full renderer suite → NOT re-run (no code change to renderer; CI runs it).
- Installer install/uninstall/upgrade, AppImage/deb/rpm inspection, Wayland/X11 runtime,
  screen-capture, AT-SPI, secret-storage, rollback → all BLOCKED (no Linux/VM here), listed with
  exact commands in BLOCKED_TESTS doc.

## 20. Blockers

- P0: Linux artifacts do not exist (declared-supported x64 AppImage/deb/rpm). Closes only via
  `desktop-release.yml` build-linux on ubuntu-latest.
- P0: Windows installer commit-binding is UNVERIFIED (installers dated 2026-08-22; unpacked-tree
  stamp re-bound to HEAD on 2026-09-12 via a `--dir`-style refresh). Closes via fresh `dist:win`
  rebuild + provenance.
- P1: Code signing unavailable (unsigned NSIS/MSI) — expected without certs; stays BLOCKED.
- P1: No clean-VM install/launch/uninstall evidence for any platform.
- P2: Binary version resource shows Electron 40.9.3 instead of app 1.0.0; single-PNG Linux icon set.

## 21. Execution plan (applied)

1. Audit (this file) → 2. Inventory (JSON/MD) → 3. Fix stale CI/test paths (done) →
2. Add artifact + packaging validators (done, green) → 5. Validate Windows artifacts (done) →
3. Attempt fresh `dist:win` rebuild for commit binding (timeboxed; result in FINAL_STATUS) →
4. Linux via CI workflow only (commands documented) → 8. Manifest + SBOM wiring →
5. Certification (BLOCKED or BETA per §78 rules).
