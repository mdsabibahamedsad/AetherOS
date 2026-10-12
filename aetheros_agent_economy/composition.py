"""Capability composition engine + dependency graph (spec sections 3-4).

Capability A + B + C = composite capability with a real dependency DAG.
Cycles are rejected deterministically. The graph also links capability
-> provider -> service -> agent -> organization -> trust/performance/
price, plus capability -> capability dependency/composition edges.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .capabilities import CapabilityDefinition, CapabilityRegistry
from aetheros_agent_market.store import JsonStore


@dataclass
class Composition:
    composition_id: str = ""
    name: str = ""
    member_ids: List[str] = field(default_factory=list)  # capability_ids in order
    edges: List[List[str]] = field(default_factory=list)  # [from, to] dependency pairs
    topo_order: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Composition":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


def topo_sort(nodes: List[str], edges: List[List[str]]) -> List[str]:
    """Deterministic Kahn's algorithm. Raises ValueError on cycles."""
    deps: Dict[str, Set[str]] = {n: set() for n in nodes}
    dependents: Dict[str, Set[str]] = {n: set() for n in nodes}
    for frm, to in edges:
        if frm not in deps or to not in deps:
            raise ValueError(f"edge references unknown node: {frm!r} -> {to!r}")
        if frm == to:
            raise ValueError(f"self-dependency: {frm!r}")
        deps[to].add(frm)
        dependents[frm].add(to)
    ready = sorted(n for n in nodes if not deps[n])
    order: List[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for dep in sorted(dependents[node]):
            deps[dep].discard(node)
            if not deps[dep]:
                ready.append(dep)
        ready.sort()
    if len(order) != len(nodes):
        cyclic = sorted(set(nodes) - set(order))
        raise ValueError(f"dependency cycle detected among: {cyclic}")
    return order


class CapabilityCompositionEngine:
    """Compose capabilities; produces dependency graph, never executes."""

    def __init__(self, home: Path, registry: CapabilityRegistry) -> None:
        self._store = JsonStore(Path(home) / "compositions.json")
        self._registry = registry

    def compose(self, name: str, member_ids: List[str],
                extra_edges: Optional[List[List[str]]] = None) -> Composition:
        if not name or len(name) > 160:
            raise ValueError("composition name required (<=160 chars)")
        if len(member_ids) < 2:
            raise ValueError("composition needs at least 2 capabilities")
        if len(set(member_ids)) != len(member_ids):
            raise ValueError("duplicate members in composition")
        defs = {}
        for cid in member_ids:
            d = self._registry.get(cid)
            if d is None:
                raise KeyError(f"unknown capability: {cid}")
            if d.status == "revoked":
                raise ValueError(f"capability revoked: {cid}")
            defs[cid] = d
        # Edges: explicit extra edges + prerequisite edges from definitions.
        edges: List[List[str]] = [list(e) for e in (extra_edges or [])]
        for cid in member_ids:
            for pre in defs[cid].prerequisites:
                if pre in defs:
                    edges.append([pre, cid])
        # Deduplicate preserving order.
        seen, deduped = set(), []
        for e in edges:
            key = (e[0], e[1])
            if key not in seen:
                seen.add(key)
                deduped.append([e[0], e[1]])
        order = topo_sort(list(member_ids), deduped)
        import secrets
        comp = Composition(
            composition_id=f"comp-{secrets.token_hex(8)}", name=name,
            member_ids=list(member_ids), edges=deduped, topo_order=order)
        self._store.put(comp.composition_id, comp.to_dict())
        return comp

    def get(self, composition_id: str) -> Optional[Composition]:
        raw = self._store.get(composition_id)
        return Composition.from_dict(raw) if raw else None

    def list(self) -> List[Composition]:
        return [Composition.from_dict(r) for r in self._store.values()]


class CapabilityGraph:
    """Read model over registry + market + trust + reputation + pricing.

    Nodes: capability, provider(agent), service, organization.
    Edges: provides, consumes, depends_on, composes, offered_by, member_of.
    Trust/performance/price resolve live from the underlying engines —
    the graph never caches a score (no stale security state).
    """

    def __init__(self, registry: CapabilityRegistry,
                 market_flow=None) -> None:
        self._registry = registry
        self._flow = market_flow

    def capability_node(self, capability_id: str) -> Dict[str, Any]:
        d = self._registry.get(capability_id)
        if d is None:
            raise KeyError(f"unknown capability: {capability_id}")
        node: Dict[str, Any] = {"kind": "capability", **d.to_dict()}
        node["providers_live"] = self._providers_for(capability_id)
        return node

    def _providers_for(self, capability_id: str) -> List[Dict[str, Any]]:
        """Providers = registry-attached agents + market services whose
        taxonomy capabilities include this id (live query, no cache)."""
        out: List[Dict[str, Any]] = []
        d = self._registry.get(capability_id)
        if d:
            for agent_id in d.providers:
                out.append({"agent_id": agent_id, "via": "registry",
                            "capability_id": capability_id})
        if self._flow is not None:
            try:
                from aetheros_agent_market.taxonomy import MatchRequest
                hits = self._flow.index.search(
                    MatchRequest(exact_capabilities=[capability_id]), limit=200)
                for h in hits:
                    out.append({"agent_id": h.agent_id,
                                "service_id": h.service_id,
                                "via": f"market:{h.source}",
                                "capability_id": capability_id})
            except Exception:
                pass
        # Deduplicate by (agent_id, service_id).
        seen, deduped = set(), []
        for p in out:
            key = (p.get("agent_id"), p.get("service_id", ""))
            if key not in seen:
                seen.add(key)
                deduped.append(p)
        return deduped

    def subgraph(self, capability_id: str, depth: int = 2) -> Dict[str, Any]:
        """Capability -> prerequisites (dependencies) + providers."""
        if depth < 0:
            raise ValueError("depth must be >= 0")
        root = self.capability_node(capability_id)
        node: Dict[str, Any] = {"capability": root, "dependencies": [],
                                "providers": root.pop("providers_live", [])}
        if depth == 0:
            return node
        d = self._registry.get(capability_id)
        for pre in (d.prerequisites if d else []):
            try:
                node["dependencies"].append(self.subgraph(pre, depth - 1))
            except KeyError:
                node["dependencies"].append({"capability_id": pre,
                                             "missing": True})
        return node

    def trace_provider(self, agent_id: str) -> Dict[str, Any]:
        """Agent -> organization, trust summary, services, capabilities."""
        info: Dict[str, Any] = {"agent_id": agent_id, "services": [],
                                "capabilities": [], "organization_id": "",
                                "trust": None}
        if self._flow is None:
            return info
        try:
            detail = self._flow.registry.discover_agents() or []
            for rec in detail:
                if rec.get("agent_id") == agent_id:
                    info["organization_id"] = rec.get("organization_id", "")
                    break
        except Exception:
            pass
        try:
            for svc in self._flow.registry.discover_services(
                    {"status": "published", "agent_id": agent_id}):
                info["services"].append(svc.get("service_id", ""))
                for cap in svc.get("capabilities", []) or []:
                    cid = cap.get("capability_id", "") if isinstance(cap, dict) else str(cap)
                    if cid and cid not in info["capabilities"]:
                        info["capabilities"].append(cid)
        except Exception:
            pass
        try:
            info["trust"] = self._flow.trust.profile(agent_id)
        except Exception:
            pass
        return info
