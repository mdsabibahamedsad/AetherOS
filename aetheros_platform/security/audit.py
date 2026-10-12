"""Audit logging — tamper-evident event logging for security."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

AUDIT_EVENT_TYPES = [
    "user.login", "user.logout", "user.create", "user.delete",
    "user.update", "user.mfa_enable", "user.mfa_disable",
    "session.create", "session.revoke",
    "role.create", "role.update", "role.delete", "role.assign", "role.revoke",
    "permission.change", "permission.deny",
    "key.create", "key.revoke", "key.rotate",
    "config.change", "system.startup", "system.shutdown",
    "agent.run", "workflow.run",
    "data.export", "data.import", "data.delete",
    "auth.failure", "auth.success",
    "admin.action",
]


@dataclass
class AuditEvent:
    event_type: str
    user_id: str
    details: dict = None
    ip_address: str = ""
    user_agent: str = ""
    severity: str = "info"

    def to_dict(self) -> dict:
        return {
            "id": getattr(self, "id", ""),
            "event_type": self.event_type,
            "user_id": self.user_id,
            "details": self.details or {},
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "severity": self.severity,
            "timestamp": getattr(self, "timestamp", ""),
            "hash": getattr(self, "hash", ""),
            "previous_hash": getattr(self, "previous_hash", ""),
        }


class AuditLogger:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._last_hash = ""
        self._init_db()

    def _init_db(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    details TEXT DEFAULT '{}',
                    ip_address TEXT DEFAULT '',
                    user_agent TEXT DEFAULT '',
                    severity TEXT DEFAULT 'info',
                    timestamp TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    previous_hash TEXT DEFAULT ''
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_type
                ON audit_log(event_type)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_user
                ON audit_log(user_id)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_time
                ON audit_log(timestamp)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_severity
                ON audit_log(severity)
            """)
            cursor = self._conn.execute(
                "SELECT hash FROM audit_log ORDER BY rowid DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                self._last_hash = row[0]
            self._conn.commit()

    def log(self, event: AuditEvent) -> str:
        import uuid
        eid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        previous = self._last_hash
        payload = f"{eid}:{event.event_type}:{event.user_id}:{now}:{previous}"
        h = hashlib.sha256(payload.encode()).hexdigest()
        self._last_hash = h
        try:
            with self._lock:
                self._conn.execute(
                    """INSERT INTO audit_log
                       (id, event_type, user_id, details, ip_address,
                        user_agent, severity, timestamp, hash, previous_hash)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (eid, event.event_type, event.user_id,
                     json.dumps(event.details or {}),
                     event.ip_address, event.user_agent,
                     event.severity, now, h, previous))
                self._conn.commit()
            return eid
        except Exception as e:
            logger.error("audit log error: %s", e)
            return ""

    def log_event(self, event_type: str, user_id: str,
                   details: dict = None,
                   ip_address: str = "", severity: str = "info") -> str:
        return self.log(AuditEvent(
            event_type=event_type, user_id=user_id,
            details=details, ip_address=ip_address,
            severity=severity,
        ))

    def query(self, event_type: str = None, user_id: str = None,
               severity: str = None, limit: int = 100,
               offset: int = 0) -> list[dict]:
        conditions = []
        params = []
        if event_type:
            conditions.append("event_type=?")
            params.append(event_type)
        if user_id:
            conditions.append("user_id=?")
            params.append(user_id)
        if severity:
            conditions.append("severity=?")
            params.append(severity)
        where = " AND ".join(conditions) if conditions else "1=1"
        with self._lock:
            cur = self._conn.execute(
                f"SELECT * FROM audit_log WHERE {where} "
                f"ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [limit, offset])
            return [self._row_to_event(r) for r in cur.fetchall()]

    def verify_chain(self) -> dict:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, event_type, user_id, timestamp, hash, previous_hash "
                "FROM audit_log ORDER BY rowid ASC")
            rows = cur.fetchall()
        valid = True
        prev_hash = ""
        for row in rows:
            eid, etype, uid, ts, h, prev = row
            payload = f"{eid}:{etype}:{uid}:{ts}:{prev}"
            computed = hashlib.sha256(payload.encode()).hexdigest()
            if computed != h or prev != prev_hash:
                valid = False
                break
            prev_hash = h
        return {"valid": valid, "entries": len(rows), "last_hash": prev_hash}

    def get_stats(self) -> dict:
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) FROM audit_log").fetchone()[0]
            by_type = self._conn.execute(
                "SELECT event_type, COUNT(*) FROM audit_log "
                "GROUP BY event_type ORDER BY COUNT(*) DESC").fetchall()
            by_severity = self._conn.execute(
                "SELECT severity, COUNT(*) FROM audit_log "
                "GROUP BY severity").fetchall()
            recent = self._conn.execute(
                "SELECT timestamp FROM audit_log ORDER BY timestamp DESC LIMIT 1").fetchone()
        return {
            "total": total,
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "latest_event": recent[0] if recent else None,
        }

    def get_event_types(self) -> list[str]:
        return AUDIT_EVENT_TYPES

    @staticmethod
    def _row_to_event(row) -> dict:
        return {
            "id": row[0], "event_type": row[1], "user_id": row[2],
            "details": json.loads(row[3]) if isinstance(row[3], str) else row[3],
            "ip_address": row[4], "user_agent": row[5],
            "severity": row[6], "timestamp": row[7],
            "hash": row[8], "previous_hash": row[9],
        }
