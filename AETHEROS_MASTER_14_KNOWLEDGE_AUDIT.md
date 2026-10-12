# AETHEROS MASTER 14 — PHASE 0 KNOWLEDGE/MEMORY AUDIT

Date: 2026-08-23 · Scope: full-repo scan for memory, retrieval, indexing, embedding,
document ingestion, knowledge graphs, RAG, citations, privacy, and data
connectors. **No code was modified.**

---

## Executive Summary

AetherOS already ships **three parallel memory architectures**:

| Layer | Status | Description |
|-------|--------|-------------|
| **Live: built-in + providers** | Production | File-based `MEMORY.md`/`USER.md` + write_approval gating + lifecycle engine (decay/conflicts/secrets/permissions) + 8 provider plugins (honcho, mem0, supermemory, byterover, hindsight, holographic, openviking, retaindb) + SessionDB (FTS5+trigram episodic search). |
| **Live: `aetheros_memory_intelligence` (fabric)** | CLI-only, complete | Trust/boundaries/provenance/versioning/conflicts/dedup/secret-scan/quarantine/retention/export/hash-chain audit. 10 test files. **Zero imports from runtime** (run_agent/cli/gateway/tools). |
| **Dead: `aetheros_knowledge`** | Un-importable | `store.py` had IndentationError (fixed from git HEAD); all consumers silently degrade; every instantiation used `:memory:` default so no persistence; `search_documents` searches title+tags only (no chunk content); no incremental indexing; no structure-aware chunker; no cross-encoder reranker; no parent-child retrieval; three parallel `knowledge` CLI surfaces (orphaned rich CLI, unregistered intelligence CLI with latent AttributeError, live stub printing fake stats). |

**Consolidation trigger met (AGENTS.md):** Two vector stacks (`aetheros_knowledge/vectordb` vs `aetheros_memory/vector_database.py`), two embedding engines (`indexing/embedders.py` vs `embedding_engine.py`) — design one ABC + orchestrator.

---

## 1. Existing Memory Architecture

### 1.1 Built-in curated store (`tools/memory_tool.py`, `tools/memory_lifecycle.py`)
- Files: `<AETHEROS_HOME>/MEMORY.md`, `<AETHEROS_HOME>/USER.md`
- Actions: add/replace/remove/search; targets: memory/user
- Write approval gate: `memory.write_approval` config → `tools/write_approval.py` decision matrix (inline prompt in CLI, staged pending in gateway/background)
- Background review thread: `agent/background_review.py` (periodic memory/skill review, provenance metadata builder)
- Lifecycle engine (`tools/memory_lifecycle.py`): confidence scoring, decay (halflife 90d, access-weighted), secret scan/redact/purge, conflict detection (attribute/polarity), resolution policies (`keep_best` confidence w/ newer tiebreak, `keep_newer`, `keep_private` — newest entry treated as correction), near-dup merge, permissions/sharing, owner-scoped visibility, crash-safe pre-image journal, repair, `maintain` aggregator
- **Gaps**: no native per-entry TTL/expiry (only maintain-time decay); no date-range deletion; no scheduled auto-retention for MEMORY.md (manual `maintain` or fabric CLI only)

### 1.2 Provider plugins (`plugins/memory/*`, `agent/memory_manager.py`, `agent/memory_provider.py`)
- 8 providers: honcho, mem0, supermemory, byterover, hindsight, holographic, openviking, retaindb
- ABC: `MemoryProvider` with lifecycle hooks (`prefetch`, `sync_turn`, `shutdown`, `on_turn_start`, `on_session_end`, `on_session_switch`, `on_pre_compress`, `on_delegation`, `on_memory_write`)
- Manager: built-in-first, at most ONE external provider; single-worker background ThreadPoolExecutor serializes writes; `extract_and_save_memories()` heuristic auto-extraction **has no caller** (dead auto-write path)
- Per-provider CLI commands registered at argparse setup time; framework only exposes CLI for **currently active** provider

### 1.3 Session/episodic store (`aetheros_state.py`)
- DB: `<AETHEROS_HOME>/state.db` (SQLite WAL, SCHEMA_VERSION=15, NFS/SMB fallback)
- Tables: `sessions` (source, user_id, model_config, parent_session_id chain, token+cost, title, handoff_*, rewind_count, archived, folder, pinned), `messages` (role, content, tool_calls, timestamp, reasoning, `active` flag for rewinds), `state_meta`, `compression_locks`
- FTS5 index on `messages_fts` (content+tool_name+tool_calls via triggers) + **trigram FTS5 table for CJK substring search** `messages_fts_trigram`
- `session_search` tool: four shapes (Discovery=query, Scroll=session_id+around+window, Read=session_id, Browse=none); filters: role_filter, sort newest|oldest, limit 1-10; cross-profile `@session:<profile>/<id>` resolution
- **Gap**: no date-range filter exists — temporal control limited to sort direction

