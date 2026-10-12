from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


_APP_PATHS_WINDOWS: dict[str, str] = {
    "terminal": "cmd.exe",
    "powershell": "powershell.exe",
    "browser": "start",
    "vscode": "code",
    "cursor": "cursor",
    "claude_code": "claude",
    "notepad": "notepad",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "file_explorer": "explorer",
    "explorer": "explorer",
    "settings": "ms-settings:",
    "calculator": "calc",
    "chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
}

_APP_PATHS_MACOS: dict[str, str] = {
    "terminal": "Terminal",
    "browser": "Safari",
    "vscode": "Visual Studio Code",
    "cursor": "Cursor",
    "claude_code": "Claude",
    "notepad": "TextEdit",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "outlook": "Microsoft Outlook",
    "file_explorer": "Finder",
    "finder": "Finder",
    "settings": "System Settings",
    "calculator": "Calculator",
    "chrome": "Google Chrome",
    "firefox": "Firefox",
    "safari": "Safari",
    "edge": "Microsoft Edge",
}

_APP_PATHS_LINUX: dict[str, str] = {
    "terminal": "gnome-terminal",
    "browser": "xdg-open",
    "vscode": "code",
    "cursor": "cursor",
    "notepad": "gedit",
    "file_explorer": "nautilus",
    "settings": "gnome-control-center",
    "calculator": "gnome-calculator",
    "chrome": "google-chrome",
    "firefox": "firefox",
    "edge": "microsoft-edge",
}

_PROCESS_MAP_WINDOWS: dict[str, str] = {
    "notepad": "notepad.exe",
    "calculator": "calculator.exe",
    "chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "vscode": "Code.exe",
    "cursor": "Cursor.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "outlook": "OUTLOOK.EXE",
    "explorer": "explorer.exe",
    "file_explorer": "explorer.exe",
    "terminal": "cmd.exe",
    "powershell": "powershell.exe",
}

_PROCESS_MAP_MACOS: dict[str, str] = {
    "terminal": "Terminal",
    "safari": "Safari",
    "chrome": "Google Chrome",
    "firefox": "firefox",
    "edge": "Microsoft Edge",
    "vscode": "Code",
    "cursor": "Cursor",
}

_PROCESS_MAP_LINUX: dict[str, str] = {}


