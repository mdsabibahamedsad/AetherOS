"""Authentication manager — local auth, OAuth2 providers, SSO."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import sqlite3
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AuthProvider(ABC):
    name: str
    display_name: str
    enabled: bool = True

    @abstractmethod
    def authenticate(self, credentials: dict) -> Optional[dict]:
        ...

    @abstractmethod
    def get_user_info(self, token: str) -> Optional[dict]:
        ...


@dataclass
class OAuth2Provider(AuthProvider):
    client_id: str = ""
    client_secret: str = ""
    authorize_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""
    scopes: list[str] = field(default_factory=lambda: ["openid", "profile", "email"])
    redirect_uri: str = "http://localhost:8756/auth/callback"

    def authenticate(self, credentials: dict) -> Optional[dict]:
        code = credentials.get("code", "")
        if not code:
            return None
        return {"provider": self.name, "code": code, "status": "pending"}

    def get_user_info(self, token: str) -> Optional[dict]:
        return {"provider": self.name, "sub": "unknown", "name": self.display_name}


class AuthManager:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._providers: dict[str, AuthProvider] = {}
        self._init_db()
        self._register_default()

    def _init_db(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS auth_users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    email TEXT,
                    display_name TEXT,
                    provider TEXT DEFAULT 'local',
                    provider_id TEXT,
                    roles TEXT DEFAULT '["user"]',
                    mfa_enabled INTEGER DEFAULT 0,
                    mfa_secret TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_login TEXT
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_auth_username
                ON auth_users(username)
            """)
            self._conn.commit()

    def _register_default(self):
        self.register_provider(LocalAuthProvider())
        self.register_provider(OAuth2Provider(
            name="google", display_name="Google"))
        self.register_provider(OAuth2Provider(
            name="github", display_name="GitHub"))

    def register_provider(self, provider: AuthProvider):
        self._providers[provider.name] = provider

    def get_provider(self, name: str) -> Optional[AuthProvider]:
        return self._providers.get(name)

    def list_providers(self) -> list[dict]:
        return [{"name": p.name, "display": p.display_name,
                 "enabled": p.enabled} for p in self._providers.values()]

    def register_user(self, username: str, password: str = None,
                       email: str = None, display_name: str = None,
                       provider: str = "local",
                       provider_id: str = None) -> Optional[dict]:
        import uuid
        uid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        pw_hash = self._hash_password(password) if password else None
        display = display_name or username
        try:
            with self._lock:
                self._conn.execute(
                    """INSERT INTO auth_users
                       (id, username, password_hash, email, display_name,
                        provider, provider_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (uid, username, pw_hash, email, display,
                     provider, provider_id, now))
                self._conn.commit()
            return self.get_user(uid)
        except sqlite3.IntegrityError:
            logger.warning("User already exists: %s", username)
            return None

    def authenticate(self, username: str, password: str = None,
                      provider: str = "local",
                      credentials: dict = None) -> Optional[dict]:
        if provider != "local":
            prov = self._providers.get(provider)
            if not prov:
                return None
            info = prov.authenticate(credentials or {})
            if not info:
                return None
            uid = info.get("sub", "")
            user = self.get_user_by_provider(provider, uid)
            if not user:
                user = self.register_user(
                    username=f"{provider}_{uid}", provider=provider,
                    provider_id=uid,
                    display_name=info.get("name", uid),
                    email=info.get("email", ""))
            if user:
                self._update_login(user["id"])
            return user
        user = self.get_user_by_username(username)
        if not user or not user.get("enabled"):
            return None
        pw_hash = user.get("password_hash", "")
        if not pw_hash or not self._verify_password(password or "", pw_hash):
            return None
        self._update_login(user["id"])
        return user

    def get_user(self, user_id: str) -> Optional[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM auth_users WHERE id=?", (user_id,))
            return self._row_to_user(cur.fetchone())

    def get_user_by_username(self, username: str) -> Optional[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM auth_users WHERE username=?", (username,))
            return self._row_to_user(cur.fetchone())

    def get_user_by_provider(self, provider: str,
                              provider_id: str) -> Optional[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM auth_users WHERE provider=? AND provider_id=?",
                (provider, provider_id))
            return self._row_to_user(cur.fetchone())

    def list_users(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM auth_users ORDER BY created_at DESC")
            return [self._row_to_user(r) for r in cur.fetchall()]

    def update_user(self, user_id: str, updates: dict) -> bool:
        allowed = {"email", "display_name", "roles", "enabled"}
        now = datetime.utcnow().isoformat() + "Z"
        sets = []
        params = []
        for k, v in updates.items():
            if k in allowed:
                if k == "roles" and isinstance(v, list):
                    v = json.dumps(v)
                sets.append(f"{k}=?")
                params.append(v)
        if not sets:
            return False
        params.append(user_id)
        try:
            with self._lock:
                self._conn.execute(
                    f"UPDATE auth_users SET {', '.join(sets)} WHERE id=?",
                    params)
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("update_user error: %s", e)
            return False

    def delete_user(self, user_id: str) -> bool:
        try:
            with self._lock:
                self._conn.execute(
                    "DELETE FROM auth_users WHERE id=?", (user_id,))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("delete_user error: %s", e)
            return False

    def change_password(self, user_id: str, old_password: str,
                         new_password: str) -> bool:
        user = self.get_user(user_id)
        if not user or not user.get("password_hash"):
            return False
        if not self._verify_password(old_password, user["password_hash"]):
            return False
        new_hash = self._hash_password(new_password)
        try:
            with self._lock:
                self._conn.execute(
                    "UPDATE auth_users SET password_hash=? WHERE id=?",
                    (new_hash, user_id))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("change_password error: %s", e)
            return False

    def get_stats(self) -> dict:
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) FROM auth_users").fetchone()[0]
            enabled = self._conn.execute(
                "SELECT COUNT(*) FROM auth_users WHERE enabled=1").fetchone()[0]
            by_provider = self._conn.execute(
                "SELECT provider, COUNT(*) FROM auth_users "
                "GROUP BY provider").fetchall()
        return {
            "total_users": total,
            "enabled": enabled,
            "by_provider": dict(by_provider),
            "providers": len(self._providers),
        }

    def close(self):
        self._conn.close()

    def _update_login(self, user_id: str):
        now = datetime.utcnow().isoformat() + "Z"
        try:
            with self._lock:
                self._conn.execute(
                    "UPDATE auth_users SET last_login=? WHERE id=?",
                    (now, user_id))
                self._conn.commit()
        except Exception:
            pass

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        h = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 salt.encode(), 100000)
        return f"{salt}:{h.hex()}"

    @staticmethod
    def _verify_password(password: str, stored: str) -> bool:
        try:
            salt, h = stored.split(":", 1)
            computed = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), 100000)
            return secrets.compare_digest(computed.hex(), h)
        except Exception:
            return False

    @staticmethod
    def _row_to_user(row) -> Optional[dict]:
        if not row:
            return None
        return {
            "id": row[0], "username": row[1],
            "password_hash": bool(row[2]),
            "email": row[3], "display_name": row[4],
            "provider": row[5], "provider_id": row[6],
            "roles": json.loads(row[7]) if isinstance(row[7], str) else row[7],
            "mfa_enabled": bool(row[8]),
            "enabled": bool(row[10]),
            "created_at": row[11], "last_login": row[12],
        }


class LocalAuthProvider(AuthProvider):
    def __init__(self):
        super().__init__(name="local", display_name="Local")

    def authenticate(self, credentials: dict) -> Optional[dict]:
        return credentials

    def get_user_info(self, token: str) -> Optional[dict]:
        return {"sub": "local", "name": "Local User"}