### 1.4 Fabric (`aetheros_memory_intelligence/`) — complete, tested, unwired
- Types: `MemoryBoundary` (USER/WORKSPACE/SESSION/AGENT/SYSTEM strictness), `TrustLevel` (UNTRUSTED/VERIFIED/UNVERIFIED), provenance records, contradiction tracking
- Pipeline stages: validate → classify → defense (secret_scan, injection, base64/unicode obfuscation) → dedup (Jaccard ≥0.92) → conflict-check → version → seal (checksum over content+provenance) → persist → audit
- Retrieval: keyword-only, boundary filter, trust-blended score `score * (0.5 + 0.5*trust)`, min_confidence grounding frame ("data-not-instructions"), scope-salted cache
- **Zero imports** from `run_agent`, `cli.py` agent runtime, `gateway/`, `tools/`, `model_tools.py`; only CLI entry point (`aetheros memory-intelligence`)
- Config `memory_intelligence` section exists with `retrieval_enable_semantic: False`, `embedding_provider: ""` — `SecureRetriever` constructed **without** `semantic_score_fn`

---

## 2. Existing Storage

| Store | Path | Tech | Notes |
|-------|------|------|-------|
| SessionDB | `<AETHEROS_HOME>/state.db` | SQLite + FTS5 | Episodic + search |
| Memory files | `<AETHEROS_HOME>/MEMORY.md`, `USER.md` | Markdown | Curated + lifecycle |
| Skill usage | `<AETHEROS_HOME>/skills/.usage.json` | JSON | Procedural memory proxy |
| Fabric | `<AETHEROS_HOME>/memory_intelligence/store/` | JSON + manifest | Trust/boundaries/versioning |
| Knowledge | `<AETHEROS_HOME>/knowledge/` | **Never used** (defaults `:memory:`) | Dead package |

---

## 3. Existing Indexing

- **`aetheros_knowledge/indexing/parsers.py`**: markdown/txt/pdf(PyPDF2→pdfminer→pdfplumber)/docx/pptx/csv/excel/json/yaml/html/epub
- **`aetheros_vision/documents.py`**: structure-aware extraction (sections/tables/metadata) + OCR fallback; returns `DocumentIntelligence` (sections/tables), surfaced via `vision_analyze`/`document_extract` tools
- **No structure-aware chunker**: `aetheros_knowledge/indexing/chunkers.py` only paragraph/sentence/token/fixed strategies (512/64 default); no markdown heading/section chunker
- **No incremental indexing**: `IndexingPipeline.index_document` computes checksum (stored in `metadata["checksum"]` + doc checksum in `center/manager.py:144`) but **never compared**; `reindex_document` = full re-index
- **No change detection / deletion propagation**: file watcher exists (`automation/file_watcher.py` emits `file.*` events via bus) but nothing connects it to indexing

---

## 4. Existing Embeddings

| Engine | Providers | Local support | Dimension tracking | Re-index on change |
|--------|-----------|---------------|-------------------|-------------------|
| `aetheros_knowledge/indexing/embedders.py` | ST (all-MiniLM-L6-v2, **random fallback** when lib missing), OpenAI, Ollama, Local TF-IDF, cohere/jina/voyage via OpenAI client | Yes (ST) | Hardcoded dims map | ❌ |
| `aetheros_memory/embedding_engine.py` | OpenAI, Gemini, Cohere, Jina, local ST | Yes | Captured once at init | ❌ |
| `aetheros_memory_intelligence` | **None** — keyword only; `semantic_score_fn` injectable but never wired | — | — | — |
| `agent/multimodal/local_models.py` | sentence-transformers | Yes | — | — |
| `plugins/memory/holographic` | HRR vectors (cosine similarity) | Yes | — | — |

- **Config keys exist but inert**: `memory_intelligence.embedding_provider/model` (config.py:1756-1757), `retrieval_enable_semantic: False` (config.py:1740); `SecureRetriever` built without `semantic_score_fn` (manager.py:88-94)
- **No dimension/version tracking on chunks** → no re-index trigger

