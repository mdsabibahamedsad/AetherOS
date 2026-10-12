"""Autonomy safety: levels, risk gating, scoped expiring approvals.

- AutonomyEngine.needs_approval(risk, autonomy, policy): risk tiers map to
  minimum autonomy + default approval; explicit settings win over inference
  but inferred behavior never overrides explicit settings.
- ScopedApproval: action+resource+automation+user+expiry; "send email X"
  never authorizes arbitrary emails (scope match required).
- Safe mode: read-only workflows only. Emergency stop handled by service.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_autonomy.models import (
    ActionRisk, ApprovalPolicy, AutonomyLevel,
    RISK_DEFAULT_APPROVAL, RISK_MIN_AUTONOMY,
)


@dataclass
class ScopedApproval:
    id: str = ""
    automation_id: str = ""
    action: str = ""
    resource: str = ""
    user: str = ""
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    approved: bool = False

    def covers(self, *, action: str, resource: str,
               automation_id: str, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.time()
        return (self.approved and self.automation_id == automation_id
                and self.action == action and self.resource == resource
                and (not self.expires_at or now <= self.expires_at))


class AutonomyEngine:
    def __init__(self, *, safe_mode: bool = False) -> None:
        self.safe_mode = safe_mode
        self._scoped: List[ScopedApproval] = []

    def needs_approval(self, risk: ActionRisk, autonomy: AutonomyLevel,
                       policy: ApprovalPolicy) -> bool:
        if policy == ApprovalPolicy.NEVER_ALLOWED:
            return True  # blocked outright (caller must refuse)
        if policy == ApprovalPolicy.ALWAYS_APPROVE:
            return True
        if policy == ApprovalPolicy.PRE_APPROVED:
            if self.safe_mode and risk != ActionRisk.READ:
                return True
            return False
        # APPROVE_ONCE: a live scoped grant covers it (checked separately
        # via covers()); at decision time, approval is required to mint it.
        if policy == ApprovalPolicy.APPROVE_ONCE:
            return True
        return autonomy < RISK_MIN_AUTONOMY.get(risk, AutonomyLevel.SUPERVISED)

    def default_policy(self, risk: ActionRisk) -> ApprovalPolicy:
        return RISK_DEFAULT_APPROVAL.get(risk, ApprovalPolicy.ALWAYS_APPROVE)

    def grant_scoped(self, approval: ScopedApproval) -> ScopedApproval:
        self._scoped.append(approval)
        return approval

    def covers(self, **kw: Any) -> bool:
        return any(a.covers(**kw) for a in self._scoped)

    def prune_expired(self, now: Optional[float] = None) -> int:
        now = now if now is not None else time.time()
        before = len(self._scoped)
        self._scoped = [a for a in self._scoped
                        if not a.expires_at or now <= a.expires_at]
        return before - len(self._scoped)
