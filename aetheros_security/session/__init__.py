"""
Session Management for AetherOS
===============================

Secure session lifecycle: create, validate, renew, and revoke sessions.

Sessions are represented as HMAC-signed tokens bound to a principal
(user/agent/device) with an absolute expiry and a sliding renewal window.
Tokens are stateless (no server-side session table required) while revocation
lists are kept in memory for the active process.

Usage::

    from aetheros_security.session import SessionManager

    manager = SessionManager()
    token = manager.create("user@example.com", timeout_seconds=3600)
    principal = manager.validate(token)   # raises SessionError if invalid
    new_token = manager.renew(token)
    manager.revoke(token)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionError(Exception):
    """Raised for invalid, expired, or revoked sessions."""


@dataclass
class Session:
    """A validated session."""
    principal: str
    issued_at: float
    expires_at: float
    renewed_at: float
    scope: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at

    def remaining(self) -> float:
        return max(0.0, self.expires_at - time.time())


class SessionManager:
    """Manages signed, expiring sessions.

    Usage::

        manager = SessionManager()

        # Create a session
        token = manager.create("user@example.com", timeout_seconds=3600)

        # Validate
        session = manager.validate(token)

        # Renew (sliding expiry, max_renewals bounded)
        new_token = manager.renew(token)

        # Revoke
        manager.revoke(token)
    """

    def __init__(self, secret: Optional[bytes] = None) -> None:
        # HMAC key: caller-provided or persisted to the AetherOS home dir.
        if secret is not None:
            self._secret = secret
        else:
            self._secret = self._load_or_generate_secret()
        self._revoked: Dict[str, float] = {}  # token_id -> revoked_at

    def _secret_path(self):
        from aetheros_constants import get_aetheros_home
        return get_aetheros_home() / ".session_secret"

    def _load_or_generate_secret(self) -> bytes:
        path = self._secret_path()
        if path.exists():
            try:
                return path.read_bytes()
            except OSError:
                pass
        secret = os.urandom(32)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(secret)
            os.chmod(path, 0o600)
        except OSError:
            pass
        return secret

    # ------------------------------------------------------------------
    # Token primitives
    # ------------------------------------------------------------------

    @staticmethod
    def _b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

    @staticmethod
    def _unb64(data: str) -> bytes:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))

    def _sign(self, payload: str) -> str:
        return self._b64(hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).digest())

    def _verify(self, payload: str, signature: str) -> bool:
        expected = self._sign(payload)
        return hmac.compare_digest(expected, signature)

    def create(
        self,
        principal: str,
        *,
        timeout_seconds: int = 3600,
        scope: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new session token.

        Args:
            principal: Identity the session belongs to.
            timeout_seconds: Absolute session lifetime.
            scope: Optional permission scopes bound to the session.
            metadata: Arbitrary non-sensitive metadata.

        Returns:
            URL-safe session token.
        """
        now = time.time()
        token_id = secrets.token_hex(16)
        body = {
            "tid": token_id,
            "sub": principal,
            "iat": now,
            "exp": now + max(1, timeout_seconds),
            "ren": now,
            "scope": scope or [],
            "meta": metadata or {},
        }
        payload = json.dumps(body, separators=(",", ":"), sort_keys=True)
        encoded = self._b64(payload.encode("utf-8"))
        token = f"{encoded}.{self._sign(encoded)}"
        logger.info("Session created for %s (ttl=%ds)", principal, timeout_seconds)
        return token

    def validate(self, token: str) -> Session:
        """Validate a token and return its session.

        Raises:
            SessionError: If the token is malformed, tampered, revoked, or
                expired.
        """
        try:
            encoded_payload, signature = token.split(".", 1)
            payload = json.loads(self._unb64(encoded_payload).decode("utf-8"))
        except Exception as exc:
            raise SessionError("Malformed session token") from exc

        if not self._verify(encoded_payload, signature):
            raise SessionError("Invalid session signature")

        token_id = payload["tid"]
        if token_id in self._revoked:
            raise SessionError("Session revoked")

        now = time.time()
        if now >= payload["exp"]:
            raise SessionError("Session expired")

        return Session(
            principal=payload["sub"],
            issued_at=payload["iat"],
            expires_at=payload["exp"],
            renewed_at=payload["ren"],
            scope=list(payload.get("scope", [])),
            metadata=dict(payload.get("meta", {})),
        )

    def renew(
        self,
        token: str,
        *,
        extension_seconds: int = 3600,
        max_renewals: int = 12,
    ) -> str:
        """Renew a valid session with a sliding extension.

        A session may only be renewed a bounded number of times so a stolen
        token cannot be kept alive forever.

        Raises:
            SessionError: If the token is invalid or the renewal budget is
                exhausted.
        """
        session = self.validate(token)
        try:
            encoded_payload, signature = token.split(".", 1)
            payload = json.loads(self._unb64(encoded_payload).decode("utf-8"))
        except Exception as exc:
            raise SessionError("Malformed session token") from exc

        renewal_count = int(payload.get("rn", 0))
        if renewal_count >= max_renewals:
            raise SessionError("Session renewal budget exhausted")

        payload["rn"] = renewal_count + 1
        payload["ren"] = time.time()
        payload["exp"] = time.time() + max(1, extension_seconds)
        new_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        new_encoded = self._b64(new_payload.encode("utf-8"))
        new_token = f"{new_encoded}.{self._sign(new_encoded)}"
        logger.info("Session renewed for %s (renewal %d)", session.principal, renewal_count + 1)
        return new_token

    def revoke(self, token: str) -> bool:
        """Revoke a session token (takes effect for this process)."""
        try:
            encoded_payload, _ = token.split(".", 1)
            payload = json.loads(self._unb64(encoded_payload).decode("utf-8"))
        except Exception:
            return False
        self._revoked[payload["tid"]] = time.time()
        return True

    def has_scope(self, session: Session, scope: str) -> bool:
        """Check whether a session grants a scope."""
        return scope in session.scope or "*" in session.scope


# Global session manager
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Return the global SessionManager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
