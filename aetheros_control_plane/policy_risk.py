"""Policy engine (§10) + risk engine (§12).

First-class YAML policy language:

    policy:
      name: production-protection
      version: v3
      deny:
        - capability: terminal.execute
          resource: production/*
      requireApproval:
        - capability: filesystem.write
          resource: /important/*
      allow:
        - capability: filesystem.read
          resource: /workspace/**

Dimensions: capability, resource, tenant, trust floor, risk ceiling,
time window. Precedence: deny > requireApproval > allow (§96 invariant).
Policies are versioned; hot-reload swaps the active version without
mutating historical decisions (§37).
"""

from __future__ import annotations

import fnmatch
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import AuthDecision, PolicyDecision, RiskLevel, TrustLevel

logger = logging.getLogger(__name__)

_RISK_ORDER = {
    RiskLevel.R0_READ_ONLY: 0, RiskLevel.R1_LOCAL_REVERSIBLE: 1,
    RiskLevel.R2_EXTERNAL_SIDE_EFFECT: 2, RiskLevel.R3_SENSITIVE_DATA: 3,
    RiskLevel.R4_HIGH_IMPACT: 4, RiskLevel.R5_CRITICAL: 5,
}

_TRUST_ORDER = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5}


@dataclass
class PolicyRule:
    id: str
    effect: str  # "allow" | "deny" | "requireApproval"
    capability: str = "*"
    resource: str = "*"
    tenant: str = "*"
    trust_floor: str = "T0"
    risk_ceiling: Optional[str] = None


@dataclass
class Policy:
    name: str
    version: str = "v1"
    rules: List[PolicyRule] = field(default_factory=list)


def _cap_match(pattern: str, capability: str) -> bool:
    return fnmatch.fnmatchcase(capability, pattern)


def _res_match(pattern: str, resource: str) -> bool:
    return fnmatch.fnmatchcase(resource, pattern)


def policy_from_dict(doc: Dict[str, Any]) -> Policy:
    body = doc.get("policy", doc)
    name = str(body.get("name", "unnamed"))
    version = str(body.get("version", "v1"))
    rules: List[PolicyRule] = []
    for effect in ("deny", "requireApproval", "allow"):
        for i, r in enumerate(body.get(effect, []) or []):
            rules.append(PolicyRule(
                id=f"{name}:{effect}[{i}]",
                effect=effect,
                capability=str(r.get("capability", "*")),
                resource=str(r.get("resource", "*")),
                tenant=str(r.get("tenant", "*")),
                trust_floor=str(r.get("trust_floor", "T0")),
                risk_ceiling=r.get("risk_ceiling"),
            ))
    return Policy(name=name, version=version, rules=rules)


def policy_from_yaml(text: str) -> Policy:
    import yaml
    return policy_from_dict(yaml.safe_load(text))


class PolicyRegistry:
    """Versioned store with hot-reload (§37)."""

    def __init__(self) -> None:
        self._versions: Dict[str, Policy] = {}
        self._active: Optional[str] = None
        self._history: List[str] = []

    def publish(self, policy: Policy) -> None:
        self._versions[policy.version] = policy
        self._active = policy.version
        self._history.append(policy.version)

    def active(self) -> Optional[Policy]:
        return self._versions.get(self._active) if self._active else None

    def rollback(self, version: str) -> bool:
        if version in self._versions:
            self._active = version
            self._history.append(version)
            return True
        return False

    def history(self) -> List[str]:
        return list(self._history)