---

## 5. Existing Retrieval

- **Keyword**: hand-rolled BM25 (`aetheros_knowledge/search/engine.py:28-39` k1=1.5 b=0.75) on **title+tags only** (max 1000 docs listed, tokenized in Python); BM25 in `tools/tool_search.py` (tool catalog); holographic FTS5+Jaccard; SessionDB FTS5+trigram
- **Semantic**: stub in `aetheros_knowledge/search/engine.py` (injectable `_semantic_score_fn`, default None); fabric has injectable hook but unconfigured
- **Hybrid**: weighted fusion only (min-max normalize, `alpha*sem + (1-alpha)*fulltext`); alpha tunable via `rag/studio.py:216`; **no RRF**
- **Reranker**: heuristic only (query-term overlap boost + quality_score*0.3); **no cross-encoder** anywhere; abstract `BaseReranker` registry empty
- **Parent-child**: none (chunks link to `documents.document_id`; `generate_citation_for_chunk` is only chunk→parent hop)
- **Metadata filters**: `search_documents` only title+tags SQL LIKE; no scope/permission/date/source filters

---

## 6. Existing Search

- `search_files`: ripgrep subprocess (files mode `--files`, content mode ripgrep-first with grep fallback)
- `session_search`: FTS5/trigram with role/sort/limit filters; no date-range
- `web_search`: plugin providers (brave-free/ddgs/searxng/exa/parallel/tavily/firecrawl), metadata-only `{title,url,description,position}` — **no publish date retained**
- `web_extract`: URL embedded-secret screening, SSRF private filter, optional LLM summarize; final fields `url, title, content, error, blocked_by_policy?`

---

## 7. Existing RAG

- **Dead**: `aetheros_knowledge/rag/studio.py` (`RAGStudio` CRUD + `retrieve` + eval hit-rate/MRR + query expansion + `tune_hybrid_search` + MMR-ish `diversify_results`) — never imported by live paths
- **Dead**: `aetheros_knowledge/deep_research.py` (`DeepResearchEngine` + claim extraction regex + source trust via `.gov/.edu` allowlist) — no skill consumes it
- **Live**: `aetheros_memory_intelligence` retrieval + grounding frame (keyword-only today)

---

## 8. Existing Citations

- **Untrusted wrapper**: `agent/tool_dispatch_helpers.py:351-385` wraps high-risk tools (`web_extract`, `web_search`, `browser_*`, `mcp_*`, ≥32 chars)
- **Structured evidence**: `aetheros_knowledge.store` `claim_evidence` table + API (support_type supports/contradicts/neutral, confidence 0-1)
- **Formatted citations**: APA/MLA/Chicago/IEEE generators in `store.py` (from `metadata["citation"]` or author/year/doi/journal)
- **Deep research output**: `{findings[], sources[], claim_evidence_map{doc_id:[relations]}, iterations}` — claim extraction heuristic regex, evidence = originating chunk (placeholder confidence 0.6)
- **Research skills**: no structured citation/evidence format; no `deep-research` skill (closest: `skills/research/research-paper-writing`)

---

## 9. Existing Project Context

- **Workdir injection**: cron jobs with `workdir` inject AGENTS.md/CLAUDE.md/.cursorrules from that directory into system prompt; terminal/file/code_exec tools use it as cwd (`TERMINAL_CWD`)
- **Session folder/pinning**: `aetheros_state.py` `sessions.folder`, `archived`, `pinned` columns
- **Kanban tenant**: soft namespace within board (`tenant` column), board isolation via pinned `AETHEROS_KANBAN_BOARD`
- **No unified project-knowledge scoping**: knowledge packages have no project/session binding today

---

## 10. Existing User Context

- `USER.md` + `user_profile_enabled` config; `memory_intelligence` boundary=USER strictest isolation; PrivacyManager (offline mode, telemetry consents, PII masking flag)

---

## 11. Existing MCP Resources

- **List/read implemented**: `tools/mcp_tool.py:2897-3005` (`list_resources`, `read_resource`); capability-gated on server-advertised `capabilities.resources`
- **Subscribe NOT implemented**: `ResourceListChangedNotification` received then explicitly ignored; no `resources/subscribe` call
- **Resources as contextual data** per MCP spec — preserve identity/metadata rather than flattening to anonymous text

---

## 12. Existing Data Connectors

