"""SQLite persistence for the AetherOS Hub registry — installed items, configs, backups."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any, Optional

from aetheros_constants import get_aetheros_home


class HubStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(get_aetheros_home() / "hub" / "registry.db")
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
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_db(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS installed_items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                version TEXT NOT NULL,
                description TEXT DEFAULT '',
                author TEXT DEFAULT '',
                license TEXT DEFAULT 'MIT',
                homepage TEXT DEFAULT '',
                github TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                permissions TEXT DEFAULT '[]',
                dependencies TEXT DEFAULT '[]',
                manifest TEXT DEFAULT '{}',
                config TEXT DEFAULT '{}',
                checksum TEXT DEFAULT '',
                signature TEXT DEFAULT '',
                install_path TEXT DEFAULT '',
                enabled INTEGER DEFAULT 1,
                compatible INTEGER DEFAULT 1,
                installed_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                size_bytes INTEGER DEFAULT 0,
                icon_url TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS hub_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS backup_records (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                path TEXT NOT NULL,
                size_bytes INTEGER DEFAULT 0,
                items_count INTEGER DEFAULT 0,
                manifest TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS install_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                item_id TEXT NOT NULL,
                action TEXT NOT NULL,
                version TEXT DEFAULT '',
                status TEXT DEFAULT 'success',
                message TEXT DEFAULT '',
                details TEXT DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_items_category ON installed_items(category);
            CREATE INDEX IF NOT EXISTS idx_items_enabled ON installed_items(enabled);
            CREATE INDEX IF NOT EXISTS idx_logs_item ON install_logs(item_id);
        """)
        self._conn.commit()

    def install_item(self, item_id: str, name: str, category: str, version: str,
                     **kwargs) -> bool:
        now = datetime.utcnow().isoformat() + "Z"
        existing = self._conn.execute(
            "SELECT version FROM installed_items WHERE id=?", (item_id,)).fetchone()
        if existing:
            self._conn.execute("""
                UPDATE installed_items SET version=?, name=?, description=?,
                  author=?, license=?, homepage=?, github=?, tags=?,
                  permissions=?, dependencies=?, manifest=?, checksum=?,
                  signature=?, install_path=?, enabled=1, compatible=1,
                  updated_at=?, size_bytes=?, icon_url=?
                WHERE id=?
            """, (
                version, name, kwargs.get("description", ""),
                kwargs.get("author", ""), kwargs.get("license", "MIT"),
                kwargs.get("homepage", ""), kwargs.get("github", ""),
                json.dumps(kwargs.get("tags", [])),
                json.dumps(kwargs.get("permissions", [])),
                json.dumps(kwargs.get("dependencies", [])),
                json.dumps(kwargs.get("manifest", {})),
                kwargs.get("checksum", ""), kwargs.get("signature", ""),
                kwargs.get("install_path", ""), now,
                kwargs.get("size_bytes", 0), kwargs.get("icon_url", ""),
                item_id,
            ))
        else:
            self._conn.execute("""
                INSERT INTO installed_items
                    (id, name, category, version, description, author, license,
                     homepage, github, tags, permissions, dependencies,
                     manifest, checksum, signature, install_path, enabled,
                     compatible, installed_at, updated_at, size_bytes, icon_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        1, 1, ?, ?, ?, ?)
            """, (
                item_id, name, category, version,
                kwargs.get("description", ""), kwargs.get("author", ""),
                kwargs.get("license", "MIT"), kwargs.get("homepage", ""),
                kwargs.get("github", ""), json.dumps(kwargs.get("tags", [])),
                json.dumps(kwargs.get("permissions", [])),
                json.dumps(kwargs.get("dependencies", [])),
                json.dumps(kwargs.get("manifest", {})),
                kwargs.get("checksum", ""), kwargs.get("signature", ""),
                kwargs.get("install_path", ""), now, now,
                kwargs.get("size_bytes", 0), kwargs.get("icon_url", ""),
            ))
        self._conn.commit()
        self._log_install(item_id, "install", version)
        return True

    def remove_item(self, item_id: str) -> bool:
        self._conn.execute("DELETE FROM installed_items WHERE id=?", (item_id,))
        self._conn.commit()
        self._log_install(item_id, "remove", "")
        return True

    def set_enabled(self, item_id: str, enabled: bool) -> bool:
        self._conn.execute("UPDATE installed_items SET enabled=? WHERE id=?",
                           (1 if enabled else 0, item_id))
        self._conn.commit()
        return True

    def get_installed(self, category: Optional[str] = None) -> list[dict]:
        if category:
            rows = self._conn.execute(
                "SELECT * FROM installed_items WHERE category=? ORDER BY name",
                (category,)).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM installed_items ORDER BY category, name").fetchall()
        return [dict(r) for r in rows]

    def get_installed_item(self, item_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM installed_items WHERE id=?", (item_id,)).fetchone()
        return dict(row) if row else None

    def is_installed(self, item_id: str) -> bool:
        return self._conn.execute(
            "SELECT 1 FROM installed_items WHERE id=?", (item_id,)).fetchone() is not None

    def get_updates_available(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM installed_items WHERE compatible=1").fetchall()
        return [dict(r) for r in rows]

    def get_broken(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM installed_items WHERE compatible=0").fetchall()
        return [dict(r) for r in rows]

    def get_disabled(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM installed_items WHERE enabled=0").fetchall()
        return [dict(r) for r in rows]

    # Settings
    def set_setting(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO hub_settings (key, value) VALUES (?, ?)",
            (key, value))
        self._conn.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        row = self._conn.execute(
            "SELECT value FROM hub_settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    # Backup records
    def save_backup(self, backup_id: str, name: str, path: str,
                    size_bytes: int, items_count: int,
                    manifest: dict) -> None:
        self._conn.execute("""
            INSERT OR REPLACE INTO backup_records
                (id, name, created_at, path, size_bytes, items_count, manifest)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (backup_id, name, datetime.utcnow().isoformat() + "Z",
              path, size_bytes, items_count, json.dumps(manifest)))
        self._conn.commit()

    def list_backups(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM backup_records ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def delete_backup(self, backup_id: str) -> bool:
        self._conn.execute("DELETE FROM backup_records WHERE id=?", (backup_id,))
        self._conn.commit()
        return True

    # Logs
    def _log_install(self, item_id: str, action: str, version: str,
                     status: str = "success", message: str = "") -> None:
        self._conn.execute("""
            INSERT INTO install_logs (timestamp, item_id, action, version, status, message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.utcnow().isoformat() + "Z", item_id, action, version, status, message))
        self._conn.commit()

    def get_logs(self, item_id: Optional[str] = None, limit: int = 100) -> list[dict]:
        if item_id:
            rows = self._conn.execute(
                "SELECT * FROM install_logs WHERE item_id=? ORDER BY timestamp DESC LIMIT ?",
                (item_id, limit)).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM install_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        installed = self._conn.execute(
            "SELECT category, COUNT(*) as count FROM installed_items GROUP BY category").fetchall()
        return {
            "total_installed": sum(r["count"] for r in installed),
            "by_category": {r["category"]: r["count"] for r in installed},
            "enabled": self._conn.execute(
                "SELECT COUNT(*) FROM installed_items WHERE enabled=1").fetchone()[0],
            "disabled": self._conn.execute(
                "SELECT COUNT(*) FROM installed_items WHERE enabled=0").fetchone()[0],
            "broken": self._conn.execute(
                "SELECT COUNT(*) FROM installed_items WHERE compatible=0").fetchone()[0],
        }

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
