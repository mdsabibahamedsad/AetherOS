"""Durable recovery journal (SQLite).

Tracks the lifecycle of every significant operation so that an unclean
shutdown leaves enough evidence to classify an operation as STARTED,
CHECKPOINTED, COMPLETED, FAILED, ABORTED or RECOVERABLE — and so recovery
never blindly repeats an operation whose outcome is UNKNOWN.

Storage lives under ``<AETHEROS_HOME>/reliability/journal.db`` (profile
aware).  Writes are append-only with a monotonic sequence; reads are
cheap.  No secrets are ever written — callers must redact before storing
details.
"""

from __future__ import annotations

import enum
import json
import logging
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 1


class JournalStatus(str, enum.Enum):
    STARTED = "STARTED"
    CHECKPOINTED = "CHECKPOINTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    RECOVERABLE = "RECOVERABLE"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS journal (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL,
    started_at REAL NOT NULL,
    component TEXT NOT NULL DEFAULT '',
    operation TEXT NOT NULL,
    checkpoint INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'STARTED',
    completed_at REAL,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_journal_op ON journal(operation_id);
CREATE INDEX IF NOT EXISTS idx_journal_status ON journal(status);
"""


class RecoveryJournal:
    """Append-only, thread-safe, SQLite-backed recovery journal.

    Usage::

        journal = get_recovery_journal()
        op_id = journal.begin(component="gateway", operation="restart")
        journal.checkpoint(op_id, step=1)
        journal.complete(op_id)
        pending = journal.recoverable()   # RECOVERABLE / STARTED ops
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._db_path = Path(db_path) if db_path else (
            get_aetheros_home() / "reliability" / "journal.db"
        )
        self._conn: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self._db_path), timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")
            conn.executescript(_SCHEMA)
            conn.commit()
            self._conn = conn
        return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.commit()
                    self._conn.close()
                except sqlite3.Error:
                    pass
                self._conn = None

    def _execute(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Cursor]:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(sql, params)
                conn.commit()
                return cur
            except sqlite3.OperationalError:
                # DB may be locked/rotated mid-operation — reconnect once.
                try:
                    self._conn = None
                    conn = self._connect()
                    cur = conn.execute(sql, params)
                    conn.commit()
                    return cur
                except sqlite3.Error as exc:
                    logger.error("Journal write failed: %s", exc)
                    return None

    # ------------------------------------------------------------------
    # Lifecycle API
    # ------------------------------------------------------------------

    def begin(self, component: str, operation: str,
              detail: Optional[Dict[str, Any]] = None) -> str:
        """Start an operation and return its operation_id."""
        op_id = uuid.uuid4().hex[:16]
        self._execute(
            "INSERT INTO journal (operation_id, started_at, component, operation, "
            "status, detail) VALUES (?, ?, ?, ?, 'STARTED', ?)",
            (op_id, time.time(), component, operation,
             json.dumps(detail or {})),
        )
        return op_id

    def checkpoint(self, operation_id: str, step: int = 1,
                   detail: Optional[Dict[str, Any]] = None) -> bool:
        """Record a checkpoint inside an operation (never a secret)."""
        cur = self._execute(
            "UPDATE journal SET checkpoint = MAX(checkpoint, ?), "
            "status = 'CHECKPOINTED', detail = ? WHERE operation_id = ?",
            (int(step), json.dumps(detail or {}), operation_id),
        )
        return bool(cur and cur.rowcount)

    def complete(self, operation_id: str,
                 detail: Optional[Dict[str, Any]] = None) -> bool:
        cur = self._execute(
            "UPDATE journal SET status = 'COMPLETED', completed_at = ?, "
            "detail = ? WHERE operation_id = ? AND status != 'COMPLETED'",
            (time.time(), json.dumps(detail or {}), operation_id),
        )
        return bool(cur and cur.rowcount)

    def fail(self, operation_id: str,
             detail: Optional[Dict[str, Any]] = None) -> bool:
        cur = self._execute(
            "UPDATE journal SET status = 'FAILED', completed_at = ?, "
            "detail = ? WHERE operation_id = ?",
            (time.time(), json.dumps(detail or {}), operation_id),
        )
        return bool(cur and cur.rowcount)

    def abort(self, operation_id: str,
              detail: Optional[Dict[str, Any]] = None) -> bool:
        cur = self._execute(
            "UPDATE journal SET status = 'ABORTED', completed_at = ?, "
            "detail = ? WHERE operation_id = ?",
            (time.time(), json.dumps(detail or {}), operation_id),
        )
        return bool(cur and cur.rowcount)

    def mark_recoverable(self, operation_id: str,
                         detail: Optional[Dict[str, Any]] = None) -> bool:
        cur = self._execute(
            "UPDATE journal SET status = 'RECOVERABLE', completed_at = ?, "
            "detail = ? WHERE operation_id = ?",
            (time.time(), json.dumps(detail or {}), operation_id),
        )
        return bool(cur and cur.rowcount)

    def append_operation(self, *, operation: str, component: str = "",
                         status: str = "STARTED",
                         detail: Optional[Dict[str, Any]] = None) -> str:
        """One-shot record (for events/audit) without a lifecycle."""
        op_id = uuid.uuid4().hex[:16]
        self._execute(
            "INSERT INTO journal (operation_id, started_at, component, operation, "
            "status, completed_at, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (op_id, time.time(), component, operation, status,
             time.time() if status in ("COMPLETED", "FAILED", "ABORTED") else None,
             json.dumps(detail or {})),
        )
        return op_id

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, operation_id: str) -> Optional[Dict[str, Any]]:
        cur = self._execute(
            "SELECT operation_id, started_at, component, operation, checkpoint, "
            "status, completed_at, detail FROM journal WHERE operation_id = ?",
            (operation_id,),
        )
        if not cur:
            return None
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def pending(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Operations that were never completed — candidates for startup
        recovery (STARTED / CHECKPOINTED / RECOVERABLE)."""
        cur = self._execute(
            "SELECT operation_id, started_at, component, operation, checkpoint, "
            "status, completed_at, detail FROM journal "
            "WHERE status IN ('STARTED', 'CHECKPOINTED', 'RECOVERABLE') "
            "ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
        return self._rows(cur)

    def recoverable(self, limit: int = 200) -> List[Dict[str, Any]]:
        cur = self._execute(
            "SELECT operation_id, started_at, component, operation, checkpoint, "
            "status, completed_at, detail FROM journal "
            "WHERE status = 'RECOVERABLE' ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
        return self._rows(cur)

    def recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self._execute(
            "SELECT operation_id, started_at, component, operation, checkpoint, "
            "status, completed_at, detail FROM journal "
            "ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
        return self._rows(cur)

    def by_component(self, component: str, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._execute(
            "SELECT operation_id, started_at, component, operation, checkpoint, "
            "status, completed_at, detail FROM journal "
            "WHERE component = ? ORDER BY started_at DESC LIMIT ?",
            (component, limit),
        )
        return self._rows(cur)

    def stats(self) -> Dict[str, Any]:
        cur = self._execute(
            "SELECT status, COUNT(*) FROM journal GROUP BY status",
        )
        counts: Dict[str, int] = {}
        total = 0
        if cur:
            for status, count in cur.fetchall():
                counts[status] = int(count)
                total += int(count)
        return {"total": total, "by_status": counts, "db_path": str(self._db_path)}

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def purge(self, older_than_seconds: float = 86400 * 90,
              keep_recoverable: bool = True) -> int:
        """Remove completed/terminal rows older than the retention window.

        RECOVERABLE rows are preserved by default so recovery evidence is not
        silently discarded.
        """
        cutoff = time.time() - older_than_seconds
        if keep_recoverable:
            cur = self._execute(
                "DELETE FROM journal WHERE status IN "
                "('COMPLETED', 'FAILED', 'ABORTED') AND completed_at IS NOT NULL "
                "AND completed_at < ?",
                (cutoff,),
            )
        else:
            cur = self._execute(
                "DELETE FROM journal WHERE completed_at IS NOT NULL AND completed_at < ?",
                (cutoff,),
            )
        return cur.rowcount if cur else 0

    def integrity(self) -> Dict[str, Any]:
        """Run SQLite quick_check on the journal store itself."""
        cur = self._execute("PRAGMA quick_check")
        ok = True
        detail = ""
        if cur:
            row = cur.fetchone()
            ok = bool(row and row[0] == "ok")
            detail = str(row[0]) if row else "no result"
        return {"ok": ok, "detail": detail, "db_path": str(self._db_path)}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: tuple) -> Dict[str, Any]:
        return {
            "operation_id": row[0],
            "started_at": row[1],
            "component": row[2],
            "operation": row[3],
            "checkpoint": row[4],
            "status": row[5],
            "completed_at": row[6],
            "detail": _loads(row[7]),
        }

    @staticmethod
    def _rows(cur: Optional[sqlite3.Cursor]) -> List[Dict[str, Any]]:
        if not cur:
            return []
        return [RecoveryJournal._row_to_dict(r) for r in cur.fetchall()]


def _loads(raw: Optional[str]) -> Any:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"raw": raw}


_journal: Optional[RecoveryJournal] = None
_journal_lock = threading.Lock()


def get_recovery_journal() -> RecoveryJournal:
    """Return the process-wide RecoveryJournal singleton."""
    global _journal
    if _journal is None:
        with _journal_lock:
            if _journal is None:
                _journal = RecoveryJournal()
    return _journal