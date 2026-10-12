"""
Secrets Manager for AetherOS
============================

Securely store and manage secrets:
    - API Keys
    - OAuth Tokens
    - Refresh Tokens
    - Cookies
    - MCP Credentials
    - Database Passwords
    - SSH Keys
    - Certificates

Secrets are stored in the operating system's secure storage when available:

    - Windows Credential Manager
    - macOS Keychain
    - Linux Secret Service (via ``keyring``/libsecret)

When no OS backend is available, secrets fall back to an on-disk vault
encrypted with AES-256-GCM (see :mod:`aetheros_security.encryption`).
Plaintext secret values are never written to disk.

Usage::

    from aetheros_security.secrets import SecretsManager, SecretCategory

    manager = SecretsManager()
    manager.store("api_key", "sk-1234567890", category=SecretCategory.API_KEY)
    key = manager.retrieve("api_key")
"""

from __future__ import annotations

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Keys that are never stored in OS keychains (OS backends reject them) are
# routed to the encrypted vault instead.
_VAULT_ONLY_PREFIXES = ("SSH_KEY", "CERTIFICATE")


def _emit_audit(event_type, *, message: str, details: Optional[Dict[str, Any]] = None,
                severity: Any = None) -> None:
    """Emit an audit event without ever including the secret value.

    The audit logger is imported lazily so importing this module never touches
    the audit log or AETHEROS_HOME. Audit failures are swallowed — a broken
    audit trail must never break secret storage itself.
    """
    try:
        from aetheros_security.audit import AuditSeverity, AuditEventType, get_audit_logger
        get_audit_logger().log(
            AuditEventType(event_type),
            severity=severity or AuditSeverity.INFO,
            source="secrets",
            details=details or {},
            message=message,
        )
    except Exception:
        logger.debug("Failed to emit audit event %r", event_type, exc_info=True)


class SecretCategory(Enum):
    """Secret categories."""
    API_KEY = "api_key"
    OAUTH_TOKEN = "oauth_token"
    REFRESH_TOKEN = "refresh_token"
    JWT_TOKEN = "jwt_token"
    COOKIE = "cookie"
    MCP_CREDENTIAL = "mcp_credential"
    DB_PASSWORD = "db_password"
    SSH_KEY = "ssh_key"
    CERTIFICATE = "certificate"
    PASSWORD = "password"
    GENERIC = "generic"


class SecretBackend(Enum):
    """Secret storage backends."""
    OS_KEYCHAIN = "os_keychain"
    WINDOWS_CREDENTIAL = "windows_credential"
    MACOS_KEYCHAIN = "macos_keychain"
    LINUX_SECRET_SERVICE = "linux_secret_service"
    ENCRYPTED_VAULT = "encrypted_vault"


@dataclass
class SecretEntry:
    """A stored secret."""
    name: str
    value: str
    category: SecretCategory = SecretCategory.GENERIC
    description: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    expires_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_meta(self) -> Dict[str, Any]:
        """Return metadata (never includes the secret value)."""
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

class SecretStore(ABC):
    """Interface for secret storage backends."""

    backend: SecretBackend

    @abstractmethod
    def store(self, entry: SecretEntry) -> bool: ...

    @abstractmethod
    def retrieve(self, name: str) -> Optional[str]: ...

    @abstractmethod
    def delete(self, name: str) -> bool: ...

    @abstractmethod
    def exists(self, name: str) -> bool: ...

    @abstractmethod
    def list_meta(self) -> List[Dict[str, Any]]: ...

    def get_meta(self, name: str) -> Optional[Dict[str, Any]]:
        for meta in self.list_meta():
            if meta["name"] == name:
                return meta
        return None

    @abstractmethod
    def is_available(self) -> bool: ...


