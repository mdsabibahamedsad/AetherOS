"""
Encryption and security layer for AetherOS Cloud Sync operations.

Provides RSA key pair generation for device identity, AES-256-GCM encryption
for sync data, end-to-end encryption for secrets, key derivation from user
passphrase, digital signatures, and an encrypted secret vault per device.

Key rotation, device-specific encryption keys, and secure keychain integration
points are supported.
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
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    logger.warning("cryptography package not available — sync crypto will be degraded")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RSA_KEY_SIZE = 4096
_AES_KEY_SIZE = 32  # 256 bits
_GCM_NONCE_SIZE = 12
_SALT_SIZE = 32
_PBKDF2_ITERATIONS = 600_000
_SIGNATURE_HASH = hashes.SHA512
_VAULT_VERSION = 1


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DeviceKeyPair:
    """RSA key pair for a device's sync identity."""
    device_id: str
    public_key_pem: str
    private_key_pem: str
    created_at: float
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.fingerprint:
            self.fingerprint = _derive_fingerprint(self.public_key_pem)


@dataclass
class EncryptedPayload:
    """Wraps an AES-256-GCM encrypted payload with metadata."""
    ciphertext: str
    nonce: str
    salt: str = ""
    key_identifier: str = ""
    tag: str = ""
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ciphertext": self.ciphertext,
            "nonce": self.nonce,
            "salt": self.salt,
            "key_identifier": self.key_identifier,
            "tag": self.tag,
            "created_at": self.created_at or time.time(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EncryptedPayload:
        return cls(
            ciphertext=data["ciphertext"],
            nonce=data["nonce"],
            salt=data.get("salt", ""),
            key_identifier=data.get("key_identifier", ""),
            tag=data.get("tag", ""),
            created_at=data.get("created_at", 0.0),
        )


@dataclass
class SignedPayload:
    """Payload with a digital signature."""
    data: str
    signature: str
    signer_fingerprint: str
    signed_at: float
    algorithm: str = "RSA-SHA512"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "signature": self.signature,
            "signer_fingerprint": self.signer_fingerprint,
            "signed_at": self.signed_at or time.time(),
            "algorithm": self.algorithm,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SignedPayload:
        return cls(
            data=data["data"],
            signature=data["signature"],
            signer_fingerprint=data["signer_fingerprint"],
            signed_at=data.get("signed_at", 0.0),
            algorithm=data.get("algorithm", "RSA-SHA512"),
        )


@dataclass
class EncryptedSecretVault:
    """Encrypted secret vault for device-local secret storage."""
    device_id: str
    entries: Dict[str, EncryptedPayload] = field(default_factory=dict)
    version: int = _VAULT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EncryptedSecretVault:
        entries = {
            k: EncryptedPayload.from_dict(v)
            for k, v in data.get("entries", {}).items()
        }
        return cls(
            device_id=data["device_id"],
            entries=entries,
            version=data.get("version", _VAULT_VERSION),
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _vault_dir() -> Path:
    return get_aetheros_home() / "sync" / "vaults"


def _vault_path(device_id: str) -> Path:
    return _vault_dir() / f"{device_id}.vault.json"


def _derive_fingerprint(public_key_pem: str) -> str:
    raw = public_key_pem.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64_decode(data: str) -> bytes:
    return base64.b64decode(data)


def _require_crypto() -> None:
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError(
            "cryptography package is required for sync crypto operations. "
            "Install with: pip install cryptography"
        )


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------


def generate_device_keypair(device_id: Optional[str] = None) -> DeviceKeyPair:
    """Generate an RSA key pair for device identity.

    Returns a :class:`DeviceKeyPair` with PEM-encoded keys and a
    SHA-256 fingerprint of the public key.
    """
    _require_crypto()
    if not device_id:
        device_id = str(uuid.uuid4())

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=_RSA_KEY_SIZE,
        backend=default_backend(),
    )
    public_key = private_key.public_key()

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    kp = DeviceKeyPair(
        device_id=device_id,
        public_key_pem=public_key_pem,
        private_key_pem=private_key_pem,
        created_at=time.time(),
    )
    logger.info("Generated key pair for device %s (fingerprint: %s)", device_id, kp.fingerprint)
    return kp


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------


def derive_key_from_passphrase(
    passphrase: str,
    salt: Optional[bytes] = None,
) -> Tuple[bytes, bytes]:
    """Derive an AES-256 key from a user passphrase using PBKDF2-HMAC-SHA512.

    Returns ``(key, salt)`` where *salt* is the salt used (randomly generated
    if not provided). Store the salt alongside the encrypted data.
    """
    _require_crypto()
    if salt is None:
        salt = os.urandom(_SALT_SIZE)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA512(),
        length=_AES_KEY_SIZE,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    key = kdf.derive(passphrase.encode("utf-8"))
    return key, salt


# ---------------------------------------------------------------------------
# AES-256-GCM encryption / decryption
# ---------------------------------------------------------------------------


def encrypt_sync_payload(
    data: bytes,
    key: bytes,
    associated_data: Optional[bytes] = None,
) -> EncryptedPayload:
    """Encrypt *data* with AES-256-GCM.

    Args:
        data: Plaintext bytes to encrypt.
        key: 32-byte AES-256 key.
        associated_data: Optional AAD for additional authentication context.

    Returns:
        An :class:`EncryptedPayload` with base64-encoded ciphertext and nonce.
    """
    _require_crypto()
    nonce = os.urandom(_GCM_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, data, associated_data or b"")
    return EncryptedPayload(
        ciphertext=_b64_encode(ct),
        nonce=_b64_encode(nonce),
        created_at=time.time(),
    )


def decrypt_sync_payload(
    payload: EncryptedPayload,
    key: bytes,
    associated_data: Optional[bytes] = None,
) -> bytes:
    """Decrypt an :class:`EncryptedPayload` with AES-256-GCM.

    Args:
        payload: The encrypted payload to decrypt.
        key: 32-byte AES-256 key (must match encryption key).
        associated_data: AAD used during encryption.

    Returns:
        Decrypted plaintext bytes.

    Raises:
        ValueError: If the ciphertext is invalid or the key is wrong.
    """
    _require_crypto()
    nonce = _b64_decode(payload.nonce)
    ct = _b64_decode(payload.ciphertext)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, associated_data or b"")


