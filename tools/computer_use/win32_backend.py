"""Win32 computer-use backend.

Implements the full ``ComputerUseBackend`` interface on Windows via ctypes
(user32 / gdi32 / kernel32) plus PIL for screen capture. No third-party GUI
automation dependency is required — everything is stdlib ctypes + PIL.

Design notes
------------
* **Import-safe on any platform.** Module-level code never touches
  ``ctypes.windll``; every OS call goes through a module-level ``_os_*``
  function that raises ``RuntimeError`` when not on Windows. Tests monkeypatch
  those functions, and importing this module on Linux/macOS is harmless.
* **Virtual screen + multi-monitor.** ``get_screen_size`` returns the virtual
  screen metrics (which span all monitors, possibly with negative origins);
  ``capture`` grabs the full virtual screen and ``capture_region`` crops it.
* **Element model.** Windows exposes no free universal AX tree here, so
  ``capture(mode="som"/"ax")`` degrades to a plain vision capture with an
  empty ``elements`` list and a note. OCR-backed ``find_text`` is implemented
  via ``aetheros_ocr`` when available (tesseract / Windows OCR).
"""

from __future__ import annotations

import base64
import io
import logging
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple

from tools.computer_use.backend import (
    ActionResult,
    CaptureResult,
    ComputerUseBackend,
    UIElement,
)

logger = logging.getLogger(__name__)

_IS_WIN32 = sys.platform == "win32"

# ── Virtual-key map (pure data — no OS access) ───────────────────────────

_VK_SPECIAL = {
    "return": 0x0D, "enter": 0x0D, "tab": 0x09, "escape": 0x1B, "esc": 0x1B,
    "backspace": 0x08, "space": 0x20, "delete": 0x2E, "insert": 0x2D,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "shift": 0x10, "ctrl": 0x11, "control": 0x11, "alt": 0x12,
    "cmd": 0x5B, "win": 0x5B, "super": 0x5B, "lwin": 0x5B, "rwin": 0x5C,
    "capslock": 0x14, "numlock": 0x90, "scrolllock": 0x91,
    "printscreen": 0x2C, "pause": 0x13,
    "backspace": 0x08, "tab": 0x09, "capslock": 0x14,
}
# punctuation / symbol keys
_VK_PUNCT = {
    ".": 0xBE, ",": 0xBC, "/": 0xBF, "\\": 0xDC, ";": 0xBA, "'": 0xDE,
    "[": 0xDB, "]": 0xDD, "-": 0xBD, "=": 0xBB, "`": 0xC0,
}


def _build_key_map() -> Dict[str, int]:
    """Full VK map: function keys, letters, digits + specials + punctuation."""
    km: Dict[str, int] = dict(_VK_SPECIAL)
    for i in range(1, 25):
        km[f"f{i}"] = 0x6F + i
    for i in range(26):
        km[chr(ord("a") + i)] = ord("A") + i
        km[chr(ord("A") + i)] = ord("A") + i
    for i in range(10):
        km[str(i)] = ord("0") + i
    km.update(_VK_PUNCT)
    return km


KEY_TO_VK: Dict[str, int] = _build_key_map()

_MODIFIER_VK = {"shift": 0x10, "ctrl": 0x11, "control": 0x11, "alt": 0x12,
                "cmd": 0x5B, "win": 0x5B, "super": 0x5B}

# Window show-state commands (ShowWindow nCmdShow).
_SW_MINIMIZE = 6
_SW_MAXIMIZE = 3
_SW_RESTORE = 9

_WM_CLOSE = 0x0010


def _parse_key_combo(keys: str) -> Tuple[Optional[int], List[int]]:
    """Parse 'ctrl+alt+t' → (VK, [modifier VKs]); None key on parse failure."""
    parts = [p.strip().lower() for p in keys.replace(",", "+").split("+") if p.strip()]
    modifiers: List[int] = []
    key: Optional[int] = None
    for part in parts:
        if part in _MODIFIER_VK:
            modifiers.append(_MODIFIER_VK[part])
            continue
        vk = KEY_TO_VK.get(part)
        if vk is not None:
            key = vk
    return key, list(dict.fromkeys(modifiers))


