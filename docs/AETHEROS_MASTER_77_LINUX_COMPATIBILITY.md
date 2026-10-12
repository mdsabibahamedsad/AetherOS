# AetherOS Master 77 — Linux Compatibility

All runtime rows below are BLOCKED (no Linux runner on this host). Source-level facts are stated
as IMPLEMENTED/TESTED only where unit tests exist; nothing is inferred as runtime PASS.

## Distribution strategy (from existing config, kept)

1. AppImage (broad distro coverage, self-contained) — primary.
2. DEB (Debian/Ubuntu) — declared.
3. RPM (Fedora/RPM-based) — declared.
4. Snap / Flatpak — NOT declared, NOT added (out of scope for stabilization).

## Static facts (verified by inspection + unit tests)

- Targets/maintainer/category/synopsis/description/executableName: all present in `build.linux`.
- `dist:linux:validate`: VALID on any host.
- `linux-session.cjs` + tests (part of the 176 passing Electron tests): session detection
  (x11/wayland/wslg/x11-forwarded/headless) and capability matrix TESTED at unit level.
- Icon: single 1024×1024 `assets/icon.png`. No corruption check possible beyond existence + size;
  builder resizes automatically. No Hermes branding found in desktop assets (P2: consider
  size-specific icon set later).
- `.desktop` Exec-path behavior: determined at package build time by electron-builder (launcher
  script indirection on recent versions) — must be read from the ACTUAL built package, not assumed.
  No package exists yet → UNVERIFIED.

## Runtime matrix (all BLOCKED — needs ubuntu-latest + GNOME/KDE VMs)

| Area | X11 | Wayland | Notes |
|---|---|---|---|
| Startup / windowing / resize / multi-window | BLOCKED | BLOCKED | — |
| Clipboard | BLOCKED | BLOCKED (limited by design) | matrix says `limited` on wayland |
| Notifications | BLOCKED | BLOCKED | — |
| Screen capture (screen/window/region) | BLOCKED | UNSUPPORTED by design (no portal path) | honest `unsupported`, not silent fallback |
| Tray | BLOCKED | BLOCKED (limited by design) | needs StatusNotifier/AppIndicator |
| Accessibility (AT-SPI) | BLOCKED | BLOCKED | React attrs alone prove nothing |
| Secret storage | BLOCKED | BLOCKED | uses Electron safeStorage → Secret Service/libsecret via Chromium; plaintext check needs runtime |
| XDG paths (config/data/cache/state) | BLOCKED | BLOCKED | code uses `app.getPath('userData')` (resolves XDG-compliant on Linux); migration never auto-deletes |
| Hermes→AetherOS migration | UNVERIFIED | UNVERIFIED | `HERMES_WEB_DIST` legacy-compat env kept intentionally; full path audit needs Linux home dirs |
| URL schemes (`aetheros://`) | BLOCKED | BLOCKED | treat params as untrusted (validation exists in hardening.cjs for API paths) |
| Autostart / crash recovery | BLOCKED | BLOCKED | integrate with Master 61 UNKNOWN_OUTCOME handling |

## Baseline distro recommendation

Ubuntu x64 + Fedora x64 first (matches CI `ubuntu-latest` build host + one RPM consumer);
Debian, openSUSE, Mint, Arch only after those two are green. No support claim beyond tested distros.
