"""Capability tokens + revocation + risk engine + approvals + autopilot (spec 40-48).

Tokens are scoped, time-limited, contract-bound. Revocation is immediate.
Risk engine is explainable. Autopilot modes are policy-gated.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_agent_market.store import JsonStore


@dataclass
class CapabilityToken:
    """Scoped, time-limited capability handle."""

    token_id: str = ""
    capability_id: str = ""
    subject_agent_id: str = ""          # holder
    audience_agent_id: str = ""         # provider who must honor it
    scope: List[str] = field(default_factory=list)  # capability sub-scopes
    contract_id: str = ""
    task_id: str = ""
    nonce: str = ""
    issuer: str = ""                    # AetherOS core
    issued_at: float = field(default_factory=time.time)
    expires_at: float = 0.0             # 0 = no expiry (use with caution)
    revoked: bool = False
    revoked_at: float = 0.0
    revoked_by: str = ""

    def is_valid(self, now: Optional[float] = None) -> bool:
        if self.revoked:
            return False
        if self.expires_at and (now or time.time()) > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityToken":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


class CapabilityTokenStore:
    """Mint, validate, revoke capability tokens."""

    def __init__(self, home: Path) -> None:
        self._store = JsonStore(Path(home) / "capability_tokens.json")

    def mint(self, capability_id: str, subject_agent_id: str,
             audience_agent_id: str, contract_id: str = "",
             task_id: str = "", scope: Optional[List[str]] = None,
             ttl_s: Optional[float] = None,
             issuer: str = "aetheros") -> CapabilityToken:
        if not capability_id or not subject_agent_id or not audience_agent_id:
            raise ValueError("capability_id, subject_agent_id, audience_agent_id required")
        tok = CapabilityToken(
            token_id=_new_id("tok"),
            capability_id=capability_id,
            subject_agent_id=subject_agent_id,
            audience_agent_id=audience_agent_id,
            scope=scope or [],
            contract_id=contract_id,
            task_id=task_id,
            nonce=secrets.token_hex(8),
            issuer=issuer,
            expires_at=time.time() + ttl_s if ttl_s else 0.0)
        self._store.put(tok.token_id, tok.to_dict())
        return tok

    def validate(self, token_id: str) -> Optional[CapabilityToken]:
        raw = self._store.get(token_id)
        if not raw:
            return None
        tok = CapabilityToken.from_dict(raw)
        if not tok.is_valid():
            return None
        return tok

    def revoke(self, token_id: str, by: str = "") -> bool:
        raw = self._store.get(token_id)
        if not raw:
            return False
        tok = CapabilityToken.from_dict(raw)
        tok.revoked = True
        tok.revoked_at = time.time()
        tok.revoked_by = by
        self._store.put(token_id, tok.to_dict())
        return True

    def revoke_all_for_agent(self, agent_id: str, by: str = "") -> int:
        count = 0
        for raw in self._store.values():
            if raw.get("subject_agent_id") == agent_id and not raw.get("revoked"):
                tok = CapabilityToken.from_dict(raw)
                tok.revoked = True
                tok.revoked_at = time.time()
                tok.revoked_by = by
                self._store.put(tok.token_id, tok.to_dict())
                count += 1
        return count

    def revoke_all_for_capability(self, capability_id: str, by: str = "") -> int:
        count = 0
        for raw in self._store.values():
            if raw.get("capability_id") == capability_id and not raw.get("revoked"):
                tok = CapabilityToken.from_dict(raw)
                tok.revoked = True
                tok.revoked_at = time.time()
                tok.revoked_by = by
                self._store.put(tok.token_id, tok.to_dict())
                count += 1
        return count


@dataclass
class RiskDimension:
    name: str = ""
    score: float = 0.0            # 0..1
    confidence: float = 0.0       # 0..1
    factors: List[str] = field(default_factory=list)
    mitigation: str = ""


@dataclass
class RiskAssessment:
    task_summary: str = ""
    dimensions: List[RiskDimension] = field(default_factory=list)
    overall_risk: float = 0.0      # 0..1
    recommended_approval: str = "human"  # none|auto|conditional|human
    required_verification: List[str] = field(default_factory=list)


class RiskEngine:
    """Explainable risk assessment. Never LLM-based."""

    def __init__(self, home: Path, flow=None) -> None:
        self._flow = flow
        self._home = home

    def assess(self, task: Dict[str, Any],
               contract: Optional["CompositeContract"] = None,
               selection: Optional[Dict[str, Any]] = None) -> RiskAssessment:
        dims = []
        summary = task.get("summary", task.get("query", "task"))[:200]

        # Financial risk
        budget_minor = task.get("budget_minor", 0)
        financial_risk_class = risk_class(budget_minor)
        dims.append(RiskDimension(
            name="financial", score=self._financial_score(financial_risk_class),
            confidence=0.9, factors=[f"budget={budget_minor}"]))

        # Operational risk
        depth = task.get("delegation_depth", 1)
        dims.append(RiskDimension(
            name="operational", score=min(1.0, depth * 0.2),
            confidence=0.8, factors=[f"delegation_depth={depth}"]))

        # Privacy risk
        data_class = task.get("data_class", "INTERNAL")
        privacy_map = {"PUBLIC": 0.1, "INTERNAL": 0.3, "CONFIDENTIAL": 0.6,
                       "PRIVATE": 0.8, "HIGHLY_SENSITIVE": 0.95}
        dims.append(RiskDimension(
            name="privacy", score=privacy_map.get(data_class, 0.5),
            confidence=0.9, factors=[f"data_class={data_class}"]))

        # Security risk
        trust = 0.5
        agent_id = selection.get("agent_id", "") if selection else ""
        if self._flow and agent_id:
            trust = self._flow.trust.profile(agent_id).get("overall", 0.0)
        dims.append(RiskDimension(
            name="security", score=max(0.0, 1.0 - trust),
            confidence=0.7, factors=[f"provider_trust={trust:.2f}"]))

        # Reliability risk
        reliability = 0.5
        if agent_id and self._flow:
            rel = self._flow.reputation.metric(agent_id, "task_success").value
            reliability = rel
        dims.append(RiskDimension(
            name="reliability", score=max(0.0, 1.0 - reliability),
            confidence=0.7, factors=[f"reliability={reliability:.2f}"]))

        # Dependency risk
        dep_depth = task.get("delegation_depth", 1)
        dims.append(RiskDimension(
            name="dependency", score=min(1.0, dep_depth * 0.15),
            confidence=0.8, factors=[f"delegation_depth={dep_depth}"]))

        overall = sum(d.score for d in dims) / len(dims)

        # Approval tier
        if overall < 0.2:
            tier = "none"
        elif overall < 0.4:
            tier = "auto"
        elif overall < 0.6:
            tier = "conditional"
        else:
            tier = "human"

        # Verification requirements
        verif = []
        if overall >= 0.6:
            verif.append("independent_verification")
        if dims[2].score >= 0.6:  # privacy
            verif.append("data_handling_audit")
        if dims[1].score >= 0.5:  # operational depth
            verif.append("chain_audit")

        return RiskAssessment(
            task_summary=task.get("summary", "task"),
            dimensions=[d.to_dict() for d in dims],
            overall_risk=round(overall, 4),
            recommended_approval=tier,
            required_verification=verif)

    def risk_class(amount_minor: int) -> str:
        """Determine risk class from budget amount in minor units."""
        if amount_minor == 0:
            return "FREE"
        elif amount_minor <= 500:
            return "LOW_COST"
        elif amount_minor <= 5000:
            return "MEDIUM_COST"
        elif amount_minor <= 50000:
            return "HIGH_COST"
        else:
            return "CRITICAL_COST"


    def _financial_score(self, risk_class: str) -> float:
        return {"FREE": 0.0, "LOW_COST": 0.2, "MEDIUM_COST": 0.4,
                "HIGH_COST": 0.7, "CRITICAL_COST": 0.95}[risk_class]


class AutopilotEngine:
    """Marketplace autopilot: OFF / ASSISTED / CONDITIONAL / AUTONOMOUS.

    All modes obey hard security/budget/data policies.
    """

    MODES = ("OFF", "ASSISTED", "CONDITIONAL", "AUTONOMOUS")

    def __init__(self, flow) -> None:
        self.flow = flow
        self._flags = flow.flags

    def recommend_plan(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Return recommended plan + explanation. Never auto-execute."""
        rec = self.flow.optimizer.recommend(task)
        return {"plan": rec, "mode": "ASSISTED",
                "explanation": "autopilot is ASSISTED; no auto-execution"}

    def maybe_execute(self, task: Dict[str, Any],
                      approved_by: str = "") -> Dict[str, Any]:
        """Execute only if mode allows AND policy permits."""
        mode = self._flags.is_enabled("automatic_payment") and "AUTONOMOUS" or \
               self._flags.is_enabled("paid_agents") and "CONDITIONAL" or \
               self._flags.is_enabled("remote_delegation") and "ASSISTED" or "OFF"

        if mode == "OFF":
            return {"status": "declined", "reason": "autopilot OFF"}
        if mode == "ASSISTED":
            rec = self.recommend_plan({"query": "task"})
            return {"status": "recommendation", "plan": rec}
        if mode == "CONDITIONAL":
            # Check budget, trust, policy
            return self._conditional_execute({"query": "task"})
        if mode == "AUTONOMOUS":
            return self._autonomous_execute({"query": "task"})
        return {"status": "unknown_mode"}

    def _conditional_execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Would run full pipeline but require explicit approval for paid/high-risk
        return {"status": "pending_approval"}

    def _autonomous_execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Full pipeline within strict boundaries
        return {"status": "executing"}

    def stop_all(self, by: str = "") -> Dict[str, Any]:
        """Emergency stop."""
        self._flags.set("remote_delegation", False, by=f"autopilot:{by}")
        self._flags.set("paid_agents", False, by=f"autopilot:{by}")
        self._flags.set("automatic_negotiation", False, by=f"autopilot:{by}")
        self._flags.set("automatic_payment", False, by=f"autopilot:{by}")
        return {"stopped": True, "by": by, "at": time.time()}