def _clamp_region(
    x: int, y: int, width: int, height: int,
    screen_w: int, screen_h: int,
) -> Optional[Tuple[int, int, int, int]]:
    """Intersect a logical region with the virtual screen; None if empty.

    Returns (x, y, w, h) in logical coords, clamped to the screen bounds.
    """
    if width <= 0 or height <= 0:
        return None
    if screen_w <= 0 or screen_h <= 0:
        return None
    x2 = x + width
    y2 = y + height
    x = max(x, 0)
    y = max(y, 0)
    x2 = min(x2, screen_w)
    y2 = min(y2, screen_h)
    if x >= x2 or y >= y2:
        return None
    return x, y, x2 - x, y2 - y


# ── OS access layer (injectable for tests; windll only inside these) ─────

def _os_get_virtual_screen() -> Tuple[int, int, int, int]:
    """Return (x, y, width, height) of the virtual screen (logical px)."""
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    user32 = ctypes.windll.user32
    x = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
    y = user32.GetSystemMetrics(77)   # SM_YVIRTUALSCREEN
    w = user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
    h = user32.GetSystemMetrics(79)   # SM_CYVIRTUALSCREEN
    return int(x), int(y), int(w), int(h)


def _os_capture_virtual_screen() -> bytes:
    """PNG bytes of the full virtual screen (physical pixels)."""
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    from PIL import ImageGrab
    img = ImageGrab.grab(all_screens=True)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _os_get_foreground_window() -> Optional[int]:
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    return int(hwnd) if hwnd else None


def _os_enum_visible_windows() -> List[Tuple[int, int]]:
    """Return [(hwnd, pid), ...] for visible top-level windows."""
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    results: List[Tuple[int, int]] = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @WNDENUMPROC
    def _cb(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        results.append((int(hwnd), int(pid.value)))
        return True

    user32.EnumWindows(_cb, 0)
    return results


def _os_get_window_title(hwnd: int) -> str:
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    length = user32.GetWindowTextLengthW(wintypes.HWND(hwnd))
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(wintypes.HWND(hwnd), buf, length + 1)
    return buf.value


def _os_get_window_rect(hwnd: int) -> Tuple[int, int, int, int]:
    """Return (x, y, w, h) of a window's bounding rectangle in screen coords."""
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))
    return (int(rect.left), int(rect.top),
            int(rect.right - rect.left), int(rect.bottom - rect.top))


def _os_set_foreground_window(hwnd: int) -> bool:
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    return bool(user32.SetForegroundWindow(wintypes.HWND(hwnd)))


def _os_show_window(hwnd: int, cmd: int) -> bool:
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    return bool(user32.ShowWindow(wintypes.HWND(hwnd), cmd))


def _os_post_close(hwnd: int) -> bool:
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    return bool(user32.PostMessageW(wintypes.HWND(hwnd), _WM_CLOSE, 0, 0))


def _os_set_cursor_pos(x: int, y: int) -> bool:
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    return bool(ctypes.windll.user32.SetCursorPos(int(x), int(y)))


def _os_mouse_event(flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> None:
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    ctypes.windll.user32.mouse_event(flags, dx, dy, data, 0)


def _os_key_event(vk: int, key_up: bool) -> None:
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    flags = 0x0002 if key_up else 0
    ctypes.windll.user32.keybd_event(vk, 0, flags, 0)


def _os_send_unicode_chars(text: str) -> bool:
    """Type arbitrary unicode text via SendInput KEYEVENTF_UNICODE."""
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    from ctypes import wintypes

    if not text:
        return True

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG), ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", INPUTUNION)]

    def _input_for(char_code: int, key_up: bool) -> INPUT:
        inp = INPUT()
        inp.type = 1  # INPUT_KEYBOARD
        inp.u.ki.wVk = 0
        inp.u.ki.wScan = char_code
        inp.u.ki.dwFlags = 0x0004 | (0x0002 if key_up else 0)  # KEYEVENTF_UNICODE
        return inp

    inputs = (INPUT * (len(text) * 2))()
    idx = 0
    for ch in text:
        inputs[idx] = _input_for(ord(ch), False)
        idx += 1
        inputs[idx] = _input_for(ord(ch), True)
        idx += 1
    sent = ctypes.windll.user32.SendInput(
        len(inputs), ctypes.byref(inputs), ctypes.sizeof(INPUT))
    return sent == len(inputs)


def _os_clipboard_read_text() -> str:
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    CF_UNICODETEXT = 13
    if not user32.OpenClipboard(None):
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(wintypes.HGLOBAL(handle))
        if not ptr:
            return ""
        try:
            data = ctypes.wstring_at(ptr)
            return data
        finally:
            kernel32.GlobalUnlock(wintypes.HGLOBAL(handle))
    finally:
        user32.CloseClipboard()


