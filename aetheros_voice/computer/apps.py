from __future__ import annotations

import os
import sys
import subprocess
from typing import Any


class AppLauncher:
    def __init__(self):
        self._platform = sys.platform
        self._app_map = self._build_app_map()

    def _build_app_map(self) -> dict[str, list[str]]:
        common = {
            "terminal": self._cmd("terminal"),
            "browser": self._cmd("browser"),
            "settings": self._cmd("settings"),
            "calculator": self._cmd("calculator"),
            "notepad": self._cmd("notepad"),
            "file manager": self._cmd("file_manager"),
            "explorer": self._cmd("file_manager"),
            "vscode": self._cmd("vscode"),
            "visual studio code": self._cmd("vscode"),
        }
        return common

    def _cmd(self, app: str):
        if self._platform == "win32":
            m = {
                "terminal": ["cmd.exe"],
                "browser": ["start", "msedge"],
                "settings": ["start", "ms-settings:"],
                "calculator": ["calc.exe"],
                "notepad": ["notepad.exe"],
                "file_manager": ["explorer.exe"],
                "vscode": ["code.cmd"],
            }
        elif self._platform == "darwin":
            m = {
                "terminal": ["open", "-a", "Terminal"],
                "browser": ["open", "-a", "Safari"],
                "settings": ["open", "-a", "System Settings"],
                "calculator": ["open", "-a", "Calculator"],
                "notepad": ["open", "-a", "TextEdit"],
                "file_manager": ["open", "."],
                "vscode": ["open", "-a", "Visual Studio Code"],
            }
        else:
            m = {
                "terminal": ["gnome-terminal"],
                "browser": ["xdg-open", "about:blank"],
                "settings": ["gnome-control-center"],
                "calculator": ["gnome-calculator"],
                "notepad": ["gedit"],
                "file_manager": ["nautilus"],
                "vscode": ["code"],
            }
        return m.get(app, [])

    async def open(self, app_name: str) -> str:
        lower = app_name.lower().strip()
        cmd = self._app_map.get(lower)
        if cmd:
            try:
                subprocess.Popen(cmd, shell=self._platform == "win32")
                return f"Opened {app_name}"
            except Exception as e:
                return f"Failed to open {app_name}: {e}"
        return f"Unknown application: {app_name}. Try: terminal, browser, settings, calculator, vscode, file manager"

    def register_app(self, name: str, command: list[str]):
        self._app_map[name.lower()] = command
