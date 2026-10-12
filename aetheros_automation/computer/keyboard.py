from __future__ import annotations

import logging
import sys
import time

log = logging.getLogger(__name__)


class KeyboardController:
    def __init__(self):
        self._pyautogui = None
        self._use_pyautogui = False
        self._keyboard_lib = None
        self._use_keyboard_lib = False
        self._user32 = None
        self._key_map: dict[str, int] = {}
        self._init_backend()

    def _init_backend(self):
        try:
            import pyautogui
            self._pyautogui = pyautogui
            self._use_pyautogui = True
            log.debug("KeyboardController: using pyautogui")
            return
        except ImportError:
            pass

        try:
            import keyboard as kb
            self._keyboard_lib = kb
            self._use_keyboard_lib = True
            log.debug("KeyboardController: using keyboard library")
            return
        except ImportError:
            pass

        if sys.platform == "win32":
            self._init_win32()
        else:
            log.warning("KeyboardController: no backend available")

    def _init_win32(self):
        import ctypes
        self._user32 = ctypes.windll.user32

        self._key_map = {
            "enter": 0x0D, "return": 0x0D,
            "tab": 0x09,
            "backspace": 0x08, "bs": 0x08,
            "shift": 0x10, "shiftleft": 0xA0, "shiftright": 0xA1,
            "ctrl": 0x11, "control": 0x11, "ctrlleft": 0xA2, "ctrlright": 0xA3,
            "alt": 0x12, "altleft": 0xA4, "altright": 0xA5,
            "escape": 0x1B, "esc": 0x1B,
            "space": 0x20, " ": 0x20,
            "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
            "home": 0x24, "end": 0x23,
            "pageup": 0x21, "pagedown": 0x22,
            "insert": 0x2D, "delete": 0x2E, "del": 0x2E,
            "capslock": 0x14, "numlock": 0x90,
            "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
            "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
            "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
            "f13": 0x7C, "f14": 0x7D, "f15": 0x7E, "f16": 0x7F,
            "f17": 0x80, "f18": 0x81, "f19": 0x82, "f20": 0x83,
            "f21": 0x84, "f22": 0x85, "f23": 0x86, "f24": 0x87,
            "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
            "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
            "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
            "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
            "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
            "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
            "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59,
            "z": 0x5A,
            ";": 0xBA, "=": 0xBB, ",": 0xBC, "-": 0xBD, ".": 0xBE,
            "/": 0xBF, "`": 0xC0, "[": 0xDB, "\\": 0xDC, "]": 0xDD,
            "'": 0xDE,
            "win": 0x5B, "lwin": 0x5B, "rwin": 0x5C,
            "apps": 0x5D, "menu": 0x5D,
            "printscreen": 0x2C, "prtsc": 0x2C,
            "scrolllock": 0x91,
            "pause": 0x13, "break": 0x13,
        }

        log.debug("KeyboardController: using ctypes Win32 fallback")

    def _is_pyautogui(self) -> bool:
        return self._use_pyautogui

    def _is_keyboard_lib(self) -> bool:
        return self._use_keyboard_lib

    def type_text(self, text: str):
        if self._is_pyautogui():
            self._pyautogui.typewrite(text)
        elif self._is_keyboard_lib():
            self._keyboard_lib.write(text)
        elif self._user32:
            self._win32_type_text(text)
        else:
            raise RuntimeError("No keyboard backend available")

    def write(self, text: str):
        self.type_text(text)

    def press_key(self, key: str):
        if self._is_pyautogui():
            self._pyautogui.press(key)
        elif self._is_keyboard_lib():
            self._keyboard_lib.send(key)
        elif self._user32:
            vk = self._key_map.get(key.lower(), ord(key.upper()) & 0xFF)
            self._user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.02)
            self._user32.keybd_event(vk, 0, 2, 0)
        else:
            raise RuntimeError("No keyboard backend available")

    def hotkey(self, *keys: str):
        if self._is_pyautogui():
            self._pyautogui.hotkey(*keys)
        elif self._is_keyboard_lib():
            for key in keys:
                self._keyboard_lib.press(key)
            for key in reversed(keys):
                self._keyboard_lib.release(key)
        elif self._user32:
            vk_codes = []
            for key in keys:
                vk = self._key_map.get(key.lower(), ord(key.upper()) & 0xFF)
                vk_codes.append(vk)
            for vk in vk_codes:
                self._user32.keybd_event(vk, 0, 0, 0)
                time.sleep(0.02)
            for vk in reversed(vk_codes):
                self._user32.keybd_event(vk, 0, 2, 0)
                time.sleep(0.02)
        else:
            raise RuntimeError("No keyboard backend available")

    def _win32_type_text(self, text: str):
        import ctypes
        from ctypes import wintypes

        PUL = ctypes.POINTER(ctypes.c_ulong)

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", PUL),
            ]

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", PUL),
            ]

        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = [
                ("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD),
            ]

        class _INPUT_UNION(ctypes.Union):
            _fields_ = [
                ("ki", KEYBDINPUT),
                ("mi", MOUSEINPUT),
                ("hi", HARDWAREINPUT),
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", wintypes.DWORD),
                ("u", _INPUT_UNION),
            ]

        INPUT_KEYBOARD = 1
        KEYEVENTF_UNICODE = 0x04
        KEYEVENTF_KEYUP = 0x02

        for char in text:
            code_point = ord(char)
            ki_down = KEYBDINPUT(0, code_point, KEYEVENTF_UNICODE, 0, None)
            ki_up = KEYBDINPUT(0, code_point, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)

            union_down = _INPUT_UNION()
            union_down.ki = ki_down
            input_down = INPUT(INPUT_KEYBOARD, union_down)

            union_up = _INPUT_UNION()
            union_up.ki = ki_up
            input_up = INPUT(INPUT_KEYBOARD, union_up)

            self._user32.SendInput(1, ctypes.byref(input_down), ctypes.sizeof(INPUT))
            self._user32.SendInput(1, ctypes.byref(input_up), ctypes.sizeof(INPUT))
            time.sleep(0.01)
