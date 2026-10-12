"""Session management — user sessions, tokens, expiry."""

from __future__ import annotations

import json
import logging
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

SESSION_DURATION = timedelta(hours=24)
SESSION_DURATION_REMEMBER = timedelta(days=30)


@dataclass
class UserSession:
    id: str
    user_id: str
    token: str
    created_at: str
    expires_at: str
    ip_address: str = ""
    user_agent: str = ""
    is_active: bool = True
    metadata: dict = None

    @property
    def is_expired(self) -> bool:
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return exp < datetime.utcnow()
        except Exception:
            return False


class SessionManager:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    ip_address TEXT DEFAULT '',
                    user_agent TEXT DEFAULT '',
                    is_active INTEGER DEFAULT 1,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_token
                ON sessions(token)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user
                ON sessions(user_id)
            """)
            self._conn.commit()

    def create_session(self, user_id: str, remember_me: bool = False,
                        ip_address: str = "", user_agent: str = "",
                        metadata: dict = None) -> UserSession:
        import uuid
        sid = str(uuid.uuid4())
        token = secrets.token_urlsafe(48)
        now = datetime.utcnow()
        duration = SESSION_DURATION_REMEMBER if remember_me else SESSION_DURATION
        expires = now + duration
        session = UserSession(
            id=sid, user_id=user_id, token=token,
            created_at=now.isoformat() + "Z",
            expires_at=expires.isoformat() + "Z",
            ip_address=ip_address, user_agent=user_agent,
            metadata=metadata or {},
        )
        try:
            with self._lock:
                self._conn.execute(
                    """INSERT INTO sessions
                       (id, user_id, token, created_at, expires_at,
                        ip_address, user_agent, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (sid, user_id, token, session.created_at,
                     session.expires_at, ip_address, user_agent,
                     json.dumps(metadata or {})))
                self._conn.commit()
            logger.debug("Created session %s for user %s", sid, user_id)
        except Exception as e:
            logger.error("create_session error: %s", e)
        return session

    def get_session(self, token: str) -> Optional[UserSession]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM sessions WHERE token=?", (token,))
            return self._row_to_session(cur.fetchone())

    def validate_session(self, token: str) -> Optional[UserSession]:
        session = self.get_session(token)
        if not session:
            return None
        if not session.is_active or session.is_expired:
            return None
        return session

    def get_user_sessions(self, user_id: str) -> list[UserSession]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM sessions WHERE user_id=? ORDER BY created_at DESC",
                (user_id,))
            return [self._row_to_session(r) for r in cur.fetchall()]

    def revoke_session(self, token: str) -> bool:
        try:
            with self._lock:
                self._conn.execute(
                    "UPDATE sessions SET is_active=0 WHERE token=?",
                    (token,))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("revoke_session error: %s", e)
            return False

    def revoke_all_user_sessions(self, user_id: str) -> int:
        try:
            with self._lock:
                cur = self._conn.execute(
                    "UPDATE sessions SET is_active=0 WHERE user_id=? AND is_active=1",
                    (user_id,))
                self._conn.commit()
                return cur.rowcount
        except Exception as e:
            logger.error("revoke_all error: %s", e)
            return 0

    def cleanup_expired(self) -> int:
        now = datetime.utcnow().isoformat() + "Z"
        try:
            with self._lock:
                cur = self._conn.execute(
                    "DELETE FROM sessions WHERE expires_at < ?", (now,))
                self._conn.commit()
                return cur.rowcount
        except Exception as e:
            logger.error("cleanup error: %s", e)
            return 0

    def get_active_sessions(self, limit: int = 100) -> list[UserSession]:
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM sessions WHERE is_active=1 AND expires_at > ? "
                "ORDER BY created_at DESC LIMIT ?", (now, limit))
            return [self._row_to_session(r) for r in cur.fetchall()]

    def get_stats(self) -> dict:
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) FROM sessions").fetchone()[0]
            active = self._conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE is_active=1 AND expires_at > ?",
                (now,)).fetchone()[0]
            expired = self._conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE expires_at < ?",
                (now,)).fetchone()[0]
        return {"total": total, "active": active, "expired": expired}

    @staticmethod
    def _row_to_session(row) -> Optional[UserSession]:
        if not row:
            return None
        return UserSession(
            id=row[0], user_id=row[1], token=row[2],
            created_at=row[3], expires_at=row[4],
            ip_address=row[5] or "", user_agent=row[6] or "",
            is_active=bool(row[7]),
            metadata=json.loads(row[8]) if isinstance(row[8], str) else row[8],
        )