class _OSBackendBase(SecretStore):
    """Shared logic for OS-backed stores.

    Values live in the OS secure store. A local JSON index tracks non-secret
    metadata (category, timestamps, description) so listing and expiry checks
    work without touching the OS store for every query.
    """

    def __init__(self, home: Optional[Path] = None) -> None:
        self._index_path = (home or self._default_home()) / "secrets_index.json"
        self._index: Dict[str, Dict[str, Any]] = {}
        self._load_index()

    @staticmethod
    def _default_home() -> Path:
        from aetheros_constants import get_aetheros_home
        return get_aetheros_home()

    def _load_index(self) -> None:
        try:
            if self._index_path.exists():
                self._index = json.loads(self._index_path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load secrets index: %s", exc)

    def _save_index(self) -> None:
        try:
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
            self._index_path.write_text(json.dumps(self._index, indent=2), "utf-8")
            try:
                os.chmod(self._index_path, 0o600)
            except OSError:
                pass
        except OSError as exc:
            logger.warning("Could not save secrets index: %s", exc)

    def _store_meta(self, entry: SecretEntry) -> None:
        self._index[entry.name] = entry.to_meta()
        self._save_index()

    def list_meta(self) -> List[Dict[str, Any]]:
        return list(self._index.values())

    def get_meta(self, name: str) -> Optional[Dict[str, Any]]:
        meta = self._index.get(name)
        return dict(meta) if meta else None

    def _remove_meta(self, name: str) -> None:
        self._index.pop(name, None)
        self._save_index()


class _WindowsCredentialStore(_OSBackendBase):
    """Windows Credential Manager via advapi32 (no external deps)."""

    backend = SecretBackend.WINDOWS_CREDENTIAL

    def __init__(self, home: Optional[Path] = None) -> None:
        super().__init__(home)
        self._target_prefix = "aetheros/"

    def is_available(self) -> bool:
        import sys
        return sys.platform == "win32"

    def _target(self, name: str) -> str:
        return f"{self._target_prefix}{name}"

    def store(self, entry: SecretEntry) -> bool:
        if not self._write_credential(self._target(entry.name), entry.value):
            return False
        self._store_meta(entry)
        return True

    def retrieve(self, name: str) -> Optional[str]:
        return self._read_credential(self._target(name))

    def delete(self, name: str) -> bool:
        self._remove_meta(name)
        return self._delete_credential(self._target(name))

    def exists(self, name: str) -> bool:
        value = self.retrieve(name)
        return value is not None

    def _write_credential(self, target: str, secret: str) -> bool:
        import ctypes
        from ctypes import wintypes

        class CREDENTIALW(ctypes.Structure):
            _fields_ = [
                ("Flags", wintypes.DWORD),
                ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", wintypes.LPBYTE),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", wintypes.LPVOID),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]

        blob = secret.encode("utf-16-le")
        buf = (ctypes.c_byte * len(blob)).from_buffer_copy(blob)
        cred = CREDENTIALW()
        cred.Type = 1  # CRED_TYPE_GENERIC
        cred.TargetName = target
        cred.CredentialBlobSize = len(blob)
        cred.CredentialBlob = ctypes.cast(buf, wintypes.LPBYTE)
        cred.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE
        cred.UserName = "aetheros"

        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        ok = advapi32.CredWriteW(ctypes.byref(cred), 0)
        return bool(ok)

    def _read_credential(self, target: str) -> Optional[str]:
        import ctypes
        from ctypes import wintypes

        class CREDENTIALW(ctypes.Structure):
            _fields_ = [
                ("Flags", wintypes.DWORD),
                ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", wintypes.LPBYTE),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", wintypes.LPVOID),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]

        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        p_cred = ctypes.POINTER(CREDENTIALW)()
        ok = advapi32.CredReadW(target, 1, 0, ctypes.byref(p_cred))
        if not ok:
            return None
        try:
            cred = p_cred.contents
            if cred.CredentialBlob and cred.CredentialBlobSize > 0:
                raw = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
                return raw.decode("utf-16-le")
            return None
        finally:
            advapi32.CredFree(p_cred)

    def _delete_credential(self, target: str) -> bool:
        import ctypes

        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        ok = advapi32.CredDeleteW(target, 1, 0)
        return bool(ok)


