"""Typed knowledge graph over entities + memories (P13, P14).

Edges are typed, timestamped, provenance-aware (evidence item id) and
confidence-aware. Stored in the unified SQLite substrate; no separate graph
database is introduced (P74).
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from agent.memory_os.entities import EntityRegistry
from agent.memory_os.models import MemoryStatus, RelationshipType
from agent.memory_os.store import MemoryStore


class KnowledgeGraph:
    def __init__(self, store: MemoryStore, entities: EntityRegistry):
        self._store = store
        self.entities = entities

    def relate(
        self,
        src_kind: str,
        src_id: str,
        rel: RelationshipType,
        dst_kind: str,
        dst_id: str,
        *,
        evidence_item_id: str = "",
        confidence: float = 0.5,
        valid_from: Optional[float] = None,
        valid_until: Optional[float] = None,
    ) -> Dict[str, Any]:
        edge = {
            "edge_id": uuid.uuid4().hex[:12],
            "src_kind": src_kind,
            "src_id": src_id,
            "dst_kind": dst_kind,
            "dst_id": dst_id,
            "rel": rel.value,
            "evidence_item_id": evidence_item_id,
            "confidence": float(confidence),
            "created_at": time.time(),
            "valid_from": valid_from,
            "valid_until": valid_until,
            "status": "active",
        }
        self._store.add_edge(edge)
        return edge

    def unlink(self, edge_id: str) -> bool:
        return self._store.remove_edge(edge_id)

    def neighbors(self, node_kind: str, node_id: str) -> List[Dict[str, Any]]:
        return self._store.edges_for(node_kind, node_id)

    def subgraph(self, node_kind: str, node_id: str, depth: int = 1) -> Dict[str, Any]:
        """Bounded traversal (depth-capped; no unbounded walks). Nodes are
        registered at discovery time so frontier boundaries count."""
        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []
        nodes[f"{node_kind}:{node_id}"] = {"kind": node_kind, "id": node_id}
        frontier = [(node_kind, node_id)]
        seen = set(frontier)
        for _ in range(max(1, depth)):
            nxt: List[tuple] = []
            for kind, nid in frontier:
                for e in self._store.edges_for(kind, nid):
                    edges.append(e)
                    for other in ((e["src_kind"], e["src_id"]),
                                  (e["dst_kind"], e["dst_id"])):
                        key = f"{other[0]}:{other[1]}"
                        if key not in nodes:
                            nodes[key] = {"kind": other[0], "id": other[1]}
                        if other not in seen:
                            seen.add(other)
                            nxt.append(other)
            frontier = nxt
        return {"nodes": list(nodes.values()), "edges": edges}

    def contradicting_edges(self, item_id: str) -> List[Dict[str, Any]]:
        out = []
        for e in self._store.all_edges():
            if e["rel"] == RelationshipType.CONTRADICTS.value and (
                e["src_id"] == item_id or e["dst_id"] == item_id
            ):
                out.append(e)
        return out

    def purge_node(self, node_kind: str, node_id: str) -> int:
        """Right-to-forget support: deactivate every edge touching a node."""
        n = 0
        for e in self._store.all_edges():
            touches = (
                e["src_kind"] == node_kind and e["src_id"] == node_id
            ) or (
                e["dst_kind"] == node_kind and e["dst_id"] == node_id
            )
            if touches and e["status"] == "active":
                e["status"] = "forgotten"
                self._store.add_edge(e)
                n += 1
        return n
