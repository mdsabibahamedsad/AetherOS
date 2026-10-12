"""Security Foundation for AetherOS.

Provides encryption, key management, and secure storage.
Integrates with the existing aetheros_security package.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aetheros_arch.security")


try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False


class SecurityFoundation:
    """Security foundation providing encryption and key management.

    Features:
    - Fernet (AES-128-CBC) encryption for config values
    - PBKDF2 key derivation from master password
    - Secure in-memory key storage
    - Encrypted persistent storage for secrets
    """

    def __init__(
        self,
        secrets_dir: Optional[Path] = None,
        master_key: Optional[bytes] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._secrets_dir = secrets_dir
        self._master_key = master_key
        self._fernet: Any = None
        self._initialized = False

        if master_key is not None and _CRYPTO_AVAILABLE:
            self._init_fernet(master_key)

    def initialize(self, master_key: bytes) -> None:
        """Initialize with a master key."""
        with self._lock:
            self._master_key = master_key
            self._init_fernet(master_key)
            self._initialized = True

    def initialize_with_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """Derive a key from a password and initialize."""
        if salt is None:
            salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.initialize(key)
        return salt

    @property
    def is_available(self) -> bool:
        return _CRYPTO_AVAILABLE

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ------------------------------------------------------------------
    # Encryption
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        if not self._initialized or not _CRYPTO_AVAILABLE:
            return plaintext
        with self._lock:
            return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        if not self._initialized or not _CRYPTO_AVAILABLE:
            return ciphertext
        with self._lock:
            return self._fernet.decrypt(ciphertext.encode()).decode()

    def encrypt_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in data.items():
            if isinstance(value, str) and self._is_secret_key(key):
                result[key] = self.encrypt(value)
            elif isinstance(value, dict):
                result[key] = self.encrypt_dict(value)
            else:
                result[key] = value
        return result

    def decrypt_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in data.items():
            if isinstance(value, str) and self._is_secret_key(key):
                try:
                    result[key] = self.decrypt(value)
                except Exception:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = self.decrypt_dict(value)
            else:
                result[key] = value
        return result

    # ------------------------------------------------------------------
    # Secure storage
    # ------------------------------------------------------------------

    def store_secret(self, name: str, value: str) -> None:
        if not self._secrets_dir:
            return
        self._secrets_dir.mkdir(parents=True, exist_ok=True)
        secret_path = self._secrets_dir / f"{name}.enc"
        encrypted = self.encrypt(value)
        secret_path.write_text(encrypted, encoding="utf-8")
        os.chmod(str(secret_path), 0o600)

    def read_secret(self, name: str) -> Optional[str]:
        if not self._secrets_dir:
            return None
        secret_path = self._secrets_dir / f"{name}.enc"
        if not secret_path.exists():
            return None
        try:
            encrypted = secret_path.read_text(encoding="utf-8")
            return self.decrypt(encrypted)
        except Exception:
            logger.warning("Failed to read secret: %s", name)
            return None

    def delete_secret(self, name: str) -> bool:
        if not self._secrets_dir:
            return False
        secret_path = self._secrets_dir / f"{name}.enc"
        if secret_path.exists():
            secret_path.unlink()
            return True
        return False

    def list_secrets(self) -> List[str]:
        if not self._secrets_dir or not self._secrets_dir.exists():
            return []
        return [p.stem for p in self._secrets_dir.glob("*.enc")]

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def hash_string(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    @staticmethod
    def hash_api_key(key: str) -> str:
        return f"ak_{hashlib.sha256(key.encode()).hexdigest()[:16]}"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _init_fernet(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    @staticmethod
    def _is_secret_key(key: str) -> bool:
        secret_indicators = [
            "api_key", "api-key", "apikey",
            "secret", "token", "password",
            "credential", "auth", "jwt",
            "key", "private_key",
        ]
        key_lower = key.lower().replace(" ", "_").replace("-", "_")
        return any(indicator in key_lower for indicator in secret_indicators)