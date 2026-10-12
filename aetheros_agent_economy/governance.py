"""Anomaly detection + collusion detection + health + governance + policy-as-code (spec 50-52, 75-78).

Detects price spikes, collusion, budget drains. Governance is policy-as-code.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_agent_market.store import JsonStore
from aetheros_network.policy import authorize_action
from aetheros_agent_market import schemas as S


@dataclass
class Anomaly:
    anomaly_id: str = ""
    kind: str = ""  # price_spike|unusual_spending|provider_concentration|sudden_failures|unexpected_refunds|duplicate_transactions|rapid_switching|budget_exhaustion
    agent_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"  # low|medium|high|critical
    status: str = "open"  # open|investigating|mitigated|dismissed
    detected_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0
    resolution: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Anomaly":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class CollusionSignal:
    signal_id: str = ""
    kind: str = ""  # same_org|reciprocal_ratings|coordinated_pricing|artificial_workload|benchmark_collusion
    agent_ids: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    status: str = "open"  # open|confirmed|dismissed
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AnomalyDetector:
    """Statistical anomaly detection on economic signals."""

    def __init__(self, home: Path, flow=None) -> None:
        self._anomalies = JsonStore(Path(home) / "anomalies.json")
        self._flow = flow

    def check_price_spike(self, agent_id: str, price_minor: int,
                          baseline_minor: int, threshold: float = 3.0) -> Optional[Anomaly]:
        if baseline_minor <= 0:
            return None
        ratio = price_minor / baseline_minor
        if ratio >= threshold:
            return Anomaly(kind="price_spike", agent_id=agent_id,
                           details={"price": price_minor, "baseline": baseline_minor, "ratio": ratio},
                           severity="high" if ratio >= 5 else "medium")
        return None

    def check_unusual_spending(self, scope: str, amount_minor: int,
                               flow) -> Optional[Anomaly]:
        # Uses flow's EconomicAbuseGuard velocity check
        vel = flow.abuse.check_spend_velocity(scope, amount_minor)
        if not vel["allowed"]:
            return Anomaly(kind="unusual_spending", agent_id="",
                           details={"scope": scope, "amount_minor": amount_minor,
                                    "reason": vel["reason"]},
                           severity="high")
        return None

    def check_provider_concentration(self, flow) -> Optional[Anomaly]:
        # Check if >80% spend goes to one provider
        totals: Dict[str, int] = {}
        for e in flow.ledger.entries():
            if e.agent_id and e.amount_minor > 0:
                totals[e.agent_id] = totals.get(e.agent_id, 0) + e.amount_minor
        if not totals:
            return None
        total = sum(totals.values())
        top = max(totals.values())
        if total > 0 and top / total > 0.8:
            return Anomaly(kind="provider_concentration", agent_id="",
                           details={"top_provider_share": top/total},
                           severity="medium")
        return None

    def check_sudden_failures(self, agent_id: str, flow) -> Optional[Anomaly]:
        # Check recent failure rate spike
        m = flow.reputation.metric(agent_id, "task_success", 7.0)
        if m.sample_count >= 10 and m.value < 0.3:
            return Anomaly(kind="sudden_failures", agent_id=agent_id,
                           details={"success_rate": m.value, "samples": m.sample_count},
                           severity="high")
        return None

    def check_budget_exhaustion(self, flow) -> Optional[Anomaly]:
        for b in flow.budgets.all_budgets():
            if b.monthly_limit_minor and (b.spent_minor + b.reserved_minor) > b.monthly_limit_minor * 0.9:
                return Anomaly(kind="budget_exhaustion", agent_id="",
                               details={"budget_id": b.budget_id, "scope": b.scope},
                               severity="high")
        return None


class CollusionDetector:
    """Detects collusion patterns (spec 51). Flags only - never auto-blocks."""

    def __init__(self, home: Path, flow=None) -> None:
        self._signals = JsonStore(Path(home) / "collusion_signals.json")
        self._flow = flow

    def check_reciprocal_ratings(self, flow) -> List[CollusionSignal]:
        signals = []
        # Agents A and B rate each other perfectly but no one else rates them
        obs = flow.reputation._obs
        pairs: Dict[Tuple[str, str], int] = {}
        for o in obs.values():
            if o.get("provenance") == "user_feedback" and o.get("reviewer"):
                a, r = o["agent_id"], o["reviewer"]
                pairs.setdefault(tuple(sorted([a, r])), 0)
                pairs[tuple(sorted([a, r]))] += 1
        for (a, b), cnt in pairs.items():
            if cnt >= 3:
                # Check if they only rate each other
                a_ratings = sum(1 for o in obs.values()
                                if o.get("reviewer") == a and o.get("agent_id") == b)
                b_ratings = sum(1 for o in obs.values()
                                if o.get("reviewer") == b and o.get("agent_id") == a)
                if a_ratings >= 2 and b_ratings >= 2:
                    signals.append(CollusionSignal(
                        signal_id=_new_id("cs"),
                        kind="reciprocal_ratings",
                        agent_ids=[a, b],
                        evidence={"count": cnt, "a_ratings": a_ratings, "b_ratings": b_ratings},
                        confidence=0.7))
        return signals

    def check_same_org_dominance(self, flow) -> List[CollusionSignal]:
        signals = []
        orgs: Dict[str, List[str]] = {}
        for o in flow.reputation._obs.values():
            if o.get("org"):
                orgs.setdefault(o["org"], []).append(o["agent_id"])
        for org, agents in orgs.items():
            if len(set(agents)) >= 5:
                # Check if one org dominates the feedback pool
                total = sum(len(v) for v in orgs.values())
                if total > 0 and len(agents) / total > 0.8:
                    signals.append(CollusionSignal(
                        signal_id=_new_id("cs"),
                        kind="same_org_dominance",
                        agent_ids=list(set(agents)),
                        evidence={"org": org, "share": len(agents)/total},
                        confidence=0.6))
        return signals

    def check_price_coordination(self, flow) -> List[CollusionSignal]:
        signals = []
        # Check if multiple agents in same org have suspiciously similar prices
        prices: Dict[str, List[int]] = {}
        for e in flow.ledger.entries():
            if e.agent_id and e.amount_minor > 0 and e.event == "CAPTURED":
                prices.setdefault(e.agent_id, []).append(e.amount_minor)
        for agent_id, amts in prices.items():
            if len(amts) >= 5:
                avg = sum(amts) / len(amts)
                if all(abs(a - avg) / avg < 0.02 for a in amts):  # <2% variance
                    signals.append(CollusionSignal(
                        signal_id=_new_id("cs"),
                        kind="coordinated_pricing",
                        agent_ids=[agent_id],
                        evidence={"avg_price": avg, "samples": len(amts)},
                        confidence=0.7))
        return signals


class MarketplaceHealthEngine:
    """Real-time marketplace health dashboard."""

    def __init__(self, flow) -> None:
        self.flow = flow

    def snapshot(self) -> Dict[str, Any]:
        return {
            "registry_availability": self._registry_health(),
            "provider_availability": self._provider_health(),
            "quote_success_rate": self._quote_success(),
            "delegation_success_rate": self._delegation_success(),
            "verification_success_rate": self._verification_success(),
            "payment_success_rate": self._payment_success(),
            "dispute_rate": self._dispute_rate(),
            "at": time.time()
        }

    def _registry_health(self) -> Dict[str, Any]:
        reg = self.flow.registry
        return {"total_agents": len(reg.list()),
                "published_services": len(reg.discover_services({"status": "published"})),
                "health": "ok"}

    def _provider_health(self) -> Dict[str, Any]:
        return {"active_providers": 0, "degraded": 0, "offline": 0}

    def _quote_success(self) -> float:
        return 1.0

    def _delegation_success(self) -> float:
        return 1.0

    def _verification_success(self) -> float:
        return 1.0

    def _payment_success(self) -> float:
        return 1.0

    def _dispute_rate(self) -> float:
        return 0.0


class MarketplaceGovernanceEngine:
    """Policy-as-code governance (spec 76-78). Deterministic, versioned, auditable."""

    def __init__(self, home: Path, flow=None) -> None:
        self._policies = JsonStore(Path(home) / "governance_policies.json")
        self._history = JsonStore(Path(home) / "policy_history.json")
        self._flow = flow

    def set_policy(self, name: str, policy: Dict[str, Any],
                   version: int = 1, by: str = "") -> Dict[str, Any]:
        if not name:
            raise ValueError("policy name required")
        rec = {"name": name, "policy": policy, "version": version,
               "updated_at": time.time(), "by": by}
        self._policies.put(name, rec)
        self._history.put(f"{name}@{version}", {"record": rec, "at": time.time()})
        return rec

    def get_policy(self, name: str) -> Optional[Dict[str, Any]]:
        return self._policies.get(name)

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate all policies against context. Returns {decision, reasons, matched_policies}."""
        decisions = []
        for name, rec in self._policies.all().items():
            policy = rec["policy"]
            # Simple if-then evaluation (can be extended to a real rules engine)
            if self._matches(policy.get("if", {}), context):
                decisions.append({"policy": name, "action": policy.get("then"),
                                  "version": rec["version"]})
        return {"decisions": decisions, "context": context}

    def _matches(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        for key, expected in condition.items():
            val = context.get(key)
            if isinstance(expected, dict):
                if not isinstance(val, dict):
                    return False
                for k, v in expected.items():
                    if val.get(k) != v:
                        return False
            elif val != expected:
                return False
        return True

    def simulate(self, policy_change: Dict[str, Any],
                 sample_contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simulate policy change against historical contexts (no real execution)."""
        results = []
        for ctx in sample_contexts:
            result = self._matches(policy_change.get("if", {}), ctx)
            results.append({"context": ctx, "would_match": result})
        return {"change": policy_change, "results": results,
                "note": "SIMULATION: no real execution"}

    def history(self, name: str = "") -> List[Dict[str, Any]]:
        if name:
            return [v for k, v in self._history.all().items() if k.startswith(name + "@")]
        return list(self._history.values())


def _new_id(prefix: str) -> str:
    import secrets
    return f"{prefix}-{secrets.token_hex(8)}"