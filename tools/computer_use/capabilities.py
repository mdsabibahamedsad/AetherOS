"""Cross-platform capability detection for computer use.

Provides a pure, deterministic picture of what the current host supports for
computer-use automation — independent of any specific backend:

* :class:`PlatformInfo` — OS / release / architecture / session type (Windows
  session, X11, Wayland, macOS) and which core capability groups are present
  (display, pointer, keyboard, clipboard, window management, app launch,
  browser, terminal).
* :func:`detect_platform_info` — reads the real host (env + ``platform``).
* :func:`backend_capabilities` — the action surface a backend implements.

Every function is best-effort and never raises: an unknown environment
degrades to an empty capability set rather than an error. Detection results
are the source for the ``computer_use`` tool's ``get_capabilities`` /
``system_info`` actions, so models can pick a strategy (element-click vs
pixel-click vs native value) before acting.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Capability group names (stable keys used by backends and the tool layer).
DISPLAY = "display"                    # screen capture / geometry
POINTER = "pointer"                    # mouse: move / click / drag / scroll
KEYBOARD = "keyboard"                  # type / key combos
CLIPBOARD = "clipboard"                # read / write clipboard
WINDOWS = "windows"                    # enumerate / focus / minimize / close
APP_LAUNCH = "app_launch"              # launch / close applications
BROWSER = "browser"                    # browser automation (dedicated tool)
TERMINAL = "terminal"                  # terminal execution (dedicated tool)
ELEMENTS = "elements"                  # accessibility (AX/SOM) element tree
OCR = "ocr"                            # OCR-backed text / element search
BACKGROUND = "background"              # automate without stealing input focus
SYSTEM_INFO = "system_info"            # OS/CPU/RAM/disk introspection

# Display-server / session types.
SESSION_UNKNOWN = "unknown"
SESSION_WINDOWS = "windows"
SESSION_X11 = "x11"
SESSION_WAYLAND = "wayland"
SESSION_MACOS = "macos"
SESSION_HEADLESS = "headless"


@dataclass
class PlatformInfo:
    """Best-effort description of the host computer-use surface."""

    os: str = ""
    os_version: str = ""
    architecture: str = ""
    session_type: str = SESSION_UNKNOWN
    display_server: str = ""           # e.g. "x11" / "wayland" / "cg" / "windows"
    display: bool = False              # a usable screen session is present
    pointer: bool = False
    keyboard: bool = False
    clipboard: bool = False
    windows: bool = False
    app_launch: bool = False
    browser: bool = False
    terminal: bool = True
    elements: bool = False             # accessibility tree available
    ocr: bool = False
    background: bool = False           # can automate without stealing focus
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "os": self.os,
            "os_version": self.os_version,
            "architecture": self.architecture,
            "session_type": self.session_type,
            "display_server": self.display_server,
            "display": self.display,
            "pointer": self.pointer,
            "keyboard": self.keyboard,
            "clipboard": self.clipboard,
            "windows": self.windows,
            "app_launch": self.app_launch,
            "browser": self.browser,
            "terminal": self.terminal,
            "elements": self.elements,
            "ocr": self.ocr,
            "background": self.background,
            "capabilities": sorted(self.capabilities),
        }

    def has(self, capability: str) -> bool:
        return capability in self.capabilities


def _probe(cmd: str) -> bool:
    """True when ``cmd`` resolves on $PATH."""
    try:
        return shutil.which(cmd) is not None
    except Exception:  # noqa: BLE001 - best-effort probe
        return False


def _is_headless_env() -> bool:
    """True when no interactive display env is present (CI containers)."""
    if sys.platform == "win32":
        return bool(os.environ.get("SESSIONNAME") == "") or bool(
            os.environ.get("CI") and not os.environ.get("DISPLAY")
        )
    if sys.platform == "darwin":
        return False
    return not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def detect_platform_info(*, _platform=None, _shutil=None) -> PlatformInfo:
    """Detect the host's computer-use capabilities (never raises)."""
    pm = _platform or platform
    system = (pm.system() or "").lower()
    info = PlatformInfo(
        os=system or sys.platform,
        os_version=(pm.release() or ""),
        architecture=(pm.machine() or ""),
    )
    try:
        info.os_version = (pm.platform() or "") or pm.release() or ""
    except Exception:  # noqa: BLE001
        pass

    if system == "windows":
        info.session_type = SESSION_WINDOWS
        info.display_server = "windows"
        info.display = True
        info.pointer = True
        info.keyboard = True
        info.clipboard = True
        info.windows = True
        info.app_launch = True
        info.browser = True
        info.terminal = True
        info.background = False          # Win32 inputs share the user session
    elif system == "darwin":
        info.session_type = SESSION_MACOS
        info.display_server = "cg"
        info.display = True
        info.pointer = True
        info.keyboard = True
        info.clipboard = True
        info.windows = True
        info.app_launch = True
        info.browser = True
        info.terminal = True
        info.background = True           # cua-driver posts events to pid/window
        info.elements = True
    elif system == "linux":
        if os.environ.get("WAYLAND_DISPLAY"):
            info.session_type = SESSION_WAYLAND
            info.display_server = "wayland"
            # Wayland has no global automation contract — report honestly.
            info.display = True
        elif os.environ.get("DISPLAY"):
            info.session_type = SESSION_X11
            info.display_server = "x11"
            info.display = True
            info.pointer = _probe("xdotool")
            info.keyboard = _probe("xdotool")
            info.clipboard = _probe("xclip")
            info.windows = _probe("wmctrl") or _probe("xdotool")
            info.app_launch = bool(_probe("xdg-open") or _probe("gtk-launch"))
            info.browser = True
            info.terminal = True
            info.background = False
            if _probe("tesseract"):
                info.ocr = True
        else:
            info.session_type = SESSION_HEADLESS
            info.display = False
    else:
        info.session_type = SESSION_UNKNOWN

    if _is_headless_env() and system != "darwin":
        info.display = False

    if info.display:
        info.capabilities += [DISPLAY]
    if info.pointer:
        info.capabilities += [POINTER]
    if info.keyboard:
        info.capabilities += [KEYBOARD]
    if info.clipboard:
        info.capabilities += [CLIPBOARD]
    if info.windows:
        info.capabilities += [WINDOWS]
    if info.app_launch:
        info.capabilities += [APP_LAUNCH]
    if info.browser:
        info.capabilities += [BROWSER]
    if info.terminal:
        info.capabilities += [TERMINAL]
    if info.elements:
        info.capabilities += [ELEMENTS]
    if info.ocr:
        info.capabilities += [OCR]
    if info.background:
        info.capabilities += [BACKGROUND]
    info.capabilities += [SYSTEM_INFO]
    return info


