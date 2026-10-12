"""Identity plane (§3) + capability attestation (§8).

Never treats display names as identities. Binds identities to Ed25519
key ids from :mod:`crypto_keys`. Lifecycle enforced on every lookup.
Wraps the existing ``aetheros_security.identity`` registry where
available (adapter, §104) but remains fully functional standalone.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .crypto_keys import KeyStore
from .models import Identity, IdentityStatus, IdentityType, TrustLevel, new_id
from .scopes import ScopeSet


class IdentityPlane:
    def __init__(self, keys: Optional[KeyStore] = None):
        self._identities: Dict[str, Identity] = {}
        self._scopes: Dict[str, ScopeSet] = {}
        self.keys = keys or KeyStore()
        # Best-effort adapter to the legacy registry (§104 legacy path).
        try:
            from aetheros_security.identity import IdentityRegistry  # type: ignore
            self._legacy = IdentityRegistry()
        except Exception:
            self._legacy = None

    # -- lifecycle ---------------------------------------------------------
    def create(self, type: IdentityType, display_name: str,
               subject: str = "", organization: str = "default",
               tenant: str = "default",
               capabilities: Optional[List[str]] = None,
               scopes: Optional[List[str]] = None,
               trust: TrustLevel = TrustLevel.T0_UNKNOWN,
               expires_in: Optional[float] = None) -> Identity:
        ident = Identity(
            id=new_id("idn"), type=type, subject=subject or new_id("sub"),
            display_name=display_name,
            capabilities=list(capabilities or []),
            scopes=list(scopes or []),
            trust_level=trust, organization=organization, tenant=tenant,
            expires_at=(time.time() + expires_in) if expires_in else None,
            status=IdentityStatus.ACTIVE,
            provenance={"created_by": "control-plane", "at": time.time()},
        )
        # Every identity gets its own signing key (§4).
        pub = self.keys.generate(ident.id)
        ident.key_ids.append(pub.key_id)
        self._identities[ident.id] = ident
        self._scopes[ident.id] = ScopeSet()
        for s in (scopes or []):
            self._scopes[ident.id].grant(s, tenant=tenant)
        return ident

    def get(self, identity_id: str) -> Optional[Identity]:
        ident = self._identities.get(identity_id)
        if ident is None:
            return None
        if ident.expires_at and time.time() > ident.expires_at:
            ident.status = IdentityStatus.EXPIRED
        return ident

    def usable(self, identity_id: str) -> bool:
        ident = self.get(identity_id)
        return bool(ident and ident.is_usable())

    def set_status(self, identity_id: str, status: IdentityStatus) -> bool:
        ident = self._identities.get(identity_id)
        if ident is None:
            return False
        ident.status = status
        ident.version += 1
        return True

    suspend = lambda self, i: self.set_status(i, IdentityStatus.SUSPENDED)
    revoke = lambda self, i: self.set_status(i, IdentityStatus.REVOKED)
    quarantine = lambda self, i: self.set_status(i, IdentityStatus.QUARANTINED)

    def rotate_keys(self, identity_id: str) -> Optional[str]:
        ident = self._identities.get(identity_id)
        if ident is None or not ident.key_ids:
            return None
        new = self.keys.rotate(ident.key_ids[-1])
        ident.key_ids.append(new.key_id)
        ident.version += 1
        return new.key_id

    def scopes_for(self, identity_id: str) -> ScopeSet:
        return self._scopes.setdefault(identity_id, ScopeSet())

    def list(self) -> List[Identity]:
        return list(self._identities.values())


# ---------------------------------------------------------------------------
# Capability attestation (§8): claims are NOT capabilities
# ---------------------------------------------------------------------------

@dataclass
class CapabilityAttestation:
    capability: str
    identity_id: str
    verifier: str
    evidence: str = ""
    level: str = "execute"  # read|write|execute|delegate|admin
    at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None

    def valid(self) -> bool:
        return self.expires_at is None or time.time() < self.expires_at


class CapabilityRegistry:
    """Claimed capabilities must be attested by a verifier before use."""

    def __init__(self) -> None:
        self._claims: Dict[str, List[str]] = {}
        self._attested: Dict[str, List[CapabilityAttestation]] = {}

    def claim(self, identity_id: str, capability: str) -> None:
        self._claims.setdefault(identity_id, [])
        if capability not in self._claims[identity_id]:
            self._claims[identity_id].append(capability)

    def attest(self, att: CapabilityAttestation) -> None:
        self._attested.setdefault(att.identity_id, []).append(att)

    def attested_capabilities(self, identity_id: str) -> List[str]:
        return [a.capability for a in self._attested.get(identity_id, [])
                if a.valid()]

    def is_attested(self, identity_id: str, capability: str) -> bool:
        return capability in self.attested_capabilities(identity_id)
