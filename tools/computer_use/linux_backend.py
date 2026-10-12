"""Linux computer-use backend (X11 via xdotool/wmctrl; honest Wayland).

Implements the ``ComputerUseBackend`` interface on Linux by shelling out to
``xdotool`` (pointer/keyboard/window primitives), ``wmctrl`` (window list /
activation) and PIL ``ImageGrab`` (screen capture). All interaction is X11;
on Wayland these tools are unavailable, so the backend reports
``is_available()`` False and every action degrades to a clear
"not available on Wayland" result rather than pretending to work.

Like the Win32 backend, module-level code touches no OS/display state — every
call goes through injectable module-level ``_os_*`` helpers so the module
imports cleanly on any platform and unit-tests run without a display.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from tools.computer_use.backend import (
    ActionResult,
    CaptureResult,
    ComputerUseBackend,
    UIElement,
)

logger = logging.getLogger(__name__)

_IS_LINUX = sys.platform.startswith("linux")

_WMCTRL_WINDOW_RE = re.compile(
    r"^(?P<hex>\w+)\s+(?P<desktop>\d+)\s+(?P<host>\S+)\s+(?P<title>.*)$"
)

# xdotool key names → X keysym names it understands.
_KEY_ALIASES = {
    "return": "Return", "enter": "Return", "tab": "Tab", "escape": "Escape",
    "esc": "Escape", "backspace": "BackSpace", "space": "space",
    "delete": "Delete", "insert": "Insert", "home": "Home", "end": "End",
    "pageup": "Prior", "pagedown": "Next",
    "left": "Left", "up": "Up", "right": "Right", "down": "Down",
    "shift": "shift", "ctrl": "ctrl", "control": "ctrl", "alt": "alt",
    "cmd": "super", "super": "super", "win": "super", "meta": "super",
    "capslock": "Caps_Lock", "numlock": "Num_Lock",
}
# Single-char printable keys pass through to xdotool as-is.
_MODIFIER_NAMES = {"shift", "ctrl", "control", "alt", "super", "win", "cmd", "meta"}


def _parse_key_combo(keys: str) -> Tuple[Optional[str], List[str]]:
    """Parse 'ctrl+alt+t' → (keysym, [modifiers]); None key on parse failure."""
    parts = [p.strip().lower() for p in keys.replace(",", "+").split("+") if p.strip()]
    modifiers: List[str] = []
    key: Optional[str] = None
    for part in parts:
        if part in _MODIFIER_NAMES:
            modifiers.append(_KEY_ALIASES.get(part, part))
            continue
        keysym = _KEY_ALIASES.get(part, part)
        key = keysym
    return key, list(dict.fromkeys(modifiers))


def _parse_wmctrl_output(output: str) -> List[Dict[str, Any]]:
    """Parse `wmctrl -lx` output into window records.

    Each line: <0xhex> <desktop> <host> <class:instance> <title...>
    """
    windows: List[Dict[str, Any]] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        hex_id = parts[0]
        desktop = parts[1]
        klass = parts[3] if len(parts) > 3 else ""
        title = " ".join(parts[4:]) if len(parts) > 4 else ""
        windows.append({
            "id": hex_id,
            "desktop": desktop,
            "app": klass,
            "title": title,
        })
    return windows


def _is_x11() -> bool:
    return bool(os.environ.get("DISPLAY"))


def _is_wayland() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY"))


def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


# ── OS access layer (injectable for tests) ───────────────────────────────

def _os_run(args: List[str], timeout: float = 10.0) -> Tuple[int, str, str]:
    """Run a command; returns (rc, stdout, stderr). Never raises."""
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except FileNotFoundError:
        return 127, "", f"{args[0]} not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"
    except Exception as exc:  # pragma: no cover - defensive
        return 1, "", str(exc)


def _os_capture_screen() -> bytes:
    """PNG bytes of the primary screen (X11 only)."""
    if not _IS_LINUX:
        raise RuntimeError("LinuxBackend requires Linux")
    if not _is_x11():
        raise RuntimeError("screen capture requires an X11 display (Wayland unsupported)")
    from PIL import ImageGrab
    img = ImageGrab.grab()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _os_xdotool(args: List[str]) -> Tuple[int, str, str]:
    return _os_run(["xdotool", *args])


def _os_wmctrl(args: List[str]) -> Tuple[int, str, str]:
    return _os_run(["wmctrl", *args])


def _os_launch(cmd: List[str]) -> int:
    """Start ``cmd`` detached from the parent session; returns the PID or 0."""
    if not cmd:
        return 0
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL, start_new_session=True,
        )
        return int(proc.pid or 0)
    except Exception:  # noqa: BLE001 - launch best-effort
        return 0


def _os_get_system_info() -> Dict[str, Any]:
    """OS / CPU / RAM / disk info via stdlib + optional psutil. Never raises."""
    import platform as _platform
    info: Dict[str, Any] = {
        "os": _platform.system() or sys.platform,
        "os_version": _platform.release() or "",
        "architecture": _platform.machine() or "",
        "session_type": "x11" if _is_x11() else ("wayland" if _is_wayland() else "headless"),
        "cpu_percent": None,
        "memory": {},
        "disk": {},
        "processors": None,
    }
    try:
        info["processors"] = _platform.processor() or None
    except Exception:  # noqa: BLE001
        pass
    try:
        import psutil
        info["cpu_percent"] = round(psutil.cpu_percent(interval=0.1), 1)
        mem = psutil.virtual_memory()
        info["memory"] = {
            "total": mem.total, "available": mem.available,
            "used": mem.used, "percent": round(mem.percent, 1),
        }
        disk = psutil.disk_usage(".")
        info["disk"] = {
            "total": disk.total, "free": disk.free,
            "used": disk.used, "percent": round(disk.percent, 1),
        }
    except Exception:  # noqa: BLE001 - psutil optional
        pass
    return info


# ── The backend ───────────────────────────────────────────────────────────

class LinuxBackend(ComputerUseBackend):
    """Linux adapter for the unified computer-use interface (X11)."""

    def __init__(self) -> None:
        self._started = False
        self._screen_w: int = 0
        self._screen_h: int = 0

    # ── Lifecycle ──────────────────────────────────────────────────
    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def is_available(self) -> bool:
        if not _IS_LINUX:
            return False
        if _is_wayland():
            # Wayland has no global input/window automation contract; report
            # honestly so check_fn / tooling doesn't pretend to work.
            return False
        return _is_x11() and (_tool_available("xdotool") or _tool_available("wmctrl"))

    def get_screen_size(self) -> Tuple[int, int]:
        if self._screen_w and self._screen_h:
            return self._screen_w, self._screen_h
        rc, out, _err = _os_xdotool(["getdisplaygeometry"])
        if rc == 0:
            parts = out.split()
            if len(parts) >= 2:
                try:
                    self._screen_w, self._screen_h = int(parts[0]), int(parts[1])
                    return self._screen_w, self._screen_h
                except ValueError:
                    pass
        return 0, 0

    # ── Capture ────────────────────────────────────────────────────
    def capture(self, mode: str = "som", app: Optional[str] = None) -> CaptureResult:
        try:
            raw = _os_capture_screen()
        except RuntimeError as exc:
            return CaptureResult(mode=mode, width=0, height=0, png_b64=None,
                                 elements=[], app="", window_title=str(exc))
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(raw))
        width, height = img.size
        return CaptureResult(
            mode=mode, width=width, height=height,
            png_b64=base64.b64encode(raw).decode("ascii"),
            elements=[], app=app or "", window_title="", png_bytes_len=len(raw),
            meta={"note": "som/ax degrade to a plain capture on Linux (no AX tree)"},
        )

    def capture_region(
        self, x: int, y: int, width: int, height: int, mode: str = "vision",
    ) -> CaptureResult:
        cap = self.capture(mode=mode)
        if not cap.png_b64:
            return cap
        if width <= 0 or height <= 0:
            return CaptureResult(mode=mode, width=0, height=0, png_b64=None,
                                 elements=[], app="", window_title="invalid region")
        try:
            raw = base64.b64decode(cap.png_b64, validate=False)
        except Exception:
            return CaptureResult(mode=mode, width=0, height=0, png_b64=None,
                                 elements=[], app="", window_title="decode failed")
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(raw))
        crop = img.crop((max(0, x), max(0, y),
                         min(img.width, x + width), min(img.height, y + height)))
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        raw_region = buf.getvalue()
        return CaptureResult(
            mode=mode, width=crop.width, height=crop.height,
            png_b64=base64.b64encode(raw_region).decode("ascii"),
            elements=[], app="", window_title="", png_bytes_len=len(raw_region),
        )

    # ── Pointer ────────────────────────────────────────────────────
    def move_mouse(self, x: int, y: int) -> ActionResult:
        rc, _out, err = _os_xdotool(["mousemove", str(int(x)), str(int(y))])
        if rc != 0:
            return ActionResult(ok=False, action="move_mouse", message=err.strip() or "xdotool mousemove failed")
        return ActionResult(ok=True, action="move_mouse",
                            message=f"moved pointer to ({x}, {y})")

    def click(
        self,
        *,
        element: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        click_count: int = 1,
        modifiers: Optional[List[str]] = None,
    ) -> ActionResult:
        if x is None or y is None:
            return ActionResult(ok=False, action="click",
                                message="Linux backend has no element model; use x/y.")
        button_num = {"left": "1", "middle": "2", "right": "3"}.get(button, "1")
        args: List[str] = ["mousemove", str(int(x)), str(int(y)), "click"]
        for _ in range(max(1, click_count)):
            args.append(button_num)
        rc, _out, err = _os_xdotool(args)
        if rc != 0:
            return ActionResult(ok=False, action="click", message=err.strip() or "xdotool click failed")
        return ActionResult(ok=True, action="click",
                            message=f"clicked {button} at ({x}, {y})")

    def drag(
        self,
        *,
        from_element: Optional[int] = None,
        to_element: Optional[int] = None,
        from_xy: Optional[Tuple[int, int]] = None,
        to_xy: Optional[Tuple[int, int]] = None,
        button: str = "left",
        modifiers: Optional[List[str]] = None,
    ) -> ActionResult:
        if from_xy is None or to_xy is None:
            return ActionResult(ok=False, action="drag",
                                message="Linux backend has no element model; use from_coordinate/to_coordinate.")
        button_num = {"left": "1", "middle": "2", "right": "3"}.get(button, "1")
        rc, _out, err = _os_xdotool([
            "mousemove", str(int(from_xy[0])), str(int(from_xy[1])),
            "mousedown", button_num,
            "mousemove", str(int(to_xy[0])), str(int(to_xy[1])),
            "mouseup", button_num,
        ])
        if rc != 0:
            return ActionResult(ok=False, action="drag", message=err.strip() or "xdotool drag failed")
        return ActionResult(ok=True, action="drag",
                            message=f"dragged {from_xy} → {to_xy}")

    def scroll(
        self,
        *,
        direction: str,
        amount: int = 3,
        element: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        modifiers: Optional[List[str]] = None,
    ) -> ActionResult:
        if x is not None and y is not None:
            _os_xdotool(["mousemove", str(int(x)), str(int(y))])
        # xdotool: button 4 = scroll up, 5 = down.
        button = "4" if direction in {"up", "left"} else "5"
        rc, _out, err = _os_xdotool(["click", "--repeat", str(max(1, min(50, amount))), button])
        if rc != 0:
            return ActionResult(ok=False, action="scroll", message=err.strip() or "xdotool scroll failed")
        return ActionResult(ok=True, action="scroll",
                            message=f"scrolled {direction} x{amount}")

    # ── Keyboard ────────────────────────────────────────────────────
    def type_text(self, text: str) -> ActionResult:
        rc, _out, err = _os_xdotool(["type", "--delay", "1", text])
        if rc != 0:
            return ActionResult(ok=False, action="type_text", message=err.strip() or "xdotool type failed")
        return ActionResult(ok=True, action="type_text",
                            message=f"typed {len(text)} characters")

    def key(self, keys: str) -> ActionResult:
        key_name, modifiers = _parse_key_combo(keys)
        if key_name is None:
            return ActionResult(ok=False, action="key",
                                message=f"could not parse key combo {keys!r}")
        combo = "+".join(modifiers + [key_name])
        rc, _out, err = _os_xdotool(["key", combo])
        if rc != 0:
            return ActionResult(ok=False, action="key", message=err.strip() or "xdotool key failed")
        return ActionResult(ok=True, action="key", message=f"pressed {keys!r}")

    def set_value(self, value: str, element: Optional[int] = None) -> ActionResult:
        if element is None:
            return ActionResult(ok=False, action="set_value",
                                message="set_value requires element= on Linux.")
        return ActionResult(ok=False, action="set_value",
                            message="Linux backend has no element model; use type_text instead.")

    # ── Introspection ──────────────────────────────────────────────
    def list_apps(self) -> List[Dict[str, Any]]:
        by_class: Dict[str, Dict[str, Any]] = {}
        for w in self.list_windows():
            app = w.get("app") or "unknown"
            entry = by_class.setdefault(app, {"name": app, "windows": 0, "window_titles": []})
            entry["windows"] += 1
            if w.get("title") and w["title"] not in entry["window_titles"]:
                entry["window_titles"].append(w["title"])
        apps = list(by_class.values())
        apps.sort(key=lambda a: a["name"].lower())
        return apps

    def focus_app(self, app: str, raise_window: bool = False) -> ActionResult:
        match = self._find_window(title=app)
        if match is None:
            return ActionResult(ok=False, action="focus_app",
                                message=f"no window matching {app!r} found")
        return self._activate(match, "focus_app")

    # ── Clipboard ──────────────────────────────────────────────────
    def read_clipboard(self) -> ActionResult:
        if not _tool_available("xclip"):
            return ActionResult(ok=False, action="read_clipboard",
                                message="xclip not installed (needed for clipboard on Linux)")
        rc, out, err = _os_run(["xclip", "-selection", "clipboard", "-o"])
        if rc != 0:
            return ActionResult(ok=False, action="read_clipboard",
                                message=err.strip() or "xclip read failed")
        text = out.rstrip("\n")
        return ActionResult(ok=True, action="read_clipboard",
                            message=f"clipboard has {len(text)} chars",
                            meta={"length": len(text), "text": text})

    def copy_clipboard(self, text: str) -> ActionResult:
        if not _tool_available("xclip"):
            return ActionResult(ok=False, action="copy_clipboard",
                                message="xclip not installed (needed for clipboard on Linux)")
        proc = subprocess.run(["xclip", "-selection", "clipboard"],
                              input=text, text=True, capture_output=True)
        if proc.returncode != 0:
            return ActionResult(ok=False, action="copy_clipboard",
                                message=(proc.stderr or "xclip write failed").strip())
        return ActionResult(ok=True, action="copy_clipboard",
                            message=f"copied {len(text)} chars to clipboard")

    def clear_clipboard(self) -> ActionResult:
        return self.copy_clipboard("")

    # ── Window management ──────────────────────────────────────────
    def list_windows(self) -> List[Dict[str, Any]]:
        rc, out, _err = _os_wmctrl(["-lx"])
        if rc != 0:
            return []
        return _parse_wmctrl_output(out)

    def get_active_window(self) -> Dict[str, Any]:
        if not _tool_available("xdotool"):
            return {}
        rc, out, _err = _os_xdotool(["getactivewindow"])
        if rc != 0:
            return {}
        hex_id = f"0x{int(out.strip(), 16):x}" if out.strip().isdigit() else ""
        for w in self.list_windows():
            if w.get("id") and hex_id and w["id"].lower() == hex_id.lower():
                return w
        return {}

    def _find_window(
        self,
        identifier: Optional[str] = None,
        title: Optional[str] = None,
        pid: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        for w in self.list_windows():
            if identifier is not None and str(w.get("id")) == str(identifier):
                return w
            if title and title.lower() in (w.get("title") or "").lower():
                return w
        return None

    def focus_window(
        self,
        identifier: Optional[str] = None,
        title: Optional[str] = None,
        pid: Optional[int] = None,
    ) -> ActionResult:
        match = self._find_window(identifier=identifier, title=title)
        if match is None:
            return ActionResult(ok=False, action="focus_window",
                                message="no matching window found")
        return self._activate(match, "focus_window")

    def _activate(self, win: Dict[str, Any], action_name: str) -> ActionResult:
        rc, _out, err = _os_wmctrl(["-ia", str(win["id"])])
        if rc != 0:
            return ActionResult(ok=False, action=action_name,
                                message=err.strip() or "wmctrl activate failed")
        return ActionResult(ok=True, action=action_name,
                            message=f"activated window {win['title']!r}")

    def minimize_window(
        self, identifier: Optional[str] = None, title: Optional[str] = None,
    ) -> ActionResult:
        match = self._find_window(identifier=identifier, title=title)
        if match is None:
            return ActionResult(ok=False, action="minimize_window",
                                message="no matching window found")
        rc, _out, err = _os_xdotool(["windowminimize", str(match["id"])])
        if rc != 0:
            return ActionResult(ok=False, action="minimize_window",
                                message=err.strip() or "xdotool windowminimize failed")
        return ActionResult(ok=True, action="minimize_window",
                            message=f"minimized window {match['title']!r}")

    def maximize_window(
        self, identifier: Optional[str] = None, title: Optional[str] = None,
    ) -> ActionResult:
        match = self._find_window(identifier=identifier, title=title)
        if match is None:
            return ActionResult(ok=False, action="maximize_window",
                                message="no matching window found")
        rc, _out, err = _os_xdotool(["windowsize", "--usehints", str(match["id"]), "100%", "100%"])
        if rc != 0:
            return ActionResult(ok=False, action="maximize_window",
                                message=err.strip() or "xdotool maximize failed")
        return ActionResult(ok=True, action="maximize_window",
                            message=f"maximized window {match['title']!r}")

    def close_window(
        self, identifier: Optional[str] = None, title: Optional[str] = None,
    ) -> ActionResult:
        match = self._find_window(identifier=identifier, title=title)
        if match is None:
            return ActionResult(ok=False, action="close_window",
                                message="no matching window found")
        # wmctrl -c sends a graceful WM_DELETE_WINDOW (same as clicking the
        # window's close button) — never a force-kill.
        rc, _out, err = _os_wmctrl(["-c", str(match["id"])])
        if rc != 0:
            return ActionResult(ok=False, action="close_window",
                                message=err.strip() or "wmctrl close failed")
        return ActionResult(ok=True, action="close_window",
                            message=f"sent close request to window {match['title']!r}")

    # ── App / system introspection ────────────────────────────────
    def get_system_info(self) -> Dict[str, Any]:
        return _os_get_system_info()

    def get_capabilities(self) -> Dict[str, Any]:
        from tools.computer_use.capabilities import (
            backend_capabilities, detect_platform_info,
        )
        platform_info = detect_platform_info()
        return {
            "os": platform_info.os,
            "platform": platform_info.to_dict(),
            "actions": backend_capabilities("linux"),
        }

    # ── Application launch / close ────────────────────────────────
    def launch_app(self, app: str, path: Optional[str] = None) -> ActionResult:
        if path:
            rc, _out, err = _os_run(["xdg-open", path])
            if rc != 0:
                return ActionResult(ok=False, action="launch_app",
                                    message=err.strip() or "xdg-open failed")
            return ActionResult(ok=True, action="launch_app",
                                message=f"opened {path!r} via xdg-open")
        name = (app or "").strip()
        if not name:
            return ActionResult(ok=False, action="launch_app",
                                message="launch_app requires `app` or `path`")
        resolved = shutil.which(name) if "/" not in name else name
        pid = _os_launch([resolved or name])
        if not pid:
            return ActionResult(ok=False, action="launch_app",
                                message=f"could not launch {name!r}")
        return ActionResult(ok=True, action="launch_app",
                            message=f"launched {name!r} (pid {pid})",
                            meta={"pid": pid, "command": name})

    def close_app(self, app: str, pid: Optional[int] = None) -> ActionResult:
        windows = self.list_windows()
        if not windows:
            return ActionResult(ok=False, action="close_app",
                                message="no windows found to close")
        targets = []
        if pid is not None:
            targets = [w for w in windows if w.get("pid") == pid]
        elif app:
            needle = (app or "").lower()
            targets = [w for w in windows if needle in (w.get("title") or "").lower()
                       or needle in (w.get("app") or "").lower()]
        if not targets:
            return ActionResult(ok=False, action="close_app",
                                message="no matching app window found")
        closed = 0
        for w in targets:
            rc, _out, _err = _os_wmctrl(["-c", str(w["id"])])
            if rc == 0:
                closed += 1
        if closed == 0:
            return ActionResult(ok=False, action="close_app",
                                message="failed to send close requests")
        return ActionResult(ok=True, action="close_app",
                            message=f"sent close request to {closed} window(s)",
                            meta={"windows": closed})

    # ── OCR-backed element search ──────────────────────────────────
    def find_text(self, text: str, app: Optional[str] = None) -> List[UIElement]:
        """OCR the screen via aetheros_vision and locate ``text`` occurrences."""
        cap = self.capture(mode="vision", app=app)
        if not cap.png_b64:
            return []
        try:
            raw = base64.b64decode(cap.png_b64, validate=False)
        except Exception:
            return []
        try:
            from aetheros_vision.ocr import create_ocr_engine
        except Exception as exc:  # pragma: no cover - dependency not present
            logger.debug("Linux find_text needs aetheros_vision: %s", exc)
            return []
        try:
            engine = create_ocr_engine()
            result = engine.extract_bytes(raw)
        except Exception as exc:  # pragma: no cover - OCR engine not available
            logger.debug("Linux find_text OCR failed: %s", exc)
            return []
        if not getattr(result, "success", False):
            return []

        needle = text.lower()
        out: List[UIElement] = []
        index = 1
        for block in getattr(result, "blocks", []) or []:
            label = getattr(block, "text", "") or ""
            if needle in label.lower():
                box = getattr(block, "box", None)
                if box is not None and hasattr(box, "x"):
                    out.append(UIElement(
                        index=index, role="AXStaticText", label=label,
                        bounds=(int(box.x), int(box.y),
                                int(getattr(box, "width", 0)),
                                int(getattr(box, "height", 0))),
                        app=app or "",
                    ))
                else:
                    out.append(UIElement(index=index, role="AXStaticText",
                                         label=label, app=app or ""))
                index += 1
        return out
