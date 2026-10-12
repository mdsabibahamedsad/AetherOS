"""Desktop Runtime — real desktop automation.

Controls applications, windows, clipboard, keyboard, mouse, and screen.
Uses PyAutoGUI for cross-platform GUI automation.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tool_runtime.interface import (
    ToolInterface,
    ToolMetadata,
    ToolResult,
    ToolRiskLevel,
    ToolCategory,
    ToolStatus,
)

logger = logging.getLogger(__name__)


class DesktopRuntime(ToolInterface):
    """Desktop automation runtime.

    Features:
    - Launch and close applications
    - Window management (list, focus, minimize, maximize, close)
    - Clipboard read/write
    - Keyboard input and hotkeys
    - Mouse movement, click, drag
    - Screen capture
    - Notifications
    """

    def __init__(self):
        meta = ToolMetadata(
            id="desktop",
            name="Desktop Runtime",
            description="Desktop automation: apps, windows, clipboard, keyboard, mouse, screen capture",
            category=ToolCategory.DESKTOP,
            risk_level=ToolRiskLevel.SYSTEM,
            version="2.0.0",
            tags=["desktop", "automation", "gui"],
            requires_approval=False,
            timeout_seconds=30.0,
        )
        super().__init__(meta)
        self._pyautogui_available = False
        self._init_backend()

    def _init_backend(self) -> None:
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            self._pyautogui_available = True
        except ImportError:
            self._pyautogui_available = False

    def schema(self) -> Dict[str, Any]:
        return {
            "name": "desktop",
            "description": self.description(),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "launch", "close", "list_windows", "focus_window",
                            "minimize_window", "maximize_window", "close_window",
                            "clipboard_read", "clipboard_write",
                            "key_press", "hotkey", "type_text",
                            "mouse_move", "mouse_click", "mouse_drag",
                            "scroll", "screenshot", "notify",
                            "screen_size", "mouse_position",
                        ],
                    },
                    "app": {"type": "string", "description": "Application name or path"},
                    "window_title": {"type": "string", "description": "Window title to match"},
                    "text": {"type": "string", "description": "Text for keyboard/clipboard"},
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "button": {"type": "string", "enum": ["left", "right", "middle"]},
                    "key": {"type": "string"},
                    "keys": {"type": "array", "items": {"type": "string"}},
                    "clicks": {"type": "integer"},
                    "duration": {"type": "number"},
                    "title": {"type": "string", "description": "Notification title"},
                    "message": {"type": "string", "description": "Notification message"},
                },
                "required": ["operation"],
            },
        }

    def validate(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        op = params.get("operation")
        if not op:
            errors.append("Missing required parameter: operation")
        return errors

    def authorize(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        if self._cancelled:
            return ToolResult.fail("Execution cancelled")

        operation = params.get("operation")
        op_map = {
            "launch": self._launch,
            "close": self._close,
            "list_windows": self._list_windows,
            "focus_window": self._focus_window,
            "minimize_window": self._minimize_window,
            "maximize_window": self._maximize_window,
            "close_window": self._close_window,
            "clipboard_read": self._clipboard_read,
            "clipboard_write": self._clipboard_write,
            "key_press": self._key_press,
            "hotkey": self._hotkey,
            "type_text": self._type_text,
            "mouse_move": self._mouse_move,
            "mouse_click": self._mouse_click,
            "mouse_drag": self._mouse_drag,
            "scroll": self._scroll,
            "screenshot": self._screenshot,
            "notify": self._notify,
            "screen_size": self._screen_size,
            "mouse_position": self._mouse_position,
        }

        handler = op_map.get(operation)
        if not handler:
            return ToolResult.fail(f"Unknown desktop operation: {operation}")

        try:
            return handler(params)
        except Exception as e:
            logger.error("Desktop operation '%s' failed: %s", operation, e)
            return ToolResult.fail(f"{type(e).__name__}: {e}")

    def _launch(self, params: Dict[str, Any]) -> ToolResult:
        app = params.get("app", "")
        if not app:
            return ToolResult.fail("No application specified")
        try:
            if platform.system() == "Windows":
                os.startfile(app)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", app])
            else:
                subprocess.Popen(shlex.split(app))
            return ToolResult.ok({"app": app, "launched": True})
        except Exception as e:
            return ToolResult.fail(f"Failed to launch {app}: {e}")

    def _close(self, params: Dict[str, Any]) -> ToolResult:
        app = params.get("app", "")
        if not app:
            return ToolResult.fail("No application specified")
        try:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/F", "/IM", app], capture_output=True, timeout=10)
            elif platform.system() == "Darwin":
                subprocess.run(["pkill", "-x", app], capture_output=True, timeout=10)
            else:
                subprocess.run(["pkill", "-x", app], capture_output=True, timeout=10)
            return ToolResult.ok({"app": app, "closed": True})
        except Exception as e:
            return ToolResult.fail(f"Failed to close {app}: {e}")

    def _list_windows(self, params: Dict[str, Any]) -> ToolResult:
        if not self._pyautogui_available:
            return ToolResult.fail("PyAutoGUI not available")
        try:
            import pygetwindow as gw
            windows = gw.getAllWindows()
            return ToolResult.ok({
                "windows": [
                    {"title": w.title, "left": w.left, "top": w.top, "width": w.width, "height": w.height}
                    for w in windows if w.title
                ],
                "count": len([w for w in windows if w.title]),
            })
        except ImportError:
            return ToolResult.fail("pygetwindow not installed")
        except Exception as e:
            return ToolResult.fail(f"Failed to list windows: {e}")

    def _focus_window(self, params: Dict[str, Any]) -> ToolResult:
        title = params.get("window_title", "")
        if not title:
            return ToolResult.fail("No window title specified")
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].activate()
                return ToolResult.ok({"window": title, "focused": True})
            return ToolResult.fail(f"Window not found: {title}")
        except Exception as e:
            return ToolResult.fail(f"Failed to focus window: {e}")

    def _minimize_window(self, params: Dict[str, Any]) -> ToolResult:
        title = params.get("window_title", "")
        if not title:
            return ToolResult.fail("No window title specified")
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].minimize()
                return ToolResult.ok({"window": title, "minimized": True})
            return ToolResult.fail(f"Window not found: {title}")
        except Exception as e:
            return ToolResult.fail(f"Failed to minimize window: {e}")

    def _maximize_window(self, params: Dict[str, Any]) -> ToolResult:
        title = params.get("window_title", "")
        if not title:
            return ToolResult.fail("No window title specified")
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].maximize()
                return ToolResult.ok({"window": title, "maximized": True})
            return ToolResult.fail(f"Window not found: {title}")
        except Exception as e:
            return ToolResult.fail(f"Failed to maximize window: {e}")

    def _close_window(self, params: Dict[str, Any]) -> ToolResult:
        title = params.get("window_title", "")
        if not title:
            return ToolResult.fail("No window title specified")
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].close()
                return ToolResult.ok({"window": title, "closed": True})
            return ToolResult.fail(f"Window not found: {title}")
        except Exception as e:
            return ToolResult.fail(f"Failed to close window: {e}")

    def _clipboard_read(self, params: Dict[str, Any]) -> ToolResult:
        try:
            import pyperclip
            text = pyperclip.paste()
            return ToolResult.ok({"clipboard": text[:5000], "length": len(text)})
        except ImportError:
            return ToolResult.fail("pyperclip not available")
        except Exception as e:
            return ToolResult.fail(f"Clipboard read failed: {e}")

    def _clipboard_write(self, params: Dict[str, Any]) -> ToolResult:
        text = params.get("text", "")
        try:
            import pyperclip
            pyperclip.copy(text)
            return ToolResult.ok({"copied": len(text), "action": "clipboard_write"})
        except ImportError:
            return ToolResult.fail("pyperclip not available")
        except Exception as e:
            return ToolResult.fail(f"Clipboard write failed: {e}")

    def _key_press(self, params: Dict[str, Any]) -> ToolResult:
        if not self._pyautogui_available:
            return ToolResult.fail("PyAutoGUI not available")
        key = params.get("key", "")
        import pyautogui
        pyautogui.press(key)
        return ToolResult.ok({"key": key})

    def _hotkey(self, params: Dict[str, Any]) -> ToolResult:
        if not self._pyautogui_available:
            return ToolResult.fail("PyAutoGUI not available")
        keys = params.get("keys", [])
        import pyautogui
        pyautogui.hotkey(*keys)
        return ToolResult.ok({"hotkey": "+".join(keys)})

    def _type_text(self, params: Dict[str, Any]) -> ToolResult:
        if not self._pyautogui_available:
            return ToolResult.fail("PyAutoGUI not available")
        text = params.get("text", "")
        import pyautogui
        pyautogui.write(text)
        return ToolResult.ok({"typed": len(text)})

    def _mouse_move(self, params: Dict[str, Any]) -> ToolResult:
        if not self._pyautogui_available:
            return ToolResult.fail("PyAutoGUI not available")
        x = params.get("x", 0)
        y = params.get("y", 0)
        duration = params.get("duration", 0.2)
        import pyautogui
        pyautogui.moveTo(x, y, duration=duration)
        return ToolResult.ok({"x": x, "y": y})

    def _mouse_click(self, params: Dict[str, Any]) -> ToolResult:
        if not self._pyautogui_available:
            return ToolResult.fail("PyAutoGUI not available")
        x = params.get("x")
        y = params.get("y")
        button = params.get("button", "left")
        clicks = params.get("clicks", 1)
        import pyautogui
        if x is not None and y is not None:
            pyautogui.click(x, y, button=button, clicks=clicks)
        else:
            pyautogui.click(button=button, clicks=clicks)
        return ToolResult.ok({"x": x, "y": y, "button": button, "clicks": clicks})

    def _mouse_drag(self, params: Dict[str, Any]) -> ToolResult:
        if not self._pyautogui_available:
            return ToolResult.fail("PyAutoGUI not available")
        x = params.get("x", 0)
        y = params.get("y", 0)
        duration = params.get("duration", 0.5)
        import pyautogui
        pyautogui.drag(x, y, duration=duration)
        return ToolResult.ok({"dx": x, "dy": y})

    def _scroll(self, params: Dict[str, Any]) -> ToolResult:
        if not self._pyautogui_available:
            return ToolResult.fail("PyAutoGUI not available")
        clicks = params.get("clicks", 1)
        import pyautogui
        pyautogui.scroll(clicks)
        return ToolResult.ok({"clicks": clicks})

    def _screenshot(self, params: Dict[str, Any]) -> ToolResult:
        if not self._pyautogui_available:
            return ToolResult.fail("PyAutoGUI not available")
        import pyautogui
        ss = pyautogui.screenshot()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            ss.save(f.name)
            return ToolResult.ok({
                "path": f.name,
                "size": os.path.getsize(f.name),
                "width": ss.width,
                "height": ss.height,
            })

    def _notify(self, params: Dict[str, Any]) -> ToolResult:
        title = params.get("title", "AetherOS")
        message = params.get("message", "")
        try:
            if platform.system() == "Windows":
                from plyer import notification
                notification.notify(title=title, message=message, timeout=5)
            elif platform.system() == "Darwin":
                subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'])
            else:
                subprocess.run(["notify-send", title, message])
            return ToolResult.ok({"title": title, "message": message})
        except Exception as e:
            return ToolResult.fail(f"Notification failed: {e}")

    def _screen_size(self, params: Dict[str, Any]) -> ToolResult:
        if not self._pyautogui_available:
            return ToolResult.fail("PyAutoGUI not available")
        import pyautogui
        w, h = pyautogui.size()
        return ToolResult.ok({"width": w, "height": h})

    def _mouse_position(self, params: Dict[str, Any]) -> ToolResult:
        if not self._pyautogui_available:
            return ToolResult.fail("PyAutoGUI not available")
        import pyautogui
        x, y = pyautogui.position()
        return ToolResult.ok({"x": x, "y": y})

    def health(self) -> Dict[str, Any]:
        base = super().health()
        base["pyautogui_available"] = self._pyautogui_available
        return base
