# AetherOS Linux Architecture / X11 / Wayland / Computer Use / Accessibility / Portals / D-Bus / Security

Architecture: same Electron app; Linux specifics in
`electron/linux-session.cjs` (detection), `tools/computer_use/
linux_backend.py` (X11 xdotool/wmctrl/PIL, honest Wayland refusal),
`aetheros_platform/linux_{paths,session,native}.py`,
`aetheros_computer/atspi.py`. Renderer → typed IPC → policy → provider.

X11: native capture/input/window-management via backend; multi-monitor
coordinates must carry display + scale; tray most reliable here. Live:
UNTESTED. Wayland: FIRST-CLASS TARGET but restricted by design —
global enumeration/capture/input are UNSUPPORTED except via portals
(Screenshot/ScreenCast/RemoteDesktop), AT-SPI, or app APIs; no bypasses.
Live: UNTESTED.

Computer use: observe (AT-SPI > window metadata > screenshot > OCR >
coordinates) → act → verify (existing `verification.py` loop; success
requires state change, never mere event emission). Capability table
(X11 vs Wayland) lives in code (`linux_session` + backend
`is_available`) and must be surfaced to agents, never hidden.

Portals: FileChooser/OpenURI/Screenshot/ScreenCast/RemoteDesktop/
Notification modeled with session-dependent expectations; RemoteDesktop
needs explicit user authorization with expiring grants. D-Bus: strict
allowlist (portals, notifications, secrets) + method/path/arg
validation; no system-bus misuse.

Security: sandbox stays on; secrets in Secret Service (never plaintext
files); clipboard reads observable + policy-governed; no renderer
shell/D-Bus; AppArmor/SELinux denials reported, never worked around by
disabling frameworks.
