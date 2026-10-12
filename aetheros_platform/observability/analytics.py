"""Analytics engine — usage tracking, aggregation, report generation."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsEvent:
    event_type: str
    category: str
    action: str
    label: str = ""
    value: float = 0.0
    user_id: str = ""
    session_id: str = ""
    properties: dict = field(default_factory=dict)
    timestamp: str = ""


class AnalyticsEngine:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    action TEXT NOT NULL,
                    label TEXT DEFAULT '',
                    value REAL DEFAULT 0.0,
                    user_id TEXT DEFAULT '',
                    session_id TEXT DEFAULT '',
                    properties TEXT DEFAULT '{}',
                    timestamp TEXT NOT NULL
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analytics_category
                ON analytics_events(category)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analytics_action
                ON analytics_events(action)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analytics_time
                ON analytics_events(timestamp)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analytics_type
                ON analytics_events(event_type)
            """)
            self._conn.commit()

    def track(self, event: AnalyticsEvent) -> int:
        ts = event.timestamp or datetime.utcnow().isoformat() + "Z"
        try:
            with self._lock:
                cur = self._conn.execute(
                    """INSERT INTO analytics_events
                       (event_type, category, action, label, value,
                        user_id, session_id, properties, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (event.event_type, event.category, event.action,
                     event.label, event.value, event.user_id,
                     event.session_id, json.dumps(event.properties), ts))
                self._conn.commit()
                return cur.lastrowid
        except Exception as e:
            logger.error("analytics track error: %s", e)
            return 0

    def track_event(self, category: str, action: str,
                     label: str = "", value: float = 0.0,
                     user_id: str = "",
                     properties: dict = None) -> int:
        return self.track(AnalyticsEvent(
            event_type="user_action", category=category, action=action,
            label=label, value=value, user_id=user_id,
            properties=properties or {},
        ))

    def count(self, category: str = None, action: str = None,
               since: str = None, until: str = None) -> int:
        conditions = []
        params = []
        if category:
            conditions.append("category=?")
            params.append(category)
        if action:
            conditions.append("action=?")
            params.append(action)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        if until:
            conditions.append("timestamp <= ?")
            params.append(until)
        where = " AND ".join(conditions) if conditions else "1=1"
        with self._lock:
            cur = self._conn.execute(
                f"SELECT COUNT(*) FROM analytics_events WHERE {where}", params)
            return cur.fetchone()[0]

    def get_events(self, category: str = None, action: str = None,
                    limit: int = 100, offset: int = 0) -> list[dict]:
        conditions = []
        params = []
        if category:
            conditions.append("category=?")
            params.append(category)
        if action:
            conditions.append("action=?")
            params.append(action)
        where = " AND ".join(conditions) if conditions else "1=1"
        with self._lock:
            cur = self._conn.execute(
                f"SELECT * FROM analytics_events WHERE {where} "
                f"ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [limit, offset])
            return [self._row_to_event(r) for r in cur.fetchall()]

    def get_category_summary(self, since: str = None) -> list[dict]:
        conditions = []
        params = []
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        where = " AND ".join(conditions) if conditions else "1=1"
        with self._lock:
            cur = self._conn.execute(
                f"SELECT category, COUNT(*) as count, "
                f"ROUND(AVG(value), 2) as avg_value "
                f"FROM analytics_events WHERE {where} "
                f"GROUP BY category ORDER BY count DESC",
                params)
            return [{"category": r[0], "count": r[1],
                      "avg_value": r[2]} for r in cur.fetchall()]

    def get_action_summary(self, category: str = None,
                            since: str = None) -> list[dict]:
        conditions = []
        params = []
        if category:
            conditions.append("category=?")
            params.append(category)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        where = " AND ".join(conditions) if conditions else "1=1"
        with self._lock:
            cur = self._conn.execute(
                f"SELECT category, action, COUNT(*) as count, "
                f"ROUND(AVG(value), 2) as avg_value "
                f"FROM analytics_events WHERE {where} "
                f"GROUP BY category, action ORDER BY count DESC",
                params)
            return [{"category": r[0], "action": r[1],
                      "count": r[2], "avg_value": r[3]} for r in cur.fetchall()]

    def get_top_labels(self, category: str, action: str = None,
                        limit: int = 10) -> list[dict]:
        conditions = ["category=?"]
        params = [category]
        if action:
            conditions.append("action=?")
            params.append(action)
        where = " AND ".join(conditions)
        with self._lock:
            cur = self._conn.execute(
                f"SELECT label, COUNT(*) as count "
                f"FROM analytics_events WHERE {where} "
                f"AND label != '' "
                f"GROUP BY label ORDER BY count DESC LIMIT ?",
                params + [limit])
            return [{"label": r[0], "count": r[1]} for r in cur.fetchall()]

    def get_timeline(self, category: str = None, action: str = None,
                      interval: str = "day",
                      since: str = None) -> list[dict]:
        import re
        date_format = {"day": "%Y-%m-%d", "hour": "%Y-%m-%d %H:00",
                       "week": "%Y-%W", "month": "%Y-%m"}.get(interval, "%Y-%m-%d")
        conditions = []
        params = []
        if category:
            conditions.append("category=?")
            params.append(category)
        if action:
            conditions.append("action=?")
            params.append(action)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        where = " AND ".join(conditions) if conditions else "1=1"
        with self._lock:
            cur = self._conn.execute(
                f"SELECT substr(timestamp, 1, 10) as period, "
                f"COUNT(*) as count FROM analytics_events "
                f"WHERE {where} GROUP BY period ORDER BY period",
                params)
            return [{"period": r[0], "count": r[1]} for r in cur.fetchall()]

    def get_user_stats(self, user_id: str) -> dict:
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) FROM analytics_events WHERE user_id=?",
                (user_id,)).fetchone()[0]
            by_category = self._conn.execute(
                "SELECT category, COUNT(*) FROM analytics_events "
                "WHERE user_id=? GROUP BY category ORDER BY COUNT(*) DESC",
                (user_id,)).fetchall()
            last_active = self._conn.execute(
                "SELECT MAX(timestamp) FROM analytics_events WHERE user_id=?",
                (user_id,)).fetchone()[0]
        return {
            "total_events": total,
            "by_category": dict(by_category),
            "last_active": last_active,
        }

    def get_overview(self) -> dict:
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) FROM analytics_events").fetchone()[0]
            unique_users = self._conn.execute(
                "SELECT COUNT(DISTINCT user_id) FROM analytics_events "
                "WHERE user_id != ''").fetchone()[0]
            categories = self._conn.execute(
                "SELECT category, COUNT(*) FROM analytics_events "
                "GROUP BY category ORDER BY COUNT(*) DESC").fetchall()
            today = datetime.utcnow().strftime("%Y-%m-%d")
            today_count = self._conn.execute(
                "SELECT COUNT(*) FROM analytics_events WHERE timestamp LIKE ?",
                (f"{today}%",)).fetchone()[0]
        return {
            "total_events": total,
            "unique_users": unique_users,
            "categories": dict(categories),
            "today_events": today_count,
        }

    def close(self):
        self._conn.close()

    @staticmethod
    def _row_to_event(row) -> dict:
        return {
            "id": row[0], "event_type": row[1], "category": row[2],
            "action": row[3], "label": row[4], "value": row[5],
            "user_id": row[6], "session_id": row[7],
            "properties": json.loads(row[8]) if isinstance(row[8], str) else row[8],
            "timestamp": row[9],
        }