class _MacKeychainStore(_OSBackendBase):
    """macOS Keychain generic passwords via the Security framework."""

    backend = SecretBackend.MACOS_KEYCHAIN

    def __init__(self, home: Optional[Path] = None) -> None:
        super().__init__(home)
        self._service = "aetheros"

    def is_available(self) -> bool:
        import sys
        return sys.platform == "darwin"

    def store(self, entry: SecretEntry) -> bool:
        import ctypes
        import ctypes.util

        security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        # Delete any existing item first so re-store updates rather than dupes.
        self._delete_item(entry.name)
        account = entry.name.encode("utf-8")
        data = entry.value.encode("utf-8")
        # SecKeychainAddGenericPassword(keychain, serviceNameLen, serviceName,
        #   accountNameLen, accountName, passwordLength, passwordData, itemRef)
        status = security.SecKeychainAddGenericPassword(
            None, len(self._service), self._service.encode("utf-8"),
            len(account), account, len(data), data, None,
        )
        if status == 0:
            self._store_meta(entry)
            return True
        logger.warning("Keychain store failed with OSStatus %d", status)
        return False

    def retrieve(self, name: str) -> Optional[str]:
        import ctypes

        security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        account = name.encode("utf-8")
        length = ctypes.c_uint32()
        data_ref = ctypes.c_void_p()
        # SecKeychainFindGenericPassword(keychain, serviceNameLen, serviceName,
        #   accountNameLen, accountName, passwordLength, passwordData, itemRef)
        status = security.SecKeychainFindGenericPassword(
            None, len(self._service), self._service.encode("utf-8"),
            len(account), account, ctypes.byref(length), ctypes.byref(data_ref), None,
        )
        if status != 0:
            return None
        try:
            raw = ctypes.string_at(data_ref, length.value)
            return raw.decode("utf-8")
        finally:
            security.SecKeychainItemFreeContent(None, data_ref)

    def delete(self, name: str) -> bool:
        self._remove_meta(name)
        return self._delete_item(name)

    def _delete_item(self, name: str) -> bool:
        import ctypes

        security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        account = name.encode("utf-8")
        length = ctypes.c_uint32()
        data_ref = ctypes.c_void_p()
        item_ref = ctypes.c_void_p()
        status = security.SecKeychainFindGenericPassword(
            None, len(self._service), self._service.encode("utf-8"),
            len(account), account, ctypes.byref(length), ctypes.byref(data_ref),
            ctypes.byref(item_ref),
        )
        if status != 0:
            return False
        try:
            return security.SecKeychainItemDelete(item_ref) == 0
        finally:
            if data_ref:
                security.SecKeychainItemFreeContent(None, data_ref)

    def exists(self, name: str) -> bool:
        return self.retrieve(name) is not None


class _LinuxSecretServiceStore(_OSBackendBase):
    """Linux Secret Service via the ``keyring`` package when present."""

    backend = SecretBackend.LINUX_SECRET_SERVICE

    def __init__(self, home: Optional[Path] = None) -> None:
        super().__init__(home)
        self._keyring = None
        try:
            import keyring  # type: ignore
            self._keyring = keyring
        except ImportError:
            pass

    def is_available(self) -> bool:
        import sys
        if sys.platform != "linux":
            return False
        return self._keyring is not None

    def _service(self) -> str:
        return "aetheros"

    def store(self, entry: SecretEntry) -> bool:
        if self._keyring is None:
            return False
        try:
            self._keyring.set_password(self._service(), entry.name, entry.value)
            self._store_meta(entry)
            return True
        except Exception as exc:
            logger.warning("Secret Service store failed: %s", exc)
            return False

    def retrieve(self, name: str) -> Optional[str]:
        if self._keyring is None:
            return None
        try:
            return self._keyring.get_password(self._service(), name)
        except Exception:
            return None

    def delete(self, name: str) -> bool:
        self._remove_meta(name)
        if self._keyring is None:
            return False
        try:
            self._keyring.delete_password(self._service(), name)
            return True
        except Exception:
            return False

    def exists(self, name: str) -> bool:
        return self.retrieve(name) is not None


