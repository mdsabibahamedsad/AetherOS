from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ComputerAction(Enum):
    SCREENSHOT = "screenshot"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    KEYBOARD_SHORTCUT = "keyboard_shortcut"
    SCROLL = "scroll"
    DRAG_DROP = "drag_drop"
    HOVER = "hover"
    MOVE_MOUSE = "move_mouse"
    GET_SCREEN_INFO = "get_screen_info"
    DETECT_WINDOWS = "detect_windows"
    FOCUS_WINDOW = "focus_window"


@dataclass
class ComputerPermission:
    action: ComputerAction
    requires_approval: bool = True
    granted: bool = False
    grant_duration: str = "once"


class ComputerUseManager:
    def __init__(self):
        self._enabled: bool = False
        self._permissions: dict[ComputerAction, ComputerPermission] = {}
        self._screen_info: dict = {}
        self._init_permissions()

    def _init_permissions(self):
        always_allow = {ComputerAction.GET_SCREEN_INFO, ComputerAction.DETECT_WINDOWS}
        for action in ComputerAction:
            self._permissions[action] = ComputerPermission(
                action=action,
                requires_approval=action not in always_allow,
                granted=False,
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self):
        self._enabled = True
        logger.info("Computer use enabled")

    def disable(self):
        self._enabled = False
        self._revoke_all()
        logger.info("Computer use disabled")

    def grant_permission(self, action: ComputerAction, duration: str = "once") -> bool:
        perm = self._permissions.get(action)
        if perm is None:
            return False
        perm.granted = True
        perm.grant_duration = duration
        return True

    def revoke_permission(self, action: ComputerAction):
        perm = self._permissions.get(action)
        if perm:
            perm.granted = False
            perm.grant_duration = "once"

    def _revoke_all(self):
        for perm in self._permissions.values():
            if perm.grant_duration != "permanent":
                perm.granted = False

    def check_permission(self, action: ComputerAction) -> bool:
        if not self._enabled:
            return False
        perm = self._permissions.get(action)
        return perm is not None and perm.granted

    def get_pending_permissions(self) -> list[ComputerPermission]:
        return [p for p in self._permissions.values() if not p.granted and p.requires_approval]

    async def get_screen_info(self) -> dict[str, Any]:
        try:
            import pyautogui
            w, h = pyautogui.size()
            self._screen_info = {"width": w, "height": h}
            return self._screen_info
        except Exception as e:
            logger.warning("Failed to get screen info: %s", e)
            return {"error": str(e)}

    async def take_screenshot(self) -> bytes | None:
        if not self.check_permission(ComputerAction.SCREENSHOT):
            logger.warning("Screenshot permission not granted")
            return None
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            import io
            buf = io.BytesIO()
            screenshot.save(buf, format="PNG")
            buf.seek(0)
            return buf.read()
        except Exception as e:
            logger.warning("Screenshot failed: %s", e)
            return None

    async def detect_windows(self) -> list[dict[str, Any]]:
        if not self.check_permission(ComputerAction.DETECT_WINDOWS):
            return []
        windows = []
        try:
            import pygetwindow as gw
            for w in gw.getAllWindows():
                if w.title:
                    windows.append({
                        "title": w.title,
                        "left": w.left, "top": w.top,
                        "width": w.width, "height": w.height,
                        "active": w.isActive,
                        "minimized": w.isMinimized,
                    })
        except ImportError:
            try:
                import subprocess
                import json
                if hasattr(subprocess, "check_output"):
                    if __import__("sys").platform == "win32":
                        result = subprocess.check_output(
                            "powershell -Command \"Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -ExpandProperty MainWindowTitle\"",
                            shell=True,
                            text=True,
                        )
                        for line in result.strip().split("\n"):
                            if line.strip():
                                windows.append({"title": line.strip()})
            except Exception:
                pass
        except Exception as e:
            logger.warning("Window detection failed: %s", e)
        return windows

    async def click(self, x: int, y: int, button: str = "left") -> bool:
        if not self.check_permission(ComputerAction.CLICK):
            return False
        try:
            import pyautogui
            pyautogui.click(x, y, button=button)
            return True
        except Exception as e:
            logger.warning("Click failed: %s", e)
            return False

    async def type_text(self, text: str) -> bool:
        if not self.check_permission(ComputerAction.TYPE):
            return False
        try:
            import pyautogui
            pyautogui.write(text)
            return True
        except Exception as e:
            logger.warning("Type failed: %s", e)
            return False

    async def keyboard_shortcut(self, keys: list[str]) -> bool:
        if not self.check_permission(ComputerAction.KEYBOARD_SHORTCUT):
            return False
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            logger.warning("Keyboard shortcut failed: %s", e)
            return False

    async def scroll(self, clicks: int = -3, x: int | None = None, y: int | None = None) -> bool:
        if not self.check_permission(ComputerAction.SCROLL):
            return False
        try:
            import pyautogui
            pyautogui.scroll(clicks, x=x, y=y)
            return True
        except Exception as e:
            logger.warning("Scroll failed: %s", e)
            return False

    async def move_mouse(self, x: int, y: int, duration: float = 0.5) -> bool:
        if not self.check_permission(ComputerAction.MOVE_MOUSE):
            return False
        try:
            import pyautogui
            pyautogui.moveTo(x, y, duration=duration)
            return True
        except Exception as e:
            logger.warning("Mouse move failed: %s", e)
            return False

    async def drag_drop(self, start_x: int, start_y: int, end_x: int, end_y: int) -> bool:
        if not self.check_permission(ComputerAction.DRAG_DROP):
            return False
        try:
            import pyautogui
            pyautogui.moveTo(start_x, start_y)
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=0.5)
            return True
        except Exception as e:
            logger.warning("Drag drop failed: %s", e)
            return False

    async def focus_window(self, title: str) -> bool:
        if not self.check_permission(ComputerAction.FOCUS_WINDOW):
            return False
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].activate()
                return True
            return False
        except Exception:
            try:
                import subprocess
                if __import__("sys").platform == "win32":
                    subprocess.run(
                        ["powershell", "-Command", f"(New-Object -ComObject WScript.Shell).AppActivate('{title}')"],
                        capture_output=True,
                    )
                    return True
            except Exception:
                pass
            return False
