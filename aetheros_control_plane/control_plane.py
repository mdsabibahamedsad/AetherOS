"""Universal Control Plane facade (§2, §117).

Wires identity → trust → policy → authorization → delegation → approval
→ risk/DLP → execution → verification → provenance → audit into one
deterministic pipeline. Adapts (not duplicates) existing
``aetheros_security`` modules: kill_switch, tokens, dlp, authz, policy,
approval, audit, network, sandbox (§104 migration strategy).
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .agent_cards import AgentCard, AgentCardVerifier
from .approvals_sessions import (ApprovalEngine, JITManager, OrgEngine,
                                 SessionManager)
from .crypto_keys import KeyResolver, KeyStore
from .data_network import NetworkPolicy, evaluate_flow
from .delegation import DelegationEngine
from .emergency import Budget, EmergencyStop, Quarantine, StopScope
from .execution_gate import ExecutionGate, GateResult, sanitize_tool_output
from .identity_plane import CapabilityRegistry, IdentityPlane
from .models import (ActionManifest, AuthDecision, ControlPlaneError,
                     FailureCode, IdentityType, PolicyDecision, RiskLevel,
                     TrustLevel)
from .policy_risk import PolicyEvaluator, PolicyRegistry, classify_risk
from .provenance_audit import AuditLog, ProvenanceGraph
from .scopes import ScopeSet
from .trust_engine import TrustEngine

logger = logging.getLogger(__name__)


class UniversalControlPlane:
    """Central trust/governance/policy plane for AetherOS (§1-2)."""

    def __init__(self, audit_path: Optional[Path] = None):
        self.keys = KeyStore()
        self.identities = IdentityPlane(self.keys)
        resolver = KeyResolver()
        resolver.attach(self.keys)
        self.trust = TrustEngine()
        self.policies = PolicyRegistry()
        self.evaluator = PolicyEvaluator(self.policies)
        self.delegation = DelegationEngine(self.keys)
        self.approvals = ApprovalEngine()
        self.jit = JITManager()
        self.sessions = SessionManager()
        self.org = OrgEngine()
        self.caps = CapabilityRegistry()
        self.network = NetworkPolicy()
        self.quarantine = Quarantine()
        self.emergency = EmergencyStop()
        self.budgets: Dict[str, Budget] = {}
        self.audit = AuditLog(audit_path)
        self.graph = ProvenanceGraph()
        self.cards = AgentCardVerifier()
        self.gate = ExecutionGate()
        self.gate.checker = self.check
        # legacy kill-switch adapter (§104)
        try:
            from aetheros_security.kill_switch import (  # type: ignore
                get_kill_switch_registry)
            self._legacy_kill = get_kill_switch_registry()
        except Exception:
            self._legacy_kill = None

    # -- main pipeline (§11) ------------------------------------------------
    def check(self, manifest: ActionManifest) -> GateResult:
        reasons: List[str] = []
        # 1. emergency stop (never needs model cooperation, §36)
        if self.emergency.blocked(StopScope.ACTION, manifest.action_id) or \
           self.emergency.blocked(StopScope.TASK, manifest.task_id) or \
           self.emergency.blocked(StopScope.AGENT, manifest.agent_id) or \
           self.emergency.blocked(StopScope.GLOBAL):
            self.audit.emit("tool.blocked",
                            {"task": manifest.task_id,
                             "agent": manifest.agent_id},
                            {"reason": "emergency-stop"})
            return GateResult(False, manifest, ["emergency stop active"],
                              code="AGENT_QUARANTINED")
        # 2. identity
        ident = self.identities.get(manifest.identity_id)
        if ident is None:
            return GateResult(False, manifest, ["unknown identity"],
                              code="IDENTITY_UNKNOWN")
        if not ident.is_usable():
            code = ("AGENT_QUARANTINED"
                    if str(ident.status) == "IdentityStatus.QUARANTINED"
                    else "IDENTITY_REVOKED")
            return GateResult(False, manifest,
                              [f"identity not usable: {ident.status}"],
                              code=code)
        if self.quarantine.is_held(ident.id):
            return GateResult(False, manifest, ["identity quarantined"],
                              code="AGENT_QUARANTINED")
        # 3. risk (policy + context, §12)
        risk = classify_risk(
            manifest.capabilities[0] if manifest.capabilities else "read",
            manifest.resources[0] if manifest.resources else "",
            manifest.data_classes[0] if manifest.data_classes else "internal",
            {"environment": manifest.sandbox})
        manifest.risk = risk
        # step-up for R4/R5 (§51)
        if risk in (RiskLevel.R4_HIGH_IMPACT, RiskLevel.R5_CRITICAL):
            reasons.append(f"high risk {risk.value}: step-up/approval needed")
        # 4. trust
        assess = self.trust.assess(
            ident.id, TrustLevel.T2_VERIFIED if risk in (
                RiskLevel.R0_READ_ONLY, RiskLevel.R1_LOCAL_REVERSIBLE)
            else TrustLevel.T3_TRUSTED)
        # 5. policy
        cap = manifest.capabilities[0] if manifest.capabilities else "*"
        res = manifest.resources[0] if manifest.resources else "*"
        pol = self.evaluator.evaluate(cap, res, ident.tenant,
                                      ident.trust_level, risk)
        manifest.policy_version = pol.policy_version
        # 6. scopes (identity + JIT temp grants, §14)
        scopes = self.identities.scopes_for(ident.id)
        effective = ScopeSet(scopes.grants + self.jit.scopes_for(
            ident.id).grants)
        missing = [s for s in manifest.scopes
                   if not effective.allows(s, ident.tenant)]
        if missing:
            self.audit.emit("tool.blocked",
                            {"task": manifest.task_id,
                             "identity": ident.id},
                            {"reason": "scope missing", "missing": missing})
            return GateResult(False, manifest,
                              [f"missing scopes: {missing}"],
                              code="SCOPE_MISSING")
        # 7. delegation validity (§15)
        if manifest.delegation_id and not self.delegation.valid(
                manifest.delegation_id, manifest.task_id, ident.tenant):
            return GateResult(False, manifest, ["delegation invalid/expired"],
                              code="DELEGATION_INVALID")
        # 8. network targets (§25)
        for target in manifest.network_targets:
            ok, why = self.network.check_url(target)
            if not ok:
                self.audit.emit("network.blocked",
                                {"task": manifest.task_id}, {"url": target,
                                                             "why": why})
                return GateResult(False, manifest, [f"network: {why}"],
                                  code="NETWORK_POLICY_BLOCKED")
        # 9. DLP on classified payloads (§21)
        for dc in manifest.data_classes:
            flow = evaluate_flow(dc, ",".join(manifest.network_targets
                                              or manifest.resources),
                                 "", ident.trust_level.value)
            if flow.decision.value == "BLOCK":
                return GateResult(False, manifest, [flow.reason],
                                  code="DATA_POLICY_BLOCKED")
            if flow.decision.value in ("REQUIRE_APPROVAL",) and \
                    not manifest.approval_id:
                return GateResult(False, manifest, [flow.reason],
                                  code="APPROVAL_REQUIRED")
        # 10. combine trust + policy
        if pol.decision == AuthDecision.DENY or \
                assess.outcome.value == "DENY":
            self.audit.emit("tool.blocked",
                            {"task": manifest.task_id,
                             "identity": ident.id},
                            {"policy": pol.explanation,
                             "trust": assess.reasons})
            return GateResult(False, manifest,
                              [f"policy: {pol.explanation}",
                               f"trust: {assess.reasons}"],
                              code="POLICY_DENIED")
        if pol.decision == AuthDecision.REQUIRE_APPROVAL or \
                assess.outcome.value in ("REQUIRE_APPROVAL", "QUARANTINE"):
            if not manifest.approval_id:
                return GateResult(False, manifest,
                                  [f"approval required: {pol.explanation}"],
                                  code="APPROVAL_REQUIRED")
        # allowed
        self.audit.emit("tool.called",
                        {"task": manifest.task_id, "identity": ident.id,
                         "action": manifest.action_id},
                        {"capability": cap, "resource": res,
                         "risk": risk.value,
                         "policy_version": pol.policy_version})
        self.graph.add(manifest.action_id, "action",
                       {"capability": cap, "resource": res})
        self.graph.link(manifest.agent_id or ident.id, "executed",
                        manifest.action_id)
        return GateResult(True, manifest,
                          reasons + [pol.explanation] + assess.reasons)

    # -- explanation APIs (§75-77) -------------------------------------------
    def why(self, manifest: ActionManifest) -> Dict[str, Any]:
        gate = self.check(manifest)
        return {"allowed": gate.allowed, "reasons": gate.reasons,
                "risk": manifest.risk.value,
                "policy_version": manifest.policy_version}

    def what_can_do(self, identity_id: str,
                    probes: List[str]) -> Dict[str, bool]:
        out = {}
        for cap in probes:
            m = ActionManifest(identity_id=identity_id,
                               capabilities=[cap], scopes=[cap])
            try:
                out[cap] = self.check(m).allowed
            except Exception:
                out[cap] = False
        return out

    # -- MCP / A2A gates (§18, §26) ------------------------------------------
    def mcp_call_allowed(self, identity_id: str, server: str, tool: str,
                         args: Dict[str, Any],
                         task_id: str = "") -> GateResult:
        ident = self.identities.get(identity_id)
        tenant = ident.tenant if ident else "default"
        m = ActionManifest(task_id=task_id, identity_id=identity_id,
                           capabilities=[f"mcp.{tool}"],
                           scopes=[f"mcp.{tool}"],
                           resources=[server], tools=[tool])
        _ = args  # args are inspected by tool-level validators downstream
        gate = self.check(m)
        if self.quarantine.is_held(f"mcp:{server}"):
            return GateResult(False, m, ["MCP server quarantined"],
                              code="AGENT_QUARANTINED")
        _ = tenant
        return gate

    def a2a_allowed(self, identity_id: str, card: AgentCard,
                    capability: str, task_id: str = "") -> GateResult:
        ok, notes = self.cards.verify(card)
        m = ActionManifest(task_id=task_id, identity_id=identity_id,
                           capabilities=[capability],
                           scopes=[capability],
                           resources=[card.endpoint],
                           network_targets=[card.endpoint])
        if not ok:
            self.audit.emit("agent.quarantined",
                            {"task": task_id}, {"card": card.name,
                                                "notes": notes})
            return GateResult(False, m, [f"agent card invalid: {notes}"],
                              code="AGENT_QUARANTINED")
        return self.check(m)

    # -- revocation propagation (§93) -----------------------------------------
    def revoke_identity(self, identity_id: str) -> Dict[str, Any]:
        self.identities.revoke(identity_id)
        sessions = self.sessions.revoke_identity(identity_id)
        self.audit.emit("identity.revoked", {"identity": identity_id},
                        {"sessions_revoked": sessions})
        return {"identity": identity_id, "sessions_revoked": sessions}

    # -- health (§83) -----------------------------------------------------------
    def health(self) -> Dict[str, Any]:
        audit_ok, audit_msg = self.audit.verify()
        return {
            "policy_active": self.policies.active().version
            if self.policies.active() else None,
            "identities": len(self.identities.list()),
            "quarantined": len(self.quarantine.list()),
            "emergency_stops": len(self.emergency.active()),
            "audit_events": len(self.audit),
            "audit_integrity": audit_msg if audit_ok else f"BROKEN: {audit_msg}",
            "audit_ok": audit_ok,
        }