| Connector | Location | Scope |
|-----------|----------|-------|
| Email | `gateway/platforms/email.py` IMAP/SMTP; `aetheros_integrations/providers/email.py` (Gmail/Outlook/IMAP/Exchange) | Messages + attachments |
| Calendar | `aetheros_integrations/providers/calendar.py` (Google/Outlook/CalDAV) | Events + availability |
| Web | `tools/web_tools.py` (search/extract) | Pages |
| Database | `aetheros_integrations/providers/databases.py` (SQLite/PostgreSQL/MySQL) | Reachable via `integration_run` tool or MCP |
| MCP resources | `tools/mcp_tool.py` | List/read only |
| GitHub | `skills/github/*` | Repos, issues, PRs |

**No generic SQL tool** in `tools/` (sqlite hits are internal stores only).

---

## 13. Duplicate Systems (consolidation targets)

| Capability | Live (keep) | Duplicates (consolidate/quarantine) |
|------------|-------------|-------------------------------------|
| Vector DB | `aetheros_memory.VectorDatabase` (LanceDB/Chroma/FAISS/SQLiteVec) | `aetheros_knowledge.vectordb` (4 backends), `plugins/memory/holographic` HRR |
| Embedding engine | `aetheros_memory.EmbeddingEngine` (OpenAI/Gemini/Cohere/Jina/local ST) | `aetheros_knowledge.indexing.embedders` (ST/OpenAI/Ollama/TF-IDF), `agent/multimodal/local_models` |
| Keyword search | SessionDB FTS5, ripgrep (`search_files`) | `aetheros_knowledge.search.engine` BM25 (title only), `tools/tool_search` BM25, holographic FTS5 |
| RAG studio | None live | `aetheros_knowledge.rag.studio`, `aetheros_memory.rag_pipeline`, `aetheros_intelligence.research` |
| Knowledge CLI | `aetheros knowledge` (platform stub, prints fake stats) | `aetheros_knowledge.cli` (orphaned rich), `aetheros_cli/intelligence_cmds` (unregistered, latent AttributeError) |
| Document parsers | `aetheros_vision.documents` (structure + OCR) | `aetheros_knowledge.indexing.parsers` (flat-text for RAG) |
| Memory stores | Built-in + fabric + providers | `aetheros_memory` (corrupt), `agent/memory_os` (empty) |

---

## 14. Missing Functionality (gap list vs Master 14 phases)

**P1 (immediate repair value):**
1. `aetheros_knowledge` dead package: fix import (DONE from HEAD), persist under AETHEROS_HOME, search chunk content, incremental indexing + deletion propagation
2. Secret scanning before indexing (Phases 89-90): apply `agent/redact.redact_sensitive_text` in `IndexingPipeline`
3. Structure-aware markdown chunker (Phase 33): add `_chunk_by_markdown_headings` preserving heading path
4. Wire fabric semantic bridge (Phases 36/37/41): optional embedder in `SecureRetriever` using existing config keys
5. Replace platform `aetheros knowledge` stub with real store-backed handlers

**P2 (architectural):**
6. Embedding versioning + re-index trigger (Phase 38)
7. Cross-encoder reranker + RRF fusion (Phases 47/48)
8. Parent-child retrieval (Phase 35)
9. Knowledge graph + entity resolution (Phases 53-55)
10. MCP resource indexing + cache handling (Phases 64-65)
11. Query router / context router (Phases 69/70)
12. Structured citation/evidence in skills (Phase 58/59)

**P3 (policy/ops):**
13. Memory promotion pipeline (Phase 10)
14. Memory correction/deletion with propagation (Phases 18-20)
15. Data export/portability (Phases 82-83)
16. Evaluation datasets + adversarial tests (Phases 95-96)

---

## 15. Privacy Risks

- **Fabric never sees live traffic** — all poisoning/secret defenses are only in CLI path; live memory writes (`tools/memory_tool.py`) have separate threat-pattern snapshot scan + background-review staging
- **`aetheros_knowledge` store** has `_check_prompt_injection` on title+metadata only (not chunk content); zero-trust permission check via `aetheros_security` but **unreachable** because package dead
- **Secret scanning**: `agent/redact._PREFIX_RE` + URL/query/userinfo/form-body redactors applied on every `read_file` + OCR output + fabric write pipeline; cron scanners separate; `aetheros_memory_intelligence` write_pipeline has `secret_scan` stage (redacts to `[REDACTED]`); skills guard separate
- **No embedding secret sanitization**: raw content → embedding vectors could memorize secrets (Phases 89-90 gap)