class AppLauncher:
    def __init__(self):
        self._platform = sys.platform
        self._psutil = None
        self._init_backend()

    def _init_backend(self):
        try:
            import psutil
            self._psutil = psutil
        except ImportError:
            log.warning("AppLauncher: psutil not available")

    def _get_app_paths(self) -> dict[str, str]:
        if self._platform == "win32":
            return _APP_PATHS_WINDOWS
        elif self._platform == "darwin":
            return _APP_PATHS_MACOS
        return _APP_PATHS_LINUX

    def _get_process_map(self) -> dict[str, str]:
        if self._platform == "win32":
            return _PROCESS_MAP_WINDOWS
        elif self._platform == "darwin":
            return _PROCESS_MAP_MACOS
        return _PROCESS_MAP_LINUX

    def _resolve_app(self, app_name: str) -> Optional[str]:
        paths = self._get_app_paths()
        lower_name = app_name.lower().replace(" ", "_")
        if lower_name in paths:
            return paths[lower_name]
        if app_name in paths:
            return paths[app_name]
        return None

    def _resolve_process_name(self, app_name: str) -> Optional[str]:
        proc_map = self._get_process_map()
        lower_name = app_name.lower().replace(" ", "_")
        if lower_name in proc_map:
            return proc_map[lower_name]
        if app_name in proc_map:
            return proc_map[app_name]
        return None

    def open(self, app_name: str) -> bool:
        resolved = self._resolve_app(app_name)
        if resolved is None:
            resolved = app_name

        try:
            if self._platform == "win32":
                if resolved == "start":
                    subprocess.Popen(["cmd", "/c", "start", "", app_name])
                elif resolved.startswith("ms-"):
                    subprocess.Popen(["start", "", resolved], shell=True)
                else:
                    subprocess.Popen([resolved])
                return True
            elif self._platform == "darwin":
                subprocess.Popen(["open", "-a", resolved])
                return True
            else:
                subprocess.Popen([resolved])
                return True
        except (FileNotFoundError, OSError) as e:
            log.warning("Failed to open app %s (%s): %s", app_name, resolved, e)
            try:
                if self._platform == "win32":
                    subprocess.Popen(["cmd", "/c", "start", "", app_name], shell=True)
                    return True
                elif self._platform == "darwin":
                    subprocess.Popen(["open", "-a", app_name])
                    return True
                else:
                    subprocess.Popen(["xdg-open", app_name])
                    return True
            except (FileNotFoundError, OSError) as e2:
                log.error("Failed to open app %s with fallback: %s", app_name, e2)
                return False

    def close(self, app_name: str) -> bool:
        proc_name = self._resolve_process_name(app_name)
        if proc_name is None:
            proc_name = app_name
            if self._platform == "win32" and not proc_name.lower().endswith(".exe"):
                proc_name += ".exe"

        try:
            if self._platform == "win32":
                result = subprocess.run(
                    ["taskkill", "/f", "/im", proc_name],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode != 0:
                    result = subprocess.run(
                        ["taskkill", "/f", "/im", app_name],
                        capture_output=True, text=True, timeout=10,
                    )
                return result.returncode == 0
            elif self._platform == "darwin":
                result = subprocess.run(
                    ["osascript", "-e", f'tell application "{proc_name}" to quit'],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode != 0:
                    subprocess.run(
                        ["killall", app_name],
                        capture_output=True, text=True, timeout=10,
                    )
                return True
            else:
                subprocess.run(
                    ["pkill", "-f", proc_name],
                    capture_output=True, text=True, timeout=10,
                )
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            log.warning("Failed to close app %s: %s", app_name, e)
            return False

    def list_running(self) -> List[Dict[str, Any]]:
        if not self._psutil:
            return []
        try:
            processes = []
            for proc in self._psutil.process_iter(["pid", "name", "create_time"]):
                try:
                    pinfo = proc.info
                    if pinfo["name"]:
                        processes.append({
                            "pid": pinfo["pid"],
                            "name": pinfo["name"],
                            "create_time": pinfo["create_time"],
                        })
                except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                    pass
            return processes
        except Exception as e:
            log.warning("Failed to list running processes: %s", e)
            return []

    def is_running(self, app_name: str) -> bool:
        if not self._psutil:
            proc_name = self._resolve_process_name(app_name)
            if proc_name is None:
                proc_name = app_name
            try:
                if self._platform == "win32":
                    result = subprocess.run(
                        ["tasklist", "/fi", f"imagename eq {proc_name}"],
                        capture_output=True, text=True, timeout=10,
                    )
                    return proc_name.lower() in result.stdout.lower()
                elif self._platform == "darwin":
                    result = subprocess.run(
                        ["pgrep", "-f", proc_name],
                        capture_output=True, text=True, timeout=10,
                    )
                    return result.returncode == 0
                else:
                    result = subprocess.run(
                        ["pgrep", "-f", proc_name],
                        capture_output=True, text=True, timeout=5,
                    )
                    return result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
                log.warning("Failed to check if %s is running: %s", app_name, e)
                return False

        proc_name = self._resolve_process_name(app_name)
        if proc_name is None:
            proc_name = app_name
        if self._platform == "win32" and not proc_name.lower().endswith(".exe"):
            proc_name += ".exe"

        try:
            for proc in self._psutil.process_iter(["name"]):
                try:
                    if proc.info["name"] and proc_name.lower() in proc.info["name"].lower():
                        return True
                except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                    pass
            return False
        except Exception:
            return False

    def wait_for_app(self, app_name: str, timeout: float = 30.0) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_running(app_name):
                return True
            time.sleep(0.5)
        return False
