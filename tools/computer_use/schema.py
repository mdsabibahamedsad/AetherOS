"""Schema for the generic `computer_use` tool.

Model-agnostic. Any tool-calling model can drive this. Vision-capable models
should prefer `capture(mode='som')` then `click(element=N)` — much more
reliable than pixel coordinates. Pixel coordinates remain supported for
models that were trained on them (e.g. Claude's computer-use RL).
"""

from __future__ import annotations

from typing import Any, Dict


# One consolidated tool with an `action` discriminator. Keeps the schema
# compact and the per-turn token cost low.
COMPUTER_USE_SCHEMA: Dict[str, Any] = {
    "name": "computer_use",
    "description": (
        "Drive the desktop in the background — screenshots, mouse, "
        "keyboard, scroll, drag, clipboard, and window management — "
        "without stealing the user's cursor or keyboard focus. "
        "Preferred workflow: call with "
        "action='capture' (mode='som' gives numbered element overlays), "
        "then click by `element` index for reliability. Pixel coordinates "
        "are supported for models trained on them. "
        "Platforms: macOS via cua-driver (background automation; requires "
        "cua-driver to be installed), Windows and Linux (X11) via the "
        "native adapters selected with HERMES_COMPUTER_USE_BACKEND."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "capture",
                    "capture_region",
                    "get_screen_size",
                    "click",
                    "double_click",
                    "right_click",
                    "middle_click",
                    "drag",
                    "scroll",
                    "move_mouse",
                    "type",
                    "key",
                    "set_value",
                    "read_clipboard",
                    "copy_clipboard",
                    "clear_clipboard",
                    "list_windows",
                    "get_active_window",
                    "focus_window",
                    "minimize_window",
                    "maximize_window",
                    "close_window",
                    "find_text",
                    "wait",
                    "list_apps",
                    "focus_app",
                    "get_capabilities",
                    "system_info",
                    "launch_app",
                    "close_app",
                ],
                "description": (
                    "Which action to perform. `capture`, `capture_region`, "
                    "`get_screen_size`, `get_capabilities`, `system_info`, "
                    "`list_windows`, `get_active_window`, `read_clipboard` "
                    "and `find_text` are read-only (no side effects, no "
                    "approval). All other actions mutate user-"
                    "visible state and require approval unless auto-approved. "
                    "Every action is also validated against its permission "
                    "(screen_read / system_info / mouse_control / "
                    "keyboard_control / clipboard_read / clipboard_write / "
                    "window_control / application_control). Use `set_value` "
                    "for select/popup elements and sliders — it selects the "
                    "matching option directly without opening the native "
                    "menu (no focus steal)."
                ),
            },
            "confidence": {
                "type": "number",
                "description": (
                    "Agent's confidence in this action's success, 0.0 to 1.0. "
                    "Higher confidence indicates unique semantic/DOM target "
                    "(1.0), visual+semantic agreement (0.5), or "
                    "coordinate-only/ambiguous (0.1). "
                    "Defaults to 1.0 for element-index clicks, "
                    "0.5 for visual+semantic, 0.1 for pure coordinates."
                ),
                "minimum": 0.0,
                "maximum": 1.0,
            },
        },
        "required": ["action"],
        "additionalProperties": False,
    },
}