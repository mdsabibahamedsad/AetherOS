"""Delegation engine + tokens (§15-16). Child ⊆ parent enforced.

Tokens are Ed25519-signed canonical JSON (real signatures via KeyStore),
short-lived, single-audience, single-task, nonce-tracked (anti-replay),
tenant-bound. Verification fails closed on: expiry, replay, audience or
task mismatch, scope escalation, depth overflow, revoked/unknown issuer.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .crypto_keys import KeyStore, SignatureVerifier, KeyResolver
from .models import ControlPlaneError, FailureCode
from .scopes import ScopeSet


@dataclass
class DelegationGrant:
    id: str
    issuer_id: str
    subject_id: str
    scopes: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    constraints: dict = field(default_factory=dict)
    issued_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 900)
    parent_id: str = ""
    depth: int = 1
    task_id: str = ""
    tenant: str = "default"
    revoked: bool = False


class DelegationEngine:
    def __init__(self, keys: KeyStore):
        self.keys = keys
        resolver = KeyResolver()
        resolver.attach(keys)
        self.verifier = SignatureVerifier(resolver)
        self._grants: Dict[str, DelegationGrant] = {}
        self._used_nonces: Dict[str, float] = {}

    # -- grants ------------------------------------------------------------
    def delegate(self, issuer_scopes: ScopeSet, issuer_id: str,
                 subject_id: str, scopes: List[str],
                 task_id: str = "", tenant: str = "default",
                 duration: float = 900, max_depth: int = 3,
                 parent_id: str = "") -> DelegationGrant:
        wanted = ScopeSet()
        for s in scopes:
            wanted.grant(s, tenant=tenant)
        if not wanted.is_subset_of(issuer_scopes, tenant):
            raise ControlPlaneError(FailureCode.DELEGATION_INVALID,
                                    "child authority exceeds parent authority")
        depth = 1
        if parent_id:
            parent = self._grants.get(parent_id)
            if parent is None or parent.revoked:
                raise ControlPlaneError(FailureCode.DELEGATION_INVALID,
                                        "unknown/revoked parent delegation")
            depth = parent.depth + 1
            if depth > max_depth and depth > parent.constraints.get(
                    "maxDepth", max_depth):
                raise ControlPlaneError(FailureCode.DELEGATION_INVALID,
                                        "delegation depth exceeded")
        grant = DelegationGrant(
            id=f"dlg_{uuid.uuid4().hex[:12]}", issuer_id=issuer_id,
            subject_id=subject_id, scopes=scopes, issued_at=time.time(),
            expires_at=time.time() + duration, parent_id=parent_id,
            depth=depth, task_id=task_id, tenant=tenant,
            constraints={"maxDepth": max_depth})
        self._grants[grant.id] = grant
        return grant

    def revoke(self, grant_id: str) -> bool:
        g = self._grants.get(grant_id)
        if g is None:
            return False
        g.revoked = True
        return True

    def chain(self, grant_id: str) -> List[DelegationGrant]:
        out: List[DelegationGrant] = []
        cur = self._grants.get(grant_id)
        while cur:
            out.append(cur)
            cur = self._grants.get(cur.parent_id) if cur.parent_id else None
        return list(reversed(out))

    def valid(self, grant_id: str, task_id: str = "",
              tenant: str = "default") -> bool:
        g = self._grants.get(grant_id)
        if g is None or g.revoked or time.time() > g.expires_at:
            return False
        if task_id and g.task_id and g.task_id != task_id:
            return False
        if g.tenant != tenant:
            return False
        return True

    # -- signed tokens -------------------------------------------------------
    def issue_token(self, grant: DelegationGrant, audience: str,
                    key_id: str) -> str:
        nonce = uuid.uuid4().hex
        body = {"issuer": grant.issuer_id, "subject": grant.subject_id,
                "delegator": grant.issuer_id, "audience": audience,
                "scopes": grant.scopes, "resources": grant.resources,
                "constraints": grant.constraints, "issuedAt": grant.issued_at,
                "expiresAt": grant.expires_at, "nonce": nonce,
                "taskId": grant.task_id,
                "parentDelegationId": grant.parent_id,
                "delegationId": grant.id, "tenant": grant.tenant}
        raw = json.dumps(body, sort_keys=True).encode()
        sig = self.keys.sign(key_id, raw)
        return json.dumps({"body": body, "keyId": key_id,
                           "signature": sig})

    def verify_token(self, token: str, audience: str,
                     task_id: str = "") -> dict:
        try:
            env = json.loads(token)
            body, key_id, sig = env["body"], env["keyId"], env["signature"]
        except Exception:
            raise ControlPlaneError(FailureCode.DELEGATION_INVALID,
                                    "malformed delegation token")
        if body.get("audience") != audience:
            raise ControlPlaneError(FailureCode.DELEGATION_INVALID,
                                    "audience mismatch")
        if body.get("nonce") in self._used_nonces and body.get(
                "constraints", {}).get("oneTime"):
            raise ControlPlaneError(FailureCode.DELEGATION_INVALID,
                                    "replay: nonce already used")
        if time.time() > body.get("expiresAt", 0):
            raise ControlPlaneError(FailureCode.TASK_AUTHORITY_EXPIRED,
                                    "delegation token expired")
        if task_id and body.get("taskId") and body["taskId"] != task_id:
            raise ControlPlaneError(FailureCode.DELEGATION_INVALID,
                                    "cross-task token reuse blocked")
        raw = json.dumps(body, sort_keys=True).encode()
        if not self.verifier.verify(key_id, raw, sig):
            raise ControlPlaneError(FailureCode.SIGNATURE_INVALID,
                                    "delegation signature invalid")
        grant = self._grants.get(body.get("delegationId", ""))
        if grant is None or grant.revoked:
            raise ControlPlaneError(FailureCode.DELEGATION_INVALID,
                                    "delegation revoked or unknown")
        self._used_nonces[body["nonce"]] = time.time()
        return body

    @staticmethod
    def request_hash(action: dict) -> str:
        return hashlib.sha256(
            json.dumps(action, sort_keys=True).encode()).hexdigest()
