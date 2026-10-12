"""Memory Visualization — data structures and builders for UI rendering.

Provides timeline, graph, tree, collection, pinned, and recent memory
views with multiple layout strategies and JSON export formats.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from aetheros_memory.knowledge_graph import KnowledgeGraph, GraphEntity, GraphRelationship
from aetheros_memory.memory_manager import MemoryManager, MemoryRecord

logger = logging.getLogger("aetheros_memory.visualization")


class GraphLayout(str, enum.Enum):
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    RADIAL = "radial"
    CIRCULAR = "circular"
    TIMELINE = "timeline"
    TREE = "tree"


@dataclass
class TimelineEntry:
    id: str = ""
    timestamp: float = 0.0
    type: str = ""
    title: str = ""
    description: str = ""
    importance: float = 1.0
    category: str = ""
    related_ids: List[str] = field(default_factory=list)


@dataclass
class CollectionEntry:
    id: str = ""
    name: str = ""
    description: str = ""
    memory_ids: List[str] = field(default_factory=list)
    entity_ids: List[str] = field(default_factory=list)
    count: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class VisualizationData:
    memories: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    timeline: List[TimelineEntry] = field(default_factory=list)
    collections: List[CollectionEntry] = field(default_factory=list)
    pinned: List[Dict[str, Any]] = field(default_factory=list)
    recent: List[Dict[str, Any]] = field(default_factory=list)
    total_count: int = 0
    graph_layout: GraphLayout = GraphLayout.FORCE_DIRECTED


class MemoryVisualization:
    def __init__(self) -> None:
        self._lock = threading.RLock()

    def build_timeline(
        self,
        memories: List[MemoryRecord],
        start_time: float = 0.0,
        end_time: float = 0.0,
        group_by: str = "day",
    ) -> List[TimelineEntry]:
        if end_time <= 0:
            end_time = time.time() + 1
        filtered = [m for m in memories if start_time <= m.created_at <= end_time]
        filtered.sort(key=lambda m: m.created_at, reverse=True)

        if group_by == "category":
            grouped: Dict[str, List[MemoryRecord]] = {}
            for m in filtered:
                grouped.setdefault(m.category.value, []).append(m)
            entries: List[TimelineEntry] = []
            for cat, group in grouped.items():
                primary = group[0]
                entries.append(TimelineEntry(
                    id=primary.id,
                    timestamp=primary.created_at,
                    type="category_group",
                    title=f"{cat} ({len(group)})",
                    description=primary.content[:200],
                    importance=primary.importance,
                    category=cat,
                    related_ids=[g.id for g in group],
                ))
            return entries

        entries = []
        for m in filtered:
            label = ""
            if group_by == "hour":
                label = time.strftime("%Y-%m-%d %H:00", time.gmtime(m.created_at))
            elif group_by == "day":
                label = time.strftime("%Y-%m-%d", time.gmtime(m.created_at))
            else:
                label = time.strftime("%Y-%m-%d %H:%M", time.gmtime(m.created_at))
            entries.append(TimelineEntry(
                id=m.id,
                timestamp=m.created_at,
                type=label,
                title=m.key or m.content[:80],
                description=m.content[:300],
                importance=m.importance,
                category=m.category.value,
                related_ids=[],
            ))
        return entries

    def build_graph_data(
        self,
        entities: List[GraphEntity],
        relationships: List[GraphRelationship],
        max_nodes: int = 100,
        layout: GraphLayout = GraphLayout.FORCE_DIRECTED,
    ) -> Dict[str, Any]:
        entity_map = {e.id: e for e in entities}
        sorted_entities = sorted(entities, key=lambda e: e.importance, reverse=True)
        top_ids = {e.id for e in sorted_entities[:max_nodes]}

        nodes = []
        for eid in top_ids:
            e = entity_map[eid]
            nodes.append({
                "id": e.id,
                "label": e.name or e.id[:12],
                "type": e.type.value,
                "importance": e.importance,
                "group": e.type.value,
                "size": 5 + e.importance * 15,
            })

        edges = []
        seen: Set[Tuple[str, str, str]] = set()
        for r in relationships:
            if r.source_id in top_ids and r.target_id in top_ids:
                key = (r.source_id, r.target_id, r.type.value)
                if key not in seen:
                    seen.add(key)
                    edges.append({
                        "id": r.id,
                        "source": r.source_id,
                        "target": r.target_id,
                        "label": r.type.value,
                        "weight": r.weight,
                        "width": 0.5 + r.weight * 2,
                    })

        return {
            "nodes": nodes,
            "edges": edges,
            "layout": layout.value,
            "total_nodes": len(entities),
            "total_edges": len(relationships),
            "displayed_nodes": len(nodes),
            "displayed_edges": len(edges),
        }

    def build_tree(
        self,
        entity_id: str,
        knowledge_graph: KnowledgeGraph,
        max_depth: int = 3,
    ) -> Dict[str, Any]:
        root = knowledge_graph.get_entity(entity_id)
        if root is None:
            return {"id": entity_id, "label": "unknown", "children": []}

        def _build(eid: str, depth: int) -> Dict[str, Any]:
            entity = knowledge_graph.get_entity(eid)
            if entity is None:
                return {"id": eid, "label": "unknown", "children": []}
            node: Dict[str, Any] = {
                "id": entity.id,
                "label": entity.name or entity.id[:12],
                "type": entity.type.value,
                "importance": entity.importance,
                "children": [],
            }
            if depth >= max_depth:
                return node
            related = knowledge_graph.get_related_entities(eid, max_depth=1)
            seen_ids: Set[str] = set()
            for rel_entity, rel, _ in related:
                if rel_entity.id not in seen_ids and rel_entity.id != eid:
                    seen_ids.add(rel_entity.id)
                    child = _build(rel_entity.id, depth + 1)
                    if child:
                        child["relationship"] = rel.type.value
                        node["children"].append(child)
            return node

        return _build(entity_id, 0)

    def build_collections(self, memories: List[MemoryRecord]) -> List[CollectionEntry]:
        tag_groups: Dict[str, List[MemoryRecord]] = {}
        cat_groups: Dict[str, List[MemoryRecord]] = {}
        for m in memories:
            for tag in m.tags:
                tag_groups.setdefault(tag, []).append(m)
            cat_groups.setdefault(m.category.value, []).append(m)

        entries: List[CollectionEntry] = []
        for tag, group in tag_groups.items():
            if len(group) < 2:
                continue
            entries.append(CollectionEntry(
                id=f"tag_{tag}",
                name=tag,
                description=f"Memories tagged with '{tag}'",
                memory_ids=[m.id for m in group],
                count=len(group),
            ))
        for cat, group in cat_groups.items():
            if len(group) < 2:
                continue
            entries.append(CollectionEntry(
                id=f"cat_{cat}",
                name=cat,
                description=f"Memories in category '{cat}'",
                memory_ids=[m.id for m in group],
                count=len(group),
            ))
        entries.sort(key=lambda e: e.count, reverse=True)
        return entries

    def get_pinned_memories(self, memory_manager: MemoryManager) -> List[Dict[str, Any]]:
        pinned = memory_manager.list_pinned()
        return [self._record_to_dict(r) for r in pinned]

    def get_recent_memories(
        self, memory_manager: MemoryManager, hours: float = 24.0
    ) -> List[Dict[str, Any]]:
        cutoff = time.time() - hours * 3600
        records = memory_manager.stats()
        recent: List[MemoryRecord] = []
        with memory_manager._lock:
            for record in memory_manager._memories.values():
                if record.created_at >= cutoff and not record.archived:
                    recent.append(record)
        recent.sort(key=lambda r: r.created_at, reverse=True)
        return [self._record_to_dict(r) for r in recent[:100]]

    def get_entity_timeline(
        self, entity_id: str, knowledge_graph: KnowledgeGraph
    ) -> List[TimelineEntry]:
        entity = knowledge_graph.get_entity(entity_id)
        if entity is None:
            return []
        related = knowledge_graph.get_related_entities(entity_id, max_depth=2)
        entries: List[TimelineEntry] = []
        for rel_entity, rel, depth in related:
            entries.append(TimelineEntry(
                id=rel_entity.id,
                timestamp=rel_entity.created_at,
                type=rel.type.value,
                title=rel_entity.name or rel_entity.id[:12],
                description=rel_entity.description[:200],
                importance=rel_entity.importance,
                category=rel_entity.type.value,
                related_ids=[entity_id],
            ))
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries

    def get_relationship_network(
        self, entity_id: str, knowledge_graph: KnowledgeGraph, max_depth: int = 2
    ) -> Dict[str, Any]:
        entity = knowledge_graph.get_entity(entity_id)
        if entity is None:
            return {"center": entity_id, "nodes": [], "edges": []}

        related = knowledge_graph.get_related_entities(entity_id, max_depth=max_depth)
        nodes: Dict[str, Dict[str, Any]] = {
            entity.id: {
                "id": entity.id,
                "label": entity.name or entity.id[:12],
                "type": entity.type.value,
                "importance": entity.importance,
                "depth": 0,
            }
        }
        edges: List[Dict[str, Any]] = []
        for rel_entity, rel, depth in related:
            if rel_entity.id not in nodes:
                nodes[rel_entity.id] = {
                    "id": rel_entity.id,
                    "label": rel_entity.name or rel_entity.id[:12],
                    "type": rel_entity.type.value,
                    "importance": rel_entity.importance,
                    "depth": depth + 1,
                }
            edges.append({
                "id": rel.id,
                "source": rel.source_id,
                "target": rel.target_id,
                "label": rel.type.value,
                "weight": rel.weight,
            })
        return {
            "center": entity_id,
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    def build_visualization(
        self,
        memory_manager: MemoryManager,
        knowledge_graph: KnowledgeGraph,
        query: Optional[str] = None,
    ) -> VisualizationData:
        if query:
            memories = memory_manager.search(query, limit=50)
        else:
            with memory_manager._lock:
                memories = [
                    r for r in memory_manager._memories.values()
                    if not r.archived and not r.is_expired
                ]

        with knowledge_graph._lock:
            entities = list(knowledge_graph._entities.values())
            relationships = list(knowledge_graph._relationships.values())

        timeline = self.build_timeline(memories, group_by="day")
        collections = self.build_collections(memories)
        pinned = self.get_pinned_memories(memory_manager)
        recent = self.get_recent_memories(memory_manager, hours=24)
        graph_data = self.build_graph_data(entities, relationships, max_nodes=100)

        return VisualizationData(
            memories=[self._record_to_dict(r) for r in memories],
            entities=graph_data["nodes"],
            relationships=graph_data["edges"],
            timeline=timeline,
            collections=collections,
            pinned=pinned,
            recent=recent,
            total_count=len(memories),
            graph_layout=GraphLayout.FORCE_DIRECTED,
        )

    def export_d3_json(self, visualization_data: VisualizationData) -> str:
        d3_data: Dict[str, Any] = {
            "nodes": [],
            "links": [],
            "timeline": [],
            "collections": [],
            "pinned": [],
            "recent": [],
            "meta": {
                "total_count": visualization_data.total_count,
                "graph_layout": visualization_data.graph_layout.value,
            },
        }
        for entity in visualization_data.entities:
            d3_data["nodes"].append({
                "id": entity.get("id", ""),
                "label": entity.get("label", ""),
                "group": entity.get("group", entity.get("type", "")),
                "size": entity.get("size", 10),
                "importance": entity.get("importance", 1.0),
            })
        for rel in visualization_data.relationships:
            d3_data["links"].append({
                "source": rel.get("source", rel.get("source_id", "")),
                "target": rel.get("target", rel.get("target_id", "")),
                "label": rel.get("label", rel.get("type", "")),
                "value": rel.get("weight", 1.0),
            })
        for entry in visualization_data.timeline:
            d3_data["timeline"].append({
                "id": entry.id,
                "date": entry.timestamp,
                "type": entry.type,
                "title": entry.title,
                "description": entry.description,
                "importance": entry.importance,
                "category": entry.category,
            })
        for c in visualization_data.collections:
            d3_data["collections"].append({
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "size": c.count,
            })
        for m in visualization_data.pinned:
            d3_data["pinned"].append({"id": m.get("id", ""), "content": m.get("content", "")[:100]})
        for m in visualization_data.recent:
            d3_data["recent"].append({"id": m.get("id", ""), "content": m.get("content", "")[:100]})
        return json.dumps(d3_data, indent=2, ensure_ascii=False)

    def export_cytoscape_json(self, visualization_data: VisualizationData) -> str:
        elements: List[Dict[str, Any]] = []
        for entity in visualization_data.entities:
            elements.append({
                "data": {
                    "id": entity.get("id", ""),
                    "label": entity.get("label", ""),
                    "type": entity.get("type", ""),
                    "importance": entity.get("importance", 1.0),
                },
                "classes": entity.get("type", "default"),
            })
        for rel in visualization_data.relationships:
            elements.append({
                "data": {
                    "id": rel.get("id", ""),
                    "source": rel.get("source", rel.get("source_id", "")),
                    "target": rel.get("target", rel.get("target_id", "")),
                    "label": rel.get("label", rel.get("type", "")),
                    "weight": rel.get("weight", 1.0),
                }
            })
        result: Dict[str, Any] = {
            "elements": elements,
            "layout": {"name": "cose", "animate": True},
            "style": [
                {"selector": "node", "style": {"label": "data(label)", "width": 30, "height": 30}},
                {"selector": "edge", "style": {"label": "data(label)", "width": "data(weight)"}},
            ],
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    @staticmethod
    def _record_to_dict(record: MemoryRecord) -> Dict[str, Any]:
        return {
            "id": record.id,
            "content": record.content,
            "summary": record.summary,
            "key": record.key,
            "category": record.category.value,
            "tags": record.tags,
            "importance": record.importance,
            "source": record.source,
            "workspace_id": record.workspace_id,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "accessed_at": record.accessed_at,
            "access_count": record.access_count,
            "pinned": record.pinned,
            "archived": record.archived,
            "metadata": record.metadata,
        }
