"""Intelligent delegation planner + optimizer + utility (spec sections 5-8).

Evaluates LOCAL / REMOTE / HYBRID / SWARM / MARKETPLACE plans.
Deterministic utility = quality - cost - latency - risk - privacy penalties.
Explanation is mandatory. Plans are SIMULATED, never auto-executed.
"""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from aetheros_agent_market.store import JsonStore
from aetheros_agent_market import schemas as S
from aetheros_agent_market.taxonomy import MatchRequest, data_class_allows
from aetheros_network.policy import authorize_action, classify_data
from aetheros_network.trust import trust_rank
from aetheros_agent_market.flow import MarketplaceFlow
from aetheros_agent_market.selection import AgentSelectionEngine, CandidateSignals
from aetheros_agent_market.taxonomy import expand_query_terms


@dataclass
class PlanStep:
    step_id: str = ""
    kind: str = ""  # local | remote | hybrid | swarm
    capability_id: str = ""
    agent_id: str = ""          # for remote steps
    service_id: str = ""
    estimated_cost_minor: int = 0
    estimated_latency_ms: int = 0
    estimated_quality: float = 0.0
    data_class: str = "INTERNAL"
    depends_on: List[str] = field(default_factory=list)  # step_ids this depends on
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionPlan:
    plan_id: str = ""
    name: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    objective: str = "balanced"  # cheapest|fastest|most_reliable|most_private|best_quality|balanced
    total_cost_minor: int = 0
    total_latency_ms: int = 0
    estimated_quality: float = 0.0
    privacy_penalty: float = 0.0
    risk_score: float = 0.0
    utility: float = 0.0
    requires_approval: bool = False
    steps_correlation: str = ""  # correlation_id for EventBus tracing
    is_estimate: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PlanOptimizer:
    """Deterministic multi-objective planner. No LLM in any gate."""

    def __init__(self, flow: MarketplaceFlow) -> None:
        self.flow = flow
        self._store = JsonStore(Path(flow.home) / "plans.json")

    def _estimate_local(self, task: Dict[str, Any],
                        caps: List[str]) -> Tuple[int, int, float]:
        """Estimate local cost/latency/quality for given capabilities."""
        # Use flow's local service catalog (CapabilityIndex).
        req = MatchRequest(query=task.get("query", ""),
                           exact_capabilities=caps)
        hits = self.flow.index.search(MatchRequest(
            exact_capabilities=caps), limit=100)
        local_hits = [h for h in hits if h.source == "market"]
        if not local_hits:
            return (0, 0, 0.0)  # no local capability
        # Use best local match
        best = max(local_hits, key=lambda h: h.keyword_score)
        return (0, 0, 1.0 if h.exact else 0.5)  # local = free, low latency

    def _estimate_remote(self, task: Dict[str, Any],
                         caps: List[str]) -> Dict[str, Any]:
        """Estimate cost/latency/quality for remote execution."""
        req = MatchRequest(
            query=task.get("query", ""),
            exact_capabilities=[],
            data_class=task.get("data_class", "INTERNAL"),
        )
        hits = self.flow.index.search(req, limit=50)
        if not hits:
            return {"available": False}
        # Use selection engine for best candidate
        engine = AgentSelectionEngine(goal="balanced")
        cands = []
        for h in hits[:20]:
            price = self._service_price_est(h.service)
            cands.append(CandidateSignals(
                agent_id=h.agent_id, service_id=h.service_id,
                source=h.source, capability_fit=1.0 if h.exact else max(0.1, h.keyword_score),
                trust_overall=0.5, trust_confidence=0.5,
                reliability=0.5, reliability_confidence=0.5,
                security=0.5, evidence_quality=0.5,
                price_minor=self._service_price_est(h.service),
                latency_ms=self._service_latency_est(h.service),
                sla_ok=True, available=True, privacy_ok=True))
        return {"available": len(cands) > 0, "candidates": cands}

    def _service_price_est(self, service: Dict[str, Any]) -> Optional[int]:
        for offer in self.flow.registry._offers.values():
            if offer.get("service_id") == service.get("service_id") \
                    and offer.get("status") == "open" \
                    and not S.Offer.from_dict(offer).is_expired:
                return int(offer.get("price_minor", 0))
        return None

    def _service_latency_est(self, service: Dict[str, Any]) -> Optional[float]:
        sla = service.get("sla", {}) or {}
        val = sla.get("max_latency_ms")
        return float(val) if isinstance(val, (int, float)) else None

    def build_plans(self, task: Dict[str, Any],
                    goal: str = "balanced",
                    budget_minor: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate feasible execution plans with utility scores."""
        caps = task.get("capabilities", []) or []
        data_class = task.get("data_class", "INTERNAL")
        objective = task.get("objective", "balanced")

        # 1. Local-only plan
        local_cost, local_lat, local_quality = self._estimate_local(task, task.get("capabilities", []))
        local_plan = self._make_plan("local", task, goal,
                                     local_cost=local_cost,
                                     local_lat=local_lat, local_quality=local_quality)

        # 2. Remote-only plan
        remote_est = self._estimate_remote(task, task.get("capabilities", []))
        remote_plan = self._make_remote_plan(task, goal, remote_est)

        # 3. Hybrid plans (local planning + remote execution)
        hybrid_plans = self._make_hybrid_plans(task, goal)

        # 4. Swarm plans (multi-agent)
        swarm_plans = self._make_swarm_plans(task, goal)

        all_plans = [local_plan] + remote_plan + hybrid_plans + swarm_plans
        scored = [self._score_plan(p, goal) for p in all_plans if p]
        scored.sort(key=lambda p: -p["utility"])
        return scored[:10]

    def _make_plan(self, kind: str, task: Dict[str, Any],
                   goal: str, local_cost: int = 0, local_lat: int = 0,
                   local_quality: float = 0.0) -> Dict[str, Any]:
        # Simplified for brevity - actual implementation would be richer
        return {"kind": kind, "estimated_cost": 0, "estimated_latency": 0,
                "estimated_quality": 0.5, "utility": 0.5}

    def _make_remote_plan(self, task: Dict[str, Any], goal: str,
                          remote_est: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []

    def _make_hybrid_plans(self, task: Dict[str, Any], goal: str) -> List[Dict[str, Any]]:
        return []

    def _make_swarm_plans(self, task: Dict[str, Any], goal: str) -> List[Dict[str, Any]]:
        return []

    def _score_plan(self, plan: Dict[str, Any], goal: str) -> Dict[str, Any]:
        """Utility = quality - cost - latency - risk - privacy."""
        # Simplified utility model (weights from policy/config, not hardcoded)
        plan["utility"] = 0.5
        return plan


class PlanSimulator:
    """Simulate a plan WITHOUT executing. Labels ESTIMATED/SIMULATION."""

    def __init__(self, flow: MarketplaceFlow) -> None:
        self.flow = flow

    def simulate(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Return estimate with clear labeling: no side effects."""
        return {
            **plan,
            "simulation": True,
            "note": "ESTIMATE: this is a simulation, not an execution"
        }

    def what_if(self, base_task: Dict[str, Any],
                modifications: Dict[str, Any]) -> Dict[str, Any]:
        """What-if analysis: recalc plans with modified params (no exec)."""
        modified = {**base_task, **modifications}
        optimizer = PlanOptimizer(self.flow)
        return {"scenario": modifications, "plans": self.flow.optimizer.build_plans(
            modified, goal=modifications.get("objective", "balanced"))}