def _os_clipboard_write_text(text: str) -> bool:
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        data = (text + "\0").encode("utf-16-le")
        size = len(data)
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not handle:
            return False
        ptr = kernel32.GlobalLock(wintypes.HGLOBAL(handle))
        if not ptr:
            return False
        try:
            ctypes.memmove(ptr, data, size)
        finally:
            kernel32.GlobalUnlock(wintypes.HGLOBAL(handle))
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            return False
        return True
    finally:
        user32.CloseClipboard()


def _os_clipboard_clear() -> bool:
    if not _IS_WIN32:
        raise RuntimeError("Win32Backend requires Windows")
    import ctypes
    user32 = ctypes.windll.user32
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        return True
    finally:
        user32.CloseClipboard()


def _os_get_system_info() -> Dict[str, Any]:
    """OS / CPU / RAM / disk info via stdlib + optional psutil. Never raises."""
    import platform as _platform
    info: Dict[str, Any] = {
        "os": _platform.system() or sys.platform,
        "os_version": _platform.version() or "",
        "architecture": _platform.machine() or "",
        "session_type": "windows",
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


def _os_launch_command(cmd: List[str], timeout: float = 10.0) -> int:
    """Start ``cmd`` detached from the console; returns the PID or 0."""
    import subprocess
    if not cmd:
        return 0
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL, creationflags=flags,
        )
        return int(proc.pid or 0)
    except Exception:  # noqa: BLE001 - launch best-effort
        return 0


# Mouse event flag constants (pure).
_MOUSEEVENTF_LEFTDOWN = 0x0002
_MOUSEEVENTF_LEFTUP = 0x0004
_MOUSEEVENTF_RIGHTDOWN = 0x0008
_MOUSEEVENTF_RIGHTUP = 0x0010
_MOUSEEVENTF_MIDDLEDOWN = 0x0020
_MOUSEEVENTF_MIDDLEUP = 0x0040
_MOUSEEVENTF_WHEEL = 0x0800

_BUTTON_FLAGS = {
    "left": (_MOUSEEVENTF_LEFTDOWN, _MOUSEEVENTF_LEFTUP),
    "right": (_MOUSEEVENTF_RIGHTDOWN, _MOUSEEVENTF_RIGHTUP),
    "middle": (_MOUSEEVENTF_MIDDLEDOWN, _MOUSEEVENTF_MIDDLEUP),
}


# ── The backend ───────────────────────────────────────────────────────────

