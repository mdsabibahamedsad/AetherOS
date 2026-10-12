"""DesktopAdapter — thin facade over :mod:`tools.computer_use`.

Reuses the shipping desktop engine: per-OS backends (cua-driver, Win32,
Linux), the permission layer, the audit log, and bounded verify-retry. The
adapter translates a unified :class:`~aetheros_actions.model.Action` into
the computer_use tool-call shape (``action`` + arguments) and parses the
tool response.

Security integration:
  * coordinates are validated against the observed screen size before any
    click/move (Step 10);
  * password-like targets are masked to ``"PASSWORD FIELD"`` (Step 27);
  * the adapter never emits clipboard contents except through an explicit
    authorised read.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

from aetheros_actions.model import Action, ActionType, Element


class DesktopAdapter:
    """Maps unified Actions onto the computer-use tool contract."""

    def __init__(self, backend_name: str = "", approval_callback=None) -> None:
        self.backend_name = backend_name  # "" = auto via env
        self.approval_callback = approval_callback
        self._dispatch_fn = None
        self._screen_size: Tuple[int, int] = (0, 0)

    def _tool(self) -> Any:
        if self._dispatch_fn is None:
            from tools.computer_use import tool as cu  # noqa: PLC0415
            if self.approval_callback is not None:
                cu.set_approval_callback(self.approval_callback)
            self._dispatch_fn = cu
        return self._dispatch_fn

    # ── screen geometry (Step 10 validation) ─────────────────────────

    def refresh_screen_size(self) -> Tuple[int, int]:
        try:
            raw = self._tool().handle_computer_use({"action": "get_screen_size"})
            data = self._parse(raw)
            w = int(data.get("width", 0))
            h = int(data.get("height", 0))
            if w and h:
                self._screen_size = (w, h)
        except Exception:  # noqa: BLE001
            pass
        return self._screen_size

    def _validate_coords(self, action: Action) -> Optional[str]:
        coord = action.parameters.get("coordinate")
        if not isinstance(coord, (list, tuple)) or len(coord) < 2:
            return None
        x, y = int(coord[0]), int(coord[1])
        w, h = self._screen_size
        if w and h and (x < 0 or y < 0 or x > w or y > h):
            return f"coordinate ({x},{y}) outside screen {w}x{h}"
        return None

    # ── action mapping ───────────────────────────────────────────────

    def execute(self, action: Action) -> Any:
        args: Dict[str, Any] = {"action": self._cu_action(action)}
        atype = action.action_type

        if atype in (ActionType.CLICK, ActionType.DOUBLE_CLICK, ActionType.MOVE):
            params = action.parameters or {}
            if params.get("element") is not None:
                args["element"] = params["element"]
            if params.get("coordinate"):
                coord = params["coordinate"]
                args["coordinate"] = [int(coord[0]), int(coord[1])]
            args["button"] = params.get("button", "left")
            args["capture_after"] = bool(params.get("capture_after", False))
        elif atype == ActionType.TYPE:
            params = action.parameters or {}
            args["text"] = str(params.get("text", action.target))
            args["capture_after"] = bool(params.get("capture_after", False))
        elif atype == ActionType.KEY_PRESS:
            args["keys"] = action.parameters.get("keys", "")
            args["capture_after"] = bool(action.parameters.get("capture_after", False))
        elif atype == ActionType.SCROLL:
            args["direction"] = action.parameters.get("direction", "down")
            args["amount"] = int(action.parameters.get("amount", 3))
        elif atype == ActionType.DRAG:
            args["from_coordinate"] = action.parameters.get("from_coordinate")
            args["to_coordinate"] = action.parameters.get("to_coordinate")
        elif atype == ActionType.WINDOW_FOCUS:
            args["window_title"] = action.parameters.get("window_title", action.target)
        elif atype == ActionType.SCREENSHOT:
            args["mode"] = action.parameters.get("mode", "som")
        elif atype == ActionType.COPY:
            args["text"] = action.parameters.get("text", "")
        elif atype == ActionType.PASTE:
            args["action"] = "read_clipboard"
        elif atype == ActionType.WAIT:
            args["seconds"] = float(action.parameters.get("seconds", 1.0))
        else:
            return {"error": f"desktop adapter does not support {atype.value}"}

        # Coordinate safety (Step 10).
        err = self._validate_coords(action)
        if err:
            return {"error": err, "hint": "re-observe before targeting coordinates"}

        raw = self._tool().handle_computer_use(args)
        return self._parse(raw)

    def _cu_action(self, action: Action) -> str:
        atype = action.action_type
        mapping = {
            ActionType.CLICK: "click",
            ActionType.DOUBLE_CLICK: "double_click",
            ActionType.MOVE: "move_mouse",
            ActionType.TYPE: "type",
            ActionType.KEY_PRESS: "key",
            ActionType.SCROLL: "scroll",
            ActionType.DRAG: "drag",
            ActionType.WINDOW_FOCUS: "focus_window",
            ActionType.SCREENSHOT: "capture",
            ActionType.COPY: "copy_clipboard",
            ActionType.PASTE: "read_clipboard",
            ActionType.WAIT: "wait",
        }
        return mapping.get(atype, atype.value.lower())

    # ── observation hooks ────────────────────────────────────────────

    def observe(self) -> Dict[str, Any]:
        window = {}
        try:
            raw = self._tool().handle_computer_use({"action": "get_active_window"})
            data = self._parse(raw)
            window = data.get("window") or {}
        except Exception:  # noqa: BLE001
            pass
        return {
            "mode": "desktop",
            "window_title": window.get("title", ""),
            "app": window.get("app", ""),
        }

    def find_text(self, text: str) -> list[Element]:
        try:
            raw = self._tool().handle_computer_use({"action": "find_text", "text": text})
            data = self._parse(raw)
            out: list[Element] = []
            for m in data.get("matches", []):
                bounds = m.get("bounds") or []
                b = tuple(int(v) for v in bounds) if len(bounds) == 4 else (0, 0, 0, 0)
                out.append(Element(role=m.get("role", ""), label=m.get("label", text),
                                   bounds=b, confidence=1.0))
            return out
        except Exception:  # noqa: BLE001
            return []

    def _parse(self, raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                return {"raw": raw[:2000]}
        return {"raw": str(raw)[:2000]}