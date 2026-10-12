# AETHEROS MASTER 18 — MEMORY AUDIT (Phase 0)

Date: 2026-08-24 · Read-only audit; no code modified during this phase.
Scope: every persistent-memory / history / state / context / vector / graph /
preference system discoverable in the repository, plus security, retention,
deletion, tests, integration points, duplicates, and gaps.

---

## 1. Existing memory systems (inventory)

### 1.1 `tools/memory_tool.py` + MEMORY.md/USER.md (the live agent-loop memory)
- File-backed curated memory (`~/.aetheros/memory/MEMORY.md`, `USER.md`),
  frozen into a snapshot for the system prompt (cache-safe pattern).
- Secret redaction happens in maintenance paths; agent-level `memory` tool is
  intercepted in `run_agent.py` before generic tool dispatch.
- Written to by Master 17's opt-in research bridge
  (`agent/research/memory_bridge.py`: `build_memory_records()`,
  `remember_research()` — provenance metadata mandatory: source=`research:<id>`,
  confidence, scope, status).
- **This is production memory today. Master 18 must not change its format or
  behavior** (prompt-cache invariant).

### 1.2 `aetheros_memory_intelligence/` — "the fabric" (security-hardened layer)
- 21 small modules composing into facade `MemoryIntelligence`
  (`remember/forget/recall/assemble_context/run_retention/integrity_check/
  export/import_bundle/fabric_backup/fabric_restore`).
- Storage: atomic JSON (`entries.json` + `manifest.json`) under
  `<AETHEROS_HOME>/memory_intelligence/store`; append-only HMAC hash-chain
  audit under `.../audit`.
- Concepts already present: 11 MemoryTypes, `MemoryBoundary`
  (USER<WORKSPACE<SESSION<AGENT<SYSTEM), `AccessContext` +
  `MemoryBoundaries.can_write/can_read`, `MemoryOrigin` with per-origin
  default trust, `TrustLevel` + trust decay half-life,
  `VerificationLevel`, ACTIVE/ARCHIVED/FORGOTTEN/QUARANTINED states,
  SHA-256 checksums/seals, injection-pattern + secret-pattern scanning,
  write pipeline, dedup, conflict detection, version history, retention,
  loop guard, scope-isolated cache, token-budgeted context assembly,
  validated export/import bundles.
- Embeddings: none built-in (`retrieval_enable_semantic=False`; injectable
  `semantic_score_fn` callable only).
- Used by: `aetheros memory-intelligence` CLI (`aetheros_cli/
  memory_intelligence_cli.py`, parser `subcommands/memory_intelligence.py`,
  registered `main.py`) and `aetheros_computer/knowledge_bridge.py`
  (guarded import).
- Tests: `tests/aetheros_memory_intelligence/` (10 files; currently carrying
  pre-existing failures on this machine — see §13).

### 1.3 `aetheros_memory/` — "the platform" (unwired)
- 17 modules: `MemoryManager` (JSON-persisted records, keyword + semantic
  search), `EmbeddingEngine` (OpenAI/Gemini/Cohere/Jina/Voyage/Local
  sentence-transformers), `VectorDatabase` (SQLite-vec/LanceDB/Chroma/Qdrant/
  FAISS backends), `KnowledgeGraph` (JSON entities/relationships), RAG
  pipeline, context retrieval w/ budgets, ranking, editor, research library,
  permissions (XOR+base64 "encryption" — weak; regex redaction), summarization,
  code/workspace intelligence, visualization, performance helpers.
- **No importer outside its own package.** Orphaned capability.
- Tests: single standalone script (`tests/aetheros_memory/test_memory.py`),
  not pytest-collected style.

### 1.4 Top-level `memory/` — "MASTER 9 Memory OS" (BROKEN / dead)
- `__init__.py` contains mangled imports (`from .\1 import ...`) → package
  cannot be imported at all.
- `memory_store.py` has duplicated SQL lines / double-quoted literals from
  in-tree patch scripts (`update_*.py` scratch artifacts; `.backup` files).
- Rich concepts on paper (typed memories, entity/relationship indexes, hybrid
  retrieval, consolidation, GC) but **dead**: the only product-code consumer
  (`agent/orchestration/memory_integration.py`) calls sync methods as async and
  always falls into its exception path.
- `tests/memory/test_memory_modules.py` therefore fails collection (observed
  in Master 18 pre-sweep).
- Decision candidate for Master 18: leave untouched (non-negotiable rule:
  no silent deletion/migration of user data; nothing can import it anyway),
  document as known-broken.

### 1.5 `agent/memory_os/memory_os.py` — prior unified-layer attempt (unwired, untested)
- 1,510-line in-memory orchestrator (Master Prompt 9 era): 9 MemoryTypes, 6
  Scopes, TrustLevel/ImportanceLevel/WriteType, per-type MemoryLayer classes,
  MemoryOrchestrator (add/search/update/delete, prompt-context builder,
  consolidation, subagent preparation).
