"""Queue recovery and dead-letter queue.

Provides safe recovery semantics for in-process job queues:

* persist critical jobs before running them (journal-backed),
* recover pending jobs after a restart,
* deduplicate jobs so restart/replay never double-executes,
* move jobs that exceed safe retries to a DEAD_LETTER store instead of
  silently discarding them.

This is a *generic* helper.  Concrete queues (``aetheros_automation.core.
task_queue``, gateway job queues) integrate by driving the journal/dedup
primitives exposed here.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_reliability.journal import get_recovery_journal
from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


@dataclass
class DeadLetterEntry:
    job_id: str
    queue: str
    reason: str
    attempts: int
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "queue": self.queue,
            "reason": self.reason,
            "attempts": self.attempts,
            "created_at": self.created_at,
        }


class QueueRecovery:
    """Journal-backed job persistence, dedup and dead-lettering.

    Usage::

        qr = QueueRecovery()
        job_id = qr.persist("billing", {"invoice_id": 7})   # before execution
        qr.mark_started(job_id)
        ...
        qr.mark_done(job_id)
        # after restart:
        pending = qr.recoverable_jobs("billing")            # deduped by job_id
        qr.dead_letter("billing", job_id, reason="retries exhausted", attempts=5)
    """

    def __init__(self, journal=None, dead_letter_dir: Optional[Any] = None) -> None:
        self._lock = threading.RLock()
        self._journal = journal or get_recovery_journal()
        self._dead_letter_dir = (
            dead_letter_dir
            if dead_letter_dir is not None
            else get_aetheros_home() / "reliability" / "dead-letter"
        )
        self._seen: Dict[str, str] = {}  # job_id -> operation_id (dedup)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def persist(self, queue: str, job: Dict[str, Any],
                job_id: Optional[str] = None) -> str:
        """Journal a job BEFORE it executes.  Returns a job id.

        The same logical job (same ``job_id``) can only be persisted once —
        re-persisting returns the original operation id (dedup).
        """
        job_id = job_id or str(uuid.uuid4().hex[:16])
        with self._lock:
            existing = self._seen.get(job_id)
        if existing:
            return existing
        op_id = self._journal.begin(
            component=queue,
            operation=f"queue-job:{job_id}",
            detail={"job_id": job_id, "job": job},
        )
        with self._lock:
            self._seen[job_id] = op_id
        return job_id

    def mark_started(self, job_id: str, queue: str = "") -> None:
        with self._lock:
            op_id = self._seen.get(job_id)
        if op_id:
            self._journal.checkpoint(op_id, step=1, detail={"state": "started"})
        elif queue:
            self._journal.append_operation(
                operation=f"queue-job:{job_id}", component=queue,
                status="CHECKPOINTED", detail={"state": "started"},
            )

    def mark_done(self, job_id: str, queue: str = "") -> None:
        with self._lock:
            op_id = self._seen.get(job_id)
        if op_id:
            self._journal.complete(op_id, detail={"state": "done"})
            self._seen.pop(job_id, None)
        elif queue:
            self._journal.append_operation(
                operation=f"queue-job:{job_id}", component=queue,
                status="COMPLETED", detail={"state": "done"},
            )

    def mark_failed(self, job_id: str, reason: str, queue: str = "") -> None:
        with self._lock:
            op_id = self._seen.get(job_id)
        if op_id:
            self._journal.fail(op_id, detail={"reason": reason})
        elif queue:
            self._journal.append_operation(
                operation=f"queue-job:{job_id}", component=queue,
                status="FAILED", detail={"reason": reason},
            )

    # ------------------------------------------------------------------
    # Recovery / dedup
    # ------------------------------------------------------------------

    def recoverable_jobs(self, queue: str) -> List[Dict[str, Any]]:
        """Jobs that were persisted but never completed (deduplicated)."""
        rows = self._journal.by_component(queue, limit=200)
        seen_ids = set()
        jobs = []
        for row in rows:
            if row["status"] not in ("STARTED", "CHECKPOINTED", "RECOVERABLE"):
                continue
            detail = row.get("detail") or {}
            job_id = detail.get("job_id") or self._job_id_from(row.get("operation", ""))
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            jobs.append({
                "job_id": job_id,
                "operation_id": row["operation_id"],
                "status": row["status"],
                "checkpoint": row["checkpoint"],
                "job": detail.get("job", {}),
            })
        return jobs

    def replay_idempotency_key(self, job: Dict[str, Any]) -> str:
        """Derive a stable idempotency key for a job (for duplicate execution
        guards).  Uses ``job_id``/``id`` or a hash of the payload."""
        if job.get("job_id"):
            return str(job["job_id"])
        if job.get("id"):
            return str(job["id"])
        import hashlib
        return hashlib.sha256(
            json.dumps(job, sort_keys=True, default=str).encode()
        ).hexdigest()[:24]

    @staticmethod
    def _job_id_from(operation: str) -> str:
        if operation.startswith("queue-job:"):
            return operation[len("queue-job:"):]
        return operation

    # ------------------------------------------------------------------
    # Dead letter
    # ------------------------------------------------------------------

    def dead_letter(self, queue: str, job_id: str, reason: str,
                    attempts: int, payload: Optional[Dict[str, Any]] = None) -> Path:
        """Move a job that exceeded safe retries into the dead-letter store.

        Returns the written path.  Never silently discards the job.
        """
        entry = DeadLetterEntry(
            job_id=job_id, queue=queue, reason=reason,
            attempts=attempts, payload=payload or {},
        )
        directory = self._dead_letter_dir / _safe(queue)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{_safe(job_id)}.json"
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(entry.to_dict(), f, indent=2)
            f.flush()
        import os
        os.replace(tmp, path)
        logger.warning("Job %s dead-lettered (%s, %d attempts)", job_id, reason, attempts)
        return path

    def dead_letter_queue(self, queue: str) -> List[Dict[str, Any]]:
        directory = self._dead_letter_dir / _safe(queue)
        if not directory.exists():
            return []
        out = []
        for path in sorted(directory.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    out.append(json.load(f))
            except (OSError, json.JSONDecodeError):
                continue
        return out

    def dead_letter_summary(self) -> Dict[str, Any]:
        if not self._dead_letter_dir.exists():
            return {"queues": {}, "total": 0}
        total = 0
        by_queue: Dict[str, int] = {}
        for queue_dir in self._dead_letter_dir.iterdir():
            if not queue_dir.is_dir():
                continue
            count = len(list(queue_dir.glob("*.json")))
            by_queue[queue_dir.name] = count
            total += count
        return {"queues": by_queue, "total": total}


def _safe(name: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name or "unknown") or "unknown"


from pathlib import Path  # noqa: E402


class _Path(str):
    """Placeholder to satisfy type hints; real Path used at runtime."""


_recovery: Optional[QueueRecovery] = None
_recovery_lock = threading.Lock()


def get_queue_recovery() -> QueueRecovery:
    """Return the process-wide QueueRecovery singleton."""
    global _recovery
    if _recovery is None:
        with _recovery_lock:
            if _recovery is None:
                _recovery = QueueRecovery()
    return _recovery