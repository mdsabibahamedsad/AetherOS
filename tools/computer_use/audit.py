"""Audit logging for computer-use actions.

Records a metadata-only append-only log of every dispatched action. The log
deliberately never stores clipboard contents, screenshot pixels, or full
typed text — ``summary`` is a short human-readable action description
(pre-built by the tool layer's ``_summarize_action``) and any raw payloads
passed via ``meta`` are redacted before write.

The default destination is ``$AETHEROS_HOME/logs/computer_use_audit.jsonl``
(profile-aware). Rotates at ``max_bytes`` (default 1 MiB) by truncating to a
single line to keep the file bounded without heavy dependencies.
"""

from __future__ import annotations

import json
import logging
import os
import time
from threading import RLock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Fields that may carry sensitive payloads (typed text, clipboard values,
# element values). Anything under these keys is dropped before logging.
_SENSITIVE_META_KEYS = ("text", "value", "clipboard", "payload")

_REDACTED = "<redacted>"


class ComputerUseAuditLog:
    """Append-only JSON-lines audit log with a memory mirror."""

    def __init__(
        self,
        path: Optional[str] = None,
        max_bytes: int = 1_048_576,
        enabled: bool = True,
    ) -> None:
        self._enabled = enabled
        self._max_bytes = max_bytes
        self._path: Optional[str] = path or self._default_path()
        self._lock = RLock()
        self._memory: List[Dict[str, Any]] = []

    @staticmethod
    def _default_path() -> Optional[str]:
        try:
            from aetheros_constants import get_aetheros_home
        except Exception:
            return None
        try:
            home = get_aetheros_home()
            logs_dir = home / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            return str(logs_dir / "computer_use_audit.jsonl")
        except Exception:  # pragma: no cover - filesystem edge cases
            return None

    @staticmethod
    def _redact(meta: Dict[str, Any]) -> Dict[str, Any]:
        """Return ``meta`` with sensitive payload keys scrubbed."""
        if not meta:
            return {}
        out: Dict[str, Any] = {}
        for key, value in meta.items():
            if key in _SENSITIVE_META_KEYS or any(s in key for s in ("text", "value", "payload")):
                out[key] = _REDACTED
            elif isinstance(value, dict):
                out[key] = ComputerUseAuditLog._redact(value)
            else:
                out[key] = value
        return out

    def record(
        self,
        *,
        action: str,
        allowed: bool,
        ok: Optional[bool] = None,
        permission: Optional[str] = None,
        backend: str = "",
        platform: str = "",
        summary: str = "",
        elapsed_ms: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append one audit entry. Never raises on log failures."""
        if not self._enabled:
            return
        entry: Dict[str, Any] = {
            "ts": time.time(),
            "action": action,
            "allowed": bool(allowed),
            "backend": backend,
            "platform": platform,
            "summary": summary,
        }
        if ok is not None:
            entry["ok"] = bool(ok)
        if permission:
            entry["permission"] = str(permission)
        if elapsed_ms is not None:
            entry["elapsed_ms"] = round(elapsed_ms, 3)
        redacted = self._redact(meta or {})
        if redacted:
            entry["meta"] = redacted

        with self._lock:
            self._memory.append(entry)
            if self._path:
                try:
                    self._append_line(json.dumps(entry, separators=(",", ":")))
                except Exception as exc:  # pragma: no cover - defensive
                    logger.debug("computer_use audit write failed: %s", exc)

    def _append_line(self, line: str) -> None:
        assert self._path is not None
        try:
            size = os.path.getsize(self._path) if os.path.exists(self._path) else 0
            if size >= self._max_bytes:
                # Bounded rotation: keep only the most recent line.
                open(self._path, "w", encoding="utf-8").close()
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError as exc:  # pragma: no cover - filesystem edge cases
            logger.debug("computer_use audit append failed: %s", exc)

    def entries(self) -> List[Dict[str, Any]]:
        """Return the in-memory mirror of recent entries."""
        with self._lock:
            return list(self._memory)

    def clear(self) -> None:
        with self._lock:
            self._memory.clear()
            if self._path:
                try:
                    open(self._path, "w", encoding="utf-8").close()
                except OSError:  # pragma: no cover
                    pass

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)


# ── Process-wide singleton ───────────────────────────────────────────────

_audit_log: Optional[ComputerUseAuditLog] = None


def get_audit_log() -> ComputerUseAuditLog:
    """Return the process-wide audit log (lazy singleton)."""
    global _audit_log
    if _audit_log is None:
        _audit_log = ComputerUseAuditLog()
    return _audit_log


def reset_audit_for_tests() -> None:
    """Test helper — drop the singleton so a fresh log is built next call."""
    global _audit_log
    _audit_log = None
