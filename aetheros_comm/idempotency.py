"""
Agent Communication Fabric — idempotency (master spec step 32).

Sensitive requests carry an idempotency key. If a request is retried (or a
duplicate arrives on the wire), the side effect must not be duplicated. The
store records ``(senderAgentId, idempotencyKey) -> result`` for a retention
window; a replayed key returns the previously computed result instead of
re-executing.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class IdempotencyRecord:
    key: str
    result: Any = None
    created_at: float = field(default_factory=time.time)


class IdempotencyStore:
    """Thread-safe idempotency key store with TTL pruning."""

    def __init__(self, ttl_seconds: float = 86400.0) -> None:
        self._ttl = ttl_seconds
        self._records: Dict[Tuple[str, str], IdempotencyRecord] = {}
        self._lock = threading.RLock()

    def lookup(self, sender: str, key: str) -> Tuple[bool, Any]:
        """Return ``(found, result)`` for ``(sender, key)``."""
        now = time.time()
        with self._lock:
            self._prune(now)
            record = self._records.get((sender, key))
            if record is None:
                return False, None
            return True, record.result

    def record(self, sender: str, key: str, result: Any = None) -> None:
        now = time.time()
        with self._lock:
            self._prune(now)
            self._records[(sender, key)] = IdempotencyRecord(
                key=key, result=result, created_at=now)

    def get_or_record(self, sender: str, key: str,
                      compute) -> Tuple[bool, Any]:
        """Idempotent execute: return ``(was_cached, result)``.

        If ``(sender, key)`` was seen, the cached result is returned without
        invoking ``compute``. Otherwise ``compute()`` runs once and is stored.
        """
        found, result = self.lookup(sender, key)
        if found:
            return True, result
        result = compute()
        self.record(sender, key, result)
        return False, result

    def _prune(self, now: float) -> None:
        cutoff = now - self._ttl
        stale = [k for k, r in self._records.items() if r.created_at < cutoff]
        for key in stale:
            del self._records[key]

    def clear(self) -> None:
        with self._lock:
            self._records.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)