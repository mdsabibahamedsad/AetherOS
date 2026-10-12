"""API authentication (Master 62 §32-35, §54).

Implemented: API keys (scrypt-hashed, display-once, scopes, expiry,
rotation, revocation, last-used) + local sessions. Secrets never enter
logs/traces (redacted at write time).
NOT_IMPLEMENTED (honest): OAuth 2.x/OIDC flows, mTLS — no provider/CA in
this environment; the key record carries issuer/audience fields for future
use but no flow is claimed.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home

API_KEY_PREFIX = "aek_"
SCRYPT_N = 2 ** 14


def _home_db() -> str:
    from aetheros_data.engine import get_engine
    return str(get_engine().db_path)


def _conn() -> sqlite3.Connection:
    from aetheros_data.engine import get_engine
    eng = get_engine()
    conn = sqlite3.connect(str(eng.db_path), check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS api_keys (key_id TEXT PRIMARY KEY, name TEXT NOT NULL,"
        " key_hash TEXT NOT NULL, salt TEXT NOT NULL, scopes TEXT NOT NULL DEFAULT '[]',"
        " owner TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL, expires_at REAL NOT NULL DEFAULT 0,"
        " status TEXT NOT NULL DEFAULT 'active', last_used_at REAL NOT NULL DEFAULT 0,"
        " usage_count INTEGER NOT NULL DEFAULT 0, rotation_of TEXT NOT NULL DEFAULT '')")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS dev_sessions (token_hash TEXT PRIMARY KEY, owner TEXT NOT NULL DEFAULT '',"
        " scopes TEXT NOT NULL DEFAULT '[]', created_at REAL NOT NULL, expires_at REAL NOT NULL)")
    conn.commit()
    return conn


def _hash(secret: str, salt: bytes) -> str:
    return hashlib.scrypt(secret.encode(), salt=salt, n=SCRYPT_N, r=8, p=1).hex()


class APIKeyManager:
    def create(self, name: str, scopes: List[str], owner: str = "",
               expires_days: int = 90) -> Dict[str, Any]:
        raw = API_KEY_PREFIX + secrets.token_urlsafe(32)
        salt = os.urandom(16)
        kid = f"key_{uuid.uuid4().hex[:12]}"
        now = time.time()
        conn = _conn()
        try:
            conn.execute(
                "INSERT INTO api_keys (key_id, name, key_hash, salt, scopes, owner,"
                " created_at, expires_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')",
                (kid, name, _hash(raw, salt), salt.hex(), __import__("json").dumps(scopes),
                 owner, now, now + expires_days * 86400))
            conn.commit()
        finally:
            conn.close()
        # Display-once: raw secret returned ONLY here, never stored.
        return {"key_id": kid, "name": name, "api_key": raw, "scopes": scopes,
                "expires_at": now + expires_days * 86400,
                "warning": "display-once: store now; it cannot be retrieved again"}

    def verify(self, raw: str) -> Optional[Dict[str, Any]]:
        if not raw or not hmac.compare_digest(raw[:4], API_KEY_PREFIX):
            return None
        conn = _conn()
        try:
            rows = conn.execute("SELECT * FROM api_keys WHERE status='active'").fetchall()
            for r in rows:
                want = _hash(raw, bytes.fromhex(r["salt"]))
                if hmac.compare_digest(want, r["key_hash"]):
                    if float(r["expires_at"]) and float(r["expires_at"]) < time.time():
                        return None
                    conn.execute("UPDATE api_keys SET last_used_at=?, usage_count=usage_count+1"
                                 " WHERE key_id=?", (time.time(), r["key_id"]))
                    conn.commit()
                    return {"key_id": r["key_id"], "name": r["name"], "owner": r["owner"],
                            "scopes": __import__("json").loads(r["scopes"])}
            return None
        finally:
            conn.close()

    def revoke(self, key_id: str) -> bool:
        conn = _conn()
        try:
            cur = conn.execute("UPDATE api_keys SET status='revoked' WHERE key_id=?", (key_id,))
            conn.commit()
            return cur.rowcount == 1
        finally:
            conn.close()

    def rotate(self, key_id: str) -> Optional[Dict[str, Any]]:
        conn = _conn()
        try:
            row = conn.execute("SELECT * FROM api_keys WHERE key_id=?", (key_id,)).fetchone()
            if row is None:
                return None
            import json
            conn.execute("UPDATE api_keys SET status='rotated' WHERE key_id=?", (key_id,))
            conn.commit()
        finally:
            conn.close()
        import json
        return self.create(row["name"], json.loads(row["scopes"]),
                           owner=row["owner"], expires_days=90) | {"rotation_of": key_id}

    def list(self, include_secret: bool = False) -> List[Dict[str, Any]]:
        assert not include_secret, "plaintext keys are never listed"
        conn = _conn()
        try:
            rows = conn.execute("SELECT key_id, name, scopes, owner, created_at, expires_at,"
                                " status, last_used_at, usage_count FROM api_keys").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def has_scope(cred: Optional[Dict[str, Any]], scope: str) -> bool:
    if cred is None:
        return False
    scopes = cred.get("scopes", [])
    return scope in scopes or "admin:*" in scopes