# ---------------------------------------------------------------------------
# Digital signatures
# ---------------------------------------------------------------------------


def sign_payload(
    data: bytes,
    private_key_pem: str,
) -> SignedPayload:
    """Sign *data* with an RSA private key (SHA-512).

    Args:
        data: The bytes to sign.
        private_key_pem: PEM-encoded RSA private key.

    Returns:
        A :class:`SignedPayload` containing the base64-encoded signature.
    """
    _require_crypto()
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )
    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(_SIGNATURE_HASH()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        _SIGNATURE_HASH(),
    )
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return SignedPayload(
        data=_b64_encode(data),
        signature=_b64_encode(signature),
        signer_fingerprint=_derive_fingerprint(public_key_pem),
        signed_at=time.time(),
    )


def verify_signature(
    signed: SignedPayload,
    public_key_pem: str,
) -> bool:
    """Verify an RSA digital signature.

    Args:
        signed: The :class:`SignedPayload` to verify.
        public_key_pem: PEM-encoded RSA public key of the claimed signer.

    Returns:
        True if the signature is valid, False otherwise.
    """
    _require_crypto()
    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode("utf-8"),
            backend=default_backend(),
        )
        data = _b64_decode(signed.data)
        signature = _b64_decode(signed.signature)
        public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(_SIGNATURE_HASH()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            _SIGNATURE_HASH(),
        )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Secret encryption (E2E for secret sync)
# ---------------------------------------------------------------------------


