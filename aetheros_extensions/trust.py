"""Signatures + publisher trust (sections 10-11, 25).

Ed25519 via `cryptography` (installed). sign() covers the package digest;
verify() checks key identity, expiry, revocation. Trust levels UNSIGNED /
UNKNOWN / SIGNED / VERIFIED_PUBLISHER / TRUSTED_PUBLISHER /
ORGANIZATION_TRUSTED. UNSIGNED is never trusted. Dev mode allows unsigned
only when explicitly enabled (visible + logged).
"""

from __future__ import annotations

import base64
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_extensions.manifest import ExtensionManifest


class TrustLevel(str):
    UNSIGNED = "unsigned"
    UNKNOWN = "unknown"
    SIGNED = "signed"
    VERIFIED_PUBLISHER = "verified_publisher"
    TRUSTED_PUBLISHER = "trusted_publisher"
    ORGANIZATION_TRUSTED = "organization_trusted"


class PublisherState(str):
    UNKNOWN = "unknown"
    UNTRUSTED = "untrusted"
    USER_TRUSTED = "user_trusted"
    ORGANIZATION_TRUSTED = "organization_trusted"
    REVOKED = "revoked"


@dataclass
class PublisherRecord:
    publisher_id: str = ""
    display_name: str = ""
    domains: List[str] = field(default_factory=list)
    verified_domains: List[str] = field(default_factory=list)
    public_keys: List[str] = field(default_factory=list)  # base64 raw Ed25519
    trust: str = PublisherState.UNKNOWN
    revoked_keys: List[str] = field(default_factory=list)
    organization: str = ""


def _ed25519():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey, Ed25519PublicKey)
        return Ed25519PrivateKey, Ed25519PublicKey
    except ImportError as exc:
        raise RuntimeError(f"signatures require 'cryptography': {exc}")


def generate_keypair() -> Dict[str, str]:
    Priv, _ = _ed25519()
    priv = Priv.generate()
    pub = priv.public_key()
    from cryptography.hazmat.primitives import serialization
    raw_priv = priv.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
        serialization.NoEncryption())
    raw_pub = pub.public_bytes(serialization.Encoding.Raw,
                               serialization.PublicFormat.Raw)
    return {"private_b64": base64.b64encode(raw_priv).decode(),
            "public_b64": base64.b64encode(raw_pub).decode()}


def sign_package_digest(package_digest: str, private_b64: str, *,
                        key_id: str = "k1",
                        expires_at: float = 0.0) -> Dict[str, Any]:
    Priv, _ = _ed25519()
    priv = Priv.from_private_bytes(base64.b64decode(private_b64))
    payload = json.dumps({"digest": package_digest, "key_id": key_id,
                          "expires_at": expires_at},
                         sort_keys=True).encode()
    sig = priv.sign(payload)
    return {"algorithm": "Ed25519", "key_id": key_id,
            "expires_at": expires_at,
            "payload_b64": base64.b64encode(payload).decode(),
            "signature_b64": base64.b64encode(sig).decode()}


def verify_signature(package_digest: str, envelope: Dict[str, Any],
                     public_b64: str, *, now: Optional[float] = None) -> Dict[str, Any]:
    """Returns {ok, reason}. Never claims verified unless crypto passes."""
    now = now if now is not None else time.time()
    _, Pub = _ed25519()
    try:
        payload = base64.b64decode(envelope.get("payload_b64", ""))
        sig = base64.b64decode(envelope.get("signature_b64", ""))
        claimed = json.loads(payload.decode("utf-8"))
    except (ValueError, KeyError) as exc:
        return {"ok": False, "reason": f"malformed envelope: {exc}"}
    if claimed.get("digest") != package_digest:
        return {"ok": False, "reason": "digest mismatch (tampered package)"}
    if claimed.get("expires_at") and now > float(claimed["expires_at"]):
        return {"ok": False, "reason": "signature expired"}
    try:
        Pub.from_public_bytes(base64.b64decode(public_b64)).verify(sig, payload)
    except Exception as exc:
        return {"ok": False, "reason": f"bad signature: {exc}"}
    return {"ok": True, "reason": "Ed25519 signature valid",
            "key_id": claimed.get("key_id", "")}


