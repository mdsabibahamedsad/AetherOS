# AetherOS Memory 2.0 — Architecture (Master 41)

## Layered model (L0–L10)

See `aetheros_memory_intelligence/layers.py` — the single source of truth.
Each `MemoryLayer` declares purpose, storage, retrieval/write/retention
policy, default confidence, privacy class, deletion behavior, record types
and scopes. Policy is data, not branches.

| Layer | Name | Storage |
|---|---|---|
| L0 | working | turn buffer (never persisted) |
| L1 | session | fabric store, session scope |
| L2 | episodic | fabric store + timeline index |
| L3 | semantic | fabric store + hybrid index |
| L4 | project | fabric store, project scope (isolation enforced) |
| L5 | preference | fabric store, user scope (explicit > inferred) |
| L6 | graph | `graph.json` adjacency store |
| L7 | research | fabric store + evidence refs |
| L8 | artifact | fabric store + artifact refs |
| L9 | procedural | fabric store (validated runs only) |
| L10 | system | fabric store, system boundary |

## Canonical record

`aetheros_memory_intelligence/record.py::MemoryRecord` — the v2 schema with
temporal validity (`valid_from/until`, `observed_at`, `last_confirmed`,
`last_used`), 14 `RecordType`s, 9 `RecordScope`s, `PrivacyClass`,
`ProvenanceKind`, `ConfidenceBand`, `RecordStatus`, version chain
(`supersedes/superseded_by`), entity/relation/artifact/evidence links, TTL.

v1 bridge: `to_entry()` / `from_entry()` project records into the existing
fabric `MemoryEntry` envelope; `MemoryService.migrate_entries()` upgrades
legacy entries in place. Existing memories are never destroyed.

## Scope resolution (`scope_visible`)

GLOBAL visible everywhere. Project/task/research/artifact-bound records
require the same `project_id` — a query without a project never sees them
(isolation rule). Other scopes follow least→most specific hierarchy.

## Key modules

- `service.py` — `MemoryService` + `RecordStore` (atomic JSON persistence).
  The one internal API: remember/retrieve/search/get/explain/update/
  supersede_memory/delete/forget/consolidate/dream/resolve_conflicts/
  run_forgetting/research_reuse/quality/health/export/import_bundle/
  add_entity/link/get_project_memory/get_entity_graph/get_timeline/get_context.
- `writer.py` — `MemoryWriter` (gates), `ForgettingEngine`,
  `Consolidator`, `DreamingLoop` (proposals only, never auto-writes
  preferences), `supersede()`.
- `graph_store.py` — entities, typed relationships, bounded traversal,
  tombstones (node removal drops incident edges).
- `hybrid.py` / `scoring.py` / `budget.py` — retrieval pipeline, documented
  weights, token-budget selection.
- `domains.py` — project views, research-reuse decisions (volatile vs stable TTL).
- `events.py` / `quality.py` — deduplicated event bus; measured quality/health.

## Integrations

- Agent tools: `tools/memory2_tool.py` (8 tools in the `memory` toolset).
- Agent facade: `MemoryIntelligence.memory2()` with v1 migration on first use.
- Desktop IPC: `tui_gateway/server.py` `memory2.*` methods (narrow typed JSON;
  no raw storage/fs/DB handles). UI: `apps/desktop/src/app/memory/index.tsx`
  + `lib/memory2-client.ts` — all live data, honest unavailable states.

## Known limitations

- `RecordStore` rewrites the full JSON file per write (O(n²) at scale);
  measured 16 writes/s at 1k records. Mitigation path: SQLite/FTS backend.
- Semantic channel defaults to token-Jaccard offline; wire `embedding_fn`
  when an embedding engine is configured.
- Sync architecture (multi-device) is NOT implemented — no fake sync exists.
