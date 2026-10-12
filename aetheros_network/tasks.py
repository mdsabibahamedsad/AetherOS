"""Remote task lifecycle (Master 46 sections 23-27, 34-37, 102-103).

States: discovered|proposed|authorized|submitted|accepted|running|waiting|
input_required|approval_required|completed|failed|cancelled|expired|
rejected|timed_out. Every task has origin/owner/target/authorization —
no orphans. State persists in SQLite so tasks survive desktop restart.
Duplicate-submission defense: each task carries an idempotency key and
the gateway reconciles (query before resubmit) instead of blindly
resending side-effecting tasks.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

TASK_STATES = (
    "discovered", "proposed", "authorized", "submitted", "accepted",
    "running", "waiting", "input_required", "approval_required",
    "completed", "failed", "cancelled", "expired", "rejected", "timed_out",
)
TERMINAL_STATES = {"completed", "failed", "cancelled", "expired", "rejected", "timed_out"}

_ALLOWED = {
    "discovered": {"proposed", "cancelled"},
    "proposed": {"authorized", "rejected", "cancelled"},
    "authorized": {"submitted", "cancelled", "expired"},
    "submitted": {"accepted", "rejected", "failed", "cancelled", "timed_out"},
    "accepted": {"running", "cancelled", "failed"},
    "running": {"waiting", "input_required", "approval_required", "completed", "failed", "cancelled", "timed_out"},
    "waiting": {"running", "cancelled", "timed_out", "expired"},
    "input_required": {"running", "cancelled", "expired"},
    "approval_required": {"running", "cancelled", "rejected", "expired"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
    "expired": set(),
    "rejected": set(),
    "timed_out": set(),
}

PRIORITIES = ("critical", "high", "normal", "low")


@dataclass
class RemoteTask:
    task_id: str
    origin_agent: str
    target_agent: str
    owner: str = ""
    user_id: str = ""
    organization_id: str = ""
    purpose: str = ""
    requirements: Dict[str, Any] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    data_scope: str = "internal"
    budget: Dict[str, Any] = field(default_factory=dict)
    deadline: float = 0.0
    priority: str = "normal"
    status: str = "discovered"
    idempotency_key: str = ""
    contract_version: str = "1"
    events: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    result: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RemoteTask":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


def new_task(origin_agent: str, target_agent: str, purpose: str, **kw: Any) -> RemoteTask:
    return RemoteTask(
        task_id=f"rt-{uuid.uuid4().hex[:12]}",
        origin_agent=origin_agent,
        target_agent=target_agent,
        purpose=purpose,
        idempotency_key=f"idem-{uuid.uuid4().hex}",
        **kw,
    )


class TaskStore:
    """SQLite-persisted task store with a bounded queue view."""

    def __init__(self, path: Path, max_queued: int = 100) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._max_queued = max_queued
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS remote_tasks (
                    task_id TEXT PRIMARY KEY, status TEXT, data TEXT,
                    created_at REAL, updated_at REAL)"""
            )

    def save(self, task: RemoteTask) -> None:
        task.updated_at = time.time()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO remote_tasks VALUES (?,?,?,?,?)",
                (task.task_id, task.status, json.dumps(task.to_dict()),
                 task.created_at, task.updated_at),
            )

    def get(self, task_id: str) -> Optional[RemoteTask]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM remote_tasks WHERE task_id=?", (task_id,)).fetchone()
        return RemoteTask.from_dict(json.loads(row["data"])) if row else None

    def transition(self, task_id: str, to: str, note: str = "") -> RemoteTask:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"unknown task: {task_id}")
        if to != task.status and to not in _ALLOWED.get(task.status, set()):
            raise ValueError(f"task transition not allowed: {task.status} -> {to}")
        task.status = to
        task.events.append({"at": time.time(), "to": to, "note": note})
        self.save(task)
        return task

    def find_by_idempotency(self, key: str) -> Optional[RemoteTask]:
        with self._connect() as conn:
            rows = conn.execute("SELECT data FROM remote_tasks").fetchall()
        for row in rows:
            task = RemoteTask.from_dict(json.loads(row["data"]))
            if task.idempotency_key == key:
                return task
        return None

    def list(self, status: Optional[str] = None, limit: int = 200) -> List[RemoteTask]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT data FROM remote_tasks WHERE status=? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT data FROM remote_tasks ORDER BY created_at DESC LIMIT ?",
                    (limit,)).fetchall()
        return [RemoteTask.from_dict(json.loads(r["data"])) for r in rows]

    def queue_depth(self) -> Dict[str, int]:
        """Bounded-queue state: queued vs running vs terminal (section 102)."""
        with self._connect() as conn:
            rows = conn.execute("SELECT status, COUNT(*) c FROM remote_tasks GROUP BY status").fetchall()
        counts = {r["status"]: r["c"] for r in rows}
        queued = sum(counts.get(s, 0) for s in ("discovered", "proposed", "authorized", "submitted"))
        return {"queued": queued, "running": counts.get("running", 0),
                "terminal": sum(counts.get(s, 0) for s in TERMINAL_STATES),
                "max_queued": self._max_queued, "full": queued >= self._max_queued}

    def reconcile(self, task_id: str, remote_state: str) -> RemoteTask:
        """Resume/reconcile after restart or reconnect (sections 35, 122):
        adopt the remote state only along a legal edge, else mark failed."""
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"unknown task: {task_id}")
        if remote_state == task.status or remote_state not in TASK_STATES:
            return task
        if remote_state in _ALLOWED.get(task.status, set()):
            return self.transition(task_id, remote_state, "reconciled with remote")
        # Remote moved somewhere unexpected: do not fabricate progress.
        task.events.append({"at": time.time(), "to": task.status,
                            "note": f"remote reports {remote_state}; kept local {task.status}"})
        self.save(task)
        return task