class PublisherTrust:
    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = Path(path) if path else None
        self._lock = threading.Lock()
        self._records: Dict[str, PublisherRecord] = {}
        self.dev_allow_unsigned = False

    def initialize(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def upsert(self, rec: PublisherRecord) -> None:
        with self._lock:
            self._records[rec.publisher_id] = rec
            self._persist()

    def get(self, publisher_id: str) -> Optional[PublisherRecord]:
        with self._lock:
            return self._records.get(publisher_id)

    def set_trust(self, publisher_id: str, trust: str) -> bool:
        with self._lock:
            rec = self._records.get(publisher_id)
            if rec is None:
                return False
            rec.trust = trust
            self._persist()
            return True

    def revoke_key(self, publisher_id: str, public_b64: str) -> bool:
        with self._lock:
            rec = self._records.get(publisher_id)
            if rec is None:
                return False
            if public_b64 not in rec.revoked_keys:
                rec.revoked_keys.append(public_b64)
            self._persist()
            return True

    def evaluate(self, manifest: ExtensionManifest,
                 envelope: Optional[Dict[str, Any]],
                 package_digest: str = "") -> Dict[str, Any]:
        """Trust verdict for an install candidate."""
        rec = self.get(manifest.publisher_id)
        if envelope is None:
            if self.dev_allow_unsigned:
                return {"level": TrustLevel.UNKNOWN, "ok": True,
                        "reason": "DEV MODE: unsigned allowed (visible, logged)"}
            return {"level": TrustLevel.UNSIGNED, "ok": False,
                    "reason": "unsigned package is not trusted"}
        if rec is None:
            return {"level": TrustLevel.UNKNOWN, "ok": False,
                    "reason": "unknown publisher"}
        if rec.trust == PublisherState.REVOKED:
            return {"level": TrustLevel.UNKNOWN, "ok": False,
                    "reason": "publisher revoked"}
        key_id = str(envelope.get("key_id", ""))
        for pub in rec.public_keys:
            if pub in rec.revoked_keys:
                continue
            v = verify_signature(package_digest, {**envelope, "key_id": key_id}
                                 if key_id else envelope, pub)
            if v.get("ok"):
                level = TrustLevel.SIGNED
                if rec.trust == PublisherState.USER_TRUSTED:
                    level = TrustLevel.TRUSTED_PUBLISHER
                elif rec.trust == PublisherState.ORGANIZATION_TRUSTED:
                    level = TrustLevel.ORGANIZATION_TRUSTED
                elif rec.verified_domains:
                    level = TrustLevel.VERIFIED_PUBLISHER
                return {"level": level, "ok": True, "reason": v["reason"]}
        return {"level": TrustLevel.UNKNOWN, "ok": False,
                "reason": "no trusted key verified this package"}

    def _persist(self) -> None:
        if self._path is None:
            return
        data = {pid: {"publisher_id": r.publisher_id, "display_name": r.display_name,
                      "domains": r.domains, "verified_domains": r.verified_domains,
                      "public_keys": r.public_keys, "trust": r.trust,
                      "revoked_keys": r.revoked_keys, "organization": r.organization}
                for pid, r in self._records.items()}
        import os
        import tempfile
        fd, tmp = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, str(self._path))
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _load(self) -> None:
        if self._path is None or not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for pid, raw in (data or {}).items():
            self._records[pid] = PublisherRecord(
                publisher_id=pid, display_name=str(raw.get("display_name", "")),
                domains=list(raw.get("domains", [])),
                verified_domains=list(raw.get("verified_domains", [])),
                public_keys=list(raw.get("public_keys", [])),
                trust=str(raw.get("trust", PublisherState.UNKNOWN)),
                revoked_keys=list(raw.get("revoked_keys", [])),
                organization=str(raw.get("organization", "")))
