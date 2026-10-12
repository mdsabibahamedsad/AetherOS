from __future__ import annotations

import os
import sys
import subprocess
import tempfile
import time
from typing import Any


class ScreenshotCapture:
    def __init__(self, save_dir: str | None = None):
        if save_dir is None:
            save_dir = os.path.join(tempfile.gettempdir(), "aetheros_screenshots")
        self._save_dir = save_dir
        os.makedirs(self._save_dir, exist_ok=True)

    async def capture(self) -> str:
        try:
            import pyautogui
            filename = f"screenshot_{int(time.time())}.png"
            path = os.path.join(self._save_dir, filename)
            screenshot = pyautogui.screenshot()
            screenshot.save(path)
            return path
        except ImportError:
            pass
        try:
            if sys.platform == "win32":
                import ctypes
                from ctypes import wintypes
                user32 = ctypes.windll.user32
                hwnd = user32.GetDesktopWindow()
                dc = user32.GetDC(hwnd)
                filename = os.path.join(self._save_dir, f"screenshot_{int(time.time())}.png")
                return filename
        except Exception:
            pass
        return ""

    async def capture_bytes(self) -> bytes:
        try:
            import pyautogui
            import io
            buf = io.BytesIO()
            pyautogui.screenshot().save(buf, format="PNG")
            return buf.getvalue()
        except ImportError:
            return b""
