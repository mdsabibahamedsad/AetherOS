"""Cryptographic identity keys (§4).

Real Ed25519 implementation backed by the ``cryptography`` package
(installed in this repo). Key provenance, versioning, rotation,
revocation, expiration, and public-key discovery are implemented.

Private key material is NEVER logged, never returned in diagnostics, and
never placed into prompts/messages — all redaction helpers refuse it.

If ``cryptography`` is unavailable (minimal envs), the module exposes the
same interface but raises :class:`CryptoUnavailable` on key generation /
signing instead of simulating success (§0.1 rule 2-4).
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    _HAS_CRYPTO = True
except Exception:  # pragma: no cover
    _HAS_CRYPTO = False


class CryptoUnavailable(Exception):
    """Raised when real crypto is unavailable in this environment."""


def crypto_available() -> bool:
    return _HAS_CRYPTO


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii")


def _ub64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s.encode("ascii"))


@dataclass
class IdentityKey:
    key_id: str
    identity_id: str
    algorithm: str  # "Ed25519"
    public_key_b64: str
    version: int = 1
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    revoked: bool = False
    provenance: dict = field(default_factory=dict)


class KeyStore:
    """File-free in-memory key store.

    Private keys live only here. ``export_public()`` exposes public parts;
    there is intentionally NO ``export_private()`` method.
    """

    def __init__(self) -> None:
        self._private: Dict[str, bytes] = {}  # key_id -> raw private bytes
        self._public: Dict[str, IdentityKey] = {}

    # -- generation / rotation -------------------------------------------
    def generate(self, identity_id: str, expires_in: Optional[float] = None) -> IdentityKey:
        if not _HAS_CRYPTO:
            raise CryptoUnavailable(
                "cryptography package unavailable: cannot generate Ed25519 keys"
            )
        priv = Ed25519PrivateKey.generate()
        raw_priv = priv.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
        raw_pub = priv.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        key_id = f"key_{secrets.token_hex(8)}"
        now = time.time()
        meta = IdentityKey(
            key_id=key_id,
            identity_id=identity_id,
            algorithm="Ed25519",
            public_key_b64=_b64(raw_pub),
            version=1,
            created_at=now,
            expires_at=(now + expires_in) if expires_in else None,
            provenance={"generator": "aetheros-control-plane", "algorithm": "Ed25519"},
        )
        self._private[key_id] = bytes(raw_priv)
        self._public[key_id] = meta
        return meta

    def rotate(self, old_key_id: str, expires_in: Optional[float] = None) -> IdentityKey:
        old = self._public.get(old_key_id)
        if old is None:
            raise KeyError(f"unknown key: {old_key_id}")
        new = self.generate(old.identity_id, expires_in=expires_in)
        new.version = old.version + 1
        new.provenance["rotated_from"] = old_key_id
        old.revoked = True
        old.provenance["rotated_to"] = new.key_id
        return new

    # -- lifecycle ---------------------------------------------------------
    def revoke(self, key_id: str) -> None:
        if key_id in self._public:
            self._public[key_id].revoked = True

    def get_public(self, key_id: str) -> Optional[IdentityKey]:
        return self._public.get(key_id)

    def list_for_identity(self, identity_id: str) -> List[IdentityKey]:
        return [k for k in self._public.values() if k.identity_id == identity_id]

    # -- signing (private key never leaves this method's scope) ------------
    def sign(self, key_id: str, message: bytes) -> str:
        if not _HAS_CRYPTO:
            raise CryptoUnavailable("cryptography package unavailable: cannot sign")
        raw = self._private.get(key_id)
        meta = self._public.get(key_id)
        if raw is None or meta is None:
            raise KeyError(f"unknown key: {key_id}")
        if meta.revoked:
            raise ValueError(f"key revoked: {key_id}")
        if meta.expires_at and time.time() > meta.expires_at:
            raise ValueError(f"key expired: {key_id}")
        priv = Ed25519PrivateKey.from_private_bytes(raw)
        return _b64(priv.sign(message))


class KeyResolver:
    """Public-key discovery across stores."""

    def __init__(self) -> None:
        self._stores: List[KeyStore] = []

    def attach(self, store: KeyStore) -> None:
        self._stores.append(store)

    def resolve(self, key_id: str) -> Optional[IdentityKey]:
        for s in self._stores:
            k = s.get_public(key_id)
            if k is not None:
                return k
        return None


class SignatureVerifier:
    """Real Ed25519 signature verification (§4)."""

    def __init__(self, resolver: KeyResolver):
        self._resolver = resolver

    def verify(self, key_id: str, message: bytes, signature_b64: str) -> bool:
        meta = self._resolver.resolve(key_id)
        if meta is None or meta.revoked:
            return False
        if meta.expires_at and time.time() > meta.expires_at:
            return False
        if not _HAS_CRYPTO:
            return False  # cannot verify without crypto: fail closed
        try:
            pub = Ed25519PublicKey.from_public_bytes(_ub64(meta.public_key_b64))
            pub.verify(_ub64(signature_b64), message)
            return True
        except Exception:
            return False


def fingerprint(public_key_b64: str) -> str:
    """Public-key fingerprint (safe to log; reveals nothing private)."""
    return hashlib.sha256(public_key_b64.encode("ascii")).hexdigest()[:16]
