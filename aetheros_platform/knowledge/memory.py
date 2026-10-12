"""Cross-session memory — persistent memory across conversations and sessions."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

MAX_MEMORY_ITEMS = 5000


class CrossSessionMemory:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS cs_memories (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'note',
                    content TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    importance REAL DEFAULT 0.5,
                    context TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cs_memory_session
                ON cs_memories(session_id)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cs_memory_type
                ON cs_memories(type)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cs_memory_relevance
                ON cs_memories(importance DESC, last_accessed DESC)
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS cs_summaries (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    token_count INTEGER DEFAULT 0,
                    start_time TEXT,
                    end_time TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            self._conn.commit()

    def store(self, session_id: str, content: str, memory_type: str = "note",
               tags: list[str] = None, importance: float = 0.5,
               context: str = "", memory_id: str = None) -> str:
        import uuid
        mid = memory_id or str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        tags_json = json.dumps(tags or [])
        try:
            with self._lock:
                self._conn.execute(
                    """INSERT OR REPLACE INTO cs_memories
                       (id, session_id, type, content, tags, importance,
                        context, created_at, last_accessed, access_count)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                    (mid, session_id, memory_type, content, tags_json,
                     importance, context, now, now))
                self._conn.commit()
                self._trim(session_id)
            return mid
        except Exception as e:
            logger.error("store error: %s", e)
            return ""

    def get(self, memory_id: str) -> Optional[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM cs_memories WHERE id=?", (memory_id,))
            row = cur.fetchone()
        if row:
            self._touch(memory_id)
            return self._row_to_memory(row)
        return None

    def search(self, query: str, session_id: str = None,
                limit: int = 20) -> list[dict]:
        with self._lock:
            if session_id:
                cur = self._conn.execute(
                    """SELECT * FROM cs_memories
                       WHERE (content LIKE ? OR tags LIKE ?) AND session_id=?
                       ORDER BY importance DESC, last_accessed DESC LIMIT ?""",
                    (f"%{query}%", f"%{query}%", session_id, limit))
            else:
                cur = self._conn.execute(
                    """SELECT * FROM cs_memories
                       WHERE content LIKE ? OR tags LIKE ?
                       ORDER BY importance DESC, last_accessed DESC LIMIT ?""",
                    (f"%{query}%", f"%{query}%", limit))
            return [self._row_to_memory(r) for r in cur.fetchall()]

    def recall(self, session_id: str, limit: int = 50) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                """SELECT * FROM cs_memories WHERE session_id=?
                   ORDER BY importance DESC, last_accessed DESC LIMIT ?""",
                (session_id, limit))
            return [self._row_to_memory(r) for r in cur.fetchall()]

    def get_by_type(self, memory_type: str, session_id: str = None,
                     limit: int = 50) -> list[dict]:
        with self._lock:
            if session_id:
                cur = self._conn.execute(
                    "SELECT * FROM cs_memories WHERE type=? AND session_id=? "
                    "ORDER BY last_accessed DESC LIMIT ?",
                    (memory_type, session_id, limit))
            else:
                cur = self._conn.execute(
                    "SELECT * FROM cs_memories WHERE type=? "
                    "ORDER BY last_accessed DESC LIMIT ?",
                    (memory_type, limit))
            return [self._row_to_memory(r) for r in cur.fetchall()]

    def update_importance(self, memory_id: str, importance: float) -> bool:
        try:
            with self._lock:
                self._conn.execute(
                    "UPDATE cs_memories SET importance=? WHERE id=?",
                    (importance, memory_id))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("update_importance error: %s", e)
            return False

    def delete(self, memory_id: str) -> bool:
        try:
            with self._lock:
                self._conn.execute(
                    "DELETE FROM cs_memories WHERE id=?", (memory_id,))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("delete error: %s", e)
            return False

    def clear_session(self, session_id: str) -> int:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM cs_memories WHERE session_id=?", (session_id,))
            self._conn.commit()
            return cur.rowcount

    def store_summary(self, session_id: str, summary: str,
                       token_count: int = 0,
                       start_time: str = "",
                       end_time: str = "") -> str:
        import uuid
        sid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            self._conn.execute(
                """INSERT INTO cs_summaries
                   (id, session_id, summary, token_count, start_time, end_time, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (sid, session_id, summary, token_count, start_time, end_time, now))
            self._conn.commit()
        return sid

    def get_summaries(self, session_id: str, limit: int = 10) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM cs_summaries WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit))
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, r)) for r in cur.fetchall()]

    def get_stats(self) -> dict:
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) FROM cs_memories").fetchone()[0]
            by_type = self._conn.execute(
                "SELECT type, COUNT(*) as c FROM cs_memories "
                "GROUP BY type ORDER BY c DESC").fetchall()
            sessions = self._conn.execute(
                "SELECT COUNT(DISTINCT session_id) FROM cs_memories").fetchone()[0]
            summaries = self._conn.execute(
                "SELECT COUNT(*) FROM cs_summaries").fetchone()[0]
        return {
            "total_memories": total,
            "by_type": dict(by_type),
            "sessions": sessions,
            "summaries": summaries,
        }

    def close(self):
        self._conn.close()

    def _touch(self, memory_id: str):
        now = datetime.utcnow().isoformat() + "Z"
        try:
            with self._lock:
                self._conn.execute(
                    "UPDATE cs_memories SET last_accessed=?, access_count=access_count+1 "
                    "WHERE id=?", (now, memory_id))
                self._conn.commit()
        except Exception:
            pass

    def _trim(self, session_id: str):
        with self._lock:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM cs_memories WHERE session_id=?",
                (session_id,)).fetchone()[0]
            if count > MAX_MEMORY_ITEMS:
                self._conn.execute(
                    """DELETE FROM cs_memories WHERE id IN (
                        SELECT id FROM cs_memories WHERE session_id=?
                        ORDER BY importance ASC, last_accessed ASC
                        LIMIT ?
                    )""", (session_id, count - MAX_MEMORY_ITEMS))
                self._conn.commit()

    @staticmethod
    def _row_to_memory(row) -> dict:
        return {
            "id": row[0], "session_id": row[1], "type": row[2],
            "content": row[3],
            "tags": json.loads(row[4]) if isinstance(row[4], str) else row[4],
            "importance": row[5], "context": row[6],
            "created_at": row[7], "last_accessed": row[8],
            "access_count": row[9],
        }
