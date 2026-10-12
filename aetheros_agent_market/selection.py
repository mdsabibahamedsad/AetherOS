"""Deterministic agent selection engine (spec section 9).

Score = CapabilityFit x TrustWeight x ReliabilityWeight x SecurityWeight
        x EvidenceWeight, then adjusted for cost/latency/SLA/privacy/
        availability. Every candidate gets a full explanation: the UI can
show exactly "why this agent was selected" (spec 98).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from . import schemas as S


@dataclass
class CandidateSignals:
    agent_id: str
    service_id: str
    source: str = ""
    capability_fit: float = 0.0      # 0..1 (1.0 = exact match)
    trust_overall: float = 0.0       # -1..1 scaled below
    trust_confidence: float = 0.0
    reliability: float = 0.0         # task_success metric value
    reliability_confidence: float = 0.0
    security: float = 0.0            # security metric value
    evidence_quality: float = 0.0
    price_minor: Optional[int] = None
    latency_ms: Optional[float] = None
    sla_ok: bool = True
    available: bool = True
    privacy_ok: bool = True
    org_id: str = ""
    preferred: bool = False          # user preference boost (small, capped)


@dataclass
class ScoredCandidate:
    agent_id: str
    service_id: str
    source: str
    score: float
    breakdown: Dict[str, Any] = field(default_factory=dict)
    eligible: bool = True
    rejection: str = ""

    def explanation(self) -> str:
        b = self.breakdown
        parts = [
            f"capability_fit={b.get('capability_fit')}",
            f"trust={b.get('trust_component')} (conf {b.get('trust_confidence')})",
            f"reliability={b.get('reliability_component')}",
            f"security={b.get('security_component')}",
            f"evidence={b.get('evidence_component')}",
            f"cost_adj={b.get('cost_adjustment')}",
            f"latency_adj={b.get('latency_adjustment')}",
            f"sla={'ok' if b.get('sla_ok') else 'FAIL'}",
            f"privacy={'ok' if b.get('privacy_ok') else 'FAIL'}",
        ]
        return f"score={self.score:.4f}: " + ", ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _scale_trust(v: float) -> float:
    """Map trust [-1,1] to weight [0,1]. Negative trust => 0."""
    return max(0.0, min(1.0, (v + 1.0) / 2.0))


class AgentSelectionEngine:
    """Stateless, deterministic scorer. No LLM in the path (spec 10)."""

    def __init__(self, goal: str = "balanced") -> None:
        if goal not in ("cheapest", "fastest", "most_reliable",
                        "most_private", "best_quality", "balanced"):
            raise ValueError(f"bad optimization goal: {goal!r}")
        self.goal = goal

    def score(self, cand: CandidateSignals,
              budget_minor: Optional[int] = None) -> ScoredCandidate:
        breakdown: Dict[str, Any] = {}
        # Hard gates first (never scored through).
        if not cand.available:
            return ScoredCandidate(cand.agent_id, cand.service_id, cand.source,
                                   0.0, breakdown, False, "unavailable")
        if not cand.sla_ok:
            return ScoredCandidate(cand.agent_id, cand.service_id, cand.source,
                                   0.0, breakdown, False, "SLA requirements unmet")
        if not cand.privacy_ok:
            return ScoredCandidate(cand.agent_id, cand.service_id, cand.source,
                                   0.0, breakdown, False, "data policy violation")
        if budget_minor is not None and cand.price_minor is not None \
                and cand.price_minor > budget_minor:
            return ScoredCandidate(cand.agent_id, cand.service_id, cand.source,
                                   0.0, breakdown, False,
                                   f"price {cand.price_minor} exceeds budget {budget_minor}")

        trust_w = _scale_trust(cand.trust_overall)
        # Low-confidence trust/reliability dampens (never rewards ignorance).
        trust_w *= 0.5 + 0.5 * cand.trust_confidence
        rel_w = cand.reliability * (0.5 + 0.5 * cand.reliability_confidence)
        sec_w = cand.security
        ev_w = 0.5 + 0.5 * cand.evidence_quality
        base = cand.capability_fit * trust_w * rel_w * sec_w * ev_w
        breakdown.update({
            "capability_fit": cand.capability_fit,
            "trust_component": round(trust_w, 4),
            "trust_confidence": cand.trust_confidence,
            "reliability_component": round(rel_w, 4),
            "security_component": sec_w,
            "evidence_component": round(ev_w, 4),
            "base": round(base, 6),
        })

        cost_adj = 1.0
        if cand.price_minor is not None and cand.price_minor > 0:
            # Logarithmic penalty: 10x price ~= -0.15. Free stays 1.0.
            import math
            cost_adj = max(0.05, 1.0 - 0.15 * math.log10(1 + cand.price_minor / 100.0))
        elif cand.price_minor == 0:
            cost_adj = 1.0
        lat_adj = 1.0
        if cand.latency_ms is not None:
            import math
            lat_adj = max(0.05, 1.0 - 0.1 * math.log10(1 + cand.latency_ms / 1000.0))

        goal_boost = 1.0
        if self.goal == "cheapest" and (cand.price_minor or 0) == 0:
            goal_boost = 1.1
        elif self.goal == "most_private" and cand.privacy_ok and cand.trust_overall >= 0.5:
            goal_boost = 1.05
        if cand.preferred:
            goal_boost *= 1.05  # capped, documented preference nudge

        # Goal-aware adjustment application (deterministic per goal).
        if self.goal == "cheapest":
            final = base * (0.2 + 0.8 * cost_adj) * (0.95 + 0.05 * lat_adj)
        elif self.goal == "fastest":
            final = base * (0.95 + 0.05 * cost_adj) * (0.2 + 0.8 * lat_adj)
        elif self.goal in ("most_reliable", "best_quality", "most_private"):
            final = base * (0.9 + 0.1 * cost_adj) * (0.9 + 0.1 * lat_adj)
        else:  # balanced
            final = base * (0.7 + 0.3 * cost_adj) * (0.7 + 0.3 * lat_adj)
        final *= goal_boost

        breakdown.update({
            "cost_adjustment": round(cost_adj, 4),
            "latency_adjustment": round(lat_adj, 4),
            "goal": self.goal,
            "goal_boost": round(goal_boost, 4),
            "sla_ok": cand.sla_ok,
            "privacy_ok": cand.privacy_ok,
        })
        return ScoredCandidate(cand.agent_id, cand.service_id, cand.source,
                               round(final, 6), breakdown, True, "")

    def rank(self, candidates: List[CandidateSignals],
             budget_minor: Optional[int] = None,
             limit: int = 10) -> List[ScoredCandidate]:
        scored = [self.score(c, budget_minor) for c in candidates]
        eligible = [s for s in scored if s.eligible]
        # Deterministic tiebreak by agent_id.
        eligible.sort(key=lambda s: (-s.score, s.agent_id))
        return eligible[:max(limit, 0)]

    def compare(self, a: ScoredCandidate, b: ScoredCandidate) -> Dict[str, Any]:
        """Transparent A-vs-B comparison matrix row source (spec 23)."""
        keys = ("capability_fit", "trust_component", "reliability_component",
                "security_component", "evidence_component", "cost_adjustment",
                "latency_adjustment")
        rows = []
        for k in keys:
            va = a.breakdown.get(k)
            vb = b.breakdown.get(k)
            winner = "tie"
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                winner = "A" if va > vb else ("B" if vb > va else "tie")
            rows.append({"metric": k, "A": va, "B": vb, "winner": winner})
        return {"A": {"agent_id": a.agent_id, "score": a.score},
                "B": {"agent_id": b.agent_id, "score": b.score},
                "rows": rows}
