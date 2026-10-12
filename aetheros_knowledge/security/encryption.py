"""Knowledge security — encryption, permissions, version history."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime
from typing import Any, Optional

from aetheros_knowledge.store import KnowledgeStore

logger = logging.getLogger(__name__)


class KnowledgeSecurity:
    def __init__(self, store: KnowledgeStore):
        self.store = store
        self._master_key: Optional[bytes] = None

    def set_master_key(self, key: bytes):
        self._master_key = key

    # --- Permissions ---
    def set_permission(self, resource_type: str, resource_id: str,
                        user_id: str, permission: str):
        now = datetime.utcnow().isoformat() + "Z"
        pid = str(uuid.uuid4())
        with self.store._lock:
            self.store._conn.execute(
                "INSERT OR REPLACE INTO permissions "
                "(id, resource_type, resource_id, user_id, permission, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (pid, resource_type, resource_id, user_id, permission, now))
            self.store._conn.commit()

    def check_permission(self, resource_type: str, resource_id: str,
                          user_id: str, required: str) -> bool:
        cur = self.store._conn.execute(
            "SELECT permission FROM permissions WHERE resource_type=? "
            "AND resource_id=? AND user_id=?",
            (resource_type, resource_id, user_id))
        for row in cur.fetchall():
            if row[0] == "*" or row[0] == required:
                return True
        return False

    def revoke_permission(self, resource_type: str, resource_id: str,
                           user_id: str):
        with self.store._lock:
            self.store._conn.execute(
                "DELETE FROM permissions WHERE resource_type=? "
                "AND resource_id=? AND user_id=?",
                (resource_type, resource_id, user_id))
            self.store._conn.commit()

    def get_permissions(self, resource_type: str = None,
                         resource_id: str = None) -> list[dict]:
        conditions = []
        params = []
        if resource_type:
            conditions.append("resource_type=?")
            params.append(resource_type)
        if resource_id:
            conditions.append("resource_id=?")
            params.append(resource_id)
        where = " AND ".join(conditions) if conditions else "1=1"
        cur = self.store._conn.execute(
            f"SELECT * FROM permissions WHERE {where} ORDER BY created_at DESC")
        columns = [d[0] for d in cur.description]
        return [dict(zip(columns, r)) for r in cur.fetchall()]

    # --- Encryption ---
    def encrypt_value(self, value: str) -> str:
        if not self._master_key:
            return value
        try:
            from cryptography.fernet import Fernet
            import base64
            key = base64.urlsafe_b64encode(self._master_key[:32].ljust(32, b'\0'))
            f = Fernet(key)
            return f.encrypt(value.encode()).decode()
        except ImportError:
            logger.warning("cryptography not installed, storing unencrypted")
            return value

    def decrypt_value(self, encrypted: str) -> str:
        if not self._master_key:
            return encrypted
        try:
            from cryptography.fernet import Fernet
            import base64
            key = base64.urlsafe_b64encode(self._master_key[:32].ljust(32, b'\0'))
            f = Fernet(key)
            return f.decrypt(encrypted.encode()).decode()
        except Exception:
            return encrypted

    # --- Safe Delete ---
    def safe_delete_document(self, did: str):
        doc = self.store.get_document(did)
        if doc:
            doc.metadata["deleted_at"] = datetime.utcnow().isoformat() + "Z"
            doc.metadata["original_collection"] = doc.collection_id
            doc.collection_id = "trash"
            doc.status = "deleted"
            self.store.save_document(doc)
            logger.info("Safe deleted document: %s", did)

    def restore_from_trash(self, did: str) -> bool:
        doc = self.store.get_document(did)
        if doc and doc.collection_id == "trash":
            original = doc.metadata.get("original_collection", "documents")
            doc.collection_id = original
            doc.status = "pending"
            self.store.save_document(doc)
            self.store.update_collection_stats(original)
            self.store.update_collection_stats("trash")
            return True
        return False

    def empty_trash(self) -> int:
        docs = self.store.list_documents(collection_id="trash")
        for d in docs:
            self.store.delete_document(d.id)
        self.store.update_collection_stats("trash")
        return len(docs)

    # --- Version History ---
    def save_version(self, document_id: str, content: str,
                      user_id: str = "") -> str:
        vid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
        with self.store._lock:
            self.store._conn.execute("""
                CREATE TABLE IF NOT EXISTS doc_versions (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
                    content TEXT NOT NULL, checksum TEXT,
                    user_id TEXT DEFAULT '', created_at TEXT NOT NULL
                )""")
            self.store._conn.execute(
                "INSERT INTO doc_versions (id, document_id, content, checksum, user_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (vid, document_id, content, checksum, user_id, now))
            self.store._conn.commit()
        return vid

    def get_versions(self, document_id: str) -> list[dict]:
        with self.store._lock:
            self.store._conn.execute("""
                CREATE TABLE IF NOT EXISTS doc_versions (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
                    content TEXT NOT NULL, checksum TEXT,
                    user_id TEXT DEFAULT '', created_at TEXT NOT NULL
                )""")
            cur = self.store._conn.execute(
                "SELECT * FROM doc_versions WHERE document_id=? ORDER BY created_at DESC",
                (document_id,))
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, r)) for r in cur.fetchall()]

    def get_version_count(self) -> int:
        try:
            return self.store._conn.execute(
                "SELECT COUNT(*) FROM doc_versions").fetchone()[0]
        except Exception:
            return 0