def encrypt_secret(
    secret_value: str,
    key: bytes,
    context: Optional[str] = None,
) -> EncryptedPayload:
    """Encrypt a secret string for end-to-end encrypted sync.

    Uses AES-256-GCM with the key derived from the user's sync passphrase.
    The *context* string is used as AAD so the ciphertext is bound to a
    specific purpose (e.g. ``"provider:openai:api_key"``).
    """
    aad = context.encode("utf-8") if context else None
    return encrypt_sync_payload(secret_value.encode("utf-8"), key, associated_data=aad)


def decrypt_secret(
    payload: EncryptedPayload,
    key: bytes,
    context: Optional[str] = None,
) -> str:
    """Decrypt a secret string that was encrypted with :func:`encrypt_secret`.

    Returns the original plaintext string.
    """
    aad = context.encode("utf-8") if context else None
    plaintext = decrypt_sync_payload(payload, key, associated_data=aad)
    return plaintext.decode("utf-8")


# ---------------------------------------------------------------------------
# Encrypted Secret Vault
# ---------------------------------------------------------------------------


class SyncCrypto:
    """High-level encryption and security operations for sync.

    Manages device key pairs, encryption keys derived from a user passphrase,
    signing/verification of sync payloads, and encrypted secret vaults.
    """

    def __init__(
        self,
        passphrase: str = "",
        device_id: Optional[str] = None,
        key_pair: Optional[DeviceKeyPair] = None,
    ) -> None:
        """Initialize SyncCrypto.

        Args:
            passphrase: User's sync encryption passphrase. If empty, the
                encryption key will be derived lazily when first needed.
            device_id: Device identifier. If not provided, one is generated
                when ``load_or_create_keys()`` is called.
            key_pair: Pre-existing key pair. If not provided, keys are
                loaded from or saved to the sync directory.
        """
        self._passphrase = passphrase
        self._device_id = device_id or ""
        self._key_pair = key_pair
        self._encryption_key: Optional[bytes] = None
        self._derived_salt: Optional[bytes] = None
        self._key_identifier: str = ""
        self._vault_cache: Dict[str, EncryptedSecretVault] = {}

    @property
    def device_id(self) -> str:
        return self._device_id or (self._key_pair.device_id if self._key_pair else "")

    @property
    def key_pair(self) -> Optional[DeviceKeyPair]:
        return self._key_pair

    @property
    def fingerprint(self) -> str:
        if self._key_pair:
            return self._key_pair.fingerprint
        return ""

    # ------------------------------------------------------------------
    # Key lifecycle
    # ------------------------------------------------------------------

    def load_or_create_keys(self, keys_dir: Optional[Path] = None) -> DeviceKeyPair:
        """Load existing device key pair from disk or generate a new one."""
        if keys_dir is None:
            keys_dir = get_aetheros_home() / "sync" / "keys"
        keys_dir.mkdir(parents=True, exist_ok=True)

        if not self._device_id:
            self._device_id = str(uuid.uuid4())

        key_path = keys_dir / f"device_{self._device_id}.key.json"
        if key_path.exists():
            try:
                kp_data = json.loads(key_path.read_text(encoding="utf-8"))
                self._key_pair = DeviceKeyPair(
                    device_id=kp_data["device_id"],
                    public_key_pem=kp_data["public_key"],
                    private_key_pem=kp_data["private_key"],
                    created_at=kp_data.get("created_at", 0.0),
                    fingerprint=kp_data.get("fingerprint", ""),
                )
                logger.debug("Loaded existing key pair for %s", self._device_id)
                return self._key_pair
            except Exception as exc:
                logger.warning("Failed to load key pair from %s: %s", key_path, exc)

        self._key_pair = generate_device_keypair(self._device_id)
        try:
            key_path.write_text(
                json.dumps({
                    "device_id": self._key_pair.device_id,
                    "public_key": self._key_pair.public_key_pem,
                    "private_key": self._key_pair.private_key_pem,
                    "created_at": self._key_pair.created_at,
                    "fingerprint": self._key_pair.fingerprint,
                }, indent=2),
                encoding="utf-8",
            )
            key_path.chmod(0o600)
            logger.info("Saved new key pair for device %s", self._device_id)
        except Exception as exc:
            logger.error("Failed to save key pair: %s", exc)

        return self._key_pair

    def rotate_key_pair(self, keys_dir: Optional[Path] = None) -> DeviceKeyPair:
        """Generate a new key pair (rotates the device identity).

        The old key pair is kept as a backup so previously-signed data can
        still be verified until all peers have learned the new key.
        """
        old_pair = self._key_pair
        self._device_id = str(uuid.uuid4())
        new_pair = self.load_or_create_keys(keys_dir)

        if old_pair and keys_dir:
            backup_dir = keys_dir / "rotated"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"device_{old_pair.device_id}.{int(time.time())}.key.json"
            try:
                backup_path.write_text(
                    json.dumps({
                        "device_id": old_pair.device_id,
                        "public_key": old_pair.public_key_pem,
                        "private_key": old_pair.private_key_pem,
                        "created_at": old_pair.created_at,
                        "fingerprint": old_pair.fingerprint,
                    }, indent=2),
                    encoding="utf-8",
                )
                backup_path.chmod(0o600)
                logger.info("Backed up rotated key pair for %s", old_pair.device_id)
            except Exception as exc:
                logger.error("Failed to back up rotated key: %s", exc)

        return new_pair

    # ------------------------------------------------------------------
    # Encryption key management
    # ------------------------------------------------------------------

    def set_passphrase(self, passphrase: str) -> None:
        """Set or update the user's sync encryption passphrase.

        Call this before performing encryption/decryption to derive the key.
        """
        self._passphrase = passphrase
        self._encryption_key = None
        self._derived_salt = None

    def get_encryption_key(self, force_derive: bool = False) -> bytes:
        """Return the derived AES-256 encryption key.

        If no key has been derived yet, derives it from the passphrase.
        The derived key is cached for the lifetime of this instance.

        Raises:
            RuntimeError: If no passphrase has been set.
        """
        if self._encryption_key is not None and not force_derive:
            return self._encryption_key
        if not self._passphrase:
            raise RuntimeError(
                "Sync encryption passphrase is not set. "
                "Call set_passphrase() or configure it in settings."
            )
        self._encryption_key, self._derived_salt = derive_key_from_passphrase(
            self._passphrase,
        )
        kf = hashlib.sha256(self._encryption_key).hexdigest()[:12]
        self._key_identifier = f"aes256_{kf}"
        return self._encryption_key

    def get_key_identifier(self) -> str:
        """Return a short identifier for the current encryption key.

        Useful for key rotation detection without exposing key material.
        """
        if not self._key_identifier:
            self.get_encryption_key()
        return self._key_identifier

    def rotate_encryption_key(self, new_passphrase: str) -> Tuple[bytes, bytes]:
        """Rotate the encryption key by deriving from a new passphrase.

        Returns ``(new_key, new_salt)``. Old ciphertexts remain decryptable
        with the old passphrase — callers should re-encrypt sensitive data
        after rotation.
        """
        self._passphrase = new_passphrase
        self._encryption_key = None
        self._derived_salt = None
        self._key_identifier = ""
        return self.get_encryption_key(), self._derived_salt

    # ------------------------------------------------------------------
    # Encrypted secret vault
    # ------------------------------------------------------------------

    def load_vault(self, device_id: Optional[str] = None) -> EncryptedSecretVault:
        """Load the encrypted secret vault for a device from disk."""
        did = device_id or self.device_id
        if not did:
            raise ValueError("device_id is required to load a vault")

        if did in self._vault_cache:
            return self._vault_cache[did]

        path = _vault_path(did)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                vault = EncryptedSecretVault.from_dict(data)
                self._vault_cache[did] = vault
                return vault
            except Exception as exc:
                logger.warning("Failed to load vault for %s: %s", did, exc)

        vault = EncryptedSecretVault(device_id=did)
        self._vault_cache[did] = vault
        return vault

    def save_vault(self, vault: Optional[EncryptedSecretVault] = None) -> None:
        """Save the encrypted secret vault to disk."""
        v = vault or (self._vault_cache.get(self.device_id) if self.device_id else None)
        if v is None:
            raise ValueError("No vault to save")

        path = _vault_path(v.device_id)
        _vault_dir().mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(json.dumps(v.to_dict(), indent=2), encoding="utf-8")
            path.chmod(0o600)
            self._vault_cache[v.device_id] = v
        except Exception as exc:
            logger.error("Failed to save vault for %s: %s", v.device_id, exc)
            raise

    def store_secret_in_vault(
        self,
        key_name: str,
        secret_value: str,
        context: Optional[str] = None,
        passphrase: Optional[str] = None,
    ) -> None:
        """Encrypt a secret and store it in the local vault.

        The secret is encrypted end-to-end using the sync passphrase before
        being written to disk.
        """
        if passphrase:
            self.set_passphrase(passphrase)
        enc_key = self.get_encryption_key()
        payload = encrypt_secret(secret_value, enc_key, context=context)

        vault = self.load_vault()
        vault.entries[key_name] = payload
        self.save_vault(vault)
        logger.debug("Stored encrypted secret '%s' in vault", key_name)

    def retrieve_secret_from_vault(
        self,
        key_name: str,
        context: Optional[str] = None,
        passphrase: Optional[str] = None,
    ) -> Optional[str]:
        """Decrypt and return a secret from the local vault.

        Returns None if the key is not found or decryption fails.
        """
        if passphrase:
            self.set_passphrase(passphrase)
        enc_key = self.get_encryption_key()

        vault = self.load_vault()
        payload = vault.entries.get(key_name)
        if payload is None:
            return None

        try:
            return decrypt_secret(payload, enc_key, context=context)
        except Exception as exc:
            logger.error("Failed to decrypt secret '%s': %s", key_name, exc)
            return None

    def delete_secret_from_vault(self, key_name: str) -> bool:
        """Remove a secret entry from the vault.

        Returns True if the entry existed and was removed.
        """
        vault = self.load_vault()
        if key_name not in vault.entries:
            return False
        del vault.entries[key_name]
        self.save_vault(vault)
        logger.debug("Deleted secret '%s' from vault", key_name)
        return True

    def list_vault_secrets(self) -> list[str]:
        """Return the list of secret key names stored in the vault."""
        vault = self.load_vault()
        return list(vault.entries.keys())

    # ------------------------------------------------------------------
    # HMAC-based integrity check
    # ------------------------------------------------------------------

    def compute_payload_hmac(self, data: bytes, key: bytes) -> str:
        """Compute an HMAC-SHA256 digest for sync payload integrity."""
        h = hmac.new(key, data, hashlib.sha256)
        return h.hexdigest()

    def verify_payload_hmac(self, data: bytes, key: bytes, expected_hmac: str) -> bool:
        """Verify an HMAC-SHA256 digest matches *data*."""
        computed = self.compute_payload_hmac(data, key)
        return hmac.compare_digest(computed, expected_hmac)


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def encrypt_with_passphrase(data: bytes, passphrase: str) -> EncryptedPayload:
    """Encrypt *data* with a key derived from *passphrase*.

    One-shot convenience function. The salt is randomly generated and
    included in the returned :class:`EncryptedPayload`.
    """
    key, salt = derive_key_from_passphrase(passphrase)
    payload = encrypt_sync_payload(data, key)
    payload.salt = _b64_encode(salt)
    return payload


def decrypt_with_passphrase(payload: EncryptedPayload, passphrase: str) -> bytes:
    """Decrypt an :class:`EncryptedPayload` using *passphrase*.

    One-shot convenience function. The salt must be present in the payload.
    """
    salt = _b64_decode(payload.salt) if payload.salt else b""
    key, _ = derive_key_from_passphrase(passphrase, salt=salt)
    return decrypt_sync_payload(payload, key)