class Win32Backend(ComputerUseBackend):
    """Real Windows adapter for the unified computer-use interface."""

    def __init__(self) -> None:
        self._started = False
        self._screen_origin: Tuple[int, int] = (0, 0)

    # ── Lifecycle ──────────────────────────────────────────────────
    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def is_available(self) -> bool:
        return _IS_WIN32

    def _screen_size(self) -> Tuple[int, int, int, int]:
        """Return (origin_x, origin_y, w, h) cached from the OS."""
        try:
            x, y, w, h = _os_get_virtual_screen()
        except RuntimeError:
            return 0, 0, 0, 0
        return x, y, w, h

    def get_screen_size(self) -> Tuple[int, int]:
        _, _, w, h = self._screen_size()
        return w, h

    # ── Capture ────────────────────────────────────────────────────
    def capture(self, mode: str = "som", app: Optional[str] = None) -> CaptureResult:
        try:
            raw = _os_capture_virtual_screen()
        except RuntimeError as exc:
            return CaptureResult(mode=mode, width=0, height=0, png_b64=None,
                                 elements=[], app="", window_title=str(exc))
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(raw))
        width, height = img.size
        png_b64 = base64.b64encode(raw).decode("ascii")
        # No free universal AX tree on Windows here — som/ax degrade to vision.
        return CaptureResult(
            mode=mode, width=width, height=height, png_b64=png_b64,
            elements=[], app=app or "", window_title="", png_bytes_len=len(raw),
            meta={"note": "som/ax degrade to a plain capture on Win32 (no AX tree)"},
        )

    def capture_region(
        self, x: int, y: int, width: int, height: int, mode: str = "vision",
    ) -> CaptureResult:
        try:
            raw = _os_capture_virtual_screen()
        except RuntimeError as exc:
            return CaptureResult(mode=mode, width=0, height=0, png_b64=None,
                                 elements=[], app="", window_title=str(exc))
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(raw))
        origin_x, origin_y, _, _ = self._screen_size()
        sx, sy = x - origin_x, y - origin_y
        region = _clamp_region(sx, sy, width, height, img.width, img.height)
        if region is None:
            return CaptureResult(mode=mode, width=0, height=0, png_b64=None,
                                 elements=[], app="",
                                 window_title="region outside the virtual screen")
        rx, ry, rw, rh = region
        crop = img.crop((rx, ry, rx + rw, ry + rh))
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        raw_region = buf.getvalue()
        return CaptureResult(
            mode=mode, width=rw, height=rh,
            png_b64=base64.b64encode(raw_region).decode("ascii"),
            elements=[], app="", window_title="", png_bytes_len=len(raw_region),
        )

    # ── Pointer ────────────────────────────────────────────────────
    def move_mouse(self, x: int, y: int) -> ActionResult:
        try:
            ok = _os_set_cursor_pos(x, y)
        except RuntimeError as exc:
            return ActionResult(ok=False, action="move_mouse", message=str(exc))
        return ActionResult(ok=ok, action="move_mouse",
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
            if element is None:
                return ActionResult(ok=False, action="click",
                                    message="click requires element= or x/y.")
            return ActionResult(ok=False, action="click",
                                message="Win32 backend has no element model; use x/y.")
        flags = _BUTTON_FLAGS.get(button)
        if flags is None:
            return ActionResult(ok=False, action="click",
                                message=f"unknown button {button!r}")
        try:
            for _ in range(max(1, click_count)):
                self._press_modifiers(modifiers)
                _os_set_cursor_pos(x, y)
                _os_mouse_event(flags[0])
                _os_mouse_event(flags[1])
                self._release_modifiers(modifiers)
        except RuntimeError as exc:
            return ActionResult(ok=False, action="click", message=str(exc))
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
                                message="Win32 backend has no element model; use from_coordinate/to_coordinate.")
        flags = _BUTTON_FLAGS.get(button, (_MOUSEEVENTF_LEFTDOWN, _MOUSEEVENTF_LEFTUP))
        try:
            self._press_modifiers(modifiers)
            _os_set_cursor_pos(int(from_xy[0]), int(from_xy[1]))
            _os_mouse_event(flags[0])
            _os_set_cursor_pos(int(to_xy[0]), int(to_xy[1]))
            _os_mouse_event(flags[1])
            self._release_modifiers(modifiers)
        except RuntimeError as exc:
            return ActionResult(ok=False, action="drag", message=str(exc))
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
            try:
                _os_set_cursor_pos(x, y)
            except RuntimeError as exc:
                return ActionResult(ok=False, action="scroll", message=str(exc))
        # WHEEL_DELTA = 120; positive scrolls up, negative scrolls down.
        sign = 1 if direction in {"up", "left"} else -1
        delta = sign * 120 * max(1, min(50, amount))
        try:
            self._press_modifiers(modifiers)
            _os_mouse_event(_MOUSEEVENTF_WHEEL, 0, 0, delta)
            self._release_modifiers(modifiers)
        except RuntimeError as exc:
            return ActionResult(ok=False, action="scroll", message=str(exc))
        return ActionResult(ok=True, action="scroll",
                            message=f"scrolled {direction} x{amount}")

    def _press_modifiers(self, modifiers: Optional[List[str]]) -> None:
        if not modifiers:
            return
        for name in modifiers:
            vk = _MODIFIER_VK.get(name.strip().lower())
            if vk:
                _os_key_event(vk, key_up=False)

    def _release_modifiers(self, modifiers: Optional[List[str]]) -> None:
        if not modifiers:
            return
        for name in reversed(modifiers):
            vk = _MODIFIER_VK.get(name.strip().lower())
            if vk:
                _os_key_event(vk, key_up=True)

    # ── Keyboard ────────────────────────────────────────────────────
    def type_text(self, text: str) -> ActionResult:
        try:
            ok = _os_send_unicode_chars(text)
        except RuntimeError as exc:
            return ActionResult(ok=False, action="type_text", message=str(exc))
        return ActionResult(ok=ok, action="type_text",
                            message=f"typed {len(text)} characters")

    def key(self, keys: str) -> ActionResult:
        vk, modifiers = _parse_key_combo(keys)
        if vk is None:
            return ActionResult(ok=False, action="key",
                                message=f"could not parse key combo {keys!r}")
        try:
            for m in modifiers:
                _os_key_event(m, key_up=False)
            _os_key_event(vk, key_up=False)
            _os_key_event(vk, key_up=True)
            for m in reversed(modifiers):
                _os_key_event(m, key_up=True)
        except RuntimeError as exc:
            return ActionResult(ok=False, action="key", message=str(exc))
        return ActionResult(ok=True, action="key", message=f"pressed {keys!r}")

    def set_value(self, value: str, element: Optional[int] = None) -> ActionResult:
        if element is None:
            return ActionResult(ok=False, action="set_value",
                                message="set_value requires element= on Win32.")
        return ActionResult(ok=False, action="set_value",
                            message="Win32 backend has no element model; use type_text instead.")

    # ── Introspection ──────────────────────────────────────────────
    def list_apps(self) -> List[Dict[str, Any]]:
        windows = self.list_windows()
        by_pid: Dict[int, Dict[str, Any]] = {}
        for w in windows:
            pid = w.get("pid", 0)
            if pid not in by_pid:
                by_pid[pid] = {"pid": pid, "name": w.get("app", ""),
                               "windows": 0, "window_titles": []}
            by_pid[pid]["windows"] += 1
            title = w.get("title", "")
            if title and title not in by_pid[pid]["window_titles"]:
                by_pid[pid]["window_titles"].append(title)
        apps = list(by_pid.values())
        apps.sort(key=lambda a: a["name"].lower())
        return apps

    def focus_app(self, app: str, raise_window: bool = False) -> ActionResult:
        """Windows has no background input routing — foreground the matching window."""
        match = self._find_window(app=app)
        if match is None:
            return ActionResult(ok=False, action="focus_app",
                                message=f"no window matching {app!r} found")
        try:
            _os_set_foreground_window(match["hwnd"])
        except RuntimeError as exc:
            return ActionResult(ok=False, action="focus_app", message=str(exc))
        return ActionResult(ok=True, action="focus_app",
                            message=f"focused window {match['title']!r}")

    # ── Clipboard ──────────────────────────────────────────────────
    def read_clipboard(self) -> ActionResult:
        try:
            text = _os_clipboard_read_text()
        except RuntimeError as exc:
            return ActionResult(ok=False, action="read_clipboard", message=str(exc))
        return ActionResult(ok=True, action="read_clipboard",
                            message=f"clipboard has {len(text)} chars",
                            meta={"length": len(text), "text": text})

    def copy_clipboard(self, text: str) -> ActionResult:
        try:
            ok = _os_clipboard_write_text(text)
        except RuntimeError as exc:
            return ActionResult(ok=False, action="copy_clipboard", message=str(exc))
        return ActionResult(ok=ok, action="copy_clipboard",
                            message=f"copied {len(text)} chars to clipboard")

    def clear_clipboard(self) -> ActionResult:
        try:
            ok = _os_clipboard_clear()
        except RuntimeError as exc:
            return ActionResult(ok=False, action="clear_clipboard", message=str(exc))
        return ActionResult(ok=ok, action="clear_clipboard",
                            message="clipboard cleared")

    # ── Window management ──────────────────────────────────────────
    def list_windows(self) -> List[Dict[str, Any]]:
        try:
            entries = _os_enum_visible_windows()
        except RuntimeError as exc:
            logger.debug("Win32 list_windows unavailable: %s", exc)
            return []
        origin_x, origin_y, _, _ = self._screen_size()
        windows = []
        for hwnd, pid in entries:
            try:
                title = _os_get_window_title(hwnd)
                rect = _os_get_window_rect(hwnd)
            except RuntimeError:
                continue
            windows.append({
                "hwnd": hwnd,
                "pid": pid,
                "title": title,
                "app": title,
                "x": rect[0] - origin_x, "y": rect[1] - origin_y,
                "width": rect[2], "height": rect[3],
            })
        windows.sort(key=lambda w: (w["title"] or "").lower())
        return windows

    def get_active_window(self) -> Dict[str, Any]:
        try:
            hwnd = _os_get_foreground_window()
        except RuntimeError:
            return {}
        if not hwnd:
            return {}
        try:
            title = _os_get_window_title(hwnd)
            rect = _os_get_window_rect(hwnd)
        except RuntimeError:
            return {"hwnd": hwnd}
        origin_x, origin_y, _, _ = self._screen_size()
        return {
            "hwnd": hwnd,
            "title": title,
            "app": title,
            "x": rect[0] - origin_x, "y": rect[1] - origin_y,
            "width": rect[2], "height": rect[3],
        }

    def _find_window(
        self,
        identifier: Optional[str] = None,
        title: Optional[str] = None,
        pid: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Locate a window by hwnd (identifier), title substring, or pid."""
        windows = self.list_windows()
        if identifier is not None:
            for w in windows:
                if str(w.get("hwnd")) == str(identifier):
                    return w
        if pid is not None:
            for w in windows:
                if w.get("pid") == pid:
                    return w
        if title:
            needle = title.lower()
            for w in windows:
                if needle in (w.get("title") or "").lower():
                    return w
        return None

    def focus_window(
        self,
        identifier: Optional[str] = None,
        title: Optional[str] = None,
        pid: Optional[int] = None,
    ) -> ActionResult:
        match = self._find_window(identifier=identifier, title=title, pid=pid)
        if match is None:
            return ActionResult(ok=False, action="focus_window",
                                message="no matching window found")
        try:
            ok = _os_set_foreground_window(match["hwnd"])
        except RuntimeError as exc:
            return ActionResult(ok=False, action="focus_window", message=str(exc))
        return ActionResult(ok=ok, action="focus_window",
                            message=f"focused window {match['title']!r}")

    def minimize_window(
        self, identifier: Optional[str] = None, title: Optional[str] = None,
    ) -> ActionResult:
        return self._window_show(identifier, title, _SW_MINIMIZE, "minimize_window")

    def maximize_window(
        self, identifier: Optional[str] = None, title: Optional[str] = None,
    ) -> ActionResult:
        return self._window_show(identifier, title, _SW_MAXIMIZE, "maximize_window")

    def _window_show(
        self, identifier: Optional[str], title: Optional[str],
        cmd: int, action_name: str,
    ) -> ActionResult:
        match = self._find_window(identifier=identifier, title=title)
        if match is None:
            return ActionResult(ok=False, action=action_name,
                                message="no matching window found")
        try:
            ok = _os_show_window(match["hwnd"], cmd)
        except RuntimeError as exc:
            return ActionResult(ok=False, action=action_name, message=str(exc))
        return ActionResult(ok=ok, action=action_name,
                            message=f"{action_name.replace('_window', '')} window {match['title']!r}")

    def close_window(
        self, identifier: Optional[str] = None, title: Optional[str] = None,
    ) -> ActionResult:
        match = self._find_window(identifier=identifier, title=title)
        if match is None:
            return ActionResult(ok=False, action="close_window",
                                message="no matching window found")
        try:
            ok = _os_post_close(match["hwnd"])
        except RuntimeError as exc:
            return ActionResult(ok=False, action="close_window", message=str(exc))
        return ActionResult(ok=ok, action="close_window",
                            message=f"sent WM_CLOSE to window {match['title']!r}")

    # ── App / system introspection ────────────────────────────────
    def get_system_info(self) -> Dict[str, Any]:
        try:
            return _os_get_system_info()
        except RuntimeError as exc:
            return {"error": str(exc)}

    def get_capabilities(self) -> Dict[str, Any]:
        from tools.computer_use.capabilities import (
            backend_capabilities, detect_platform_info,
        )
        platform_info = detect_platform_info()
        return {
            "os": platform_info.os,
            "platform": platform_info.to_dict(),
            "actions": backend_capabilities("win32"),
        }

    # ── Application launch / close ────────────────────────────────
    def launch_app(self, app: str, path: Optional[str] = None) -> ActionResult:
        cmd: List[str] = []
        if path:
            cmd = [path]
        else:
            name = (app or "").strip()
            if not name:
                return ActionResult(ok=False, action="launch_app",
                                    message="launch_app requires `app` or `path`")
            resolved = shutil.which(name) if "/" not in name and "\\" not in name else None
            cmd = [resolved or name]
        pid = _os_launch_command(cmd)
        if not pid:
            return ActionResult(ok=False, action="launch_app",
                                message=f"could not launch {cmd[0]!r}")
        return ActionResult(ok=True, action="launch_app",
                            message=f"launched {cmd[0]!r} (pid {pid})",
                            meta={"pid": pid, "command": cmd[0]})

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
            targets = [w for w in windows if needle in (w.get("title") or "").lower()]
        if not targets:
            return ActionResult(ok=False, action="close_app",
                                message="no matching app window found")
        closed = 0
        for w in targets:
            try:
                if _os_post_close(w["hwnd"]):
                    closed += 1
            except RuntimeError:
                continue
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
            logger.debug("Win32 find_text needs aetheros_vision: %s", exc)
            return []
        try:
            engine = create_ocr_engine()
            result = engine.extract_bytes(raw)
        except Exception as exc:  # pragma: no cover - OCR engine not available
            logger.debug("Win32 find_text OCR failed: %s", exc)
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
