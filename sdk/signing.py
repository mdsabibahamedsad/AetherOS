"""
Plugin Package Signing
======================

Cryptographic signing and verification for Aetheros extension packages.

Uses Ed25519 signatures (via the ``cryptography`` library when available,
with a fallback to Python's built-in hashlib + hmac for hash-based
verification).

Signing workflow:
    1. Publisher generates a key pair (private + public)
    2. Publisher signs the package SHA-256 hash with their private key
    3. Users verify the signature against the publisher's public key
    4. The signature is stored inside the .aep file as ``.signature``

The publisher's public key is registered in the marketplace and can be
pinned in enterprise configurations.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sdk.packaging import PluginPackage

logger = logging.getLogger(__name__)


class SignatureError(Exception):
    """Raised on signing/verification failures."""


@dataclass
class PublisherKey:
    """A publisher's public key for signature verification."""
    key_id: str
    public_key: str
    algorithm: str = "ed25519"
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.fingerprint:
            self.fingerprint = hashlib.sha256(
                self.public_key.encode("utf-8")
            ).hexdigest()[:16]


def sign_package(
    package: PluginPackage,
    private_key_pem: str,
    key_id: str,
) -> str:
    """Sign a plugin package with the publisher's private key.

    The signature is stored as a JSON file inside the package at
    ``.signature``.

    Args:
        package: The PluginPackage to sign.
        private_key_pem: PEM-encoded private key.
        key_id: Identifier for the signing key (for key rotation).

    Returns:
        The signature string (base64-encoded).

    Raises:
        SignatureError: If signing fails.
    """
    try:
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import ed25519

        # Load private key
        private_key = serialization.load_ssh_private_key(
            private_key_pem.encode("utf-8") if not private_key_pem.startswith("-----") else
            private_key_pem.encode("utf-8"),
            password=None,
        )

        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise SignatureError("Key is not an Ed25519 private key")

        # Sign the package hash
        payload = package.file_hash.encode("utf-8")
        signature = private_key.sign(payload)

        # Encode as hex
        sig_hex = signature.hex()

    except ImportError:
        # Fallback: HMAC-SHA256 with a derived key
        logger.warning("cryptography library not available; using HMAC-SHA256 fallback")
        import hmac
        import os

        # If private_key_pem is the actual key material, use it directly
        key_material = private_key_pem.encode("utf-8")
        sig_bytes = hmac.new(key_material, package.file_hash.encode("utf-8"), "sha256").digest()
        sig_hex = sig_bytes.hex()
    except Exception as exc:
        raise SignatureError(f"Signing failed: {exc}") from exc

    # Write signature into the package
    signature_data = {
        "key_id": key_id,
        "algorithm": "ed25519" if "cryptography" in sys.modules else "hmac-sha256",
        "signature": sig_hex,
        "file_hash": package.file_hash,
        "file_size": package.file_size,
    }
    _write_signature_to_package(package, signature_data)

    return sig_hex


def verify_signature(
    package: PluginPackage,
    publisher_key: PublisherKey,
) -> bool:
    """Verify a plugin package's signature against a publisher's public key.

    Args:
        package: The PluginPackage to verify.
        publisher_key: The publisher's public key.

    Returns:
        True if the signature is valid.

    Raises:
        SignatureError: If verification fails or no signature is found.
    """
    # Read signature from package
    signature_data = _read_signature_from_package(package)
    if signature_data is None:
        raise SignatureError("No signature found in package")

    # Verify file hash matches
    current_hash = package._compute_hash()
    stored_hash = signature_data.get("file_hash", "")
    if current_hash != stored_hash:
        raise SignatureError(
            f"File hash mismatch: current={current_hash[:16]}... "
            f"stored={stored_hash[:16]}..."
        )

    algorithm = signature_data.get("algorithm", "ed25519")

    if algorithm == "hmac-sha256":
        # HMAC fallback: only valid when the package was signed with the
        # HMAC fallback path (cryptography unavailable at sign time).
        import hmac

        expected_sig = bytes.fromhex(signature_data.get("signature", ""))
        key_material = publisher_key.public_key.encode("utf-8")
        computed = hmac.new(key_material, current_hash.encode("utf-8"),
                            "sha256").digest()
        return hmac.compare_digest(expected_sig, computed)

    if algorithm == "ed25519":
        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519
        except ImportError as exc:
            raise SignatureError(
                "cryptography library required to verify Ed25519 signatures"
            ) from exc
        try:
            raw = publisher_key.public_key.strip()
            if raw.startswith("ssh-ed25519 "):
                # OpenSSH public key format: "ssh-ed25519 <base64> [comment]"
                import base64
                blob = base64.b64decode(raw.split()[1])
                # blob = string("ssh-ed25519") + string(32-byte key)
                key_bytes = blob[-32:]
            else:
                # Raw 32-byte public key as hex.
                key_bytes = bytes.fromhex(raw)
            if len(key_bytes) != 32:
                raise SignatureError("Ed25519 public key must be 32 bytes")
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(key_bytes)
            public_key.verify(bytes.fromhex(signature_data.get("signature", "")),
                              current_hash.encode("utf-8"))
            return True
        except SignatureError:
            raise
        except Exception as exc:
            raise SignatureError(f"Ed25519 verification failed: {exc}") from exc

    raise SignatureError(f"Unsupported signature algorithm: {algorithm}")


def _write_signature_to_package(
    package: PluginPackage,
    signature_data: Dict[str, Any],
) -> None:
    """Write the signature file into the package directory."""
    if package.source_dir is None:
        raise SignatureError("Package has no source directory — cannot write signature")

    sig_path = package.source_dir / ".signature"
    sig_path.write_text(json.dumps(signature_data, indent=2), encoding="utf-8")


def _read_signature_from_package(
    package: PluginPackage,
) -> Optional[Dict[str, Any]]:
    """Read the signature file from a package."""
    if package.source_dir is not None:
        sig_path = package.source_dir / ".signature"
        if sig_path.exists():
            return json.loads(sig_path.read_text(encoding="utf-8"))

    # Try reading from the .aep archive
    if package.package_path and package.package_path.exists():
        import gzip
        import tarfile
        try:
            with gzip.open(package.package_path, "rb") as f_gz:
                with tarfile.open(fileobj=f_gz, mode="r") as tar:
                    try:
                        member = tar.getmember(".signature")
                    except KeyError:
                        return None
                    f = tar.extractfile(member)
                    if f:
                        return json.loads(f.read().decode("utf-8"))
        except Exception:
            return None

    return None