class _EncryptedVaultStore(SecretStore):
    """On-disk vault encrypted with AES-256-GCM (cross-platform fallback)."""

    backend = SecretBackend.ENCRYPTED_VAULT

    def __init__(self, home: Optional[Path] = None) -> None:
        from aetheros_security.encryption import EncryptionManager

        self._encryption = EncryptionManager()
        self._vault_path = (home or self._default_home()) / "secrets.vault"
        self._vault: Dict[str, Dict[str, Any]] = {}
        self._load_vault()

    @staticmethod
    def _default_home() -> Path:
        from aetheros_constants import get_aetheros_home
        return get_aetheros_home()

    def is_available(self) -> bool:
        return True

    def _load_vault(self) -> None:
        if not self._vault_path.exists():
            return
        try:
            data = json.loads(self._encryption.decrypt(self._vault_path.read_text("utf-8")))
            self._vault = data.get("secrets", {})
        except Exception as exc:
            logger.warning("Could not load secrets vault: %s", exc)

    def _save_vault(self) -> None:
        try:
            self._vault_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps({"secrets": self._vault})
            self._vault_path.write_text(self._encryption.encrypt(payload), "utf-8")
            try:
                os.chmod(self._vault_path, 0o600)
            except OSError:
                pass
        except Exception as exc:
            logger.error("Could not save secrets vault: %s", exc)

    def store(self, entry: SecretEntry) -> bool:
        self._vault[entry.name] = entry.to_meta()
        self._vault[entry.name]["value"] = entry.value
        self._save_vault()
        return True

    def retrieve(self, name: str) -> Optional[str]:
        item = self._vault.get(name)
        return item.get("value") if item else None

    def delete(self, name: str) -> bool:
        if name in self._vault:
            del self._vault[name]
            self._save_vault()
            return True
        return False

    def exists(self, name: str) -> bool:
        return name in self._vault

    def list_meta(self) -> List[Dict[str, Any]]:
        out = []
        for name, item in self._vault.items():
            meta = dict(item)
            meta.pop("value", None)
            meta["name"] = name
            out.append(meta)
        return out

    def get_meta(self, name: str) -> Optional[Dict[str, Any]]:
        item = self._vault.get(name)
        if not item:
            return None
        meta = dict(item)
        meta.pop("value", None)
        meta["name"] = name
        return meta


def _detect_backend() -> SecretBackend:
    """Pick the best available backend for the current platform."""
    import sys

    if sys.platform == "win32":
        return SecretBackend.WINDOWS_CREDENTIAL
    if sys.platform == "darwin":
        return SecretBackend.MACOS_KEYCHAIN
    if sys.platform == "linux":
        try:
            import keyring  # noqa: F401
            return SecretBackend.LINUX_SECRET_SERVICE
        except ImportError:
            pass
    return SecretBackend.ENCRYPTED_VAULT