- No persistence anywhere (all layers are dicts); no external importers
  (grep: only a docstring mention in `agent/multimodal/media_abstraction.py`).
- `.backup` sibling present.
- Master 18 decision: **keep the file importable for compatibility**, build the
  real implementation as proper modules in the same package, do not delete.

### 1.6 Conversation/session state — `aetheros_state.py` (SessionDB, SQLite WAL)
- Tables: `schema_version`, `sessions` (id/source/model/tokens/cost/handoff/
  folder/pinned), `messages` (role/content/tool-calls/reasoning/active),
  `state_meta` KV, `compression_locks`, `messages_fts` (FTS5) +
  `messages_fts_trigram`. This is chat history, not semantic memory.
- Plus profile-aware `get_aetheros_home()` layout everywhere.

### 1.7 Provider-plugin memory (opt-in backends)
- `plugins/memory/{honcho,mem0,supermemory,byterover,hindsight,holographic,
  openviking,retaindb}` implementing `agent/memory_provider.py::MemoryProvider`
  ABC, orchestrated by `agent/memory_manager.py`. CLI `aetheros memory
  setup|status|off|maintain`. Closed set (policy: new providers ship as
  external plugin repos).

### 1.8 Knowledge-graph implementations (four, unintegrated)
- `memory/knowledge_graph.py` (broken pkg), `aetheros_memory/knowledge_graph.py`
  (platform, JSON), `aetheros_automation/knowledge/knowledge_graph.py`,
  `agent/research/knowledge_graph.py` (research-scoped, SQLite-backed via
  research store, provenance-aware). Master 17 report already flagged
  consolidation as follow-up — Master 18 provides the unified graph.

### 1.9 Computer-use memory (Master 15)
- `aetheros_computer/pattern_memory.py`: sanitized UI-pattern store (redact →
  refuse-if-still-secret), bounded 512 entries, JSON at `<AETHEROS_HOME>/
  computer_actions/ui_patterns.json`; hints only, never auto-executed.
- `aetheros_computer/task_checkpoint.py`: per-task JSON checkpoints w/ budget
  + resume filters.
- `aetheros_computer/knowledge_bridge.py`: consumes pattern memory + fabric,
  treats hints strictly as DATA (injection markers downgraded inert).

### 1.10 Task checkpoints
- `tools/checkpoint_manager.py` (main task/file checkpoints; auto-prune wired
  into CLI/TUI), `aetheros_reliability/checkpoint.py::CheckpointStore`,
  orchestrator/undo/orchestration-local variants (each self-scoped).

### 1.11 Scheduler / cron
- `cron/jobs.py` + `cron/scheduler.py`; jobs support origin tagging (research
  uses it via `agent/research/scheduler_bridge.py`). Reusable for memory
  maintenance jobs.

### 1.12 MCP infrastructure
- `mcp_serve.py`: FastMCP server; tools registered as decorated functions
  returning JSON strings inside `create_mcp_server()` (10 tools today);
  launched by `aetheros mcp serve`.
- `agent/transports/aetheros_tools_mcp_server.py` (explicit add_tool pattern).

## 2. Storage backends in play
| System | Backend | Path |
|---|---|---|
| SessionDB | SQLite WAL + FTS5 | `<home>/sessions/…` |
| Fabric | Atomic JSON + manifest + HMAC audit | `<home>/memory_intelligence/` |
| Platform | JSON dir (+optional vector sqlite) | `./memory_data` default |
| Master-9 OS | in-memory (SQLite code broken) | n/a |
| Provider plugins | provider-defined | provider-defined |
| UI patterns | JSON | `<home>/computer_actions/` |
| Research store | SQLite WAL | `<home>/research/research.db` |

## 3. Schemas (essentials)
- Fabric `MemoryEntry`: strict allow-list fields + checksum/seal + schema
  version; boundary/trust/origin/state enums.
- Platform `MemoryRecord`: category/key/tags/importance/permissions string/ttl.
- SessionDB `messages`: role/content/tool_calls/reasoning/session_id/active.
- Research store: tasks/sources/claims/evidence/contradictions/events/kg_graphs/
  domain_stats (provenance-complete).

## 4. Retrieval systems
- SessionDB FTS5/trigram search over messages (`session_search` toolset).
- Fabric `SecureRetriever`: authorization-checked keyword retrieval, optional
  injected semantic scorer, loop-guarded.
- Platform: keyword scoring + cosine over vector backends.
- Legacy memory_os: naive substring scoring.
- Research engine: corroboration/citation retrieval (M17).

## 5. Embedding systems
- Platform `EmbeddingEngine`: multi-provider; cloud needs network+keys;
  LOCAL = sentence-transformers (offline, model download required).
- Master-9 `embeddings.py`: ada-002-style provider abstraction (broken pkg).
- Fabric: injection point only (`semantic_score_fn`).
- Nothing embeddings-related is active in the agent loop today.

