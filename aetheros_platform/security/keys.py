"""Key management — encryption key generation, storage, rotation."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

KEY_ALGORITHMS = ["aes-256-gcm", "aes-256-cbc", "chacha20-poly1305"]
KEY_SIZES = {"aes-256-gcm": 32, "aes-256-cbc": 32, "chacha20-poly1305": 32}


@dataclass
class EncryptionKey:
    id: str
    algorithm: str
    created_at: str
    expires_at: Optional[str]
    is_active: bool
    purpose: str
    key_hash: str


class KeyManager:
    def __init__(self, db_path: str = ":memory:",
                 master_key: bytes = None):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._master_key = master_key or secrets.token_bytes(32)
        self._init_db()

    def _init_db(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS encryption_keys (
                    id TEXT PRIMARY KEY,
                    algorithm TEXT NOT NULL DEFAULT 'aes-256-gcm',
                    key_data BLOB NOT NULL,
                    key_hash TEXT NOT NULL,
                    purpose TEXT DEFAULT 'general',
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS key_rotation_log (
                    id TEXT PRIMARY KEY,
                    old_key_id TEXT,
                    new_key_id TEXT,
                    reason TEXT,
                    rotated_at TEXT NOT NULL
                )
            """)
            self._conn.commit()

    def generate_key(self, algorithm: str = "aes-256-gcm",
                      purpose: str = "general",
                      expires_in_days: int = None) -> EncryptionKey:
        import uuid
        kid = str(uuid.uuid4())
        key_size = KEY_SIZES.get(algorithm, 32)
        raw_key = secrets.token_bytes(key_size)
        encrypted = self._encrypt_master(raw_key)
        key_hash = hashlib.sha256(raw_key).hexdigest()
        now = datetime.utcnow().isoformat() + "Z"
        expires = None
        if expires_in_days:
            from datetime import timedelta
            expires = (datetime.utcnow() + timedelta(days=expires_in_days)
                       ).isoformat() + "Z"
        try:
            with self._lock:
                self._conn.execute(
                    "INSERT INTO encryption_keys "
                    "(id, algorithm, key_data, key_hash, purpose, created_at, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (kid, algorithm, encrypted, key_hash, purpose, now, expires))
                self._conn.commit()
            logger.info("Generated %s key %s for %s", algorithm, kid, purpose)
        except Exception as e:
            logger.error("generate_key error: %s", e)
        return self.get_key(kid)

    def get_key(self, key_id: str) -> Optional[EncryptionKey]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM encryption_keys WHERE id=?", (key_id,))
            return self._row_to_key(cur.fetchone())

    def get_active_key(self, purpose: str = "general") -> Optional[EncryptionKey]:
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM encryption_keys WHERE purpose=? AND is_active=1 "
                "AND (expires_at IS NULL OR expires_at > ?) "
                "ORDER BY created_at DESC LIMIT 1",
                (purpose, now))
            return self._row_to_key(cur.fetchone())

    def get_raw_key(self, key_id: str) -> Optional[bytes]:
        key = self.get_key(key_id)
        if not key:
            return None
        with self._lock:
            cur = self._conn.execute(
                "SELECT key_data FROM encryption_keys WHERE id=?", (key_id,))
            row = cur.fetchone()
        if row:
            return self._decrypt_master(row[0])
        return None

    def list_keys(self, purpose: str = None) -> list[dict]:
        with self._lock:
            if purpose:
                cur = self._conn.execute(
                    "SELECT * FROM encryption_keys WHERE purpose=? ORDER BY created_at DESC",
                    (purpose,))
            else:
                cur = self._conn.execute(
                    "SELECT * FROM encryption_keys ORDER BY created_at DESC")
            return [self._key_to_dict(r) for r in cur.fetchall()]

    def revoke_key(self, key_id: str) -> bool:
        try:
            with self._lock:
                self._conn.execute(
                    "UPDATE encryption_keys SET is_active=0 WHERE id=?",
                    (key_id,))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("revoke_key error: %s", e)
            return False

    def rotate_keys(self, purpose: str = "general",
                     reason: str = "scheduled") -> Optional[EncryptionKey]:
        old_key = self.get_active_key(purpose)
        new_key = self.generate_key(purpose=purpose)
        if not new_key:
            return None
        if old_key:
            self.revoke_key(old_key.id)
            import uuid
            from datetime import datetime
            log_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat() + "Z"
            try:
                with self._lock:
                    self._conn.execute(
                        "INSERT INTO key_rotation_log "
                        "(id, old_key_id, new_key_id, reason, rotated_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (log_id, old_key.id, new_key.id, reason, now))
                    self._conn.commit()
            except Exception as e:
                logger.error("rotate_key log error: %s", e)
        logger.info("Rotated keys for %s: %s -> %s",
                     purpose, old_key.id if old_key else "none", new_key.id)
        return new_key

    def get_rotation_history(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM key_rotation_log ORDER BY rotated_at DESC LIMIT 50")
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, r)) for r in cur.fetchall()]

    def get_stats(self) -> dict:
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) FROM encryption_keys").fetchone()[0]
            active = self._conn.execute(
                "SELECT COUNT(*) FROM encryption_keys WHERE is_active=1").fetchone()[0]
            by_purpose = self._conn.execute(
                "SELECT purpose, COUNT(*) FROM encryption_keys "
                "GROUP BY purpose").fetchall()
            rotations = self._conn.execute(
                "SELECT COUNT(*) FROM key_rotation_log").fetchone()[0]
        return {
            "total_keys": total,
            "active": active,
            "by_purpose": dict(by_purpose),
            "rotations": rotations,
        }

    def close(self):
        self._conn.close()

    def _encrypt_master(self, data: bytes) -> bytes:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(self._master_key)
        f = Fernet(key)
        return f.encrypt(data)

    def _decrypt_master(self, data: bytes) -> bytes:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(self._master_key)
        f = Fernet(key)
        return f.decrypt(data)

    @staticmethod
    def _row_to_key(row) -> Optional[EncryptionKey]:
        if not row:
            return None
        return EncryptionKey(
            id=row[0], algorithm=row[1],
            created_at=row[4], expires_at=row[5],
            is_active=bool(row[6]), purpose=row[3],
            key_hash=row[2],
        )

    @staticmethod
    def _key_to_dict(row) -> dict:
        if not row:
            return {}
        return {
            "id": row[0], "algorithm": row[1],
            "key_hash": row[2], "purpose": row[3],
            "created_at": row[4], "expires_at": row[5],
            "is_active": bool(row[6]),
        }