---

## 16. Security Risks

- Three parallel "knowledge" CLIs: only stub prints fake stats; orphaned intelligence CLI has latent `AttributeError` (`SearchEngine.keyword_search` doesn't exist)
- `aetheros_knowledge` zero-trust permission check imports `aetheros_security` (identity/tokens/tool_authz) but **package dead** so never enforced
- `aetheros_vision/documents` OCR output redacted via `aetheros_vision.security.redact_sensitive_text` — good
- Prompt-injection defense: untrusted wrappers + STEER channel + MediaTrust pipeline + fabric injection blocklist + knowledge-store blocklist (but dead)
- **Web research provenance lost**: `web_extract` retains only `url, title, content, error` — no publish date, no authority metadata (Phase 63 gap)

---

## 17. Performance Risks

- `aetheros_knowledge/vectordb/sqlite_vec.py`: full-table-scan brute-force cosine (no sqlite-vec extension despite name)
- BM25 over 1000 docs listed then tokenized in Python per query
- No incremental indexing → full re-index on every `index_document`
- No change detection → watcher events not connected
- `aetheros_knowledge` defaults `:memory:` → all indexes vanish at process exit

---

## 18. Files Requiring Modification (Master-14 implementation map)

| Area | Files |
|------|-------|
| Knowledge store persistence + search + incremental | `aetheros_knowledge/store.py` (db_path from AETHEROS_HOME, FTS or chunk LIKE search, checksum+mtime incremental skip, tombstone on delete), `aetheros_knowledge/indexing/pipeline.py` (secret scan, incremental skip, embedding version stamp + outdated detect), `aetheros_knowledge/center/manager.py` (import_file uses checksum) |
| Chunking | `aetheros_knowledge/indexing/chunkers.py` (add `_chunk_by_markdown_headings`) |
| Embedding versioning | `aetheros_knowledge/indexing/embedders.py` (return dims+model+version), `pipeline.py` (stamp chunks, detect outdated) |
| Fabric semantic bridge | `aetheros_memory_intelligence/manager.py` (construct SecureRetriever with optional embedder from config) |
| CLI platform stub replacement | `aetheros_platform/cli.py` (`plt_handle_knowledge` → KnowledgeStore/KnowledgeCenter/IndexingPipeline) |
| Secret scanning before embed | `aetheros_knowledge/indexing/pipeline.py` (import `agent.redact.redact_sensitive_text`) |
| Config | `aetheros_cli/config.py` (`knowledge:` section after `memory_intelligence`, `_config_version` bump only if migration) |
| Tests | `tests/aetheros_knowledge/` new dir; extend `tests/aetheros_memory_intelligence/` for semantic bridge |

---

## 19. Files That Must Remain Untouched

- `aetheros_state.py` (SessionDB — session/episodic contract)
- `tools/memory_tool.py` + `tools/memory_lifecycle.py` + `tools/write_approval.py` (live curated memory contract)
- `aetheros_state.py` SessionDB (FTS5/trigram search contract)
- `agent/memory_manager.py` + `agent/memory_provider.py` + `plugins/memory/*` (provider ABC contract)
- `aetheros_constants.py` / `aetheros_cli/main.py` profile override (AETHEROS_HOME scoping)
- `gateway/run.py` message guards, `gateway/platforms/*` adapters
- `tools/registry.py` / `model_tools.py` discovery contract
- All MASTER 1–13 behavior contracts

---

## Audit Verdict

Master 14 must **repair and wire the dead `aetheros_knowledge` package** (now importable after git restore) as the **single persistent knowledge spine**, reusing:
- Parsers from `indexing/parsers.py` (already reused by `aetheros_vision`)
- Chunkers + embedders (consolidate with `aetheros_memory` later per ABC)
- `aetheros_vision/documents` structure extraction for OCR/tables
- `automation/file_watcher` events → incremental indexing
- `agent/redact` secret scanning before embed
- `aetheros_memory_intelligence` trust/boundaries/provenance logic (compose, don't duplicate)
- Built-in memory lifecycle + provider plugins for procedural/episodic

The stub `aetheros knowledge` CLI must be replaced with real store-backed handlers; the orphaned intelligence CLI must be removed or registered; the fabric must be optionally bridged for semantic retrieval with existing config keys. All within the preservation rules — no duplicate stores, no silent permission changes, no secret leakage.