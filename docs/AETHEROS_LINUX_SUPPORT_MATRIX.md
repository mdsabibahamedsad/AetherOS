# AetherOS Linux Support Matrix (honest baseline)

No cell is PASS: no Linux runtime testing was performed in this phase.
Cells reflect source-verified config (CONFIG) vs untested (UNTESTED).

| Combo | Build cfg | Runtime | Computer use | Capture | Notes |
|---|---|---|---|---|---|
| Ubuntu LTS + GNOME + Wayland (x64) | CONFIG (AppImage/deb) | UNTESTED | portal-only, UNTESTED | portal, UNTESTED | primary target |
| Ubuntu LTS + GNOME + X11 (x64) | CONFIG | UNTESTED | xdotool backend exists, UNTESTED live | native, UNTESTED | best X11 bet |
| Fedora + GNOME + Wayland (x64) | CONFIG (rpm) | UNTESTED | UNTESTED | UNTESTED | rpm path |
| Debian stable + X11 (x64) | CONFIG (deb) | UNTESTED | UNTESTED | UNTESTED | — |
| KDE Plasma (Wayland/X11) | CONFIG | UNTESTED | UNTESTED | UNTESTED | tray fragmented |
| XFCE | CONFIG | UNTESTED | UNTESTED | UNTESTED | portals thin |
| Arch | UNTESTED | UNTESTED | UNTESTED | UNTESTED | best-effort only |
| ARM64 any | NOT SUPPORTED (no arm64 target) | — | — | — | needs build infra |
| Flatpak | NOT SUPPORTED (no manifest) | — | — | — | decision: not pursued |

Policy: a cell becomes PASS only with executed install/launch/feature
evidence on that exact combo. Packaging strategy: AppImage primary,
deb secondary, rpm secondary, Flatpak NOT SUPPORTED (no manifest, no
portal-permission model filed — marketing-free decision).
