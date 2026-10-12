"""Idempotency registry (Step 61).

Tracks which actions have already been executed (by ``idempotency_key``) so
retry-safe pipelines can skip work that already succeeded. Pure in-memory
state keyed by (session, key). The manager consults this before executing an
action that carries an ``idempotency_key``.
"""

from __future__ import annotations

import threading
from typing import Dict, Optional


class IdempotencyRegistry:
    """Per-session dedup of executed actions by idempotency key."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # session_id → {idempotency_key → action_id}
        self._seen: Dict[str, Dict[str, str]] = {}

    def seen(self, key: str, session_id: str = "") -> bool:
        """True when ``key`` has already been recorded for this session."""
        if not key:
            return False
        with self._lock:
            return key in self._seen.get(session_id, {})

    def check_and_record(self, key: str, action_id: str, session_id: str = "") -> bool:
        """Atomically check+record. Returns False when ``key`` was already seen
        (caller should skip execution)."""
        if not key:
            return True  # no dedup key → nothing to dedup
        with self._lock:
            bucket = self._seen.setdefault(session_id, {})
            if key in bucket:
                return False
            bucket[key] = action_id
            return True

    def record(self, key: str, action_id: str, session_id: str = "") -> None:
        """Record ``key`` as executed (no check)."""
        if not key:
            return
        with self._lock:
            self._seen.setdefault(session_id, {})[key] = action_id

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            self._seen.pop(session_id, None)

    def reset(self) -> None:
        with self._lock:
            self._seen.clear()


# Process-wide default registry (shared by managers that don't inject one).
_default_registry: Optional[IdempotencyRegistry] = None


def get_idempotency_registry() -> IdempotencyRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = IdempotencyRegistry()
    return _default_registry


def reset_idempotency_for_tests() -> None:
    global _default_registry
    _default_registry = None