# Backend → implemented action surface (used by backend_capabilities). The
# unified actions that all backends implement via the ABC are implicit.
_COMMON_ACTIONS = (
    "capture", "capture_region", "get_screen_size", "click", "double_click",
    "right_click", "middle_click", "drag", "scroll", "move_mouse", "type",
    "key", "wait", "list_apps", "focus_app", "get_capabilities", "system_info",
)

_BACKEND_EXTRA_ACTIONS: Dict[str, Tuple[str, ...]] = {
    "cua": ("set_value", "list_windows", "get_active_window", "focus_window",
            "minimize_window", "maximize_window", "close_window",
            "read_clipboard", "copy_clipboard", "clear_clipboard",
            "find_text", "launch_app", "close_app"),
    "win32": ("set_value", "list_windows", "get_active_window", "focus_window",
              "minimize_window", "maximize_window", "close_window",
              "read_clipboard", "copy_clipboard", "clear_clipboard",
              "find_text", "launch_app", "close_app"),
    "linux": ("list_windows", "get_active_window", "focus_window",
              "minimize_window", "maximize_window", "close_window",
              "read_clipboard", "copy_clipboard", "clear_clipboard",
              "find_text", "launch_app", "close_app"),
    "noop": ("set_value", "list_windows", "get_active_window", "focus_window",
             "minimize_window", "maximize_window", "close_window",
             "read_clipboard", "copy_clipboard", "clear_clipboard",
             "find_text", "launch_app", "close_app"),
}


def backend_capabilities(backend_name: str) -> List[str]:
    """Return the action surface a backend implements (union of common+extra)."""
    key = (backend_name or "cua").lower().replace("driver", "").strip(" -")
    key = {"windows": "win32", "x11": "linux", "": "cua"}.get(key, key)
    extras = _BACKEND_EXTRA_ACTIONS.get(key, ())
    return sorted(set(_COMMON_ACTIONS) | set(extras))


def backend_supports_action(backend_name: str, action: str) -> bool:
    """True when ``action`` is part of ``backend_name``'s action surface."""
    return action in backend_capabilities(backend_name)