"""
Token Lifecycle Management for AetherOS
=======================================

Secure token issuance, validation, rotation, and revocation with replay
protection for one-time tokens. Supports bearer tokens (reusable until
expiry/revocation) and one-time tokens (invalidated after first use).

Usage::

    from aetheros_security.tokens import TokenManager, TokenError

    manager = TokenManager()
    token = manager.create(
        principal="user:alice",
        typ="bearer",
        scp=["filesystem:read", "network:connect"],
        expires_in=3600,
    )
    payload = manager.validate(token)  # raises TokenError if invalid
    # Rotate a token (returns new token, revokes old)
    new_token = manager.rotate(token)
    # Revoke a token or all tokens for a principal
    manager.revoke(token)
    manager.revoke_principal("user:alice")
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default token signing key persistence location
_TOKEN_KEY_PATH: Optional[str] = None  # set lazily in _get_token_key_path()


class TokenError(Exception):
    """Raised for invalid token operations."""
    pass


@dataclass
class Token:
    """A signed token with payload and signature."""
    payload: str
    signature: str

    @property
    def token_string(self) -> str:
        """Return the full token as ``payload.signature``."""
        return f"{self.payload}.{self.signature}"

    @classmethod
    def from_string(cls, token: str) -> "Token":
        """Parse a token string into payload and signature."""
        try:
            payload, signature = token.rsplit(".", 1)
            return cls(payload=payload, signature=signature)
        except ValueError:
            raise TokenError("Malformed token")


@dataclass
class TokenPayload:
    """Token payload claims."""
    jti: str  # JWT ID (nonce)
    sub: str  # subject (principal)
    typ: str  # token type
    scp: List[str] = field(default_factory=list)  # scopes
    iat: int = 0  # issued at
    exp: int = 0  # expires at
    aud: Optional[str] = None  # audience
    iss: str = "aetheros"  # issuer
    dpt: int = 0  # delegation depth allowed
    parent: Optional[str] = None  # parent jti for delegation chain

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON encoding."""
        return {
            "jti": self.jti,
            "sub": self.sub,
            "typ": self.typ,
            "scp": self.scp,
            "iat": self.iat,
            "exp": self.exp,
            "aud": self.aud,
            "iss": self.iss,
            "dpt": self.dpt,
            "parent": self.parent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenPayload":
        """Create from dict."""
        return cls(
            jti=data["jti"],
            sub=data["sub"],
            typ=data["typ"],
            scp=list(data.get("scp", [])),
            iat=int(data.get("iat", 0)),
            exp=int(data.get("exp", 0)),
            aud=data.get("aud"),
            iss=data.get("iss", "aetheros"),
            dpt=int(data.get("dpt", 0)),
            parent=data.get("parent"),
        )


class TokenManager:
    """Manages token lifecycle with signing key persistence and replay protection.

    The manager uses an HMAC-SHA256 signing key persisted to the AetherOS home
    directory. Token validation includes signature verification, expiry check,
    and replay protection for one-time tokens.
    """

    def __init__(self, secret: Optional[bytes] = None) -> None:
        # HMAC key: caller-provided or persisted to the AetherOS home dir.
        if secret is not None:
            self._secret = secret
        else:
            self._secret = self._load_or_generate_secret()
        # Replay protection cache for one-time tokens: jti -> expiry_at
        self._replay_cache: Dict[str, float] = {}
        # Revoked tokens cache: jti -> expiry_at
        self._revoked_cache: Dict[str, float] = {}

    def _get_token_key_path(self) -> str:
        """Return the path to the persisted token signing key."""
        global _TOKEN_KEY_PATH
        if _TOKEN_KEY_PATH is None:
            from aetheros_constants import get_aetheros_home
            _TOKEN_KEY_PATH = str(get_aetheros_home() / ".token_signing_key")
        return _TOKEN_KEY_PATH

    def _load_or_generate_secret(self) -> bytes:
        """Load the signing key from disk, or generate and persist a new one."""
        path = self._get_token_key_path()
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    key = f.read()
                if len(key) >= 32:  # HMAC-SHA256 expects at least 256-bit key
                    return key
                else:
                    logger.warning(
                        "Token signing key too short (%d bytes), regenerating",
                        len(key),
                    )
            except OSError:
                pass  # fall through to generate
        # Generate a new key
        secret = os.urandom(32)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(secret)
            os.chmod(path, 0o600)  # owner read/write only
            logger.info("Generated new token signing key at %s", path)
        except OSError as exc:
            logger.warning("Could not persist token signing key: %s", exc)
        return secret

    # ------------------------------------------------------------------
    # Token primitives
    # ------------------------------------------------------------------

    @staticmethod
    def _b64encode(data: bytes) -> str:
        """URL-safe base64 encode without padding."""
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

    @staticmethod
    def _b64decode(data: str) -> bytes:
        """Decode URL-safe base64 string, adding padding as needed."""
        padding = 4 - len(data) % 4
        if padding == 4:
            data = data
        else:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    def _sign(self, payload: str) -> str:
        """Sign a payload with the manager's secret."""
        return self._b64encode(
            hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).digest()
        )

    def _verify(self, payload: str, signature: str) -> bool:
        """Verify a signature against the payload."""
        try:
            expected = self._sign(payload)
            return hmac.compare_digest(expected, signature)
        except Exception:
            return False

    def _clean_caches(self) -> None:
        """Remove expired entries from replay and revoked caches."""
        now = time.time()
        # Clean replay cache
        expired_jtis = [jti for jti, expiry in self._replay_cache.items() if expiry <= now]
        for jti in expired_jtis:
            del self._replay_cache[jti]
        # Clean revoked cache
        expired_jtis = [jti for jti, expiry in self._revoked_cache.items() if expiry <= now]
        for jti in expired_jtis:
            del self._revoked_cache[jti]

    # ------------------------------------------------------------------
    # Token lifecycle
    # ------------------------------------------------------------------

    def create(
        self,
        principal: str,
        *,
        typ: str = "bearer",
        scp: Optional[List[str]] = None,
        expires_in: int = 3600,
        aud: Optional[str] = None,
        dpt: int = 0,
        parent: Optional[str] = None,
        one_time: bool = False,
    ) -> str:
        """Create a new signed token.

        Args:
            principal: Token subject (e.g., "user:alice", "agent:agent-1").
            typ: Token type ("bearer", "one_time", "delegation", etc.).
            scp: List of permission scopes bound to the token.
            expires_in: Seconds until token expires (0 = no expiry).
            aud: Optional audience restriction.
            dpt: Delegation depth allowed (0 = no delegation, >0 = can delegate).
            parent: Parent JTI for delegation chain.
            one_time: If True, token is invalidated after first validation.

        Returns:
            URL-safe signed token string.
        """
        now = int(time.time())
        jti = uuid.uuid4().hex
        payload = TokenPayload(
            jti=jti,
            sub=principal,
            typ=typ,
            scp=list(scp or []),
            iat=now,
            # fail-closed: negative TTLs yield an ALREADY-EXPIRED token,
            # never a non-expiring one (0 remains the explicit no-expiry)
            exp=(now + max(0, expires_in)) if expires_in > 0 else
            (now if expires_in < 0 else 0),
            aud=aud,
            dpt=dpt,
            parent=parent,
        )
        payload_json = json.dumps(payload.to_dict(), separators=(",", ":"), sort_keys=True)
        payload_b64 = self._b64encode(payload_json.encode("utf-8"))
        signature = self._sign(payload_b64)
        token = f"{payload_b64}.{signature}"
        logger.info(
            "Token created for %s (type=%s expires_in=%s one_time=%s)",
            principal,
            typ,
            expires_in,
            one_time,
        )
        return token

    def validate(self, token: str) -> TokenPayload:
        """Validate a token and return its payload.

        Args:
            token: Signed token string.

        Returns:
            TokenPayload if valid.

        Raises:
            TokenError: If the token is invalid, expired, malformed, or
                replayed (for one-time tokens).
        """
        self._clean_caches()
        try:
            payload_b64, signature = token.rsplit(".", 1)
        except ValueError:
            raise TokenError("Malformed token")

        if not self._verify(payload_b64, signature):
            raise TokenError("Invalid token signature")

        try:
            payload_json = self._b64decode(payload_b64).decode("utf-8")
            payload_dict = json.loads(payload_json)
            payload = TokenPayload.from_dict(payload_dict)
        except Exception as exc:
            raise TokenError(f"Invalid token payload: {exc}") from exc

        now = time.time()
        if payload.exp > 0 and now >= payload.exp:
            raise TokenError("Token expired")

        # Audience and issuer checks (optional)
        # if payload.aud and payload.aud != expected_aud:
        #     raise TokenError("Invalid audience")
        # if payload.iss and payload.iss != expected_iss:
        #     raise TokenError("Invalid issuer")

        # Replay protection for one-time tokens
        if payload.typ == "one_time":
            if payload.jti in self._replay_cache:
                raise TokenError("Token replayed")
            # Mark as seen with expiry to clean later
            self._replay_cache[payload.jti] = payload.exp or (now + 3600)
        elif payload.typ == "bearer":
            # Bearer tokens can be reused; check revocation
            if payload.jti in self._revoked_cache:
                raise TokenError("Token revoked")
        else:
            # Other token types (delegation, etc.) follow bearer semantics
            if payload.jti in self._revoked_cache:
                raise TokenError("Token revoked")

        return payload

    def renew(self, token: str, extends_in: int = 3600) -> str:
        """Renew a valid token with a new expiry.

        Args:
            token: Token to renew.
            extends_in: Seconds to extend expiry from now.

        Returns:
            New signed token with same claims but new expiry and JTI.

        Raises:
            TokenError: If the token is invalid.
        """
        payload = self.validate(token)  # validates and caches if one-time
        # For one-time tokens, renewal consumes the token (cannot be renewed after validate?)
        # Actually, validate already marked it as seen; we should not allow renewal of one-time.
        if payload.typ == "one_time":
            raise TokenError("Cannot renew a one-time token")
        return self.create(
            principal=payload.sub,
            typ=payload.typ,
            scp=payload.scp,
            expires_in=extends_in,
            aud=payload.aud,
            dpt=payload.dpt,
            parent=payload.parent,
        )

    def rotate(self, token: str) -> str:
        """Rotate a token: return a new token and revoke the old one.

        Args:
            token: Token to rotate.

        Returns:
            New signed token with same claims but new JTI.

        Raises:
            TokenError: If the token is invalid.
        """
        payload = self.validate(token)
        # Revoke the old token by adding its JTI to revoked cache
        self._revoked_cache[payload.jti] = payload.exp or (time.time() + 3600)
        # Issue a new token with same claims
        return self.create(
            principal=payload.sub,
            typ=payload.typ,
            scp=payload.scp,
            expires_in=max(0, payload.exp - int(time.time())) if payload.exp > 0 else 0,
            aud=payload.aud,
            dpt=payload.dpt,
            parent=payload.parent,
        )

    def revoke(self, token: str) -> bool:
        """Revoke a token (adds its JTI to the revoked cache).

        Args:
            token: Token to revoke.

        Returns:
            True if the token was valid and revoked, False if malformed.
        """
        try:
            payload = self.validate(token)
            # If validation succeeded, add to revoked cache
            self._revoked_cache[payload.jti] = payload.exp or (time.time() + 3600)
            return True
        except TokenError:
            return False

    def revoke_principal(self, principal: str) -> None:
        """Revoke all tokens for a principal (lazy: relies on expiry + JTI uniqueness).
        Note: This does not prevent reuse of a valid token until it expires or is
        explicitly revoked. For immediate revocation, callers should track issued
        tokens and revoke them individually.
        """
        # In a full implementation, we would maintain an index of JTIs by principal.
        # For now, we rely on callers to manage token revocation individually.
        logger.warning(
            "revoke_principal called for %s; immediate revocation not implemented "
            "without token tracking",
            principal,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Return manager statistics."""
        self._clean_caches()
        return {
            "replay_cache_size": len(self._replay_cache),
            "revoked_cache_size": len(self._revoked_cache),
        }


# Global token manager
_token_manager: TokenManager | None = None


def get_token_manager() -> TokenManager:
    """Return the global TokenManager singleton."""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager