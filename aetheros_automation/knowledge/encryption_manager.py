from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class EncryptionScheme(str, Enum):
    AES_256_GCM = "aes_256_gcm"
    CHACHA20 = "chacha20"
    NONE = "none"


@dataclass
class EncryptionConfig:
    scheme: EncryptionScheme = EncryptionScheme.AES_256_GCM
    key_path: str = ""
    enabled: bool = True
    encrypt_at_rest: bool = True
    encrypt_in_transit: bool = True
    key_rotation_days: int = 90


class KnowledgeEncryption:
    def __init__(self, config: EncryptionConfig | None = None):
        self._config = config or EncryptionConfig()
        self._key: Optional[bytes] = None

    @property
    def is_available(self) -> bool:
        return self._config.enabled and self._key is not None

    def generate_key(self) -> bytes:
        import os
        self._key = os.urandom(32)
        return self._key

    def load_key(self, key_path: str) -> bool:
        try:
            p = Path(key_path)
            if p.exists():
                self._key = p.read_bytes()
                return len(self._key) == 32
            return False
        except (IOError, OSError):
            return False

    def save_key(self, key_path: str) -> bool:
        if not self._key:
            return False
        try:
            Path(key_path).write_bytes(self._key)
            return True
        except (IOError, OSError):
            return False

    def encrypt(self, data: str) -> str:
        if not self.is_available:
            return data
        try:
            from cryptography.fernet import Fernet
            import base64
            f = Fernet(base64.urlsafe_b64encode(self._key[:32].ljust(32, b'\x00')))
            return f.encrypt(data.encode()).decode()
        except ImportError:
            return data

    def decrypt(self, encrypted_data: str) -> str:
        if not self.is_available:
            return encrypted_data
        try:
            from cryptography.fernet import Fernet
            import base64
            f = Fernet(base64.urlsafe_b64encode(self._key[:32].ljust(32, b'\x00')))
            return f.decrypt(encrypted_data.encode()).decode()
        except ImportError:
            return encrypted_data

    def encrypt_dict(self, data: dict, sensitive_fields: list[str] | None = None) -> dict:
        if not self.is_available:
            return data
        fields = sensitive_fields or ["value", "content", "text", "secret", "token", "key"]
        result = dict(data)
        for field in fields:
            if field in result and isinstance(result[field], str):
                result[field] = self.encrypt(result[field])
        return result

    def decrypt_dict(self, data: dict, sensitive_fields: list[str] | None = None) -> dict:
        if not self.is_available:
            return data
        fields = sensitive_fields or ["value", "content", "text"]
        result = dict(data)
        for field in fields:
            if field in result and isinstance(result[field], str):
                try:
                    result[field] = self.decrypt(result[field])
                except Exception:
                    pass
        return result

    def get_config(self) -> dict:
        return {
            "scheme": self._config.scheme.value,
            "enabled": self._config.enabled,
            "encrypt_at_rest": self._config.encrypt_at_rest,
            "encrypt_in_transit": self._config.encrypt_in_transit,
            "key_rotation_days": self._config.key_rotation_days,
            "key_loaded": self._key is not None,
        }
