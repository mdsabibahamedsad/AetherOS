"""macOS Keychain abstraction (Master 65).

Service/account model with access-scope validation and a hard rule:
NEVER silently fall back to plaintext storage. The live SecItem backend
needs macOS (BLOCKED — MACOS ENVIRONMENT); this module defines the
contract + an in-memory backend for tests and a `keychainctl`-style
diagnostic surface. Secret classes follow the platform taxonomy
(MODEL_API_KEY, MCP_CREDENTIAL, OAUTH_TOKEN, SESSION_TOKEN, ...).
"""

from __future__ import annotations

import time
from dataclasses import dataclass


class KeychainError(Exception):
    pass


class PlaintextFallbackForbidden(KeychainError):
    pass


@dataclass
class KeychainItem:
    service: str
    account: str
    access: str = "user"  # user|device|session
    created_at: float = 0.0
    updated_at: float = 0.0


class KeychainBackend:
    def store(self, item: KeychainItem, secret: str) -> None:
        raise NotImplementedError

    def read(self, service: str, account: str) -> str:
        raise NotImplementedError

    def delete(self, service: str, account: str) -> bool:
        raise NotImplementedError


class UnavailableBackend(KeychainBackend):
    """Honest absence: every op raises; callers must NOT catch-and-plaintext."""

    def __init__(self, reason: str = "macOS Keychain unavailable on this host"):
        self.reason = reason

    def store(self, item: KeychainItem, secret: str) -> None:
        raise KeychainError(self.reason)

    def read(self, service: str, account: str) -> str:
        raise KeychainError(self.reason)

    def delete(self, service: str, account: str) -> bool:
        raise KeychainError(self.reason)


class MemoryBackend(KeychainBackend):
    """Test-only backend. Production MUST use SecItem, never this."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], tuple[KeychainItem, str]] = {}

    def store(self, item: KeychainItem, secret: str) -> None:
        _validate_item(item, secret)
        now = time.time()
        item.created_at = item.created_at or now
        item.updated_at = now
        self._store[(item.service, item.account)] = (item, secret)

    def read(self, service: str, account: str) -> str:
        try:
            return self._store[(service, account)][1]
        except KeyError:
            raise KeychainError(f"missing item {service}/{account}")

    def delete(self, service: str, account: str) -> bool:
        return self._store.pop((service, account), None) is not None


def _validate_item(item: KeychainItem, secret: str) -> None:
    if not item.service or not item.account:
        raise KeychainError("service and account required")
    if item.access not in ("user", "device", "session"):
        raise KeychainError(f"unknown access scope '{item.access}'")
    if not secret:
        raise KeychainError("refusing to store empty secret")


def require_keychain_or_fail(backend: KeychainBackend | None) -> KeychainBackend:
    """Callers use this instead of try/except-and-plaintext fallbacks."""
    if backend is None:
        raise PlaintextFallbackForbidden("no Keychain backend; plaintext forbidden")
    return backend
