# AetherOS Linux Release

Status: **NOT production-ready yet.** Packaging is declared, CI-built, and
the shared test suite runs cross-platform — but install/launch/update/
uninstall verification on real distros has not been executed. This document
is the certification checklist; each box needs executable evidence.

## 1. Targets (declared in `apps/desktop/package.json` → `build.linux`)

| Item | Value |
|---|---|
| Formats | AppImage, deb, rpm |
| Architecture | x64 (arm64 is a natural follow-up but NOT declared today) |
| Category | Development |
| Maintainer | AetherOS <support@aetheros.com> |
| Executable name | `aetheros` |
| Icon | `assets/icon.png` |
| Artifact naming | `AetherOS-${version}-linux-${arch}.${ext}` |
| Protocol handler | `aetheros://` (electron-builder `protocols`) |

Build locally on Linux (or via the `desktop-release.yml` ubuntu job):

```bash
cd apps/desktop
npm ci
npm run dist:linux          # AppImage + deb + rpm into dist-packaged/
```

## 2. Desktop integration produced by electron-builder

- deb/rpm: `/opt/AetherOS*`, desktop entry, icon registration, `aetheros://`
  MIME/protocol registration.
- AppImage: self-contained; desktop entry embedded for appimage-launcher
  integrations.

## 3. Certification checklist — every item needs a recorded run

### Package metadata
- [ ] `dpkg -I AetherOS-*.deb` shows correct name/version/maintainer/description
- [ ] `rpm -qpi AetherOS-*.rpm` matches
- [ ] AppImage runs from a clean `$HOME`

### Install / launch / update / uninstall / reinstall / data preservation
- [ ] Install deb on Ubuntu LTS: `sudo apt install ./AetherOS-*.deb`
- [ ] Launch from the applications menu AND terminal (`aetheros`)
- [ ] `~/.config/AetherOS` (userData) created on first run
- [ ] Agent home resolves to `~/.aetheros` (never Windows paths)
- [ ] Upgrade install preserves sessions/config (no user-data loss)
- [ ] Uninstall removes binaries; **keeps** `~/.aetheros` + userData
- [ ] Reinstall picks prior state up cleanly
- [ ] rpm equivalent checks on Fedora/RHEL
- [ ] AppImage equivalent with `--appimage-extract-and-run` on a minimal distro

### Display servers
- X11 session:
  - [ ] window controls, multi-window, DPI scaling
  - [ ] clipboard
  - [ ] screen capture (`capabilityStatus('screen_capture', x11)` = native)
  - [ ] input synthesis / window management where exposed
- Wayland session:
  - capture/input/window-management MUST surface the structured
    `capability_unavailable` errors from `electron/linux-session.cjs`
    (this is correct behavior, verify it renders as "unavailable", never as
    silent failure or fake success)
  - [ ] notifications work
  - [ ] clipboard verified per-compositor: GNOME, KDE Plasma, wlroots
- X11-forwarded / SSH: GPU fallback engages (`detectRemoteDisplay`), tray
  reports unsupported.

### Security parity (must equal Windows/macOS results)
Run the shared hardening suite on Linux:

```bash
cd apps/desktop && node --test electron/hardening.test.cjs electron/bootstrap-platform.test.cjs electron/linux-session.test.cjs
```

Verify at runtime: context isolation, sandbox, CSP, navigation guard,
permission handlers, external-open allowlist (see
`docs/AETHEROS_PLATFORM_SECURITY.md`).

## 4. Package integrity / signing

Per actual distribution model (do not invent mechanisms):

- AppImage/deb/rpm produced by CI are covered by SHA-256 manifest +
  artifact attestation in `.github/workflows/desktop-release.yml`
  (`RELEASE_MANIFEST.sha256`, `gh attestation verify`).
- Optional repo signing (GPG for apt/yum repos) is NOT implemented; do not
  claim signed-repository support until keys + infra exist.
- Never store signing material in source control.

## 5. Performance gates (measure before certifying)

Record startup time, steady-state RSS, CPU idle %, and renderer
responsiveness on representative hardware (one X11 GNOME, one Wayland KDE).
No invented numbers: attach measurements to this file when available.
