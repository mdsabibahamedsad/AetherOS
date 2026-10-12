"""
Encryption for AetherOS
=======================

Encrypt sensitive data:
    - Configuration
    - Memory snapshots
    - Backups
    - Workspace metadata
    - Session tokens
    - Credentials

Uses modern authenticated encryption (AES-256-GCM) with a unique nonce per
encryption and optional associated data. Ciphertext is versioned so the
format can evolve and old keys can be retired via rotation.

Usage::

    from aetheros_security.encryption import EncryptionManager

    manager = EncryptionManager()
    encrypted = manager.encrypt("sensitive data")
    decrypted = manager.decrypt(encrypted)

    # Rotate the master key (old ciphertext stays decryptable via key history)
    manager.rotate_key()
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

# Format version stored in the ciphertext header. Bump when the wire format
# changes; decrypt() dispatches on this byte so old blobs keep working.
_CIPHER_FORMAT_VERSION = 1
_HEADER_VERSION = b"\x01"  # 1 byte version + 12 byte nonce + tag || ciphertext
_NONCE_SIZE = 12  # GCM recommends 96-bit nonces
_TAG_SIZE = 16
_HEADER_SIZE = 1 + _NONCE_SIZE
_KEY_LENGTH = 32  # 256-bit AES key
_KEY_ID_LENGTH = 12


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""


class EncryptionManager:
    """Manages authenticated encryption for AetherOS.

    Usage::

        manager = EncryptionManager()

        # Encrypt data
        encrypted = manager.encrypt("sensitive data")

        # Decrypt data
        decrypted = manager.decrypt(encrypted)

        # Encrypt a binary blob
        blob = manager.encrypt_bytes(b"raw bytes")

        # Encrypt file (binary-safe)
        manager.encrypt_file("config.yaml")

        # Decrypt file
        manager.decrypt_file("config.yaml.enc")

        # Rotate master key
        manager.rotate_key()
    """

    def __init__(self, key_file: Optional[str] = None) -> None:
        self._key_file = key_file
        self._key_id, self._key = self._load_or_generate_key()

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------

    def _get_key_file_path(self):
        from aetheros_constants import get_aetheros_home
        if self._key_file is not None:
            from pathlib import Path
            return Path(self._key_file)
        return get_aetheros_home() / ".encryption_key"

    def _get_history_file_path(self):
        return self._get_key_file_path().with_suffix(".key_history")

    def _load_or_generate_key(self) -> tuple[str, bytes]:
        """Load the current key, migrating legacy raw-key files."""
        key_file = self._get_key_file_path()

        if key_file.exists():
            try:
                raw = key_file.read_bytes()
                if len(raw) == _KEY_LENGTH:
                    # Legacy raw 32-byte key file -> migrate to versioned format
                    key_id = uuid.uuid4().hex[:_KEY_ID_LENGTH]
                    self._write_key(key_id, raw)
                    return key_id, raw
                payload = json.loads(raw.decode("utf-8"))
                if "key" in payload:
                    key_id = payload.get("key_id", uuid.uuid4().hex[:_KEY_ID_LENGTH])
                    key = base64.b64decode(payload["key"])
                    if len(key) != _KEY_LENGTH:
                        raise ValueError("Key has invalid length")
                    return key_id, key
            except Exception as exc:
                logger.warning("Could not read encryption key file: %s", exc)

        # Generate new key
        key = os.urandom(_KEY_LENGTH)
        key_id = uuid.uuid4().hex[:_KEY_ID_LENGTH]
        self._write_key(key_id, key)
        return key_id, key

    def _write_key(self, key_id: str, key: bytes) -> None:
        key_file = self._get_key_file_path()
        try:
            key_file.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps({
                "key_id": key_id,
                "key": base64.b64encode(key).decode("ascii"),
                "created_at": None,
            })
            key_file.write_bytes(payload.encode("utf-8"))
            try:
                os.chmod(key_file, 0o600)
            except OSError:
                pass
        except OSError as exc:
            logger.warning("Could not save encryption key: %s", exc)

    def rotate_key(self) -> dict:
        """Rotate the master encryption key.

        The current key is moved into the key history so previously encrypted
        data remains decryptable. New encryptions use the fresh key.

        Returns:
            Metadata describing the rotation.
        """
        old_key_id, old_key = self._key_id, self._key
        history_file = self._get_history_file_path()
        try:
            history = []
            if history_file.exists():
                history = json.loads(history_file.read_text("utf-8"))
            history.append({
                "key_id": old_key_id,
                "key": base64.b64encode(old_key).decode("ascii"),
                "retired_at": None,
            })
            # Keep only the most recent 4 retired keys; older ones can never be
            # decrypted again, so retaining them only grows attack surface.
            history = history[-4:]
            history_file.write_text(json.dumps(history, indent=2), "utf-8")
            os.chmod(history_file, 0o600)
        except OSError as exc:
            logger.warning("Could not persist retired key: %s", exc)

        new_key = os.urandom(_KEY_LENGTH)
        new_id = uuid.uuid4().hex[:_KEY_ID_LENGTH]
        self._key_id, self._key = new_id, new_key
        self._write_key(new_id, new_key)
        logger.info("Encryption key rotated: %s -> %s", old_key_id, new_id)
        return {"old_key_id": old_key_id, "new_key_id": new_id}

    def get_key_id(self) -> str:
        """Return the active key identifier."""
        return self._key_id

    def _keys_for_decryption(self):
        """Yield (key_id, key) candidates, active key first."""
        yield self._key_id, self._key
        history_file = self._get_history_file_path()
        if not history_file.exists():
            return
        try:
            history = json.loads(history_file.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for entry in history:
            yield entry["key_id"], base64.b64decode(entry["key"])

    def derive_key(self, password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
        """Derive a key from a password (PBKDF2-HMAC-SHA256).

        Used for portable export / import where the master key must not travel
        with the artifact.

        Returns:
            (key, salt) tuple. Pass the same salt back for decryption.
        """
        salt = salt or secrets.token_bytes(16)
        key = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations=310_000, dklen=_KEY_LENGTH
        )
        return key, salt

    # ------------------------------------------------------------------
    # String / bytes primitives
    # ------------------------------------------------------------------

    def _encrypt_with_key(self, key: bytes, data: bytes, aad: Optional[bytes]) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(_NONCE_SIZE)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, data, aad or b"")
        return _HEADER_VERSION + nonce + ct

    def _decrypt_with_key(self, key: bytes, blob: bytes, aad: Optional[bytes]) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if len(blob) < _HEADER_SIZE + _TAG_SIZE:
            raise EncryptionError("Ciphertext too short")
        if blob[0] != _CIPHER_FORMAT_VERSION:
            raise EncryptionError(f"Unsupported cipher format version: {blob[0]}")
        nonce = blob[1 : 1 + _NONCE_SIZE]
        ct = blob[1 + _NONCE_SIZE :]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ct, aad or b"")

    def encrypt(self, plaintext: str, *, aad: Optional[str] = None) -> str:
        """Encrypt a string.

        Args:
            plaintext: Data to encrypt.
            aad: Optional authenticated-but-unencrypted context (e.g. a field
                name) bound to the ciphertext.

        Returns:
            Base64-encoded, versioned AES-GCM ciphertext.
        """
        blob = self._encrypt_with_key(self._key, plaintext.encode("utf-8"), aad.encode("utf-8") if aad else None)
        return base64.b64encode(blob).decode("ascii")

    def decrypt(self, ciphertext: str, *, aad: Optional[str] = None) -> str:
        """Decrypt a string.

        Args:
            ciphertext: Base64-encoded, versioned AES-GCM ciphertext.
            aad: Same associated data used at encryption time.

        Returns:
            Decrypted plaintext.

        Raises:
            EncryptionError: On authentication failure or malformed input.
        """
        try:
            blob = base64.b64decode(ciphertext.encode("ascii"))
        except Exception as exc:
            raise EncryptionError("Malformed ciphertext") from exc
        aad_bytes = aad.encode("utf-8") if aad else None
        for _key_id, key in self._keys_for_decryption():
            try:
                return self._decrypt_with_key(key, blob, aad_bytes).decode("utf-8")
            except EncryptionError:
                continue
            except Exception:
                continue
        raise EncryptionError("Decryption failed: authentication error or unknown key")

    def encrypt_bytes(self, data: bytes, *, aad: Optional[str] = None) -> bytes:
        """Encrypt a raw byte string, returning raw (non-base64) ciphertext."""
        return self._encrypt_with_key(self._key, data, aad.encode("utf-8") if aad else None)

    def decrypt_bytes(self, blob: bytes, *, aad: Optional[str] = None) -> bytes:
        """Decrypt raw ciphertext produced by :meth:`encrypt_bytes`."""
        aad_bytes = aad.encode("utf-8") if aad else None
        for _key_id, key in self._keys_for_decryption():
            try:
                return self._decrypt_with_key(key, blob, aad_bytes)
            except EncryptionError:
                continue
        raise EncryptionError("Decryption failed: authentication error or unknown key")

    # ------------------------------------------------------------------
    # File helpers (binary-safe)
    # ------------------------------------------------------------------

    def encrypt_file(self, input_path: str, output_path: Optional[str] = None) -> str:
        """Encrypt a file in place (binary-safe).

        Args:
            input_path: Path to file to encrypt.
            output_path: Path to encrypted file. If None, adds .enc extension.

        Returns:
            Path to encrypted file.
        """
        if output_path is None:
            output_path = input_path + ".enc"
        with open(input_path, "rb") as f:
            data = f.read()
        blob = self._encrypt_with_key(self._key, data, None)
        with open(output_path, "wb") as f:
            f.write(blob)
        logger.info("File encrypted: %s -> %s", input_path, output_path)
        return output_path

    def decrypt_file(self, input_path: str, output_path: Optional[str] = None) -> str:
        """Decrypt a file encrypted by :meth:`encrypt_file` (binary-safe).

        Args:
            input_path: Path to encrypted file.
            output_path: Path to decrypted file. If None, removes .enc extension.

        Returns:
            Path to decrypted file.
        """
        if output_path is None:
            output_path = input_path.removesuffix(".enc")
        with open(input_path, "rb") as f:
            blob = f.read()
        data = None
        for _key_id, key in self._keys_for_decryption():
            try:
                data = self._decrypt_with_key(key, blob, None)
                break
            except EncryptionError:
                continue
        if data is None:
            raise EncryptionError("File decryption failed: authentication error or unknown key")
        with open(output_path, "wb") as f:
            f.write(data)
        logger.info("File decrypted: %s -> %s", input_path, output_path)
        return output_path

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    def hash(self, data: str) -> str:
        """Generate a SHA-256 hash of data."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def hash_bytes(self, data: bytes) -> str:
        """Generate a SHA-256 hash of a byte string."""
        return hashlib.sha256(data).hexdigest()

    def verify_hash(self, data: str, expected_hash: str) -> bool:
        """Verify data matches an expected SHA-256 hash."""
        return hmac_compare(self.hash(data), expected_hash)

    def verify_hash_bytes(self, data: bytes, expected_hash: str) -> bool:
        """Verify a byte string matches an expected SHA-256 hash."""
        return hmac_compare(self.hash_bytes(data), expected_hash)


def hmac_compare(left: str, right: str) -> bool:
    """Constant-time string comparison to avoid timing side channels."""
    import hmac

    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


# Global encryption manager
_encryption_manager: EncryptionManager | None = None


def get_encryption_manager() -> EncryptionManager:
    """Return the global EncryptionManager singleton."""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager
