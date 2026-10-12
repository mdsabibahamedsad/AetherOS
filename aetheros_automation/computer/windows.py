from __future__ import annotations

import logging
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


class WindowManager:
    def __init__(self):
        self._platform = sys.platform
        self._win32gui = None
        self._user32 = None
        self._init_backend()

    def _init_backend(self):
        if self._platform == "win32":
            try:
                import win32gui
                import win32con
                import win32process
                self._win32gui = win32gui
                self._win32con = win32con
                self._win32process = win32process
                log.debug("WindowManager: using win32gui")
            except ImportError:
                import ctypes
                self._user32 = ctypes.windll.user32
                log.debug("WindowManager: using ctypes Win32 fallback")
        elif self._platform == "darwin":
            log.debug("WindowManager: using osascript (macOS)")
        else:
            log.debug("WindowManager: using xdotool/wmctrl (Linux)")

    def list_windows(self) -> List[Dict[str, Any]]:
        if self._win32gui:
            return self._list_windows_win32()
        elif self._user32:
            return self._list_windows_ctypes()
        elif self._platform == "darwin":
            return self._list_windows_macos()
        else:
            return self._list_windows_linux()

    def _list_windows_win32(self) -> List[Dict[str, Any]]:
        windows: List[Dict[str, Any]] = []

        def enum_callback(hwnd, _):
            if not self._win32gui.IsWindowVisible(hwnd):
                return True
            title = self._win32gui.GetWindowText(hwnd)
            if not title:
                return True
            _, pid = self._win32process.GetWindowThreadProcessId(hwnd)
            windows.append({
                "hwnd": hwnd,
                "title": title,
                "process_id": pid,
                "class_name": self._win32gui.GetClassName(hwnd),
            })
            return True

        self._win32gui.EnumWindows(enum_callback, None)
        return windows

    def _list_windows_ctypes(self) -> List[Dict[str, Any]]:
        import ctypes
        from ctypes import wintypes

        windows: List[Dict[str, Any]] = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def enum_callback(hwnd, lparam):
            if not self._user32.IsWindowVisible(hwnd):
                return True
            length = self._user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value
            if not title:
                return True
            pid = wintypes.DWORD()
            self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            windows.append({
                "hwnd": hwnd,
                "title": title,
                "process_id": pid.value,
                "class_name": "",
            })
            return True

        callback = WNDENUMPROC(enum_callback)
        self._user32.EnumWindows(callback, 0)
        return windows

    def _list_windows_macos(self) -> List[Dict[str, Any]]:
        windows: List[Dict[str, Any]] = []
        try:
            result = subprocess.run(
                [
                    "osascript", "-e",
                    'tell application "System Events" to get {name, id} of every process whose visible is true',
                ],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                items = [x.strip() for x in result.stdout.split(",")]
                processes = []
                for i in range(0, len(items), 2):
                    if i + 1 < len(items):
                        processes.append({"name": items[i], "pid": items[i + 1]})

                for proc in processes:
                    win_result = subprocess.run(
                        [
                            "osascript", "-e",
                            f'tell application "System Events" to get title of every window of process "{proc["name"]}"',
                        ],
                        capture_output=True, text=True, timeout=10,
                    )
                    if win_result.returncode == 0 and win_result.stdout.strip():
                        titles = win_result.stdout.strip().split(", ")
                        for t in titles:
                            t_clean = t.strip()
                            if t_clean:
                                windows.append({
                                    "title": t_clean,
                                    "process_id": int(proc["pid"]) if proc["pid"].isdigit() else 0,
                                    "process_name": proc["name"],
                                })
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError) as e:
            log.warning("Failed to list macOS windows: %s", e)
        return windows

    def _list_windows_linux(self) -> List[Dict[str, Any]]:
        windows: List[Dict[str, Any]] = []
        try:
            result = subprocess.run(
                ["wmctrl", "-l", "-p"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        windows.append({
                            "hwnd": int(parts[0], 16),
                            "process_id": int(parts[1]),
                            "title": parts[3],
                        })
                    elif len(parts) >= 3:
                        windows.append({
                            "hwnd": int(parts[0], 16),
                            "process_id": int(parts[1]),
                            "title": parts[2] if len(parts) > 2 else "",
                        })
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            log.warning("Failed to list Linux windows (wmctrl required): %s", e)
        return windows

    def get_active_window(self) -> Optional[Dict[str, Any]]:
        if self._win32gui:
            hwnd = self._win32gui.GetForegroundWindow()
            if hwnd:
                title = self._win32gui.GetWindowText(hwnd)
                _, pid = self._win32process.GetWindowThreadProcessId(hwnd)
                return {
                    "hwnd": hwnd,
                    "title": title,
                    "process_id": pid,
                }
        elif self._user32:
            import ctypes
            from ctypes import wintypes

            hwnd = self._user32.GetForegroundWindow()
            if hwnd:
                length = self._user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    self._user32.GetWindowTextW(hwnd, buffer, length + 1)
                    title = buffer.value
                    pid = wintypes.DWORD()
                    self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    return {
                        "hwnd": hwnd,
                        "title": title,
                        "process_id": pid.value,
                    }
        elif self._platform == "darwin":
            try:
                result = subprocess.run(
                    [
                        "osascript", "-e",
                        'tell application "System Events" to get {name, title} of first process whose frontmost is true',
                    ],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0 and result.stdout.strip():
                    parts = result.stdout.strip().split(", ")
                    if len(parts) >= 2:
                        return {"process_name": parts[0], "title": parts[1]}
            except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                log.warning("Failed to get active macOS window: %s", e)
        else:
            try:
                result = subprocess.run(
                    ["xdotool", "getactivewindow"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    wid = result.stdout.strip()
                    name_result = subprocess.run(
                        ["xdotool", "getwindowname", wid], capture_output=True, text=True, timeout=5
                    )
                    title = name_result.stdout.strip() if name_result.returncode == 0 else ""
                    pid_result = subprocess.run(
                        ["xdotool", "getwindowpid", wid], capture_output=True, text=True, timeout=5
                    )
                    pid = int(pid_result.stdout.strip()) if pid_result.returncode == 0 and pid_result.stdout.strip().isdigit() else 0
                    return {"hwnd": int(wid), "title": title, "process_id": pid}
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                log.warning("Failed to get active Linux window (xdotool required): %s", e)
        return None

    def focus_window(self, title_or_pid: str | int):
        if self._win32gui:
            self._focus_window_win32(title_or_pid)
        elif self._user32:
            self._focus_window_ctypes(title_or_pid)
        elif self._platform == "darwin":
            self._focus_window_macos(title_or_pid)
        else:
            self._focus_window_linux(title_or_pid)

    def _focus_window_win32(self, title_or_pid: str | int):
        hwnd = self._find_hwnd_win32(title_or_pid)
        if hwnd:
            if self._win32gui.IsIconic(hwnd):
                self._win32gui.ShowWindow(hwnd, self._win32con.SW_RESTORE)
            self._win32gui.SetForegroundWindow(hwnd)

    def _focus_window_ctypes(self, title_or_pid: str | int):
        hwnd = self._find_hwnd_ctypes(title_or_pid)
        if hwnd:
            if self._user32.IsIconic(hwnd):
                self._user32.ShowWindow(hwnd, 9)
            self._user32.SetForegroundWindow(hwnd)

    def _focus_window_macos(self, title_or_pid: str | int):
        title = str(title_or_pid)
        try:
            subprocess.run(
                ["osascript", "-e", f'tell application "{title}" to activate'],
                capture_output=True, timeout=15,
            )
        except subprocess.TimeoutExpired:
            log.warning("Failed to focus macOS window: %s", title_or_pid)

    def _focus_window_linux(self, title_or_pid: str | int):
        target = str(title_or_pid)
        try:
            if isinstance(title_or_pid, int) or target.isdigit():
                subprocess.run(
                    ["xdotool", "windowactivate", str(title_or_pid)],
                    capture_output=True, timeout=5,
                )
            else:
                subprocess.run(
                    ["xdotool", "search", "--name", target, "windowactivate"],
                    capture_output=True, timeout=5,
                )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            log.warning("Failed to focus Linux window: %s", e)

    def _find_hwnd_win32(self, title_or_pid: str | int) -> Optional[int]:
        if isinstance(title_or_pid, int):
            return self._find_hwnd_by_pid_win32(title_or_pid)
        return self._find_hwnd_by_title_win32(title_or_pid)

    def _find_hwnd_by_title_win32(self, title: str) -> Optional[int]:
        def enum_callback(hwnd, _):
            if not self._win32gui.IsWindowVisible(hwnd):
                return True
            win_title = self._win32gui.GetWindowText(hwnd)
            if title.lower() in win_title.lower() or win_title.lower() in title.lower():
                found.append(hwnd)
                return False
            return True

        found: list = []
        self._win32gui.EnumWindows(enum_callback, None)
        return found[0] if found else None

    def _find_hwnd_by_pid_win32(self, pid: int) -> Optional[int]:
        def enum_callback(hwnd, _):
            if not self._win32gui.IsWindowVisible(hwnd):
                return True
            _, win_pid = self._win32gui.GetWindowThreadProcessId(hwnd)
            if win_pid == pid:
                found.append(hwnd)
                return False
            return True

        found: list = []
        self._win32gui.EnumWindows(enum_callback, None)
        return found[0] if found else None

    def _find_hwnd_ctypes(self, title_or_pid: str | int) -> Optional[int]:
        import ctypes
        from ctypes import wintypes

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        found: list = []

        if isinstance(title_or_pid, int):
            target_pid = title_or_pid

            def enum_callback(hwnd, lparam):
                if not self._user32.IsWindowVisible(hwnd):
                    return True
                pid = wintypes.DWORD()
                self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == target_pid:
                    found.append(hwnd)
                    return False
                return True
        else:
            target_title = str(title_or_pid).lower()

            def enum_callback(hwnd, lparam):
                if not self._user32.IsWindowVisible(hwnd):
                    return True
                length = self._user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buffer = ctypes.create_unicode_buffer(length + 1)
                self._user32.GetWindowTextW(hwnd, buffer, length + 1)
                win_title = buffer.value.lower()
                if target_title in win_title or win_title in target_title:
                    found.append(hwnd)
                    return False
                return True

        callback = WNDENUMPROC(enum_callback)
        self._user32.EnumWindows(callback, 0)
        return found[0] if found else None

    def minimize_window(self, title_or_pid: str | int):
        if self._win32gui:
            hwnd = self._find_hwnd_win32(title_or_pid)
            if hwnd:
                self._win32gui.ShowWindow(hwnd, self._win32con.SW_MINIMIZE)
        elif self._user32:
            hwnd = self._find_hwnd_ctypes(title_or_pid)
            if hwnd:
                self._user32.ShowWindow(hwnd, 6)
        elif self._platform == "darwin":
            title = str(title_or_pid)
            subprocess.run(
                ["osascript", "-e",
                 f'tell application "System Events" to set miniaturized of every window of first process whose name contains "{title}" to true'],
                capture_output=True, timeout=10,
            )

    def maximize_window(self, title_or_pid: str | int):
        if self._win32gui:
            hwnd = self._find_hwnd_win32(title_or_pid)
            if hwnd:
                self._win32gui.ShowWindow(hwnd, self._win32con.SW_MAXIMIZE)
        elif self._user32:
            hwnd = self._find_hwnd_ctypes(title_or_pid)
            if hwnd:
                self._user32.ShowWindow(hwnd, 3)
        elif self._platform == "darwin":
            title = str(title_or_pid)
            subprocess.run(
                ["osascript", "-e",
                 f'tell application "{title}" to set bounds of front window to {{0, 0, 2560, 1440}}'],
                capture_output=True, timeout=10,
            )

    def restore_window(self, title_or_pid: str | int):
        if self._win32gui:
            hwnd = self._find_hwnd_win32(title_or_pid)
            if hwnd:
                self._win32gui.ShowWindow(hwnd, self._win32con.SW_RESTORE)
        elif self._user32:
            hwnd = self._find_hwnd_ctypes(title_or_pid)
            if hwnd:
                self._user32.ShowWindow(hwnd, 9)
        elif self._platform == "darwin":
            title = str(title_or_pid)
            subprocess.run(
                ["osascript", "-e",
                 f'tell application "System Events" to set miniaturized of every window of first process whose name contains "{title}" to false'],
                capture_output=True, timeout=10,
            )

    def close_window(self, title_or_pid: str | int):
        if self._win32gui:
            hwnd = self._find_hwnd_win32(title_or_pid)
            if hwnd:
                self._win32gui.PostMessage(hwnd, self._win32con.WM_CLOSE, 0, 0)
        elif self._user32:
            hwnd = self._find_hwnd_ctypes(title_or_pid)
            if hwnd:
                WM_CLOSE = 0x0010
                self._user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        elif self._platform == "darwin":
            title = str(title_or_pid)
            subprocess.run(
                ["osascript", "-e", f'tell application "{title}" to close front window'],
                capture_output=True, timeout=10,
            )
        else:
            try:
                subprocess.run(
                    ["xdotool", "search", "--name", str(title_or_pid), "windowclose"],
                    capture_output=True, timeout=5,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                log.warning("Failed to close Linux window: %s", e)

    def get_window_bounds(self, title: str) -> Optional[Dict[str, int]]:
        if self._win32gui:
            hwnd = self._find_hwnd_by_title_win32(title)
            if hwnd:
                rect = self._win32gui.GetWindowRect(hwnd)
                return {"x": rect[0], "y": rect[1], "width": rect[2] - rect[0], "height": rect[3] - rect[1]}
        elif self._user32:
            import ctypes
            from ctypes import wintypes

            hwnd = self._find_hwnd_ctypes(title)
            if hwnd:
                class RECT(ctypes.Structure):
                    _fields_ = [
                        ("left", wintypes.LONG),
                        ("top", wintypes.LONG),
                        ("right", wintypes.LONG),
                        ("bottom", wintypes.LONG),
                    ]
                rect = RECT()
                self._user32.GetWindowRect(hwnd, ctypes.byref(rect))
                return {
                    "x": rect.left,
                    "y": rect.top,
                    "width": rect.right - rect.left,
                    "height": rect.bottom - rect.top,
                }
        elif self._platform == "darwin":
            try:
                result = subprocess.run(
                    ["osascript", "-e",
                     f'tell application "System Events" to get bounds of first window of first process whose name contains "{title}"'],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0 and result.stdout.strip():
                    parts = result.stdout.strip().split(", ")
                    if len(parts) == 4:
                        return {
                            "x": int(parts[0]),
                            "y": int(parts[1]),
                            "width": int(parts[2]) - int(parts[0]),
                            "height": int(parts[3]) - int(parts[1]),
                        }
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError) as e:
                log.warning("Failed to get macOS window bounds: %s", e)
        else:
            try:
                wid_result = subprocess.run(
                    ["xdotool", "search", "--name", title, "getwindowgeometry"],
                    capture_output=True, text=True, timeout=5,
                )
                if wid_result.returncode == 0:
                    coords = {}
                    for line in wid_result.stdout.strip().split("\n"):
                        if ":" in line:
                            key, val = line.split(":", 1)
                            coords[key.strip()] = val.strip()
                    if "x" in coords or "X" in coords:
                        x_part = coords.get("x") or coords.get("X", "0")
                        y_part = coords.get("y") or coords.get("Y", "0")
                        width_part = "0"
                        height_part = "0"
                        for k in coords:
                            if k.lower().strip() == "width":
                                width_part = coords[k]
                            elif k.lower().strip() == "height":
                                height_part = coords[k]
                        return {
                            "x": int(x_part) if x_part.isdigit() else 0,
                            "y": int(y_part) if y_part.isdigit() else 0,
                            "width": int(width_part) if width_part.isdigit() else 800,
                            "height": int(height_part) if height_part.isdigit() else 600,
                        }
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                log.warning("Failed to get Linux window bounds: %s", e)
        return None
