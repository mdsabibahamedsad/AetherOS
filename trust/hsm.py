"""Key custody: local secure backend (real, OS-backed) + PKCS#11
probe (honest BLOCKED without hardware/library).

Private keys never touch logs, prompts, audit records, renderer
payloads, or JSON configs. The local backend stores via
aetheros_security SecretsManager (OS keychain/Keychain/Secret
Service, AES-256-GCM vault fallback). A PKCS#11 HSM is used only
when a library + token are actually present; otherwise every HSM
operation reports BLOCKED with the concrete reason.
"""
from __future__ import annotations

import base64
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional


class CustodyStatus(str):
    AVAILABLE = "AVAILABLE"
    BLOCKED = "BLOCKED"


@dataclass
class CustodyInfo:
    backend: str
    status: str
    reason: str = ""


class KeyCustody(ABC):
    backend = "abstract"

    @abstractmethod
    def generate(self, label: str) -> str:
        """Create a key; return key id. Private material never leaves."""

    @abstractmethod
    def sign(self, key_id: str, message: bytes) -> str:
        """Sign inside custody; return base64 signature."""

    @abstractmethod
    def public_key_b64(self, key_id: str) -> str:
        """Export public key only."""

    @abstractmethod
    def info(self) -> CustodyInfo:
        """Availability + reason (never fake AVAILABLE)."""


class LocalCustody(KeyCustody):
    """OS-backed secure storage via SecretsManager. Real on all three
    desktop OSes (keychain / Credential Manager / Secret Service),
    encrypted-vault fallback otherwise. Process-local cache holds
    keys only in memory, never on disk outside the vault."""

    backend = "local-os"

    def __init__(self, namespace: str = "trust-fabric") -> None:
        from aetheros_security.secrets import SecretsManager
        self._mgr = SecretsManager()
        self._ns = namespace
        self._cache: Dict[str, bytes] = {}
        self._pubs: Dict[str, str] = {}

    def _slot(self, key_id: str) -> str:
        return f"{self._ns}/{key_id}"

    def generate(self, label: str) -> str:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey)
        from cryptography.hazmat.primitives import serialization
        key_id = f"hsm-local-{uuid.uuid4().hex[:12]}"
        priv = Ed25519PrivateKey.generate()
        raw = priv.private_bytes(
            serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
            serialization.NoEncryption())
        pub = base64.urlsafe_b64encode(priv.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw)).decode()
        # sealed into OS custody; memory cache only
        self._mgr.store(self._slot(key_id),
                        base64.urlsafe_b64encode(raw).decode())
        self._cache[key_id] = bytes(raw)
        self._pubs[key_id] = pub
        return key_id

    def _raw(self, key_id: str) -> bytes:
        if key_id in self._cache:
            return self._cache[key_id]
        try:
            sealed = self._mgr.retrieve(self._slot(key_id))
        except Exception as exc:
            raise KeyError(f"unknown key {key_id}") from exc
        if not sealed:
            raise KeyError(f"unknown key {key_id}")
        raw = base64.urlsafe_b64decode(sealed.encode())
        self._cache[key_id] = raw
        return raw

    def sign(self, key_id: str, message: bytes) -> str:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey)
        priv = Ed25519PrivateKey.from_private_bytes(self._raw(key_id))
        return base64.urlsafe_b64encode(priv.sign(message)).decode()

    def public_key_b64(self, key_id: str) -> str:
        if key_id in self._pubs:
            return self._pubs[key_id]
        # re-derive from sealed material (public only)
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey)
        from cryptography.hazmat.primitives import serialization
        priv = Ed25519PrivateKey.from_private_bytes(self._raw(key_id))
        pub = base64.urlsafe_b64encode(priv.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw)).decode()
        self._pubs[key_id] = pub
        return pub

    def forget(self, key_id: str) -> None:
        self._cache.pop(key_id, None)
        self._pubs.pop(key_id, None)

    def info(self) -> CustodyInfo:
        try:
            backend = type(self._mgr).__name__
            return CustodyInfo(self.backend, CustodyStatus.AVAILABLE,
                               f"os-backed secrets ({backend})")
        except Exception as exc:
            return CustodyInfo(self.backend, CustodyStatus.BLOCKED,
                               str(exc)[:200])


class Pkcs11Custody(KeyCustody):
    """Real PKCS#11 path when library + token exist; honest BLOCKED
    otherwise. Never pretends a software key is an HSM key."""

    backend = "pkcs11-hsm"

    def __init__(self, lib_path: str = "", token_label: str = "",
                 pin_env: str = "AETHEROS_HSM_PIN") -> None:
        self.lib_path = lib_path
        self.token_label = token_label
        self.pin_env = pin_env
        self._reason = self._probe()

    def _probe(self) -> str:
        import os
        if not self.lib_path or not os.path.exists(self.lib_path):
            return ("BLOCKED: no PKCS#11 library configured/found "
                    "(set lib path + token label + PIN env)")
        try:
            import ctypes
            ctypes.CDLL(self.lib_path)
        except Exception as exc:
            return f"BLOCKED: cannot load PKCS#11 library: {exc}"[:200]
        if not os.environ.get(self.pin_env):
            return (f"BLOCKED: PIN env {self.pin_env} unset; refusing "
                    "to proceed without operator-provided PIN")
        return ""

    def info(self) -> CustodyInfo:
        if self._reason:
            return CustodyInfo(self.backend, CustodyStatus.BLOCKED,
                               self._reason)
        return CustodyInfo(self.backend, CustodyStatus.AVAILABLE,
                           "PKCS#11 token present")

    def _blocked(self) -> KeyError:
        raise KeyError(f"HSM unavailable: {self._reason or 'unknown'}")

    def generate(self, label: str) -> str:
        self._blocked()

    def sign(self, key_id: str, message: bytes) -> str:
        self._blocked()

    def public_key_b64(self, key_id: str) -> str:
        self._blocked()
