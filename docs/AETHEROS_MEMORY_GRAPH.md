# AetherOS Memory 2.0 — Knowledge Graph (Master 41)

Implementation: `aetheros_memory_intelligence/graph_store.py`.

- 17 `EntityType`s (person…artifact), 18 `RelationType`s (owns…derived_from).
- Entities: canonical name + aliases (normalized dedup index), description,
  attributes, confidence, first/last seen, source ids, project id.
- Relationships: confidence, source, provenance, timestamps, validity window,
  project id.
- `upsert_entity` merges (union aliases/sources, max confidence).
- `add_relationship` dedups identical (src, type, dst).
- `neighbors(id, depth, project_id)` — bounded BFS for the graph channel.
- Deletion = tombstone: node removed, incident edges dropped, name index
  cleaned, tombstone set blocks re-linking (`forget` cascades per project).
- Persistence: atomic `graph.json`, lazy-loaded.

The graph is retrieval infrastructure (graph channel + entity-match scoring),
not decoration. The desktop graph surface lists live entities/relationships
from `memory2.graph`; no fake nodes.
