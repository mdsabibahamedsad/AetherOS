"""Policy extensions (§13-14, §79-85, §147-148): extended decisions,
deterministic precedence, content-hashed versioning, dry-run
simulator, canary lifecycle, regression runner, trace replay.
Base allow/deny/approval evaluation stays in M50 PolicyEvaluator."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from aetheros_control_plane.models import AuthDecision, PolicyDecision
from aetheros_control_plane.policy_risk import PolicyEvaluator, PolicyRegistry

from .models import ExtendedDecision, Risk, new_id

# §148 precedence, lowest index wins on conflict (§147: DENY wins).
_PRECEDENCE = ("global-deny", "organization", "user", "task", "agent",
               "tool", "resource", "temporary-approval")


@dataclass(frozen=True)
class PolicyVersion:
    policy_id: str
    version: str
    content_hash: str
    stage: str = "DRAFT"  # DRAFT|TEST|SHADOW|CANARY|ACTIVE|DEPRECATED|REVOKED
    at: float = field(default_factory=time.time)


def hash_policy(content: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(content, sort_keys=True).encode()).hexdigest()


class PolicyStore:
    """Versioned, hashed, staged policies with deterministic precedence."""

    def __init__(self) -> None:
        self._versions: Dict[str, List[PolicyVersion]] = {}
        self._bodies: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._order = {name: i for i, name in enumerate(_PRECEDENCE)}

    def publish(self, policy_id: str, body: Dict[str, Any],
                layer: str = "task") -> PolicyVersion:
        if layer not in self._order:
            raise ValueError(f"unknown layer {layer}")
        n = len(self._versions.get(policy_id, [])) + 1
        ver = PolicyVersion(policy_id, f"v{n}",
                            hash_policy({**body, "_layer": layer}))
        self._versions.setdefault(policy_id, []).append(ver)
        self._bodies[(policy_id, ver.version)] = {**body, "_layer": layer}
        return ver

    def set_stage(self, policy_id: str, version: str, stage: str) -> None:
        vers = self._versions.get(policy_id, [])
        for i, v in enumerate(vers):
            if v.version == version:
                vers[i] = PolicyVersion(v.policy_id, v.version,
                                        v.content_hash, stage, v.at)
                return
        raise KeyError(f"{policy_id}@{version}")

    def active(self, policy_id: str) -> Optional[Dict[str, Any]]:
        for v in reversed(self._versions.get(policy_id, [])):
            if v.stage == "ACTIVE":
                return self._bodies[(policy_id, v.version)]
        return None

    def evaluate_layers(self, layers: Dict[str, str]) -> str:
        """Deterministic conflict resolution across layers (§147-148)."""
        ordered = sorted(layers.items(),
                         key=lambda kv: self._order.get(kv[0], 99))
        for _, decision in ordered:
            if decision == "DENY":
                return "DENY"
        for _, decision in ordered:
            if decision != "ALLOW":
                return decision
        return "ALLOW"


def extend_decision(base: AuthDecision, risk: Risk,
                    context: Optional[Dict[str, Any]] = None
                    ) -> ExtendedDecision:
    """Map M50 base decisions onto the §13 decision set."""
    ctx = context or {}
    if base == AuthDecision.DENY:
        return ExtendedDecision.DENY
    if base == AuthDecision.REQUIRE_APPROVAL:
        return ExtendedDecision.REQUIRE_APPROVAL
    if base == AuthDecision.CHALLENGE_STEP_UP:
        return ExtendedDecision.REQUIRE_STEP_UP_AUTH
    # ALLOW refinements from risk/context
    if risk in (Risk.R7_PHYSICAL_WORLD, Risk.R8_IRREVERSIBLE_CRITICAL) \
            and ctx.get("simulated") is not True:
        return ExtendedDecision.SIMULATION_ONLY
    if ctx.get("sandbox_available") and risk in (
            Risk.R5_FINANCIAL_LEGAL_ORG, Risk.R6_INFRA_MODIFICATION):
        return ExtendedDecision.SANDBOX_ONLY
    if ctx.get("rate_limited"):
        return ExtendedDecision.RATE_LIMIT
    if ctx.get("defer"):
        return ExtendedDecision.DEFER
    return ExtendedDecision.ALLOW


@dataclass
class ExplainedDecision:
    decision: ExtendedDecision
    policy_id: str = ""
    policy_version: str = ""
    policy_hash: str = ""
    matched_rules: Tuple[str, ...] = ()
    identity: str = ""
    requested_action: str = ""
    resource: str = ""
    risk: str = ""
    missing_authority: Tuple[str, ...] = ()
    required_approval: str = ""
    reason: str = ""


class PolicySimulator:
    """Dry-run 'what would happen if X' without executing (§79)."""

    def __init__(self, evaluator: PolicyEvaluator):
        self.evaluator = evaluator

    def simulate(self, capability: str, resource: str = "*",
                 tenant: str = "default") -> Dict[str, Any]:
        from aetheros_control_plane.models import TrustLevel
        from aetheros_control_plane.policy_risk import RiskLevel
        dec: PolicyDecision = self.evaluator.evaluate(
            capability, resource, tenant, TrustLevel.T0_UNKNOWN,
            RiskLevel.R0_READ_ONLY)
        return {"decision": dec.decision.value,
                "matched_rules": dec.matched_rules,
                "denied_rules": dec.denied_rules,
                "required_scopes": dec.required_scopes,
                "required_approvals": dec.required_approvals,
                "explanation": dec.explanation,
                "policy_version": dec.policy_version,
                "executed": False}


class PolicyCanary:
    """DRAFT->TEST->SHADOW->CANARY->ACTIVE lifecycle (§83)."""

    STAGES = ("DRAFT", "TEST", "SHADOW", "CANARY", "ACTIVE",
              "DEPRECATED", "REVOKED")

    def __init__(self, store: PolicyStore):
        self.store = store

    def advance(self, policy_id: str, version: str) -> str:
        vers = self.store._versions.get(policy_id, [])
        cur = next((v.stage for v in vers if v.version == version), None)
        if cur is None:
            raise KeyError(f"{policy_id}@{version}")
        idx = self.STAGES.index(cur)
        if idx + 1 >= len(self.STAGES):
            return cur
        nxt = self.STAGES[idx + 1]
        if nxt == "ACTIVE":
            self._require_tests(policy_id, version)
        self.store.set_stage(policy_id, version, nxt)
        return nxt

    def _require_tests(self, policy_id: str, version: str) -> None:
        body = self.store._bodies.get((policy_id, version), {})
        if not body.get("tests_passed"):
            raise ValueError("cannot activate untested high-impact policy")


class PolicyRegression:
    """Run known-good/known-bad/adversarial/boundary cases (§82)."""

    def __init__(self, decide: Callable[[Dict[str, Any]], str]):
        self.decide = decide
        self.cases: List[Dict[str, Any]] = []

    def add(self, name: str, request: Dict[str, Any],
            expected: str) -> None:
        self.cases.append({"name": name, "request": request,
                           "expected": expected})

    def run(self) -> Dict[str, Any]:
        false_allows, false_denies, results = [], [], []
        for c in self.cases:
            got = self.decide(c["request"])
            ok = got == c["expected"]
            results.append({"name": c["name"], "expected": c["expected"],
                            "got": got, "ok": ok})
            if not ok and c["expected"] == "DENY":
                false_allows.append(c["name"])
            if not ok and c["expected"] == "ALLOW":
                false_denies.append(c["name"])
        return {"total": len(results),
                "passed": sum(1 for r in results if r["ok"]),
                "false_allows": false_allows,
                "false_denies": false_denies, "results": results}


class GovernanceReplay:
    """Replay a recorded action trace against old/current/proposed
    policy evaluators and diff decisions (§85)."""

    def __init__(self, evaluators: Dict[str, Callable[[Dict], str]]):
        self.evaluators = evaluators

    def replay(self, trace: List[Dict[str, Any]]) -> Dict[str, Any]:
        per_policy: Dict[str, List[str]] = {}
        for name, fn in self.evaluators.items():
            per_policy[name] = [fn(a) for a in trace]
        diffs = []
        names = list(per_policy)
        for i, a in enumerate(trace):
            vals = {n: per_policy[n][i] for n in names}
            if len(set(vals.values())) > 1:
                diffs.append({"action": a, "decisions": vals})
        return {"decisions": per_policy, "diffs": diffs}
