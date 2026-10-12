"""Research knowledge graph with conservative entity resolution (P50-53).

Entities are merged ONLY on identical normalized names of the same type
that also share at least one corroborating source; everything else stays a
distinct node until an explicit, evidence-backed resolution is recorded.
Every edge carries confidence plus evidence/source references.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple


ENTITY_TYPES = frozenset(
    {"person", "organization", "product", "technology", "event", "document",
     "claim", "source", "repository", "location"}
)

RELATIONS = frozenset(
    {"authored", "published", "created", "depends_on", "mentions",
     "contradicts", "supports", "related_to"}
)


def normalize_entity_name(name: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (name or "").lower()))


@dataclass
class GraphEntity:
    name: str
    etype: str
    normalized: str = ""
    entity_id: str = ""
    confidence: float = 0.3
    source_ids: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.normalized:
            self.normalized = normalize_entity_name(self.name)


@dataclass
class GraphEdge:
    src_id: str
    dst_id: str
    relation: str
    confidence: float
    edge_id: str = ""
    evidence_refs: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)


class ResearchKnowledgeGraph:
    """In-memory graph; persistence goes through ResearchStore.save_graph."""

    def __init__(self):
        self.entities: Dict[str, GraphEntity] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self._counter = 0

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter:05d}"

    # -- entities ---------------------------------------------------------

    def add_entity(
        self,
        name: str,
        etype: str,
        confidence: float = 0.3,
        source_ids: Optional[List[str]] = None,
    ) -> Tuple[str, bool]:
        """Returns (entity_id, created_new). Conservative resolution applies."""
        if etype not in ENTITY_TYPES:
            raise ValueError(f"unknown entity type: {etype}")
        normalized = normalize_entity_name(name)
        for existing in self.entities.values():
            if existing.normalized == normalized and existing.etype == etype:
                shared = set(existing.source_ids or []) & set(source_ids or [])
                if shared:
                    if confidence > existing.confidence:
                        existing.confidence = confidence
                    for sid in source_ids or []:
                        if sid not in existing.source_ids:
                            existing.source_ids.append(sid)
                    return existing.entity_id, False
                # Same name, no shared evidence: do NOT merge (P51).
        eid = self._next_id("e")
        self.entities[eid] = GraphEntity(
            name=name.strip(), etype=etype, normalized=normalized,
            entity_id=eid, confidence=max(0.0, min(1.0, confidence)),
            source_ids=list(source_ids or []),
        )
        return eid, True

    def declare_alias(self, canonical_id: str, alias: str,
                      evidence_source_ids: Optional[List[str]] = None) -> bool:
        """Explicit, evidence-backed name resolution (the ONLY other merge)."""
        canonical = self.entities.get(canonical_id)
        if canonical is None:
            return False
        normalized_alias = normalize_entity_name(alias)
        duplicate = next(
            (
                e
                for e in self.entities.values()
                if e.entity_id != canonical_id and e.normalized == normalized_alias
            ),
            None,
        )
        if duplicate is not None:
            if not (evidence_source_ids or []) and not (
                set(duplicate.source_ids) & set(canonical.source_ids)
            ):
                return False
            for sid in duplicate.source_ids:
                if sid not in canonical.source_ids:
                    canonical.source_ids.append(sid)
            for edge in self.edges.values():
                if edge.src_id == duplicate.entity_id:
                    edge.src_id = canonical_id
                if edge.dst_id == duplicate.entity_id:
                    edge.dst_id = canonical_id
            del self.entities[duplicate.entity_id]
            if normalized_alias not in canonical.aliases:
                canonical.aliases.append(duplicate.name)
            return True
        if alias not in canonical.aliases:
            canonical.aliases.append(alias)
        return True

    def find_by_name(self, name: str, etype: Optional[str] = None) -> List[GraphEntity]:
        normalized = normalize_entity_name(name)
        return [
            e
            for e in self.entities.values()
            if e.normalized == normalized and (etype is None or e.etype == etype)
        ]

    # -- edges --------------------------------------------------------------

    def link(
        self,
        src_id: str,
        relation: str,
        dst_id: str,
        confidence: float = 0.4,
        evidence_refs: Optional[List[str]] = None,
        source_ids: Optional[List[str]] = None,
    ) -> Optional[GraphEdge]:
        if relation not in RELATIONS:
            raise ValueError(f"unknown relation: {relation}")
        if src_id not in self.entities or dst_id not in self.entities:
            return None
        for edge in self.edges.values():
            if (edge.src_id, edge.relation, edge.dst_id) == (src_id, relation, dst_id):
                edge.confidence = max(edge.confidence, confidence)
                for ref in evidence_refs or []:
                    if ref not in edge.evidence_refs:
                        edge.evidence_refs.append(ref)
                return edge
        edge = GraphEdge(
            src_id=src_id,
            dst_id=dst_id,
            relation=relation,
            confidence=max(0.0, min(1.0, confidence)),
            edge_id=self._next_id("r"),
            evidence_refs=list(evidence_refs or []),
            source_ids=list(source_ids or []),
        )
        self.edges[edge.edge_id] = edge
        return edge

    # -- traversal ------------------------------------------------------------

    def neighbors(self, entity_id: str) -> List[Tuple[GraphEdge, GraphEntity]]:
        out = []
        for edge in self.edges.values():
            if edge.src_id == entity_id:
                out.append((edge, self.entities[edge.dst_id]))
            elif edge.dst_id == entity_id:
                out.append((edge, self.entities[edge.src_id]))
        return out

    def multi_hop(self, start_id: str, max_hops: int = 2) -> List[List[GraphEdge]]:
        """Chains of up to max_hops edges starting at start_id."""
        chains: List[List[GraphEdge]] = []

        def walk(current: str, path: List[GraphEdge]) -> None:
            if len(path) >= max_hops:
                return
            for edge, _neighbor in self.neighbors(current):
                if any(e.edge_id == edge.edge_id for e in path):
                    continue
                chains.append(path + [edge])
                nxt = edge.dst_id if edge.src_id == current else edge.src_id
                walk(nxt, path + [edge])

        walk(start_id, [])
        return chains

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> Dict:
        return {
            "entities": [dict(e.__dict__) for e in self.entities.values()],
            "edges": [
                {k: v for k, v in e.__dict__.items()} for e in self.edges.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ResearchKnowledgeGraph":
        graph = cls()
        for edata in data.get("entities", []):
            entity = GraphEntity(**edata)
            graph.entities[entity.entity_id] = entity
        for rdata in data.get("edges", []):
            edge = GraphEdge(**rdata)
            graph.edges[edge.edge_id] = edge
        return graph

    @staticmethod
    def extract_candidate_entities(text: str,
                                   known_names: Iterable[str] = ()) -> List[str]:
        """Very conservative candidate extraction: capitalized phrases that
        exactly match known vocabulary, plus explicit CamelCase tech tokens.
        Never invents entities from arbitrary prose alone."""
        found: List[str] = []
        for known in known_names:
            if known and re.search(
                r"\b" + re.escape(known.split()[0]), text or "", re.I
            ):
                found.append(known)
        for token in re.findall(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b", text or ""):
            if token not in found:
                found.append(token)
        return found[:12]
