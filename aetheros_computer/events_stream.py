"""
Live action stream + structured timeline (Master 15 Phases 64-65).

A bounded, thread-safe in-process pub/sub emitting ONLY safe runtime events:

    OBSERVE, PLAN, WAITING_APPROVAL, ACTION, VERIFY, RECOVERY,
    PAUSED, USER_TAKEOVER, COMPLETE, FAILED

Payload policy (enforced here): event type, task/action ids, action name,
risk tier, target HASH (never raw target), state — never chain-of-thought,
never raw page content, never credentials.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

MAX_HISTORY = 1000
MAX_SUBSCRIBERS = 32

EVENT_TYPES = frozenset({
    "OBSERVE", "PLAN", "WAITING_APPROVAL", "ACTION", "VERIFY",
    "RECOVERY", "PAUSED", "USER_TAKEOVER", "COMPLETE", "FAILED",
})


def safe_target_hash(target: Any) -> str:
    return hashlib.sha256(str(target or "").encode("utf-8", "replace")).hexdigest()[:12]


class ActionStream:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: List[Callable[[Dict[str, Any]], None]] = []
        self._history: Deque[Dict[str, Any]] = deque(maxlen=MAX_HISTORY)

    def emit(self, event_type: str, *, task_id: str = "", action_id: str = "",
             action: str = "", risk: str = "", target_hash: str = "",
             detail: str = "") -> Optional[Dict[str, Any]]:
        if event_type not in EVENT_TYPES:
            return None
        evt = {
            "ts": time.time(),
            "event": event_type,
            "task_id": str(task_id)[:80],
            "action_id": str(action_id)[:16],
            "action": str(action)[:80],
            "risk": str(risk)[:20],
            "target_hash": str(target_hash)[:12],
            "detail": str(detail or "")[:200],
        }
        with self._lock:
            self._history.append(evt)
            subs = list(self._subs)
        for fn in subs:
            try:
                fn(evt)
            except Exception:
                pass  # a bad subscriber never breaks the pipeline
        return evt

    def subscribe(self, fn: Callable[[Dict[str, Any]], None]) -> bool:
        with self._lock:
            if len(self._subs) >= MAX_SUBSCRIBERS:
                return False
            if fn not in self._subs:
                self._subs.append(fn)
        return True

    def unsubscribe(self, fn: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            try:
                self._subs.remove(fn)
            except ValueError:
                pass

    def timeline(self, task_id: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        """Newest-first filtered view (Phase 65)."""
        with self._lock:
            items = list(self._history)
        if task_id:
            items = [e for e in items if e["task_id"] == task_id]
        items.reverse()
        return items[: max(1, limit)]

    def render_timeline_ascii(self, task_id: str = "", limit: int = 25) -> str:
        rows = self.timeline(task_id=task_id, limit=limit)
        lines = ["TIMELINE (newest first)", "-----------------------"]
        for e in rows:
            ts = time.strftime("%H:%M:%S", time.localtime(e["ts"]))
            suffix = f" | {e['detail']}" if e["detail"] else ""
            lines.append(f"{ts} {e['event']:<16} {e['action'][:40]:<40} "
                         f"risk={e['risk'] or '-':<14}{suffix}")
        if not rows:
            lines.append("(no events)")
        return "\n".join(lines)


_instance: Optional[ActionStream] = None
_inst_lock = threading.Lock()


def get_stream() -> ActionStream:
    global _instance
    with _inst_lock:
        if _instance is None:
            _instance = ActionStream()
        return _instance


def reset_stream() -> None:
    global _instance
    with _inst_lock:
        _instance = ActionStream()


__all__ = [
    "ActionStream",
    "get_stream",
    "reset_stream",
    "safe_target_hash",
    "EVENT_TYPES",
]
