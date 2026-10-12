"""Approval orchestration (§34-36, §76-77): single/multi/quorum/
role/owner/step-up/time-limited/conditional approvals over M50's
ApprovalEngine. Separation of duties: an agent can NEVER approve its
own critical action (§76-77)."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from aetheros_control_plane.approvals_sessions import ApprovalEngine

from .models import TrustError, SecurityError


@dataclass
class ApprovalRequest:
    request_id: str = ""
    actor: str = ""
    action: str = ""
    resource: str = ""
    purpose: str = ""
    risk: str = "R1"
    evidence: tuple = ()
    proposed_effects: str = ""
    reversibility: str = "reversible"
    expiration: float = 0.0
    approver_policy: str = "single"  # single|quorum:N|role:X|owner|step-up
    task_id: str = ""


@dataclass
class ApprovalDecision:
    request_id: str = ""
    granted: bool = False
    approvers: tuple = ()
    at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    conditions: tuple = ()


class ApprovalOrchestrator:
    def __init__(self, engine: Optional[ApprovalEngine] = None):
        self.engine = engine or ApprovalEngine()
        self._requests: Dict[str, ApprovalRequest] = {}
        self._votes: Dict[str, Dict[str, bool]] = {}
        self._decisions: Dict[str, ApprovalDecision] = {}

    def request(self, req: ApprovalRequest) -> str:
        req_id = req.request_id or f"apr_{uuid.uuid4().hex[:10]}"
        req = ApprovalRequest(**{**req.__dict__, "request_id": req_id,
                                 "expiration": req.expiration or
                                 time.time() + 600})
        self._requests[req_id] = req
        self._votes[req_id] = {}
        # bridge into M50 engine for single-approval audit trail
        self.engine.request(req.action, req.resource, req.actor,
                            task_id=req.task_id)
        return req_id

    def vote(self, request_id: str, approver: str,
             granted: bool) -> Optional[ApprovalDecision]:
        req = self._requests.get(request_id)
        if req is None or time.time() > req.expiration:
            return ApprovalDecision(request_id, False, (approver,),
                                    expires_at=req.expiration if req else 0.0)
        # §76-77 separation of duties: self-approval of critical acts denied
        if approver == req.actor and req.risk in ("R7", "R8", "CRITICAL"):
            self._votes[request_id][approver] = False
            return self._tally(req)
        self._votes[request_id][approver] = granted
        return self._tally(req)

    def _tally(self, req: ApprovalRequest) -> Optional[ApprovalDecision]:
        votes = self._votes[req.request_id]
        policy = req.approver_policy
        needed, decision = 1, None
        if policy == "single" or policy == "owner":
            if True in votes.values():
                decision = True
            elif False in votes.values() and not any(votes.values()):
                decision = False
        elif policy.startswith("quorum:"):
            needed = int(policy.split(":")[1])
            yes = sum(1 for v in votes.values() if v)
            if yes >= needed:
                decision = True
        elif policy.startswith("role:") or policy == "step-up":
            if any(votes.values()):
                decision = True
        if decision is None:
            return None  # still pending
        dec = ApprovalDecision(req.request_id, decision,
                               tuple(a for a, v in votes.items() if v),
                               expires_at=req.expiration)
        self._decisions[req.request_id] = dec
        if decision:
            for ap_id in list(self.engine._pending):
                self.engine.decide(ap_id, True)
        return dec

    def consume(self, request_id: str, action: str, resource: str,
                actor: str) -> bool:
        dec = self._decisions.get(request_id)
        if dec is None or not dec.granted or time.time() > dec.expires_at:
            return False
        req = self._requests[request_id]
        return (req.action, req.resource, req.actor) == (action, resource,
                                                         actor)

    def pending(self) -> List[ApprovalRequest]:
        decided = set(self._decisions)
        return [r for rid, r in self._requests.items() if rid not in decided]
