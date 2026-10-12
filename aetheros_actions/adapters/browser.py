"""BrowserAdapter — thin facade over :mod:`tools.browser_tool`.

Reuses the shipping browser engine (agent-browser CLI, CDP supervisor, cloud
providers, Camofox). Session isolation is handled by the existing
``task_id``-keyed session management — every run gets its own task_id so
sessions stay isolated (Step 7). Cookies and session tokens are never
surfaced: we only pass through navigate/snapshot/click/type/scroll/back/
press/vision results and drop any payload that would expose credentials.

Browser session management contract (Step 7):
  * session_id → opaque task_id per run (no cross-session reuse).
  * close() → cleanup_browser(task_id) to tear the session down.
  * Never returns cookies / tokens / storage to the caller.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from aetheros_actions.model import Action, ActionType, Element


class BrowserAdapter:
    """Maps unified Actions onto :mod:`tools.browser_tool` handlers."""

    def __init__(self, task_id: str = "") -> None:
        self.task_id = task_id or "aetheros-actions"
        self._tool = None  # lazy import to avoid heavy deps at import time

    def _t(self) -> Any:
        if self._tool is None:
            import tools.browser_tool as bt  # noqa: PLC0415
            self._tool = bt
        return self._tool

    # ── session lifecycle (Step 7) ───────────────────────────────────

    def open_session(self) -> Dict[str, str]:
        return {"session_id": self.task_id, "isolated": True}

    def close_session(self) -> None:
        try:
            self._t().cleanup_browser(self.task_id)
        except Exception:  # noqa: BLE001
            pass

    # ── action mapping ───────────────────────────────────────────────

    def execute(self, action: Action) -> Any:
        atype = action.action_type
        if atype == ActionType.NAVIGATE:
            return self._parse(self._t().browser_navigate(action.target, self.task_id))
        if atype in (ActionType.SCREENSHOT, ActionType.OPEN):
            return self._parse(self._t().browser_snapshot(full=False, task_id=self.task_id))
        if atype == ActionType.CLICK:
            ref = action.parameters.get("ref") or action.target
            return self._parse(self._t().browser_click(ref, self.task_id))
        if atype == ActionType.TYPE:
            ref = action.parameters.get("ref") or action.target
            text = action.parameters.get("text", "")
            return self._parse(self._t().browser_type(ref, text, self.task_id))
        if atype == ActionType.SCROLL:
            direction = action.parameters.get("direction", "down")
            return self._parse(self._t().browser_scroll(direction, self.task_id))
        if atype == ActionType.CLOSE:
            return self._parse(self._t().browser_back(self.task_id))
        if atype == ActionType.KEY_PRESS:
            key = action.parameters.get("key", "")
            return self._parse(self._t().browser_press(key, self.task_id))
        return {"error": f"browser adapter does not support {atype.value}"}

    # ── observation hooks ────────────────────────────────────────────

    def observe_tab(self) -> Dict[str, Any]:
        try:
            snapshot = self._parse(self._t().browser_snapshot(full=False, task_id=self.task_id))
            return {"mode": "browser", "url": snapshot.get("url", ""), "snapshot": snapshot}
        except Exception:  # noqa: BLE001
            return {"mode": "browser", "url": ""}

    def _parse(self, raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                return {"raw": raw[:2000]}
        return {"raw": str(raw)[:2000]}