"""AuditLogger — safe observability for computer-use actions (Step 38).

Records per-action telemetry: action id, timestamp, agent/session, tool,
action, result, latency, risk, permission result, and failure reason.

Redaction invariants (never logged):
  * passwords, API keys, cookies, tokens;
  * clipboard contents;
  * sensitive page contents / full typed text beyond a short summary.

Backed by the existing :class:`tools.computer_use.audit.ComputerUseAuditLog`
when available, falling back to an in-memory ring (test-friendly).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_actions.model import Action

_SENSITIVE_KEYS = ("password", "apikey", "api_key", "token", "cookie",
                   "secret", "credential", "privatekey", "clipboard")


def _redact(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {k: _redact(v, k) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(v, key) for v in value]
    if any(s in key.lower() for s in _SENSITIVE_KEYS):
        return "<redacted>"
    return value


class AuditLogger:
    """Metadata-only audit of the action pipeline."""

    def __init__(self, backend: Optional[Any] = None, max_entries: int = 1000) -> None:
        self.backend = backend  # tools.computer_use.audit log, or None
        self._entries: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._max_entries = max_entries

    def record(
        self,
        action: Optional[Action],
        *,
        decision: str = "",
        ok: Optional[bool] = None,
        error: str = "",
        elapsed_ms: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "ts": time.time(),
            "action_type": action.action_type.value if action else "",
            "action_id": action.action_id if action else "",
            "agent_id": action.agent_id if action else "",
            "session_id": action.session_id if action else "",
            "target": action.target if action else "",
            "risk_level": action.risk_level.value if action else "",
            "decision": decision,
            "permission": action.permission if action else "",
            "ok": ok,
            "elapsed_ms": round(elapsed_ms, 3) if elapsed_ms is not None else None,
        }
        if error:
            entry["error"] = str(error)[:300]
        if meta:
            entry["meta"] = _redact(meta)
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]
        if self.backend is not None:
            try:
                self.backend.record(
                    action=entry["action_type"],
                    allowed=(decision != "DENY"),
                    ok=ok,
                    permission=entry["permission"],
                    summary=f"decision={decision}"
                            + (f" error={error[:120]}" if error else ""),
                )
            except Exception:  # noqa: BLE001
                pass
        return entry

    def entries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        with self._lock:
            out = list(self._entries)
        return out[-limit:] if limit else out

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()