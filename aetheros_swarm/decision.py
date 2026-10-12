"""Decision engine: single-vs-multi + topology selection (sections 9-10, 55).

Estimates complexity, parallelism, domain diversity, verification need,
context size, failure risk, budgets and tool diversity from the goal text
(deterministic heuristics — no LLM call), then prices coordination:
spawn + context-transfer + communication + sync + verification + tokens +
latency + failure risk. Multi-agent must beat single-agent by a margin.
Simplest reliable architecture wins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from aetheros_swarm.models import Topology

_PARALLEL_HINTS = re.compile(r"\b(each|every|all|compare|competitors|files|sources|batch|map|in parallel)\b", re.I)
_DOMAIN_HINTS = re.compile(r"\b(research|code|test|security|browser|document|data|write|review|deploy)\b", re.I)
_VERIFY_HINTS = re.compile(r"\b(verify|test|prove|validate|audit|production|deploy|publish|purchase|delete)\b", re.I)
_COMPLEX_HINTS = re.compile(r"\b(and then|after that|compare|investigate|analyze|report|multi|several|architecture|strategy)\b", re.I)


@dataclass
class TaskFeatures:
    complexity: float = 0.0
    parallelism: float = 0.0
    domain_diversity: int = 1
    verification_need: float = 0.0
    context_size_est: int = 0
    failure_risk: float = 0.2
    tool_diversity: int = 1
    steps_est: int = 1


def analyze_goal(goal: str) -> TaskFeatures:
    text = goal or ""
    words = text.split()
    domains = set(_DOMAIN_HINTS.findall(text.lower()))
    complexity = min(1.0, 0.15 + 0.1 * len(_COMPLEX_HINTS.findall(text))
                     + 0.05 * max(0, len(words) - 10) / 10.0)
    parallelism = min(1.0, 0.1 + 0.3 * len(_PARALLEL_HINTS.findall(text)))
    verification = min(1.0, 0.2 * len(_VERIFY_HINTS.findall(text)) + (0.3 if "production" in text.lower() else 0.0))
    steps = max(1, text.count(" then ") + text.count(" after ") + text.count(",") // 2 + 1)
    return TaskFeatures(
        complexity=round(complexity, 3),
        parallelism=round(parallelism, 3),
        domain_diversity=max(1, len(domains)),
        verification_need=round(verification, 3),
        context_size_est=len(text) // 4,
        failure_risk=round(min(0.9, 0.2 + 0.1 * steps + 0.2 * verification), 3),
        tool_diversity=max(1, len(domains)),
        steps_est=steps)


@dataclass
class OrchestrationDecision:
    mode: str = "single"  # single|multi
    topology: Topology = Topology.SINGLE
    roles: List[str] = field(default_factory=list)
    agent_count: int = 1
    reason: str = ""
    features: TaskFeatures = field(default_factory=TaskFeatures)
    costs: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"mode": self.mode, "topology": self.topology.value,
                "roles": self.roles, "agent_count": self.agent_count,
                "reason": self.reason,
                "features": {f: getattr(self.features, f) for f in self.features.__dataclass_fields__},
                "costs": self.costs}


class OrchestrationDecisionEngine:
    """Deterministic single-vs-multi + topology choice."""

    # Coordination price table (relative units; documented, configurable).
    SPAWN = 1.0
    CTX_TRANSFER = 0.6
    MSG = 0.15
    SYNC = 0.5
    VERIFY_STEP = 0.8
    MARGIN = 1.5  # multi must beat single by this factor of value

    def __init__(self, *, max_agents: int = 10, prefer_single_bias: float = 0.4) -> None:
        self.max_agents = max_agents
        self.prefer_single_bias = prefer_single_bias

    def decide(self, goal: str, *, budget_tokens: int = 20000,
               latency_budget_s: float = 1800.0,
               force_single: bool = False) -> OrchestrationDecision:
        feats = analyze_goal(goal)
        if force_single:
            return OrchestrationDecision(mode="single", topology=Topology.SINGLE,
                                         roles=["coder"], agent_count=1,
                                         reason="force_single requested", features=feats)
        # Value of distribution grows with parallelism × diversity × steps.
        value_multi = (feats.parallelism * 2.0 + feats.domain_diversity * 0.8
                       + feats.steps_est * 0.5 + feats.verification_need * 0.7)
        # Coordination cost grows with agents needed.
        agents_needed = min(self.max_agents,
                            max(2, feats.domain_diversity + (1 if feats.parallelism > 0.4 else 0)
                                + (1 if feats.verification_need > 0.4 else 0)))
        cost_multi = (agents_needed * self.SPAWN
                      + agents_needed * self.CTX_TRANSFER
                      + agents_needed * 3 * self.MSG + self.SYNC
                      + feats.verification_need * 2 * self.VERIFY_STEP
                      + self.prefer_single_bias * 3.0)
        if value_multi < self.MARGIN * cost_multi / 4.0:
            return OrchestrationDecision(
                mode="single", topology=Topology.SINGLE, roles=["coder"],
                agent_count=1, features=feats,
                reason=f"single wins: value={value_multi:.2f} cost={cost_multi:.2f}",
                costs={"value_multi": round(value_multi, 2), "cost_multi": round(cost_multi, 2)})
        topology, roles = self._pick_topology(feats, goal)
        return OrchestrationDecision(
            mode="multi", topology=topology, roles=roles,
            agent_count=min(len(roles), self.max_agents), features=feats,
            reason=f"multi wins: value={value_multi:.2f} cost={cost_multi:.2f} -> {topology.value}",
            costs={"value_multi": round(value_multi, 2), "cost_multi": round(cost_multi, 2)})

    def _pick_topology(self, feats: TaskFeatures, goal: str):
        low = goal.lower()
        roles: List[str] = []
        if feats.parallelism > 0.5 and feats.verification_need < 0.5:
            topo = Topology.MAP_REDUCE if "each" in low or "every" in low else Topology.PARALLEL
            roles = ["researcher", "researcher", "analyst"]
        elif feats.verification_need > 0.5 and "code" in low:
            topo = Topology.REVIEW_LOOP
            roles = ["coder", "reviewer", "verifier"]
        elif feats.domain_diversity >= 3:
            topo = Topology.PIPELINE
            roles = ["researcher", "analyst", "writer", "reviewer"]
        elif "debate" in low or "compare" in low and "alternative" in low:
            topo = Topology.DEBATE
            roles = ["analyst", "analyst", "reviewer", "verifier"]
        elif feats.domain_diversity >= 2 and feats.steps_est >= 3:
            topo = Topology.HIERARCHICAL
            roles = ["orchestrator", "researcher", "coder", "reviewer"]
        else:
            topo = Topology.SUPERVISOR
            roles = ["orchestrator", "coder", "verifier"]
        if feats.verification_need > 0.6 and "verifier" not in roles:
            roles.append("verifier")
        return topo, roles