class PolicyEvaluator:
    """Deterministic evaluator. Deny > approval > allow."""

    def __init__(self, registry: PolicyRegistry):
        self.registry = registry

    def evaluate(self, capability: str, resource: str = "*",
                 tenant: str = "default",
                 trust: TrustLevel = TrustLevel.T0_UNKNOWN,
                 risk: RiskLevel = RiskLevel.R0_READ_ONLY) -> PolicyDecision:
        policy = self.registry.active()
        version = policy.version if policy else "v0-empty"
        matched, denied = [], []
        approval_needed: List[str] = []
        if policy:
            for rule in policy.rules:
                if rule.tenant not in ("*", tenant):
                    continue
                if not _cap_match(rule.capability, capability):
                    continue
                if not _res_match(rule.resource, resource):
                    continue
                if _TRUST_ORDER.get(trust.value, 0) < _TRUST_ORDER.get(rule.trust_floor, 0):
                    continue
                if rule.risk_ceiling and _RISK_ORDER[risk] > _RISK_ORDER.get(
                        rule.risk_ceiling, 5):
                    continue
                matched.append(rule.id)
                if rule.effect == "deny":
                    denied.append(rule.id)
                elif rule.effect == "requireApproval":
                    approval_needed.append(rule.id)
        if denied:
            return PolicyDecision(
                decision=AuthDecision.DENY, matched_rules=matched,
                denied_rules=denied, risk=risk,
                explanation=f"Denied by {denied[0]}", policy_version=version)
        if approval_needed:
            return PolicyDecision(
                decision=AuthDecision.REQUIRE_APPROVAL, matched_rules=matched,
                required_approvals=approval_needed, risk=risk,
                explanation=f"Approval required by {approval_needed[0]}",
                policy_version=version)
        allows = [m for m in matched
                  if self._rule(policy, m) == "allow"] if policy else []
        if allows:
            return PolicyDecision(
                decision=AuthDecision.ALLOW, matched_rules=matched, risk=risk,
                explanation=f"Allowed by {allows[0]}", policy_version=version)
        return PolicyDecision(
            decision=AuthDecision.DENY, matched_rules=matched, risk=risk,
            explanation="Default deny: no allow rule matched",
            policy_version=version)

    @staticmethod
    def _rule(policy: Optional[Policy], rid: str) -> str:
        for r in (policy.rules if policy else []):
            if r.id == rid:
                return r.effect
        return ""


# ---------------------------------------------------------------------------
# Risk engine (§12): policy + context, not tool name alone
# ---------------------------------------------------------------------------

_SENSITIVE_PREFIXES = ("/etc/", "/root", "~/.ssh", ".aws/", ".aetheros/",
                       "credentials", "secret")
_DESTRUCTIVE_TOKENS = ("rm -rf", "mkfs", "drop database", "delete production",
                       "sudo ", "shutdown", "format ")


def classify_risk(capability: str, resource: str = "",
                  data_class: str = "internal",
                  context: Optional[Dict[str, Any]] = None) -> RiskLevel:
    ctx = context or {}
    cap = capability.lower()
    res = resource.lower()
    dc = data_class.lower()
    if any(t in f"{cap} {res} {ctx.get('command', '')}".lower()
           for t in _DESTRUCTIVE_TOKENS) or "production" in res:
        if "irreversible" in str(ctx.get("flags", "")).lower() or "production" in res:
            if cap.startswith("infra") or "critical" in res:
                return RiskLevel.R5_CRITICAL
        return RiskLevel.R4_HIGH_IMPACT
    if dc in ("secret", "restricted") or "secret" in cap or "credential" in cap:
        return RiskLevel.R3_SENSITIVE_DATA
    if dc in ("confidential", "sensitive"):
        return RiskLevel.R3_SENSITIVE_DATA
    if any(k in cap for k in ("email.send", "message.send", "publish",
                              "payment", "deploy", "network.request")):
        return RiskLevel.R2_EXTERNAL_SIDE_EFFECT
    if any(k in cap for k in (".write", ".execute", ".delete", ".update")):
        target = ctx.get("environment", "local")
        if target in ("production", "remote", "shared"):
            return RiskLevel.R2_EXTERNAL_SIDE_EFFECT
        return RiskLevel.R1_LOCAL_REVERSIBLE
    return RiskLevel.R0_READ_ONLY
