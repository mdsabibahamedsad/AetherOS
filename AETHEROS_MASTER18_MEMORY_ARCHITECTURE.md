# AETHEROS MASTER 18 — Memory Architecture

Date: 2026-08-24 · Companion: `AETHEROS_MASTER18_MEMORY_AUDIT.md`,
`AETHEROS_MASTER18_FINAL_REPORT.md`, `aetheros_master18_final_status.json`.

## 1. Design stance

Compose, don't replace. The unified layer lives in `agent/memory_os/` as a
set of focused modules over one new profile-safe SQLite substrate
(`<AETHEROS_HOME>/memory_os/memory_os.db`, WAL). Existing memory systems keep
their data, APIs and behavior untouched (audit §1); the unified layer indexes,
links and governs lifecycle on top, and bridges inbound from research,
computer-use and task checkpoints. No new model tools are registered
(Footprint Ladder rung 2 for the CLI surface).

## 2. Modules

| Module | Responsibility | Phases |
|---|---|---|
| `models.py` | 17 MemoryTypes, 6 Scopes, 8 Statuses, 5-step Confidence, 8 SourceTypes, Sensitivity, PreferenceKind, 14 RelationshipTypes, `MemoryItem` (every P15 field + validity windows + provenance), classification labels | P2, P7, P10, P12, P15-17, P28-30 |
| `store.py` | SQLite adapter: items/item_versions/entities/aliases/edges/working_slots/audit_log/counters + FTS5; hash-chained audit; single-lock threading model; storage protocol (adapters possible) | P13, P24, P74-75, P79 |
| `security.py` | Secret refusal (10+ credential patterns), injection firewall patterns, `AccessContext` (user/agent/tool/system), read-authorization predicate, write firewall (untrusted sources can never create procedural/workflow/system types; everything external downgrades to CANDIDATE or QUARANTINE) | P32-40 |
| `entities.py` | Entity registry + resolution on identifier / namespace(repo,domain) / alias+type agreement / canonical-key collisions; MERGED/SEPARATE/UNCERTAIN outcomes; explicit merge & separate | P10-11 |
| `graph.py` | Typed, timestamped, provenance- and confidence-aware edges over entities+items; bounded subgraph traversal; contradiction queries; purge-on-forget | P13-14 |
| `lifecycle.py` | Promotion pipeline (stops at CANDIDATE without human approval), conflict detection via semantic_key, supersede chains preserving historical validity, dedup/merge, TTL expiry sweep + purge, decay candidates (exempting explicit preferences/procedures/workflows/system), archive/restore, feedback application, correction cascade into derived items, stale detection, revalidation, episodic→semantic consolidation retaining per-event provenance | P17-18, P21, P24-26, P48-55 |
| `retrieval.py` | Hybrid ranking: FTS5 keyword + vector cosine (via `embeddings.py`) + entity/graph expansion (1-hop neighbor boost) + recency/importance/confidence weighting − stale/quarantine penalties; temporal-validity filter; precision guard (zero relevance signal ⇒ zero score); budget cap; per-hit explanations ("why retrieved / source / when / relevance"); working-memory slots (objective/entities/constraints/files/tools/decisions/pending/task_state) with episodic snapshot | P3, P41-47, P64 |
| `embeddings.py` | `EmbeddingProvider` interface, offline deterministic `HashingEmbedder`, persistent `item_embeddings` table with model/dim/created_at, safe re-indexing | P42, P71-73 |
| `manager.py` | `MemoryManager` facade: remember/get/update/search/list/versions/forget(+where)/link/unlink/summarize/export/import/backup/restore/maintenance/stats/audit; controls (enable, project toggle, session-only, private mode, confirmation gate); conflict-aware writes; candidate confirmation restricted to user actors | P1, P19-23, P52, P59-69, P80, P91 |
| `bridges.py` | research record ingestion (Master 17 shapes; verified→ACTIVE else CANDIDATE), computer-use UI-pattern import (hint-only, pre-sanitized upstream), task checkpoint references (no duplication of `tools/checkpoint_manager.py`), cron maintenance scheduling via `cron.jobs.create_job` | P85-87 |

## 3. Trust boundaries (non-negotiables mapping)

- **Memory-is-data-not-authority**: retrieved content is returned as content;
  nothing retrieved can elevate itself to system/procedural standing. The
  firewall enforces this at *write* time so poisoned entries never become
  authoritative at all.
- **Provenance completeness**: `Provenance(origin_event, actor, explicit,
  evidence_ids, channel)` on every item; edges additionally carry
  `evidence_item_id`. Provenance survives versioning, merging, export.
- **Least privilege**: tools never see SENSITIVE or ORG/SYSTEM scope; agents
  see shared/user-scope items only when `allow_agents` was explicitly set, and
  never across projects or foreign tasks; users never see other owners'
  USER/TASK/SESSION items.
- **Right to forget**: deletion removes row + FTS + versions + graph edge
  activations; audit keeps a content-free tombstone; retrieval/get/list/
  versions cannot resurrect.

## 4. Context assembly order (P92)

system policy → security policy → explicit current user instruction →
authorized task state → trusted project context → verified memory
(ACTIVE/CONFIRMED+) → untrusted external information. Memory never outranks
current instructions; `assemble` surfaces remain labeled blocks.

## 5. Embeddings / vectors (P42, P71-73)

`agent/memory_os/embeddings.py` closes the vector gap offline:

- `EmbeddingProvider` — the swap interface (name, dim, embed(text)).
- `HashingEmbedder(dim=256)` — default provider: deterministic feature
  hashing of word tokens + char trigrams, L2-normalized. No network, no model
  download; captures lexical + sub-word similarity (morphological variants).
- `SemanticScorer` — bounded-cache callable adapting a provider to the
  retriever's `(query, content) -> 0..1` hook.
- `EmbeddingIndex` — persistent vectors in `item_embeddings(memory_id, model,
  dim, created_at, vector)` (P72); `reindex()` safely rebuilds and re-stamps
  metadata; cosine ranking activates via `manager.enable_semantic_search()`.
- Heavier providers (e.g. `aetheros_memory.embedding_engine`, cloud or local
  sentence-transformers) subclass `EmbeddingProvider` — retrieval, storage
  and lifecycle code are untouched.

## 6. Threading/storage notes

One connection, one lock: every `MemoryStore` public call holds a process-wide
RLock (sqlite connections are not thread-safe even with
`check_same_thread=False`). Writes commit inside the lock; reads share it.
This removed all observed cross-thread locking hazards under the concurrency
smoke test.

## 7. Test map

`tests/agent/test_memory_os_{models,store,security,lifecycle,
entities_graph,retrieval,scenarios,redteam,perf,embeddings,volume,stress}.py`
+ `tests/cli/test_memory_os_cmd.py` — 137 tests: unit coverage per module,
SC01-SC30 golden scenarios, red-team vectors (poisoning, cross-project/user
leakage, secret extraction, deleted-memory recovery, permission bypass,
inference escalation, malicious webpage/document/import), offline vector
retrieval + re-indexing, performance/volume ceilings, multi-project/multi-agent
concurrency stress with isolation assertions.
