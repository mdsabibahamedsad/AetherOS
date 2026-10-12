from __future__ import annotations

import io
import logging
import os
import sys
import tempfile
from datetime import datetime
from typing import Optional, Tuple

log = logging.getLogger(__name__)


class ScreenshotCapture:
    def __init__(self):
        self._pyautogui = None
        self._use_pyautogui = False
        self._pillow = None
        self._use_pillow = False
        self._user32 = None
        self._gdi32 = None
        self._init_backend()

    def _init_backend(self):
        try:
            import pyautogui
            self._pyautogui = pyautogui
            self._use_pyautogui = True
            log.debug("ScreenshotCapture: using pyautogui")
            return
        except ImportError:
            pass

        try:
            from PIL import Image, ImageGrab
            self._pillow = Image
            self._pillow_grab = ImageGrab
            self._use_pillow = True
            log.debug("ScreenshotCapture: using PIL ImageGrab")
            return
        except ImportError:
            pass

        if sys.platform == "win32":
            self._init_win32()
        else:
            log.warning("ScreenshotCapture: no screenshot backend available")

    def _init_win32(self):
        import ctypes
        from ctypes import wintypes

        self._user32 = ctypes.windll.user32
        self._gdi32 = ctypes.windll.gdi32

        self._SRCCOPY = 0x00CC0020
        self._CAPTUREBLT = 0x40000000

        log.debug("ScreenshotCapture: using ctypes Win32 fallback")

    def _ensure_pil(self):
        if not self._use_pillow:
            try:
                from PIL import Image, ImageGrab
                self._pillow = Image
                self._pillow_grab = ImageGrab
                self._use_pillow = True
            except ImportError:
                raise RuntimeError("PIL/Pillow is required for the ctypes screenshot fallback")

    def _generate_path(self, prefix: str = "screenshot") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        return os.path.join(tempfile.gettempdir(), f"{prefix}_{timestamp}.png")

    def capture(self, output_path: Optional[str] = None) -> str:
        path = output_path or self._generate_path()

        if self._use_pyautogui:
            img = self._pyautogui.screenshot()
            img.save(path)
            return path

        if self._use_pillow:
            img = self._pillow_grab.grab()
            img.save(path)
            return path

        return self._capture_win32_ctypes(path)

    def capture_bytes(self) -> bytes:
        if self._use_pyautogui:
            img = self._pyautogui.screenshot()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

        if self._use_pillow:
            img = self._pillow_grab.grab()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

        path = self._generate_path()
        self._capture_win32_ctypes(path)
        with open(path, "rb") as f:
            data = f.read()
        try:
            os.remove(path)
        except OSError:
            pass
        return data

    def capture_region(self, x: int, y: int, w: int, h: int) -> str:
        path = self._generate_path("screenshot_region")

        if self._use_pyautogui:
            img = self._pyautogui.screenshot(region=(x, y, w, h))
            img.save(path)
            return path

        if self._use_pillow:
            img = self._pillow_grab.grab(bbox=(x, y, x + w, y + h))
            img.save(path)
            return path

        return self._capture_win32_ctypes(path, region=(x, y, w, h))

    def _capture_win32_ctypes(self, path: str, region: Optional[Tuple[int, int, int, int]] = None) -> str:
        import ctypes
        from ctypes import wintypes
        self._ensure_pil()

        hwnd_desktop = self._user32.GetDesktopWindow()
        hdc_desktop = self._user32.GetDC(hwnd_desktop)
        hdc_mem = self._gdi32.CreateCompatibleDC(hdc_desktop)

        if region:
            x, y, w, h = region
        else:
            x = self._user32.GetSystemMetrics(76)
            y = self._user32.GetSystemMetrics(77)
            w = self._user32.GetSystemMetrics(78)
            h = self._user32.GetSystemMetrics(79)
            if w == 0 or h == 0:
                x = self._user32.GetSystemMetrics(0)
                y = self._user32.GetSystemMetrics(1)
                w = self._user32.GetSystemMetrics(0)
                h = self._user32.GetSystemMetrics(1)

        hbitmap = self._gdi32.CreateCompatibleBitmap(hdc_desktop, w, h)
        self._gdi32.SelectObject(hdc_mem, hbitmap)

        self._gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_desktop, x, y, self._SRCCOPY)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buffer_size = w * h * 4
        buffer = ctypes.create_string_buffer(buffer_size)

        self._gdi32.GetDIBits(
            hdc_mem, hbitmap, 0, h,
            buffer, ctypes.byref(bmi), 0,
        )

        self._gdi32.DeleteObject(hbitmap)
        self._gdi32.DeleteDC(hdc_mem)
        self._user32.ReleaseDC(hwnd_desktop, hdc_desktop)

        img = self._pillow.frombuffer("RGBA", (w, h), buffer, "raw", "BGRA", 0, 1)
        img = img.convert("RGB")
        img.save(path)
        return path
