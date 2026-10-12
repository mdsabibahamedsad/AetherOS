"""SQLite persistence for the Connect Hub — connections, credentials, activity logs."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any, Optional

from aetheros_constants import get_aetheros_home


class ConnectStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(get_aetheros_home() / "connect" / "connections.db")
        import os
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
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS connections (
                id TEXT PRIMARY KEY,
                service_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'disconnected',
                label TEXT DEFAULT '',
                config TEXT DEFAULT '{}',
                permissions_granted TEXT DEFAULT '[]',
                permissions_missing TEXT DEFAULT '[]',
                connected_at TEXT,
                last_health_check TEXT,
                last_sync TEXT,
                sync_mode TEXT DEFAULT 'manual',
                sync_interval INTEGER DEFAULT 3600,
                error_message TEXT DEFAULT '',
                version TEXT DEFAULT '1.0.0',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS credentials (
                service_id TEXT NOT NULL,
                connection_id TEXT NOT NULL PRIMARY KEY,
                encrypted_data TEXT DEFAULT '',
                key_hint TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id TEXT PRIMARY KEY,
                connection_id TEXT NOT NULL,
                service_id TEXT NOT NULL,
                service_name TEXT DEFAULT '',
                action TEXT NOT NULL,
                status TEXT DEFAULT 'success',
                message TEXT DEFAULT '',
                timestamp TEXT NOT NULL,
                details TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS health_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_id TEXT NOT NULL,
                service_id TEXT NOT NULL,
                status TEXT NOT NULL,
                api_available INTEGER DEFAULT 0,
                auth_valid INTEGER DEFAULT 0,
                rate_limited INTEGER DEFAULT 0,
                latency_ms REAL DEFAULT 0.0,
                error_count INTEGER DEFAULT 0,
                last_error TEXT DEFAULT '',
                checked_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS connect_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_conn_service ON connections(service_id);
            CREATE INDEX IF NOT EXISTS idx_conn_status ON connections(status);
            CREATE INDEX IF NOT EXISTS idx_conn_category ON connections(category);
            CREATE INDEX IF NOT EXISTS idx_activity_conn ON activity_log(connection_id);
            CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_health_conn ON health_checks(connection_id);
        """)
        self._conn.commit()

    def save_connection(self, conn: 'ServiceConnection') -> bool:
        import json
        now = datetime.utcnow().isoformat() + "Z"
        existing = self._conn.execute(
            "SELECT id FROM connections WHERE id=?", (conn.id,)).fetchone()
        if existing:
            self._conn.execute("""
                UPDATE connections SET service_id=?, service_name=?, category=?,
                  status=?, label=?, config=?, permissions_granted=?,
                  permissions_missing=?, connected_at=?, last_health_check=?,
                  last_sync=?, sync_mode=?, sync_interval=?, error_message=?,
                  version=?, metadata=?, updated_at=?
                WHERE id=?
            """, (
                conn.service_id, conn.service_name, conn.category.value,
                conn.status.value, conn.label, json.dumps(conn.config),
                json.dumps(conn.permissions_granted),
                json.dumps(conn.permissions_missing),
                conn.connected_at, conn.last_health_check, conn.last_sync,
                conn.sync_mode.value, conn.sync_interval, conn.error_message,
                conn.version, json.dumps(conn.metadata), now, conn.id,
            ))
        else:
            self._conn.execute("""
                INSERT INTO connections
                    (id, service_id, service_name, category, status, label,
                     config, permissions_granted, permissions_missing,
                     connected_at, last_health_check, last_sync, sync_mode,
                     sync_interval, error_message, version, metadata,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conn.id, conn.service_id, conn.service_name, conn.category.value,
                conn.status.value, conn.label, json.dumps(conn.config),
                json.dumps(conn.permissions_granted),
                json.dumps(conn.permissions_missing),
                conn.connected_at, conn.last_health_check, conn.last_sync,
                conn.sync_mode.value, conn.sync_interval, conn.error_message,
                conn.version, json.dumps(conn.metadata), now, now,
            ))
        self._conn.commit()
        return True

    def get_connection(self, connection_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM connections WHERE id=?", (connection_id,)).fetchone()
        return dict(row) if row else None

    def list_connections(self, category: str = None,
                          status: str = None) -> list[dict]:
        parts = ["SELECT * FROM connections WHERE 1=1"]
        params = []
        if category:
            parts.append("AND category=?")
            params.append(category)
        if status:
            parts.append("AND status=?")
            params.append(status)
        parts.append("ORDER BY category, service_name")
        rows = self._conn.execute(" ".join(parts), params).fetchall()
        return [dict(r) for r in rows]

    def delete_connection(self, connection_id: str) -> bool:
        self._conn.execute("DELETE FROM credentials WHERE connection_id=?",
                           (connection_id,))
        self._conn.execute("DELETE FROM activity_log WHERE connection_id=?",
                           (connection_id,))
        self._conn.execute("DELETE FROM health_checks WHERE connection_id=?",
                           (connection_id,))
        self._conn.execute("DELETE FROM connections WHERE id=?",
                           (connection_id,))
        self._conn.commit()
        return True

    def set_status(self, connection_id: str, status: str,
                    error_message: str = "") -> None:
        self._conn.execute("""
            UPDATE connections SET status=?, error_message=?, updated_at=?
            WHERE id=?
        """, (status, error_message, datetime.utcnow().isoformat() + "Z",
              connection_id))
        self._conn.commit()

    def save_credential(self, service_id: str, connection_id: str,
                         encrypted_data: str, key_hint: str = "",
                         expires_at: str = "") -> bool:
        now = datetime.utcnow().isoformat() + "Z"
        self._conn.execute("""
            INSERT OR REPLACE INTO credentials
                (service_id, connection_id, encrypted_data, key_hint,
                 created_at, updated_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (service_id, connection_id, encrypted_data, key_hint,
              now, now, expires_at))
        self._conn.commit()
        return True

    def get_credential(self, connection_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM credentials WHERE connection_id=?",
            (connection_id,)).fetchone()
        return dict(row) if row else None

    def delete_credential(self, connection_id: str) -> bool:
        self._conn.execute("DELETE FROM credentials WHERE connection_id=?",
                           (connection_id,))
        self._conn.commit()
        return True

    def log_activity(self, entry: 'ActivityEntry') -> None:
        self._conn.execute("""
            INSERT INTO activity_log
                (id, connection_id, service_id, service_name, action,
                 status, message, timestamp, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (entry.id, entry.connection_id, entry.service_id,
              entry.service_name, entry.action, entry.status,
              entry.message, entry.timestamp,
              json.dumps(entry.details)))
        self._conn.commit()

    def get_activity(self, connection_id: str = None,
                      limit: int = 100) -> list[dict]:
        if connection_id:
            rows = self._conn.execute("""
                SELECT * FROM activity_log WHERE connection_id=?
                ORDER BY timestamp DESC LIMIT ?
            """, (connection_id, limit)).fetchall()
        else:
            rows = self._conn.execute("""
                SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def save_health_check(self, result: 'HealthCheckResult') -> None:
        self._conn.execute("""
            INSERT INTO health_checks
                (connection_id, service_id, status, api_available,
                 auth_valid, rate_limited, latency_ms, error_count,
                 last_error, checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (result.connection_id, result.service_id, result.status.value,
              1 if result.api_available else 0,
              1 if result.auth_valid else 0,
              1 if result.rate_limited else 0,
              result.latency_ms, result.error_count, result.last_error,
              result.checked_at))
        self._conn.commit()

    def get_health_history(self, connection_id: str,
                            limit: int = 50) -> list[dict]:
        rows = self._conn.execute("""
            SELECT * FROM health_checks WHERE connection_id=?
            ORDER BY checked_at DESC LIMIT ?
        """, (connection_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_latest_health(self, connection_id: str) -> Optional[dict]:
        row = self._conn.execute("""
            SELECT * FROM health_checks WHERE connection_id=?
            ORDER BY checked_at DESC LIMIT 1
        """, (connection_id,)).fetchone()
        return dict(row) if row else None

    def set_setting(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO connect_settings (key, value) VALUES (?, ?)",
            (key, value))
        self._conn.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        row = self._conn.execute(
            "SELECT value FROM connect_settings WHERE key=?",
            (key,)).fetchone()
        return row["value"] if row else default

    def get_stats(self) -> dict:
        total = self._conn.execute(
            "SELECT COUNT(*) FROM connections").fetchone()[0]
        connected = self._conn.execute(
            "SELECT COUNT(*) FROM connections WHERE status='connected'").fetchone()[0]
        by_category = self._conn.execute("""
            SELECT category, COUNT(*) as count FROM connections
            GROUP BY category
        """).fetchall()
        return {
            "total": total,
            "connected": connected,
            "disconnected": total - connected,
            "by_category": {r["category"]: r["count"] for r in by_category},
        }
