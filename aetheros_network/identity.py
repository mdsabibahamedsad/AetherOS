"""Canonical agent identity (Master 46 section 5).

Identity is stable and auditable. Agents are never identified solely by
hostname, IP, URL, or display name: the canonical key is ``agent_id`` plus
the public-key fingerprint. Hostnames/URLs are endpoints (mutable);
identity is the key binding.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

_AGENT_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")


def new_agent_id(organization_id: str = "local") -> str:
    """Mint a canonical agent id: ``aetheros:<org>:<12 hex>``."""
    org = re.sub(r"[^a-zA-Z0-9_-]", "-", organization_id)[:48] or "local"
    return f"aetheros:{org}:{secrets.token_hex(6)}"


def new_instance_id() -> str:
    return f"inst-{uuid.uuid4().hex[:12]}"


def fingerprint_public_key(public_key_der: bytes) -> str:
    """Stable key fingerprint: ``sha256:<hex>`` of the DER bytes."""
    return "sha256:" + hashlib.sha256(public_key_der).hexdigest()


def generate_signing_keypair() -> Dict[str, bytes]:
    """Generate an Ed25519 signing keypair. Requires ``cryptography``."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    private = ed25519.Ed25519PrivateKey.generate()
    public = private.public_key()
    priv_der = private.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub_der = public.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return {"private_der": priv_der, "public_der": pub_der}


@dataclass
class AgentIdentity:
    """Canonical, auditable identity for one agent principal."""

    agent_id: str
    canonical_name: str = ""
    display_name: str = ""
    instance_id: str = ""
    organization_id: str = "local"
    owner: str = ""
    issuer: str = ""  # who vouched for this identity (org CA, pairing, self)
    public_keys: List[str] = field(default_factory=list)  # key fingerprints
    endpoints: List[str] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)  # e.g. ["A2A/1.0"]
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0  # 0 = no expiry
    status: str = "active"  # active | suspended | revoked | expired
    trust_level: str = "unknown"
    revocation_status: str = "good"  # good | revoked | unknown

    def validate(self) -> List[str]:
        errors = []
        if not _AGENT_ID_RE.match(self.agent_id or ""):
            errors.append(f"invalid agent_id: {self.agent_id!r}")
        if self.expires_at and self.expires_at <= self.created_at:
            errors.append("expires_at must be after created_at")
        if self.status not in ("active", "suspended", "revoked", "expired", "offline"):
            errors.append(f"unknown status: {self.status!r}")
        return errors

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at) and time.time() > self.expires_at

    @property
    def effective_status(self) -> str:
        if self.revocation_status == "revoked" or self.status == "revoked":
            return "revoked"
        if self.is_expired:
            return "expired"
        return self.status

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentIdentity":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    def audit_key(self) -> str:
        """Short stable key for logs: agent_id + first key fingerprint."""
        fp = (self.public_keys[0][-12:] if self.public_keys else "nokey")
        return f"{self.agent_id}#{fp}"


def sign_bytes(private_key_der: bytes, payload: bytes) -> bytes:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    private = serialization.load_der_private_key(private_key_der, password=None)
    assert isinstance(private, ed25519.Ed25519PrivateKey)
    return private.sign(payload)


def verify_signature(public_key_der: bytes, signature: bytes, payload: bytes) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization

    public = serialization.load_der_public_key(public_key_der)
    try:
        public.verify(signature, payload)  # type: ignore[attr-defined]
        return True
    except (InvalidSignature, Exception):
        return False
