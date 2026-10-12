"""Capability Discovery Engine (spec section 3).

Answers "what agents can do X?" across: local agents, trusted A2A
agents, private org registry, curated registry, user registries,
marketplace registry, direct Agent Card URL.

Deterministic constraints filter first (taxonomy.match_service);
keyword overlap only ranks survivors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from . import taxonomy as T


@dataclass
class IndexedService:
    service: Dict[str, Any]
    source: str                       # local|trusted_a2a|org|curated|user|market|direct
    trust_rank: int = 0
    price_minor: Optional[int] = None
    latency_ms: Optional[float] = None
    regions: List[str] = field(default_factory=list)


@dataclass
class DiscoveryHit:
    service: Dict[str, Any]
    source: str
    exact: bool
    keyword_score: float
    reasons: List[str] = field(default_factory=list)


class CapabilityIndex:
    """In-memory index over pluggable service providers."""

    def __init__(self) -> None:
        self._providers: Dict[str, Callable[[], List[IndexedService]]] = {}

    def add_provider(self, name: str,
                     fn: Callable[[], List[IndexedService]]) -> None:
        self._providers[name] = fn

    def sources(self) -> List[str]:
        return sorted(self._providers)

    def search(self, req: T.MatchRequest,
               limit: int = 50) -> List[DiscoveryHit]:
        hits: List[DiscoveryHit] = []
        for source, fn in self._providers.items():
            try:
                services = fn()
            except Exception:
                continue  # a dead source must not break discovery
            for item in services:
                m = T.match_service(
                    item.service, req,
                    agent_trust_rank=item.trust_rank,
                    price_minor=item.price_minor,
                    latency_ms=item.latency_ms,
                    regions=item.regions,
                )
                if m is None:
                    continue
                hits.append(DiscoveryHit(service=item.service, source=source,
                                         exact=m.exact, keyword_score=m.keyword_score,
                                         reasons=[f"source={source}"] + m.reasons))
        # Exact matches first, then keyword relevance. Deterministic order.
        hits.sort(key=lambda h: (not h.exact, -h.keyword_score,
                                 h.service.get("service_id", "")))
        return hits[:max(limit, 0)]


def local_services_provider(registry) -> Callable[[], List[IndexedService]]:
    """Adapt a MarketplaceRegistry (local/org) into an index provider."""
    def _fn() -> List[IndexedService]:
        out = []
        for svc in registry.discover_services({"status": "published"}):
            out.append(IndexedService(service=svc, source="market",
                                      trust_rank=0, regions=[]))
        return out
    return _fn


def network_services_provider() -> Callable[[], List[IndexedService]]:
    """Adapt trusted A2A network agents: each published skill becomes a
    searchable service entry derived from the LIVE card (never invented)."""
    def _fn() -> List[IndexedService]:
        from aetheros_network import gateway as _gw
        from aetheros_network.registry import AgentRegistry
        from aetheros_network.trust import TrustStore, trust_rank
        home = _gw.default_home()
        net = AgentRegistry(home / "registry.json")
        trust = TrustStore(home / "trust.json")
        try:
            rank_of = trust_rank
        except Exception:
            rank_of = lambda lvl: 0  # noqa: E731
        out: List[IndexedService] = []
        for rec in net.list():
            agent_id = rec.get("agent_id", "")
            try:
                rank = rank_of(trust.level(agent_id))
            except Exception:
                rank = 0
            card = rec.get("card", {}) or {}
            for skill in card.get("skills", []) or []:
                if not isinstance(skill, dict):
                    continue
                cap_id = str(skill.get("id", ""))
                if not cap_id:
                    continue
                svc = {
                    "service_id": f"a2a:{agent_id}:{cap_id}",
                    "agent_id": agent_id,
                    "name": str(skill.get("name", cap_id)),
                    "description": str(skill.get("description", "")),
                    "capabilities": [{"capability_id": cap_id,
                                      "protocols": ["A2A"],
                                      "data_classes": ["PUBLIC", "INTERNAL"]}],
                    "supported_protocols": ["A2A"],
                    "availability": "available" if rec.get("health") in ("online", "unknown") else "unavailable",
                    "status": "published",
                    "pricing_model": "quote",
                }
                out.append(IndexedService(
                    service=svc, source="trusted_a2a", trust_rank=rank,
                    latency_ms=rec.get("latency_ms"), regions=[]))
        return out
    return _fn
