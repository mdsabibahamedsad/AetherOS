"""Capability tokens (§10-11, §113): short-lived Ed25519-signed
WHO/WHAT/WHERE/WHY/WHEN/LIMITS tokens validated independently by the
tool runtime. Nonce + expiry + audience + max-use replay defense."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Dict, List, Optional

from aetheros_control_plane.crypto_keys import (
    KeyResolver,
    KeyStore,
    SignatureVerifier,
)

from .models import CapabilityToken, TrustError, SecurityError, new_id


def _canonical(token: CapabilityToken) -> bytes:
    body = {k: v for k, v in token.__dict__.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, default=str).encode()


class CapabilityAuthority:
    def __init__(self, keys: KeyStore, key_id: str):
        self.keys = keys
        self.key_id = key_id
        resolver = KeyResolver()
        resolver.attach(keys)
        self.verifier = SignatureVerifier(resolver)
        self._seen_nonces: Dict[str, float] = {}
        self._uses: Dict[str, int] = {}

    def issue(self, subject: str, action: str, resource: str,
              purpose: str, ttl_s: float = 300.0, max_uses: int = 1,
              data_limit: str = "INTERNAL", network_policy: str = "deny",
              approval_id: str = "", audience: str = "",
              issuer: str = "trust-fabric") -> CapabilityToken:
        now = time.time()
        token = CapabilityToken(
            token_id=new_id("ctok"), subject=subject, action=action,
            resource=resource, purpose=purpose, issued_at=now,
            expires_at=now + ttl_s, max_uses=max_uses, uses=0,
            data_limit=data_limit, network_policy=network_policy,
            approval_id=approval_id, audience=audience, issuer=issuer,
            nonce=uuid.uuid4().hex)
        sig = self.keys.sign(self.key_id, _canonical(token))
        return CapabilityToken(**{**token.__dict__, "signature": sig})

    def validate(self, token: CapabilityToken,
                 audience: str) -> CapabilityToken:
        """Independent tool-side validation. Raises TrustError on any
        failure — fail closed (§40)."""
        now = time.time()
        if not token.signature:
            raise TrustError(SecurityError.AUTHORITY_MISSING,
                             "unsigned capability token")
        try:
            ok = self.verifier.verify(self.key_id, _canonical(token),
                                      token.signature)
        except Exception:
            ok = False
        if not ok:
            raise TrustError(SecurityError.AUTHORITY_MISSING,
                             "invalid token signature")
        if now > token.expires_at:
            raise TrustError(SecurityError.CAPABILITY_EXPIRED,
                             f"token {token.token_id} expired")
        if token.audience and token.audience != audience:
            raise TrustError(SecurityError.AUTHORITY_MISSING,
                             "token audience mismatch")
        if token.nonce in self._seen_nonces and token.max_uses <= 1:
            raise TrustError(SecurityError.AUTHORITY_MISSING,
                             "token replay rejected")
        used = self._uses.get(token.token_id, 0)
        if used >= token.max_uses:
            raise TrustError(SecurityError.CAPABILITY_EXPIRED,
                             "token max-uses exhausted")
        self._seen_nonces[token.nonce] = now
        self._uses[token.token_id] = used + 1
        self._gc(now)
        return token

    def _gc(self, now: float) -> None:
        old = [n for n, t in self._seen_nonces.items() if now - t > 3600]
        for n in old:
            del self._seen_nonces[n]


def token_hash(token: CapabilityToken) -> str:
    return hashlib.sha256(_canonical(token)).hexdigest()
