"""ActionExecutor — dispatch (Step 12).

Runs one :class:`~aetheros_actions.model.Action` by delegating to the
installed adapters:

* browser actions → :class:`~aetheros_actions.adapters.browser.BrowserAdapter`
* desktop actions → the computer-use backend (via the existing tool layer)
* file/app actions → filesystem-safe operations

The executor is adapter-agnostic: it receives an ``execute`` callable or a
dict-style handler map, so tests inject fakes and the real system injects
the production adapters. Every execution returns an
:class:`ActionResult` that carries ``ok``, the outcome payload, and elapsed
time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from aetheros_actions.model import Action, ActionType


@dataclass
class ActionResult:
    """Outcome of executing one action."""

    ok: bool
    action: Action
    payload: Any = None
    message: str = ""
    elapsed_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "action": self.action.to_dict(),
            "message": self.message,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "error": self.error,
        }


class ActionExecutor:
    """Dispatches an action to the right adapter."""

    def __init__(self, handler: Optional[Callable[[Action], Any]] = None,
                 handlers: Optional[Dict[str, Callable[[Action], Any]]] = None) -> None:
        self.handler = handler or self._default_handler
        self.handlers = handlers or {}

    # ── public API ───────────────────────────────────────────────────

    def execute(self, action: Action) -> ActionResult:
        start = time.monotonic()
        try:
            key = action.action_type.value
            fn = self.handlers.get(key) or self.handler
            payload = fn(action)
            ok = not isinstance(payload, Exception)
            return ActionResult(
                ok=ok,
                action=action,
                payload=payload,
                elapsed_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as exc:  # noqa: BLE001
            return ActionResult(
                ok=False,
                action=action,
                error=str(exc),
                elapsed_ms=(time.monotonic() - start) * 1000,
            )

    # ── default (stub) — real integrations override via constructor ──

    def _default_handler(self, action: Action) -> Any:  # pragma: no cover
        raise NotImplementedError(
            "ActionExecutor needs a handler; inject a BrowserAdapter/DesktopAdapter"
        )


def writer_for(executor: ActionExecutor) -> Callable[[Action], ActionResult]:
    """Compatibility alias: expose executor.execute as a plain function."""
    return executor.execute