from __future__ import annotations

import asyncio
import subprocess
import sys
import os
from typing import Any

from aetheros_voice.computer.screenshot import ScreenshotCapture
from aetheros_voice.computer.apps import AppLauncher
from aetheros_voice.computer.screen import ScreenUnderstanding


class ComputerController:
    def __init__(self):
        self.screenshot = ScreenshotCapture()
        self.apps = AppLauncher()
        self.screen = ScreenUnderstanding()

    async def click(self, x: int, y: int, button: str = "left"):
        try:
            import pyautogui
            pyautogui.click(x=x, y=y, button=button)
            return True
        except ImportError:
            pass
        platform = sys.platform
        if platform == "win32":
            import ctypes
            from ctypes import wintypes
            flags = {0: (0x0002, 0x0004), "left": (0x0002, 0x0004), "right": (0x0008, 0x0010), "middle": (0x0020, 0x0040)}
            down, up = flags.get(button, flags[0])
            ctypes.windll.user32.SetCursorPos(x, y)
            ctypes.windll.user32.mouse_event(down, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(up, 0, 0, 0, 0)
        return True

    async def move_mouse(self, x: int, y: int):
        try:
            import pyautogui
            pyautogui.moveTo(x, y)
        except ImportError:
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.SetCursorPos(x, y)

    async def scroll(self, amount: int = 1, direction: str = "down"):
        try:
            import pyautogui
            pyautogui.scroll(-amount if direction == "down" else amount)
        except ImportError:
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.mouse_event(0x0800 if direction == "down" else 0x0FF00, 0, 0, amount * 120, 0)

    async def type_text(self, text: str):
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=0.01)
        except ImportError:
            import pyperclip
            pyperclip.copy(text)
            await self.key_combo("ctrl", "v")

    async def press_key(self, key: str):
        try:
            import pyautogui
            pyautogui.press(key)
        except ImportError:
            import keyboard
            keyboard.press_and_release(key)

    async def key_combo(self, *keys: str):
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
        except ImportError:
            import keyboard
            keyboard.send("+".join(keys))

    async def open_app(self, app_name: str):
        return await self.apps.open(app_name)

    async def take_screenshot(self) -> str:
        return await self.screenshot.capture()

    async def get_clipboard_text(self) -> str:
        try:
            import pyperclip
            return pyperclip.paste()
        except ImportError:
            return ""

    async def understand_screen(self) -> str:
        return await self.screen.analyze()

    async def highlight_element(self, x: int, y: int, w: int, h: int):
        try:
            import pyautogui
            import pyautogui as pg
            pg.moveTo(x, y)
            pg.drag(w, h, duration=0.2)
        except ImportError:
            pass

    async def lock_screen(self):
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
        else:
            subprocess.run(["xdg-screensaver", "lock"] if sys.platform != "darwin" else ["pmset", "displaysleepnow"])

    async def shutdown(self):
        if sys.platform == "win32":
            subprocess.run(["shutdown", "/s", "/t", "5"])
        else:
            subprocess.run(["shutdown", "-h", "+1"])

    async def restart(self):
        if sys.platform == "win32":
            subprocess.run(["shutdown", "/r", "/t", "5"])
        else:
            subprocess.run(["shutdown", "-r", "+1"])

    async def sleep(self):
        if sys.platform == "win32":
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
        else:
            subprocess.run(["systemctl", "suspend"] if sys.platform == "linux" else ["pmset", "sleepnow"])

    async def volume_up(self):
        if sys.platform == "win32":
            for _ in range(5):
                await self.press_key("volumeup")
        else:
            await self.press_key("volumeup")

    async def volume_down(self):
        if sys.platform == "win32":
            for _ in range(5):
                await self.press_key("volumedown")
        else:
            await self.press_key("volumedown")

    async def mute(self):
        await self.press_key("volumemute")

    async def unmute(self):
        await self.press_key("volumemute")

    async def media_next(self):
        await self.press_key("nexttrack")

    async def media_previous(self):
        await self.press_key("prevtrack")

    async def media_play_pause(self):
        await self.press_key("playpause")
