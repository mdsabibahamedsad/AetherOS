"""Agent network router (Master 46 sections 27-30, 90).

Selects among local agent / local swarm / trusted remote / organization /
federated candidates using capability, trust, privacy, latency, cost,
availability. Never picks an untrusted agent merely for speed. Every
decision emits an AgentRouteDecision trace.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .trust import trust_rank

ROUTING_MODES = (
    "local_only", "trusted_local", "organization_only",
    "trusted_remote", "federated", "auto",
)


@dataclass
class RouteCandidate:
    agent_id: str
    kind: str  # local | swarm | remote | organization | federated
    capabilities: List[str] = field(default_factory=list)
    trust: str = "unknown"
    latency_ms: Optional[float] = None
    cost: Optional[float] = None
    available: bool = True
    organization_id: str = ""
    reliability: Optional[float] = None  # 0..1, evidence-backed, task-class specific


@dataclass
class AgentRouteDecision:
    task_id: str
    candidates: List[str]
    eligible: List[str]
    rejected: Dict[str, str]
    selected: str
    trust: str = ""
    policy: str = ""
    privacy: str = ""
    latency_ms: Optional[float] = None
    cost: Optional[float] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AgentNetworkRouter:
    def __init__(self, organization_id: str = "local") -> None:
        self._org = organization_id

    def route(self, task_id: str, required_capabilities: List[str],
              candidates: List[RouteCandidate], mode: str = "auto",
              max_data_class: str = "internal",
              sla: Optional[Dict[str, Any]] = None) -> AgentRouteDecision:
        if mode not in ROUTING_MODES:
            raise ValueError(f"unknown routing mode: {mode!r}")
        sla = sla or {}
        rejected: Dict[str, str] = {}
        eligible: List[RouteCandidate] = []

        for c in candidates:
            reason = self._filter(c, mode, required_capabilities, max_data_class, sla)
            if reason:
                rejected[c.agent_id] = reason
            else:
                eligible.append(c)

        selected = ""
        if eligible:
            # Order: trust rank first, then capability coverage, reliability,
            # latency, cost. Speed/cost never outrank trust.
            def score(c: RouteCandidate):
                cover = len(set(c.capabilities) & set(required_capabilities))
                return (
                    trust_rank(c.trust),
                    cover,
                    c.reliability if c.reliability is not None else 0.5,
                    -(c.latency_ms if c.latency_ms is not None else 1e9),
                    -(c.cost if c.cost is not None else 1e9),
                )
            eligible.sort(key=score, reverse=True)
            selected = eligible[0].agent_id

        sel = next((c for c in eligible if c.agent_id == selected), None)
        return AgentRouteDecision(
            task_id=task_id,
            candidates=[c.agent_id for c in candidates],
            eligible=[c.agent_id for c in eligible],
            rejected=rejected,
            selected=selected,
            trust=sel.trust if sel else "",
            policy=f"mode={mode}",
            privacy=f"max_data={max_data_class}",
            latency_ms=sel.latency_ms if sel else None,
            cost=sel.cost if sel else None,
        )

    def _filter(self, c: RouteCandidate, mode: str, required: List[str],
                max_data_class: str, sla: Dict[str, Any]) -> str:
        if mode == "local_only" and c.kind not in ("local", "swarm"):
            return f"mode=local_only excludes {c.kind}"
        if mode == "trusted_local" and (c.kind not in ("local", "swarm") or trust_rank(c.trust) < 3):
            return "mode=trusted_local requires verified local"
        if mode == "organization_only" and (
                c.organization_id != self._org or trust_rank(c.trust) < 5):
            return "mode=organization_only requires org-trusted member"
        if mode == "trusted_remote" and (
                c.kind not in ("remote", "organization") or trust_rank(c.trust) < 3):
            return "mode=trusted_remote requires verified remote"
        if mode == "federated" and c.kind not in ("remote", "organization", "federated"):
            return "mode=federated excludes local-only candidates"
        if not c.available:
            return "unavailable"
        if trust_rank(c.trust) < 0:
            return f"agent is {c.trust}"
        if mode in ("auto", "federated") and trust_rank(c.trust) < 2 and c.kind != "local":
            return f"trust {c.trust} too low for network routing"
        missing = set(required) - set(c.capabilities)
        if missing:
            return f"missing capabilities: {sorted(missing)}"
        # Privacy: sensitive+ data never goes below user_trusted.
        if max_data_class in ("sensitive", "highly_sensitive") and trust_rank(c.trust) < 4:
            return f"data class {max_data_class} requires user_trusted+, has {c.trust}"
        if max_data_class == "highly_sensitive" and c.kind in ("remote", "federated") \
                and trust_rank(c.trust) < 6:
            return "highly_sensitive remote delivery requires fully_trusted"
        if sla.get("max_latency_ms") is not None and c.latency_ms is not None \
                and c.latency_ms > sla["max_latency_ms"]:
            return f"latency {c.latency_ms} exceeds sla {sla['max_latency_ms']}"
        if sla.get("max_cost") is not None and c.cost is not None \
                and c.cost > sla["max_cost"]:
            return f"cost {c.cost} exceeds sla {sla['max_cost']}"
        if sla.get("required_trust") and trust_rank(c.trust) < trust_rank(sla["required_trust"]):
            return f"sla requires trust {sla['required_trust']}"
        return ""
