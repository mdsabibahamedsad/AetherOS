"""Linux session/compositor detection (Master 66).

Python mirror of electron/linux-session.cjs heuristics: X11 vs Wayland
vs WSL vs headless, desktop environment, portal-channel expectations.
Env-injectable → unit-testable anywhere. Capability honesty: Wayland
global capture/input stays UNSUPPORTED (portal paths only).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class LinuxSession:
    applicable: bool
    session_type: str  # x11|wayland|xwayland|headless|unknown
    desktop: str
    compositor: str
    is_wsl: bool
    forwarded_x11: bool
    global_capture: str  # native|unsupported
    global_input: str    # native|unsupported


def detect_session(env: dict | None = None,
                   platform: str | None = None) -> LinuxSession:
    e = env if env is not None else os.environ
    plat = platform if platform is not None else sys.platform
    if not plat.startswith("linux"):
        return LinuxSession(False, "unknown", "", "", False, False,
                            "unsupported", "unsupported")
    wayland = str(e.get("WAYLAND_DISPLAY", "")).strip()
    stype = str(e.get("XDG_SESSION_TYPE", "")).strip().lower()
    display = str(e.get("DISPLAY", "")).strip()
    desktop = str(e.get("XDG_CURRENT_DESKTOP", "") or e.get("DESKTOP_SESSION", "")).strip()
    is_wsl = bool(e.get("WSL_DISTRO_NAME") or e.get("WSL_INTEROP"))
    forwarded = bool(display) and ":" in display and bool(display.split(":")[0])

    if wayland or stype == "wayland":
        session, capture, inp = "wayland", "unsupported", "unsupported"
    elif display or stype == "x11":
        session, capture, inp = "x11", "native", "native"
    else:
        session, capture, inp = "headless", "unsupported", "unsupported"
    return LinuxSession(True, session, desktop, "", is_wsl, forwarded,
                        capture, inp)
