"""Structured recovery-event schema and store.

Every recovery event carries a stable, queryable shape:

    recoveryId, componentId, failureType, detectedAt, diagnosis, attempt,
    action, result, verified, duration, traceId

Events are emitted to a bounded in-memory ring AND appended to the durable
recovery journal so operators can inspect them after restart.
"""

from __future__ import annotations

import enum
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class RecoveryResult(str, enum.Enum):
    NOT_ATTEMPTED = "not_attempted"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    EXHAUSTED = "exhausted"
    VERIFIED = "verified"
    NOT_VERIFIED = "not_verified"


@dataclass
class RecoveryEvent:
    component_id: str
    failure_type: str
    action: str
    detected_at: float = field(default_factory=time.time)
    diagnosis: str = ""
    attempt: int = 0
    result: str = RecoveryResult.NOT_ATTEMPTED.value
    verified: bool = False
    duration_ms: float = 0.0
    trace_id: str = ""
    recovery_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recoveryId": self.recovery_id,
            "componentId": self.component_id,
            "failureType": self.failure_type,
            "detectedAt": self.detected_at,
            "diagnosis": self.diagnosis,
            "attempt": self.attempt,
            "action": self.action,
            "result": self.result,
            "verified": self.verified,
            "duration": round(self.duration_ms, 2),
            "traceId": self.trace_id,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecoveryEvent":
        return cls(
            component_id=data.get("componentId", ""),
            failure_type=data.get("failureType", "UNKNOWN"),
            action=data.get("action", ""),
            detected_at=data.get("detectedAt", time.time()),
            diagnosis=data.get("diagnosis", ""),
            attempt=data.get("attempt", 0),
            result=data.get("result", RecoveryResult.NOT_ATTEMPTED.value),
            verified=bool(data.get("verified", False)),
            duration_ms=float(data.get("duration", 0.0) or 0.0),
            trace_id=data.get("traceId", ""),
            recovery_id=data.get("recoveryId", uuid.uuid4().hex[:12]),
            message=data.get("message", ""),
        )


class RecoveryEventStore:
    """In-memory ring of recovery events, optionally persisted to the journal.

    Usage::

        store = get_recovery_event_store()
        store.record(RecoveryEvent(component_id="gateway",
                                   failure_type="CRASH", action="restart"))
    """

    def __init__(self, max_events: int = 500) -> None:
        self._lock = threading.RLock()
        self._events: deque = deque(maxlen=max_events)
        self._journal: Optional[Any] = None  # lazy: RecoveryJournal

    def _journal_store(self):
        if self._journal is None:
            try:
                from aetheros_reliability.journal import get_recovery_journal
                self._journal = get_recovery_journal()
            except Exception:
                self._journal = False  # never retry in this process
        return self._journal if self._journal is not False else None

    def record(self, event: RecoveryEvent) -> RecoveryEvent:
        with self._lock:
            self._events.append(event)
        journal = self._journal_store()
        if journal is not None:
            try:
                journal.append_operation(
                    operation=f"recovery:{event.action}",
                    component=event.component_id,
                    status="completed" if event.verified else event.result,
                    detail={
                        "recovery_id": event.recovery_id,
                        "failure_type": event.failure_type,
                        "diagnosis": event.diagnosis,
                        "attempt": event.attempt,
                        "verified": event.verified,
                        "duration_ms": event.duration_ms,
                        "trace_id": event.trace_id,
                        "message": event.message,
                    },
                )
            except Exception:
                pass
        return event

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            events = list(self._events)[-limit:]
        return [e.to_dict() for e in events]

    def for_component(self, component_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            events = [
                e for e in list(self._events)[-limit * 5:]
                if e.component_id == component_id
            ]
        return [e.to_dict() for e in events[-limit:]]

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._events)
            by_result: Dict[str, int] = {}
            for e in self._events:
                by_result[e.result] = by_result.get(e.result, 0) + 1
        return {
            "total": total,
            "by_result": by_result,
            "recent": [e.to_dict() for e in list(self._events)[-10:]],
        }


_event_store: Optional[RecoveryEventStore] = None
_event_store_lock = threading.Lock()


def get_recovery_event_store() -> RecoveryEventStore:
    """Return the process-wide RecoveryEventStore singleton."""
    global _event_store
    if _event_store is None:
        with _event_store_lock:
            if _event_store is None:
                _event_store = RecoveryEventStore()
    return _event_store