"""Action firewall (§42): final enforcement point. No consequential
tool action bypasses it. Pipeline: proposal -> normalize -> identity ->
authority -> policy -> risk -> data -> path -> approval -> capability
token -> execution -> verification -> receipt -> audit."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_control_plane.models import ActionManifest

from . import capabilities as cap_mod
from .models import (ActionProposal, CapabilityToken, ExecutionContext,
                     ExtendedDecision, Risk, SecurityError, TrustError,
                     new_id)
from .paths import ExecutionPathTracker
from .policy_ext import ExplainedDecision, extend_decision
from .risk import RiskEngine


class ActionFirewall:
    def __init__(self, plane, risk: Optional[RiskEngine] = None,
                 paths: Optional[ExecutionPathTracker] = None):
        self.plane = plane
        self.risk = risk or RiskEngine()
        self.paths = paths or ExecutionPathTracker()
        self._decisions: List[ExplainedDecision] = []

    def evaluate(self, proposal: ActionProposal,
                 ctx: ExecutionContext) -> ExplainedDecision:
        ra = self.risk.classify(proposal.capability,
                                proposal.resource.pattern,
                                proposal.data_classification.value,
                                {"task": ctx.task_id})
        gate = self.risk.gate_for(ra.level)
        manifest = ActionManifest(
            action_id=new_id("act"), task_id=ctx.task_id,
            agent_id=proposal.identity_id,
            identity_id=proposal.identity_id,
            capabilities=[proposal.capability],
            scopes=[proposal.capability],
            resources=[proposal.resource.pattern],
            data_classes=[proposal.data_classification.value],
            model=ctx.model_id, tools=[ctx.tool_id])
        result = self.plane.check(manifest)
        decision = self._map_gate(result, ra.level, ctx)
        explained = ExplainedDecision(
            decision=decision,
            policy_version=getattr(result, "policy_version", "v1") or "v1",
            matched_rules=tuple(getattr(result, "matched_rules", []) or ()),
            identity=proposal.identity_id,
            requested_action=proposal.capability,
            resource=proposal.resource.pattern,
            risk=ra.level.value,
            missing_authority=tuple(
                getattr(result, "missing_scopes", []) or ()),
            required_approval=",".join(
                getattr(result, "required_approvals", []) or ()),
            reason="; ".join(getattr(result, "reasons", []) or
                             [f"path={gate}"]))
        self._decisions.append(explained)
        self.paths.record(ctx.task_id, manifest.action_id,
                          proposal.capability, proposal.resource.pattern,
                          ra.level, [proposal.data_classification.value])
        return explained

    def _map_gate(self, result: Any, level: Risk,
                  ctx: ExecutionContext) -> ExtendedDecision:
        from aetheros_control_plane.models import AuthDecision
        code = str(getattr(result, "code", "") or "")
        allowed = bool(getattr(result, "allowed", False))
        if not allowed:
            if "APPROVAL" in code:
                return ExtendedDecision.REQUIRE_APPROVAL
            return ExtendedDecision.DENY
        return extend_decision(AuthDecision.ALLOW, level,
                               {"sandbox_available": True})

    def authorize_and_issue(self, proposal: ActionProposal,
                            ctx: ExecutionContext,
                            cap_authority) -> CapabilityToken:
        """Full path through approval + token issuance. Raises TrustError
        unless the decision is an unqualified ALLOW."""
        explained = self.evaluate(proposal, ctx)
        if explained.decision != ExtendedDecision.ALLOW:
            raise TrustError(
                SecurityError.POLICY_DENIED,
                f"{explained.decision.value}: {explained.reason}")
        return cap_authority.issue(
            subject=proposal.identity_id, action=proposal.capability,
            resource=proposal.resource.pattern, purpose=proposal.purpose,
            audience=ctx.tool_id)
