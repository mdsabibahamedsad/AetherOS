# AETHEROS Master 66 — Linux Audit

Windows host: display-server/desktop/VM/package claims are BLOCKED unless
source-verified or unit-tested. Nothing fabricated.

## Existing capabilities (source-verified)

- Electron builder linux: AppImage/deb/rpm × x64 (`package.json#build`).
- CI: `validate-linux-config` + `build-linux` (ubuntu-latest, deps,
  AppImage/deb/rpm, `dist:linux` scripts).
- `electron/linux-session.cjs`: X11/Wayland/WSL detection + honest
  capability levels (native/limited/unsupported); Wayland capture stays
  UNSUPPORTED until validated. Tested (`linux-session.test.cjs`).
- `tools/computer_use/`: backend interface + X11 impl
  (xdotool/wmctrl/PIL, injectable, honest Wayland degradation) +
  `verification.py` observe-act-verify loop + `permissions.py` +
  `audit.py`.
- `platform_caps.py`: linux → X11-only note; macOS cua; Windows SendInput.
- Backend home: `~/.aetheros` (no XDG adoption — gap, Category A).
- Protocol `aetheros://` + file associations in builder config (shared).

## Gaps (new work this phase)

XDG path layer, session detection (Python), portal model, D-Bus
allowlist model, Secret Service abstraction, AT-SPI schema, desktop-
entry structural check, linux CI job, support matrix, migration
detection.

## BLOCKED (need Linux runner/VM/hardware)

X11/Wayland runtime verification, GNOME/KDE/XFCE behavior, portals
live, AT-SPI live, notifications/tray live, screen capture live,
audio/camera, GPU/HiDPI, AppImage/deb/rpm build+install+upgrade,
systemd autostart live, ARM64 build, Flatpak decision validation,
clean-VM journeys, benchmarks on hardware.

## Security posture

Electron flags shared with Win/Mac; no renderer shell; computer-use
behind approval gates; no secrets in code (verified by sweep).
P0 blockers in current scope: none — gaps are missing-verification,
not broken code. P1: XDG adoption, portal-gated capture paths,
per-user install verification.
