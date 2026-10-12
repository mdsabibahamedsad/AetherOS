"""Structured execution logging — persistent log store with search and filtering."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


class WorkflowLogStore:
    """SQLite-backed store for workflow execution logs."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(get_aetheros_home() / "workflows" / "logs.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    @property
    def _conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def _init_db(self):
        import os
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                execution_id TEXT,
                node_id TEXT,
                level TEXT NOT NULL DEFAULT 'INFO',
                message TEXT NOT NULL,
                data TEXT,
                category TEXT DEFAULT ''
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_wf_logs_workflow
            ON workflow_logs(workflow_id)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_wf_logs_execution
            ON workflow_logs(execution_id)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_wf_logs_timestamp
            ON workflow_logs(timestamp)
        """)
        self._conn.commit()

    def log(self, workflow_id: str, message: str, level: str = "INFO",
            execution_id: str = None, node_id: str = None,
            data: Any = None, category: str = "") -> int:
        self._conn.execute("""
            INSERT INTO workflow_logs
                (timestamp, workflow_id, execution_id, node_id, level, message, data, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.utcnow().isoformat() + "Z", workflow_id, execution_id,
              node_id, level, message,
              json.dumps(data) if data is not None else None, category))
        self._conn.commit()
        return self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def info(self, workflow_id: str, message: str, **kwargs) -> int:
        return self.log(workflow_id, message, "INFO", **kwargs)

    def warning(self, workflow_id: str, message: str, **kwargs) -> int:
        return self.log(workflow_id, message, "WARNING", **kwargs)

    def error(self, workflow_id: str, message: str, **kwargs) -> int:
        return self.log(workflow_id, message, "ERROR", **kwargs)

    def search(self, workflow_id: str = None, execution_id: str = None,
               level: str = None, category: str = None,
               query: str = None, limit: int = 100,
               offset: int = 0) -> list[dict]:
        parts = ["SELECT * FROM workflow_logs WHERE 1=1"]
        params = []
        if workflow_id:
            parts.append("AND workflow_id = ?")
            params.append(workflow_id)
        if execution_id:
            parts.append("AND execution_id = ?")
            params.append(execution_id)
        if level:
            parts.append("AND level = ?")
            params.append(level)
        if category:
            parts.append("AND category = ?")
            params.append(category)
        if query:
            parts.append("AND message LIKE ?")
            params.append(f"%{query}%")
        parts.append("ORDER BY timestamp DESC")
        parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])
        rows = self._conn.execute(" ".join(parts), params).fetchall()
        return [dict(r) for r in rows]

    def get_execution_logs(self, execution_id: str) -> list[dict]:
        rows = self._conn.execute("""
            SELECT * FROM workflow_logs WHERE execution_id = ?
            ORDER BY timestamp ASC
        """, (execution_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_workflow_logs(self, workflow_id: str, limit: int = 200) -> list[dict]:
        rows = self._conn.execute("""
            SELECT * FROM workflow_logs WHERE workflow_id = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (workflow_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self, workflow_id: str = None) -> dict:
        if workflow_id:
            row = self._conn.execute("""
                SELECT level, COUNT(*) as count
                FROM workflow_logs WHERE workflow_id = ?
                GROUP BY level
            """, (workflow_id,)).fetchall()
        else:
            row = self._conn.execute("""
                SELECT level, COUNT(*) as count
                FROM workflow_logs GROUP BY level
            """).fetchall()
        stats = {"total": 0}
        for r in row:
            stats[r["level"]] = r["count"]
            stats["total"] += r["count"]
        return stats

    def clear(self, workflow_id: str = None) -> int:
        if workflow_id:
            cursor = self._conn.execute("DELETE FROM workflow_logs WHERE workflow_id = ?",
                                        (workflow_id,))
        else:
            cursor = self._conn.execute("DELETE FROM workflow_logs")
        self._conn.commit()
        return cursor.rowcount

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


import os
