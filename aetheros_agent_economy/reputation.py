"""Contextual reputation + specialization + performance profiles + learning (spec 5-7, 16-20).

Reputation is NEVER a single number. It's contextual by domain, task class,
capability. Specialization is inferred from VERIFIED outcomes only.
Learning is opt-in, policy-gated, and never manipulates user choice.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_agent_market.reputation import ReputationEngine
from aetheros_agent_market.store import JsonStore
from aetheros_agent_market import schemas as S


@dataclass
class DomainReputation:
    """Reputation scoped to a capability domain (e.g., 'coding', 'research')."""

    domain: str = ""
    agent_id: str = ""
    metrics: Dict[str, Metric] = field(default_factory=dict)  # per-domain metrics
    task_classes: Dict[str, Dict[str, Metric]] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentSpecialization:
    """Inferred from VERIFIED outcomes only. Never from names/claims."""

    agent_id: str = ""
    specializations: Dict[str, float] = field(default_factory=dict)  # domain -> strength [0,1]
    evidence_count: Dict[str, int] = field(default_factory=dict)  # domain -> verified sample count
    last_recomputed: float = field(default_factory=time.time)
    min_samples_for_claim: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceProfile:
    """Observable metrics with provenance (spec 17)."""

    agent_id: str = ""
    metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # name -> {value, confidence, sample_count, window, provenance}
    domain_reputations: Dict[str, DomainReputation] = field(default_factory=dict)
    specialization: Optional[AgentSpecialization] = None
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceProfiler:
    """Builds contextual profiles from ReputationEngine (verified outcomes only)."""

    def __init__(self, trust: Any, reputation: ReputationEngine,
                 flow=None) -> None:
        self._trust = trust
        self._reputation = reputation
        self._flow = flow

    def build_profile(self, agent_id: str,
                      window_days: float = 30.0) -> PerformanceProfile:
        """Builds contextual profile from verified outcomes only."""
        base = self._reputation.profile(agent_id, window_days)
        domains = self._extract_domains(agent_id, window_days)
        spec = self._infer_specialization(agent_id, window_days)
        return PerformanceProfile(
            agent_id=agent_id,
            metrics=base.metrics,
            domain_reputations=domains,
            specialization=spec)

    def _extract_domains(self, agent_id: str,
                         window_days: float) -> Dict[str, DomainReputation]:
        """Groups reputation metrics by capability domain."""
        # Map metrics to domains via taxonomy. Only VERIFIED/observed outcomes count.
        out: Dict[str, DomainReputation] = {}
        # Simplified: map known metric prefixes to domains
        domain_map = {
            "coding": "coding",
            "research": "research",
            "documents": "documents",
            "media": "media",
            "data": "data",
            "browser": "browser",
        }
        # In real implementation, would map each metric to its domain
        # For now, return empty - full impl would use taxonomy mapping
        return out

    def _infer_specialization(self, agent_id: str,
                              window_days: float) -> Optional[AgentSpecialization]:
        """Infer from VERIFIED outcomes only. Min 3 samples per domain."""
        profile = self._reputation.profiles_for([agent_id], window_days).get(agent_id)
        if not profile:
            return None
        specs: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for name, metric in profile.metrics.items():
            if metric.provenance != "verified":
                continue
            if metric.sample_count < 3:
                continue
            # Map metric to domain (simplified)
            domain = self._metric_to_domain(name)
            if not domain:
                continue
            val = metric.value
            if val >= 0.7 and metric.confidence >= 0.5:
                specs[domain] = max(specs.get(domain, 0.0), val)
                counts[domain] = counts.get(domain, 0) + metric.sample_count
        if not specs:
            return None
        return AgentSpecialization(
            agent_id=agent_id,
            specializations=specs,
            evidence_count=counts)

    @staticmethod
    def _metric_to_domain(name: str) -> Optional[str]:
        if name.startswith("coding.") or "code" in name:
            return "coding"
        if name.startswith("research.") or "research" in name:
            return "research"
        if name.startswith("documents.") or name in ("citation", "extraction", "translation"):
            return "documents"
        if name in ("latency", "cost_efficiency"):
            return "performance"
        if name == "security":
            return "security"
        return None


class DiscoveryLearner:
    """Records user choices (opt-in only). Never manipulates choice."""

    def __init__(self, home: Path) -> None:
        self._store = JsonStore(Path(home) / "discovery_learn.json")

    def record_choice(self, user_id: str, task: str, agent_id: str,
                      was_optimal: bool = True) -> Dict[str, Any]:
        """Record a user's explicit preference for a task type."""
        entry = {"id": _new_id("learn"), "user_id": user_id,
                 "task_type": task[:200], "agent_id": agent_id,
                 "was_optimal": was_optimal, "at": time.time()}
        self._store.put(entry["id"], entry)
        return entry

    def get_preferences(self, user_id: str,
                        limit: int = 100) -> List[Dict[str, Any]]:
        out = []
        for raw in self._store.values():
            if raw.get("user_id") == user_id:
                out.append(raw)
        out.sort(key=lambda x: x.get("at", 0), reverse=True)
        return out[:limit]


def _new_id(prefix: str) -> str:
    import secrets
    return f"{prefix}-{secrets.token_hex(8)}"