_BACKEND_CLASSES = {
    SecretBackend.WINDOWS_CREDENTIAL: _WindowsCredentialStore,
    SecretBackend.MACOS_KEYCHAIN: _MacKeychainStore,
    SecretBackend.LINUX_SECRET_SERVICE: _LinuxSecretServiceStore,
    SecretBackend.ENCRYPTED_VAULT: _EncryptedVaultStore,
}


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class SecretsManager:
    """Manages secrets for AetherOS.

    Usage::

        manager = SecretsManager()

        # Store a secret
        manager.store("api_key", "sk-1234567890", category=SecretCategory.API_KEY)

        # Retrieve a secret
        key = manager.retrieve("api_key")

        # Delete a secret
        manager.delete("api_key")

        # List all secrets
        secrets = manager.list_secrets()
    """

    def __init__(
        self,
        backend: Optional[SecretBackend] = None,
        home: Optional[Path] = None,
    ) -> None:
        backend = backend or _detect_backend()
        store_cls = _BACKEND_CLASSES.get(backend, _EncryptedVaultStore)
        self._store = store_cls(home=home)
        if not self._store.is_available():
            logger.info(
                "Backend %s unavailable, falling back to encrypted vault",
                backend.value,
            )
            self._store = _EncryptedVaultStore(home=home)
        self._backend = self._store.backend

    @property
    def backend(self) -> SecretBackend:
        """The active secret storage backend."""
        return self._backend

    def store(
        self,
        name: str,
        value: str,
        *,
        category: SecretCategory = SecretCategory.GENERIC,
        description: str = "",
        expires_in: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store a secret.

        Args:
            name: Secret name/identifier.
            value: Secret value.
            category: Secret category.
            description: Secret description.
            expires_in: Expiry time in seconds (0 = no expiry).
            metadata: Additional metadata.

        Returns:
            True if successful.
        """
        now = time.time()
        entry = SecretEntry(
            name=name,
            value=value,
            category=category,
            description=description,
            created_at=now,
            updated_at=now,
            expires_at=now + expires_in if expires_in > 0 else 0,
            metadata=metadata or {},
        )
        ok = self._store.store(entry)
        if ok:
            logger.info("Secret stored: %s (category: %s)", name, category.value)
            _emit_audit(
                "secret_created",
                message=f"Secret stored: {name}",
                details={"name": name, "category": category.value, "description": description},
            )
        return ok

    def retrieve(self, name: str, *, check_expiry: bool = True) -> Optional[str]:
        """Retrieve a secret.

        Args:
            name: Secret name.
            check_expiry: Check if the secret has expired.

        Returns:
            Secret value or None if not found/expired.
        """
        meta = self._store.get_meta(name)
        if not meta:
            return None
        if check_expiry and meta.get("expires_at", 0) > 0 and time.time() > meta["expires_at"]:
            logger.warning("Secret expired: %s", name)
            return None
        value = self._store.retrieve(name)
        if value is not None:
            _emit_audit(
                "secret_accessed",
                message=f"Secret accessed: {name}",
                details={"name": name},
            )
        return value

    def delete(self, name: str) -> bool:
        """Delete a secret.

        Returns:
            True if the secret existed and was removed.
        """
        existed = self._store.delete(name)
        if existed:
            logger.info("Secret deleted: %s", name)
        return existed

    def exists(self, name: str) -> bool:
        """Check if a secret exists."""
        return self._store.get_meta(name) is not None

    def list_secrets(self, category: Optional[SecretCategory] = None) -> List[Dict[str, Any]]:
        """List secret metadata (never includes values)."""
        metas = self._store.list_meta()
        if category:
            metas = [m for m in metas if m.get("category") == category.value]
        return metas

    def get_secret_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get secret metadata (without the value)."""
        return self._store.get_meta(name)

    def rotate(self, name: str, new_value: str) -> bool:
        """Rotate a secret (update its value in place).

        Returns:
            True if the secret was updated.
        """
        meta = self._store.get_meta(name)
        if not meta:
            return False
        entry = SecretEntry(
            name=name,
            value=new_value,
            category=SecretCategory(meta.get("category", "generic")),
            description=meta.get("description", ""),
            created_at=meta.get("created_at", 0.0),
            updated_at=time.time(),
            expires_at=meta.get("expires_at", 0.0),
            metadata=meta.get("metadata", {}),
        )
        ok = self._store.store(entry)
        if ok:
            logger.info("Secret rotated: %s", name)
            _emit_audit(
                "secret_created",
                message=f"Secret rotated: {name}",
                details={"name": name, "category": entry.category.value},
            )
        return ok

    def cleanup_expired(self) -> int:
        """Remove expired secrets.

        Returns:
            Number of secrets removed.
        """
        now = time.time()
        expired = [
            m["name"] for m in self._store.list_meta()
            if m.get("expires_at", 0) > 0 and now > m["expires_at"]
        ]
        for name in expired:
            self._store.delete(name)
        if expired:
            logger.info("Cleaned up %d expired secrets", len(expired))
        return len(expired)

    def get_stats(self) -> Dict[str, Any]:
        """Get secrets statistics."""
        metas = self._store.list_meta()
        categories: Dict[str, int] = {}
        for meta in metas:
            cat = meta.get("category", "generic")
            categories[cat] = categories.get(cat, 0) + 1
        now = time.time()
        expired = sum(
            1 for m in metas if m.get("expires_at", 0) > 0 and now > m["expires_at"]
        )
        return {
            "total_secrets": len(metas),
            "by_category": categories,
            "expired": expired,
            "backend": self.backend.value,
        }


# Global secrets manager
_secrets_manager: SecretsManager | None = None


def get_secrets_manager() -> SecretsManager:
    """Return the global SecretsManager singleton."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager
