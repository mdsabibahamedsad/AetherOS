"""
Approval Management for AetherOS
===============================

Human approval for high-risk actions. Approvals are **bound to the exact
action** — an approved request does NOT authorize a different action, a
different resource, a different recipient, or additional side effects
(master security spec steps 13-14).

An approval carries:
    - principal, action, resource (the exact binding)
    - risk level and reason
    - an expiry timestamp (approvals do not live forever)
    - a fingerprint computed over the exact action+resource+parameters

Resolution happens OUTSIDE the model's reasoning loop — a deterministic
callback decides ALLOW / DENY. A resolved approval is single-use and
cannot be replayed for a different resource.

Usage::

    from aetheros_security.approval import ApprovalManager, ApprovalStatus

    manager = ApprovalManager()
    approval = manager.create("agent-1", "email:send", "john@example.com",
                              risk="high", reason="Send report")
    ok = manager.resolve(approval.approval_id, approved=True)
    assert manager.is_valid(approval.approval_id, "email:send",
                            "john@example.com")
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 300  # 5 minutes


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class Approval:
    """A single-action approval."""
    approval_id: str
    principal: str
    action: str
    resource: str
    risk: str = "high"
    reason: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = 0.0
    expires_at: float = 0.0
    resolved_at: float = 0.0
    fingerprint: str = ""
    resolver: str = "user"

    def __post_init__(self) -> None:
        now = time.time()
        if not self.approval_id:
            self.approval_id = uuid.uuid4().hex
        if not self.created_at:
            self.created_at = now
        if not self.expires_at:
            self.expires_at = now + _DEFAULT_TTL_SECONDS
        if not self.fingerprint:
            self.fingerprint = compute_fingerprint(
                self.action, self.resource, self.parameters,
            )

    @property
    def expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "principal": self.principal,
            "action": self.action,
            "resource": self.resource,
            "risk": self.risk,
            "reason": self.reason,
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "resolved_at": self.resolved_at,
            "fingerprint": self.fingerprint,
        }


def compute_fingerprint(action: str, resource: str,
                        parameters: Optional[Dict[str, Any]] = None) -> str:
    """Stable fingerprint of the exact action, resource, and parameters.

    Two approvals for the same action on a different resource produce
    different fingerprints, so a binding cannot be replayed elsewhere.
    """
    payload = json.dumps({
        "action": (action or "").lower(),
        "resource": resource or "",
        "parameters": parameters or {},
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ApprovalError(Exception):
    """Raised for invalid approval operations."""


class ApprovalManager:
    """Manages the approval lifecycle.

    Approvals are held in-memory for the process lifetime; persistence is
    intentionally minimal (approvals are short-lived by design).
    """

    def __init__(self, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
        self._approvals: Dict[str, Approval] = {}
        self._ttl_seconds = ttl_seconds
        self._resolver: Optional[Callable[[Approval], bool]] = None

    def register_resolver(self, resolver: Callable[[Approval], bool]) -> None:
        """Register the deterministic human-approval resolver.

        The resolver receives the full approval binding and returns True to
        allow, False to deny. This is the ONLY way approvals are decided —
        never by model reasoning.
        """
        self._resolver = resolver

    def create(
        self,
        principal: str,
        action: str,
        resource: str = "",
        *,
        risk: str = "high",
        reason: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> Approval:
        """Create a new approval for one exact action."""
        now = time.time()
        approval = Approval(
            approval_id=uuid.uuid4().hex,
            principal=principal,
            action=action,
            resource=resource,
            risk=risk,
            reason=reason,
            parameters=parameters or {},
            created_at=now,
            expires_at=now + (ttl_seconds or self._ttl_seconds),
        )
        self._approvals[approval.approval_id] = approval
        logger.info("Approval created: %s %s on %s (risk=%s)",
                    principal, action, resource, risk)
        self._emit_audit("approval_created", principal,
                         {"approval_id": approval.approval_id,
                          "action": action, "resource": resource, "risk": risk})
        return approval

    def get(self, approval_id: str) -> Optional[Approval]:
        return self._approvals.get(approval_id)

    def pending(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._approvals.values()
                if a.status == ApprovalStatus.PENDING]

    def resolve(self, approval_id: str, *, approved: bool,
                resolver: str = "user") -> bool:
        """Resolve a pending approval.

        Returns True if the approval was successfully resolved (now
        APPROVED or DENIED). Expired approvals are marked EXPIRED and
        resolve to False.
        """
        approval = self._approvals.get(approval_id)
        if approval is None:
            return False
        if approval.status != ApprovalStatus.PENDING:
            return False
        if approval.expired:
            approval.status = ApprovalStatus.EXPIRED
            return False
        approval.status = (ApprovalStatus.APPROVED if approved
                           else ApprovalStatus.DENIED)
        approval.resolved_at = time.time()
        approval.resolver = resolver
        self._emit_audit("approval_resolved", approval.principal,
                         {"approval_id": approval_id, "approved": approved})
        return True

    def is_valid(self, approval_id: str, action: str, resource: str,
                 parameters: Optional[Dict[str, Any]] = None) -> bool:
        """Whether an approval still authorizes the EXACT action+resource.

        The fingerprint must match, the approval must be APPROVED, and it
        must not have expired.
        """
        approval = self._approvals.get(approval_id)
        if approval is None:
            return False
        if approval.status != ApprovalStatus.APPROVED:
            return False
        if approval.expired:
            approval.status = ApprovalStatus.EXPIRED
            return False
        if not hmac.compare_digest(
                approval.fingerprint,
                compute_fingerprint(action, resource, parameters)):
            return False
        return True

    def check_and_consume(self, approval_id: str, action: str, resource: str,
                          parameters: Optional[Dict[str, Any]] = None) -> bool:
        """Validate an approval and consume it (single-use).

        Once consumed, the approval cannot be reused — even for the same
        exact action. This implements "approve once, act once."
        """
        if not self.is_valid(approval_id, action, resource, parameters):
            return False
        approval = self._approvals.get(approval_id)
        if approval is not None:
            approval.status = ApprovalStatus.REVOKED  # consumed
            self._emit_audit("approval_consumed", approval.principal,
                             {"approval_id": approval_id})
        return True

    def request_and_resolve(self, principal: str, action: str, resource: str = "",
                            *, reason: str = "",
                            parameters: Optional[Dict[str, Any]] = None,
                            resolver: Optional[Callable[[Approval], bool]] = None,
                            ttl_seconds: Optional[int] = None) -> bool:
        """Create an approval and resolve it through the resolver.

        The resolver (registered or passed) decides. This path never lets
        the model decide — only a deterministic callback.
        """
        approval = self.create(principal, action, resource,
                               reason=reason, parameters=parameters,
                               ttl_seconds=ttl_seconds)
        decide = resolver or self._resolver
        if decide is None:
            logger.warning("No approval resolver registered; denying %s",
                           approval.approval_id)
            self.resolve(approval.approval_id, approved=False, resolver="none")
            return False
        approved = bool(decide(approval))
        self.resolve(approval.approval_id, approved=approved)
        return approved

    def revoke(self, approval_id: str) -> bool:
        approval = self._approvals.get(approval_id)
        if approval is None or approval.status == ApprovalStatus.REVOKED:
            return False
        approval.status = ApprovalStatus.REVOKED
        return True

    def get_stats(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for approval in self._approvals.values():
            key = approval.status.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    @staticmethod
    def _emit_audit(event_type: str, principal: str,
                    details: Dict[str, Any]) -> None:
        try:
            from aetheros_security.audit import (AuditEventType, AuditSeverity,
                                                 get_audit_logger)
            try:
                event = AuditEventType(event_type)
            except ValueError:
                event = AuditEventType.CUSTOM
            get_audit_logger().log(event, severity=AuditSeverity.INFO,
                                   user=principal, source="approval",
                                   details=details,
                                   message=f"Approval: {event_type}")
        except Exception:
            pass


# Global approval manager
_approval_manager: ApprovalManager | None = None


def get_approval_manager() -> ApprovalManager:
    """Return the global ApprovalManager singleton."""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
    return _approval_manager