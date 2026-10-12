"""Credential manager — securely store, retrieve, and manage service credentials."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

from aetheros_constants import get_aetheros_home
from connect.store import ConnectStore

logger = logging.getLogger(__name__)


class CredentialManager:
    def __init__(self, store: Optional[ConnectStore] = None):
        self.store = store or ConnectStore()
        self._master_key = self._load_or_create_key()

    def _load_or_create_key(self) -> bytes:
        key_file = get_aetheros_home() / "connect" / ".master_key"
        if key_file.exists():
            return base64.b64decode(key_file.read_text().strip())
        import secrets
        key = secrets.token_bytes(32)
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(base64.b64encode(key).decode())
        key_file.chmod(0o600)
        return key

    def _encrypt(self, data: dict) -> str:
        try:
            from cryptography.fernet import Fernet
            f = Fernet(base64.urlsafe_b64encode(self._master_key[:32]))
            return f.encrypt(json.dumps(data).encode()).decode()
        except ImportError:
            import hashlib, json
            payload = json.dumps(data).encode()
            key = hashlib.sha256(self._master_key).digest()[:16]
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding
            iv = os.urandom(16)
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            encryptor = cipher.encryptor()
            padder = padding.PKCS7(128).padder()
            padded = padder.update(payload) + padder.finalize()
            encrypted = encryptor.update(padded) + encryptor.finalize()
            return base64.b64encode(iv + encrypted).decode()

    def _decrypt(self, encrypted_data: str) -> dict:
        try:
            from cryptography.fernet import Fernet, InvalidToken
            f = Fernet(base64.urlsafe_b64encode(self._master_key[:32]))
            try:
                return json.loads(f.decrypt(encrypted_data.encode()).decode())
            except InvalidToken:
                pass
            raw = base64.b64decode(encrypted_data.encode())
            iv, ciphertext = raw[:16], raw[16:]
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding
            key = hashlib.sha256(self._master_key).digest()[:16]
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            padded = decryptor.update(ciphertext) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            return json.loads(unpadder.update(padded) + unpadder.finalize())
        except Exception as e:
            logger.error("Decryption failed: %s", e)
            return {}

    def save_credentials(self, connection_id: str, service_id: str,
                          credentials: dict, expires_at: str = "") -> bool:
        encrypted = self._encrypt(credentials)
        key_hint = ", ".join(list(credentials.keys())[:3])
        result = self.store.save_credential(
            service_id, connection_id, encrypted, key_hint, expires_at)
        logger.info("Credentials saved for %s (fields: %s)", connection_id, key_hint)
        return result

    def get_credentials(self, connection_id: str) -> Optional[dict]:
        record = self.store.get_credential(connection_id)
        if record and record.get("encrypted_data"):
            return self._decrypt(record["encrypted_data"])
        return None

    def delete_credentials(self, connection_id: str) -> bool:
        return self.store.delete_credential(connection_id)

    def has_credentials(self, connection_id: str) -> bool:
        cred = self.store.get_credential(connection_id)
        return cred is not None and bool(cred.get("encrypted_data"))

    def get_key_hint(self, connection_id: str) -> str:
        cred = self.store.get_credential(connection_id)
        return cred.get("key_hint", "") if cred else ""

    def rotate_master_key(self) -> None:
        import secrets
        new_key = secrets.token_bytes(32)
        old_key = self._master_key
        connections = self.store.list_connections()
        for conn in connections:
            old_creds = self.get_credentials(conn["id"])
            if old_creds:
                self._master_key = new_key
                self.save_credentials(conn["id"], conn.get("service_id", ""), old_creds)
        self._master_key = new_key
        key_file = get_aetheros_home() / "connect" / ".master_key"
        key_file.write_text(base64.b64encode(new_key).decode())
        logger.info("Master key rotated")