## 6. Permissions
- Fabric boundaries/ACL (strongest): owner/boundary checks on read/write.
- Platform `MemoryPermissions`: PermissionLevel ACL + access filter.
- Gateway/tool-level approval system exists platform-wide (command approval,
  `tools/approval.py` doctrine: silence is not consent — M17 gate codified it).

## 7. Encryption
- Real AEAD available: `aetheros_security/encryption/__init__.py::
  EncryptionManager` (AES-GCM, key file + rotation, password KDF).
- `aetheros_knowledge` Fernet wrapper; `aetheros_cli/api_key_store.py` OS
  keychain (`SecretsManager`); `aetheros_cli/sync_crypto.py` device keys +
  encrypted vaults.
- Weak spot: platform XOR+base64 `encrypt_content` (do not use); auth.json
  OAuth tokens unencrypted (pre-existing, out of M18 scope but documented).

## 8. Retention & deletion (today)
- Fabric: retention runner, TTL, archive/forget/quarantine states.
- tools/memory_tool maintain path: decay/purge (`aetheros memory maintain`).
- SessionDB: session deletion, message active-flagging; FTS follows table.
- Checkpoints: prune + auto-prune.
- No cross-system "delete everywhere" workflow exists (gap).

## 9. Tests covering memory today
- `tests/aetheros_memory_intelligence/` (10 files), `tests/memory/` (broken),
  `tests/aetheros_memory/test_memory.py` (script), `tests/hermes_state/`,
  `tests/tools/test_memory_tool_schema.py`, provider-plugin tests under
  `tests/plugins/memory/`, computer-use tests under `tests/*computer*`.

## 10. Integration points Master 18 will use (compose, not replace)
1. Fabric security primitives (patterns/trust semantics) — reference, not fork.
2. `EncryptionManager` for backups (P69-70).
3. `cron.jobs.create_job` for scheduled maintenance (P87) — scheduler_bridge pattern.
4. Master 17 research bridge record shape for research→memory ingestion (P85).
5. Computer-use `pattern_memory` entries imported as UI_PATTERN memories (P86).
6. `CheckpointManager`/task checkpoints referenced for task resume context (P9).
7. MCP: additive tools in `mcp_serve.create_mcp_server` (P88-89).
8. CLI: new subcommand beside existing ones (rung 2 footprint ladder).
9. Optional embedding/vector adapters delegating to `aetheros_memory` engines
   when user configures them — no new vector database created (P71-73).

## 11. Duplicates / collisions (facts to respect)
- Three different `MemoryEntry` classes; two `MemoryManager`s; two
  `KnowledgeGraph`s; two `RetentionPolicy`s; two embedding-provider enums.
- Master 18's unified layer must namespace its own classes clearly
  (`agent.memory_os.*`) and never re-export colliding names.

## 12. Missing capabilities (gaps Master 18 fills)
- Unified typed MemoryItem with full provenance + lifecycle + validity windows.
- Entity resolution (MERGED/SEPARATE/UNCERTAIN) and typed relationship graph
  spanning projects/tasks/research/computer-use.
- Controlled promotion pipeline (conversation→working→episodic→candidate→
  approved) with confirmation.
- Preference memory with EXPLICIT/INFERRED/TEMPORARY distinction.
- Temporal memory: valid_from/valid_until, supersede chains, stale detection,
  revalidation.
- Hybrid retrieval with budget + explanations ("why retrieved").
- Right-to-forget cascade across items/versions/entities/edges/embeddings/
  caches with audit tombstones.
- Private mode; enable/disable toggles; export/import with validation;
  encrypted backup/restore.
- Multi-agent isolation rules and memory firewall enforcement tests
  (external content can never create authoritative/procedural memory).
- Golden scenarios SC01-SC30 + safety/red-team suite + performance/stress.

## 13. Pre-existing failure baseline (this machine, observed pre-M18)
- `tests/aetheros_memory_intelligence/`: 62 failures across 6 files
  (cache_loopguard, context_engine, retrieval, dedup_retention,
  write_pipeline, audit_backup_transfer) — present before any M18 change;
  M18 must not be blamed for them and must not regress them further.
- `tests/memory/test_memory_modules.py`: collection error (broken pkg §1.4).

## 14. Build decision (recorded for the architecture doc)
New unified substrate: dedicated SQLite DB at
`<AETHEROS_HOME>/memory_os/memory_os.db` (WAL), following the Master 17
research-store precedent. Justification: the only queryable, transactional,
profile-safe pattern in-repo; avoids mutating three existing stores and their
formats (rule: preserve user data + APIs); avoids the fabric's JSON store for
indexed workloads while remaining composable with it. Existing stores remain
untouched and authoritative for their own data; the unified layer adds
index/link/lifecycle on top and bridges in research/computer-use/checkpoints.
