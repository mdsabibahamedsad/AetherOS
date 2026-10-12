"""
Authentication for AetherOS
===========================

Multi-method authentication for local accounts:

    - Local password accounts (PBKDF2-HMAC-SHA256 hashed)
    - Passwordless one-time codes (email/CLI delivery hook)
    - OAuth / SSO providers (config-registered, token validated by provider)
    - Device authentication (challenge-response)
    - Biometric hooks (platform capability callback, opt-in)

Successful authentication yields a signed session managed by
:mod:`aetheros_security.session` with configurable timeout and secure renewal.

Usage::

    from aetheros_security.authentication import AuthenticationManager

    manager = AuthenticationManager()
    manager.register_account("user@example.com", "correct horse battery staple")
    ok = manager.authenticate_password("user@example.com", "correct horse battery staple")
    token = manager.create_session("user@example.com")
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_security.session import SessionError, get_session_manager

logger = logging.getLogger(__name__)

_PBKDF2_ITERATIONS = 310_000
_OTP_TTL_SECONDS = 600  # one-time codes valid for 10 minutes


class AuthenticationError(Exception):
    """Raised when authentication fails."""


@dataclass
class AuthAccount:
    """A locally registered account."""
    identifier: str
    password_hash: str = ""
    salt: str = ""
    methods: List[str] = field(default_factory=list)  # password, passwordless, oauth, device, biometric
    enabled: bool = True
    created_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OAuthProvider:
    """A configured OAuth/SSO provider (config-level registration)."""
    name: str
    client_id: str = ""
    issuer: str = ""
    authorization_url: str = ""
    token_url: str = ""
    jwks_url: str = ""
    enabled: bool = True


class AuthenticationManager:
    """Manages authentication for AetherOS.

    Accounts are persisted to ``<AETHEROS_HOME>/auth_accounts.json``. Password
    hashes are PBKDF2-HMAC-SHA256 with per-account random salts. One-time
    passwordless codes and device challenges are held in memory only.
    """

    def __init__(self, accounts_file: Optional[str] = None) -> None:
        self._accounts_file = Path(accounts_file) if accounts_file else self._default_accounts_file()
        self._accounts: Dict[str, AuthAccount] = {}
        self._otps: Dict[str, tuple[str, float]] = {}       # identifier -> (code, expires)
        self._devices: Dict[str, str] = {}                  # device_id -> challenge
        self._oauth_providers: Dict[str, OAuthProvider] = {}
        self._biometric_callback: Optional[Callable[[str], bool]] = None
        self._load()

    @staticmethod
    def _default_accounts_file() -> Path:
        from aetheros_constants import get_aetheros_home
        return get_aetheros_home() / "auth_accounts.json"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._accounts_file.exists():
            return
        try:
            data = json.loads(self._accounts_file.read_text("utf-8"))
            for ident, acc in data.get("accounts", {}).items():
                self._accounts[ident] = AuthAccount(
                    identifier=ident,
                    password_hash=acc.get("password_hash", ""),
                    salt=acc.get("salt", ""),
                    methods=list(acc.get("methods", [])),
                    enabled=acc.get("enabled", True),
                    created_at=acc.get("created_at", 0.0),
                    metadata=acc.get("metadata", {}),
                )
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load auth accounts: %s", exc)

    def _save(self) -> None:
        try:
            self._accounts_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"accounts": {}}
            for ident, acc in self._accounts.items():
                data["accounts"][ident] = {
                    "password_hash": acc.password_hash,
                    "salt": acc.salt,
                    "methods": acc.methods,
                    "enabled": acc.enabled,
                    "created_at": acc.created_at,
                    "metadata": acc.metadata,
                }
            self._accounts_file.write_text(json.dumps(data, indent=2), "utf-8")
            try:
                os.chmod(self._accounts_file, 0o600)
            except OSError:
                pass
        except OSError as exc:
            logger.warning("Could not save auth accounts: %s", exc)

    # ------------------------------------------------------------------
    # Password hashing
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        salt = salt or secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), _PBKDF2_ITERATIONS
        )
        return digest.hex(), salt

    # ------------------------------------------------------------------
    # Account management
    # ------------------------------------------------------------------

    def register_account(
        self,
        identifier: str,
        password: Optional[str] = None,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Register a local account.

        If ``password`` is provided the account supports password auth;
        otherwise it is set up for passwordless / device / OAuth methods.
        """
        identifier = identifier.strip().lower()
        account = self._accounts.get(identifier)
        if account is None:
            account = AuthAccount(identifier=identifier, created_at=time.time())
            self._accounts[identifier] = account

        if password:
            digest, salt = self._hash_password(password)
            account.password_hash = digest
            account.salt = salt
            if "password" not in account.methods:
                account.methods.append("password")
        if metadata:
            account.metadata.update(metadata)
        account.enabled = True
        self._save()
        logger.info("Account registered: %s", identifier)
        return True

    def set_password(self, identifier: str, password: str) -> bool:
        """Set or reset an account's password."""
        account = self._accounts.get(identifier.strip().lower())
        if account is None:
            return False
        digest, salt = self._hash_password(password)
        account.password_hash = digest
        account.salt = salt
        if "password" not in account.methods:
            account.methods.append("password")
        self._save()
        return True

    def disable_account(self, identifier: str) -> bool:
        """Disable an account (cannot authenticate until re-enabled)."""
        account = self._accounts.get(identifier.strip().lower())
        if account is None:
            return False
        account.enabled = False
        self._save()
        return True

    def enable_account(self, identifier: str) -> bool:
        """Re-enable a disabled account."""
        account = self._accounts.get(identifier.strip().lower())
        if account is None:
            return False
        account.enabled = True
        self._save()
        return True

    def delete_account(self, identifier: str) -> bool:
        """Delete an account and revoke its identity."""
        identifier = identifier.strip().lower()
        if identifier in self._accounts:
            del self._accounts[identifier]
            self._otps.pop(identifier, None)
            self._save()
            return True
        return False

    def list_accounts(self) -> List[Dict[str, Any]]:
        """List account metadata (never password material)."""
        return [
            {
                "identifier": acc.identifier,
                "methods": list(acc.methods),
                "enabled": acc.enabled,
                "created_at": acc.created_at,
                "metadata": dict(acc.metadata),
            }
            for acc in self._accounts.values()
        ]

    # ------------------------------------------------------------------
    # Password authentication
    # ------------------------------------------------------------------

    def authenticate_password(self, identifier: str, password: str) -> bool:
        """Authenticate with a password.

        Verifies in constant-ish time: a missing account still performs a
        PBKDF2 derivation against a dummy hash to blunt timing side channels.
        """
        identifier = identifier.strip().lower()
        account = self._accounts.get(identifier)
        if account is None or not account.enabled or not account.password_hash:
            # Burn equivalent work to avoid account-existence timing leaks.
            self._hash_password(password)
            return False
        digest, _ = self._hash_password(password, account.salt)
        return hmac.compare_digest(digest, account.password_hash)

    # ------------------------------------------------------------------
    # Passwordless (one-time code)
    # ------------------------------------------------------------------

    def request_passwordless_code(self, identifier: str) -> Optional[str]:
        """Generate a one-time code for passwordless sign-in.

        Returns the code (to be delivered by the caller's channel of choice).
        The code expires after ``_OTP_TTL_SECONDS`` and is single-use.
        """
        identifier = identifier.strip().lower()
        account = self._accounts.get(identifier)
        if account is None or not account.enabled:
            return None
        code = f"{secrets.randbelow(1_000_000):06d}"
        self._otps[identifier] = (code, time.time() + _OTP_TTL_SECONDS)
        if "passwordless" not in account.methods:
            account.methods.append("passwordless")
            self._save()
        logger.info("Passwordless code issued for %s", identifier)
        return code

    def verify_passwordless_code(self, identifier: str, code: str) -> bool:
        """Verify and consume a one-time passwordless code."""
        identifier = identifier.strip().lower()
        stored = self._otps.get(identifier)
        if not stored:
            return False
        expected, expires = stored
        self._otps.pop(identifier, None)  # single-use
        if time.time() > expires:
            return False
        return hmac.compare_digest(expected, code)

    # ------------------------------------------------------------------
    # OAuth / SSO
    # ------------------------------------------------------------------

    def register_oauth_provider(self, provider: OAuthProvider) -> None:
        """Register an OAuth/SSO provider configuration."""
        self._oauth_providers[provider.name] = provider

    def get_oauth_provider(self, name: str) -> Optional[OAuthProvider]:
        return self._oauth_providers.get(name)

    def list_oauth_providers(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": p.name,
                "client_id": p.client_id,
                "issuer": p.issuer,
                "enabled": p.enabled,
            }
            for p in self._oauth_providers.values()
        ]

    def authenticate_oauth(self, provider_name: str, identifier: str, verified: bool = False) -> bool:
        """Record an OAuth/SSO sign-in.

        In production, ``verified`` must come from validating the provider's
        ID token / assertion. A ``verified=True`` call that matches a known
        account (or a new identifier when the provider is enabled) succeeds.
        """
        provider = self._oauth_providers.get(provider_name)
        if provider is None or not provider.enabled:
            return False
        if not verified:
            return False
        identifier = identifier.strip().lower()
        account = self._accounts.get(identifier)
        if account is None:
            account = AuthAccount(identifier=identifier, created_at=time.time())
            self._accounts[identifier] = account
        if "oauth" not in account.methods:
            account.methods.append("oauth")
            self._save()
        return True

    # ------------------------------------------------------------------
    # Device authentication
    # ------------------------------------------------------------------

    def start_device_auth(self, device_id: str) -> str:
        """Start device authentication, returning a challenge string."""
        challenge = secrets.token_hex(24)
        self._devices[device_id] = challenge
        return challenge

    def verify_device_auth(self, device_id: str, challenge_response: str) -> bool:
        """Verify a device challenge response."""
        expected = self._devices.pop(device_id, None)
        if expected is None:
            return False
        return hmac.compare_digest(expected, challenge_response)

    # ------------------------------------------------------------------
    # Biometric hooks
    # ------------------------------------------------------------------

    def register_biometric_callback(self, callback: Callable[[str], bool]) -> None:
        """Register a platform biometric verifier.

        The callback receives an identifier and returns whether the platform's
        biometric check (Touch ID, Windows Hello, fingerprint) succeeded.
        """
        self._biometric_callback = callback

    def authenticate_biometric(self, identifier: str) -> bool:
        """Authenticate via the registered biometric callback.

        Returns False when no callback is registered (no support).
        """
        identifier = identifier.strip().lower()
        account = self._accounts.get(identifier)
        if account is None or not account.enabled:
            return False
        if self._biometric_callback is None:
            return False
        ok = bool(self._biometric_callback(identifier))
        if ok and "biometric" not in account.methods:
            account.methods.append("biometric")
            self._save()
        return ok

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(
        self,
        identifier: str,
        *,
        timeout_seconds: int = 3600,
        scope: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a signed session token for an authenticated identifier."""
        identifier = identifier.strip().lower()
        if identifier not in self._accounts:
            raise AuthenticationError(f"No such account: {identifier}")
        return get_session_manager().create(
            identifier, timeout_seconds=timeout_seconds, scope=scope, metadata=metadata
        )

    def validate_session(self, token: str):
        """Validate a session token.

        Raises:
            SessionError: On invalid/expired/revoked tokens.
        """
        return get_session_manager().validate(token)

    def renew_session(self, token: str, *, extension_seconds: int = 3600) -> str:
        """Securely renew a session token (bounded renewal budget)."""
        return get_session_manager().renew(token, extension_seconds=extension_seconds)

    def revoke_session(self, token: str) -> bool:
        """Revoke a session token."""
        return get_session_manager().revoke(token)

    def has_permission(self, token: str, scope: str) -> bool:
        """Check a scope against a valid session token."""
        session = self.validate_session(token)
        return get_session_manager().has_scope(session, scope)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "accounts": len(self._accounts),
            "oauth_providers": len(self._oauth_providers),
            "biometric_supported": self._biometric_callback is not None,
        }


# Global authentication manager
_auth_manager: AuthenticationManager | None = None


def get_authentication_manager() -> AuthenticationManager:
    """Return the global AuthenticationManager singleton."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthenticationManager()
    return _auth_manager
