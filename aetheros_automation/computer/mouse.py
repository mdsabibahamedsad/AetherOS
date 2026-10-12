from __future__ import annotations

import logging
import sys
import time
from typing import Optional, Tuple

log = logging.getLogger(__name__)


class MouseController:
    def __init__(self):
        self._pyautogui = None
        self._use_pyautogui = False
        self._user32 = None
        self._init_backend()

    def _init_backend(self):
        try:
            import pyautogui
            self._pyautogui = pyautogui
            self._use_pyautogui = True
            log.debug("MouseController: using pyautogui")
        except ImportError:
            if sys.platform == "win32":
                self._init_win32()
            else:
                log.warning("MouseController: pyautogui not available, no fallback")

    def _init_win32(self):
        import ctypes
        from ctypes import wintypes

        self._user32 = ctypes.windll.user32

        self._MOUSEEVENTF_MOVE = 0x0001
        self._MOUSEEVENTF_LEFTDOWN = 0x0002
        self._MOUSEEVENTF_LEFTUP = 0x0004
        self._MOUSEEVENTF_RIGHTDOWN = 0x0008
        self._MOUSEEVENTF_RIGHTUP = 0x0010
        self._MOUSEEVENTF_MIDDLEDOWN = 0x0020
        self._MOUSEEVENTF_MIDDLEUP = 0x0040
        self._MOUSEEVENTF_WHEEL = 0x0800

        log.debug("MouseController: using ctypes Win32 fallback")

    def _is_pyautogui(self) -> bool:
        return self._use_pyautogui

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left"):
        if self._is_pyautogui():
            self._pyautogui.click(x, y, button=button)
        elif self._user32:
            if x is not None and y is not None:
                self._user32.SetCursorPos(x, y)
                time.sleep(0.05)
            if button == "right":
                self._user32.mouse_event(self._MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                self._user32.mouse_event(self._MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            elif button == "middle":
                self._user32.mouse_event(self._MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
                self._user32.mouse_event(self._MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
            else:
                self._user32.mouse_event(self._MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                self._user32.mouse_event(self._MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            raise RuntimeError("No mouse backend available")

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None):
        if self._is_pyautogui():
            self._pyautogui.doubleClick(x, y)
        elif self._user32:
            if x is not None and y is not None:
                self._user32.SetCursorPos(x, y)
                time.sleep(0.05)
            self._user32.mouse_event(self._MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            self._user32.mouse_event(self._MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.05)
            self._user32.mouse_event(self._MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            self._user32.mouse_event(self._MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            raise RuntimeError("No mouse backend available")

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None):
        self.click(x, y, button="right")

    def move(self, x: int, y: int):
        if self._is_pyautogui():
            self._pyautogui.moveTo(x, y)
        elif self._user32:
            self._user32.SetCursorPos(x, y)
        else:
            raise RuntimeError("No mouse backend available")

    def drag(self, x1: int, y1: int, x2: int, y2: int, button: str = "left"):
        if self._is_pyautogui():
            self._pyautogui.moveTo(x1, y1)
            self._pyautogui.drag(x2 - x1, y2 - y1, button=button)
        elif self._user32:
            self.move(x1, y1)
            time.sleep(0.1)
            down_flag = self._MOUSEEVENTF_LEFTDOWN
            up_flag = self._MOUSEEVENTF_LEFTUP
            if button == "right":
                down_flag = self._MOUSEEVENTF_RIGHTDOWN
                up_flag = self._MOUSEEVENTF_RIGHTUP
            elif button == "middle":
                down_flag = self._MOUSEEVENTF_MIDDLEDOWN
                up_flag = self._MOUSEEVENTF_MIDDLEUP
            self._user32.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.05)
            steps = 20
            for i in range(1, steps + 1):
                cx = x1 + (x2 - x1) * i // steps
                cy = y1 + (y2 - y1) * i // steps
                self._user32.SetCursorPos(cx, cy)
                time.sleep(0.01)
            self._user32.mouse_event(up_flag, 0, 0, 0, 0)
        else:
            raise RuntimeError("No mouse backend available")

    def scroll(self, amount: int, direction: str = "down"):
        if self._is_pyautogui():
            clicks = -amount if direction == "down" else amount
            self._pyautogui.scroll(clicks)
        elif self._user32:
            wheel_amount = -amount if direction == "down" else amount
            self._user32.mouse_event(self._MOUSEEVENTF_WHEEL, 0, 0, wheel_amount * 120, 0)
        else:
            raise RuntimeError("No mouse backend available")

    def get_position(self) -> Tuple[int, int]:
        if self._is_pyautogui():
            return self._pyautogui.position()
        elif self._user32:
            import ctypes
            from ctypes import wintypes

            class POINT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

            pt = POINT()
            self._user32.GetCursorPos(ctypes.byref(pt))
            return (pt.x, pt.y)
        else:
            raise RuntimeError("No mouse backend available")
