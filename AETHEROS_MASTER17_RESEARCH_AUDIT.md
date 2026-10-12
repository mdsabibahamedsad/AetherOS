# AETHEROS MASTER 17 — Research System Audit (Phase 0)

Date: 2026-08-23 · Scope: research/web/document/knowledge infrastructure survey.
**No code was modified in this phase.**

---

## 1. Existing Capabilities

### 1.1 Web search + fetch (MATURE — reuse, do not duplicate)

| Capability | Location | Notes |
|---|---|---|
| `web_search` tool | `tools/web_tools.py:1543` | `{query, limit}` → `{title,url,description,position}`; backend-operator passthrough (`site:`, `filetype:`) |
| `web_extract` tool | `tools/web_tools.py:1553` | URLs → markdown; handles PDF URLs; >5k chars LLM-summarized (aux task `web_extract`), >2M refused; secret-in-URL block (:1049) + SSRF pre-flight (:1093) |
| Provider ABC | `agent/web_search_provider.py:63` | `WebSearchProvider`: `name`, `is_available()` (network-free probe), `supports_search/extract()`, canonical envelopes |
| Registry | `agent/web_search_registry.py:48,133` | last-writer-wins; resolution precedence explicit-config → single-eligible → `_LEGACY_PREFERENCE`; `get_active_search_provider()` / `get_active_extract_provider()` |
| Providers (8, plugin-per-dir under `plugins/web/`) | firecrawl, parallel (keyed+keyless MCP), tavily, exa, searxng, brave-free, ddgs, xai | xai is search-only agentic w/ citation annotations |
| `x_search` tool | `tools/x_search_tool.py:516` | **only structured-citation surface today**: `answer`, `citations`, `inline_citations` spans, degradation detection when answer came from model memory |
| Toolset wiring | `toolsets.py:97-118` | `"web"=["web_search","web_extract"]`, `"search"=["web_search"]`, `"x_search"` off by default |

### 1.2 Browser (MATURE — Master 15 surface)

- Tools (`tools/browser_tool.py:3789-3870`, toolset `browser`): `browser_navigate` (+compact snapshot), `browser_snapshot` (a11y tree with `@eN` refs, >8k summarized), `browser_click/type/scroll/back/press/get_images/vision/console`.
- Extensions: `browser_cdp` raw CDP passthrough (`browser_cdp_tool.py:555`), `browser_dialog`, `browser_download/upload/tab` (`browser_transfer_tools.py:367-412`), `browser_form_fill/submit` (`browser_form_tools.py:185/214`).
- Backends: agent-browser CLI (default headless Chromium), cloud plugins, Camoufox REST anti-detect (`browser_camofox.py`), CDP override, Lightpanda w/ Chrome fallback, hybrid local-sidecar for private URLs.
- Post-nav redirect safety: final URL re-checked against always-blocked/private IPs → navigates to `about:blank` (`browser_tool.py:2401-2433`).
- Computer use: `computer_use` shim (`tools/computer_use_tool.py`) → cua-driver via MCP stdio.

### 1.3 Documents / PDF / OCR / vision

| Capability | Location | State |
|---|---|---|
| `document_extract` | `tools/vision_tools.py:1801` → `aetheros_vision/documents.py::DocumentIntelligence.extract` | PDF chain PyPDF2→pdfminer→pdfplumber (+inline fallbacks); DOCX/PPTX/XLSX/MD/HTML/RTF/TXT |
| Tables | pdfplumber / DOCX / XLSX / Markdown paths only | Structured `TableData(headers, rows)`; **PyPDF2/pdfminer paths lose tables** |
| Page numbers | `documents.py:109` form-feed counting | **Unreliable** — winning parsers join with `\n`, no `\f` |
| OCR | `aetheros_vision/ocr.py` Tesseract / Windows OCR / Azure; scanned-PDF rasterize fallback (`documents.py:113-130`) | Marked as OCR-derived? Not consistently |
| `image_ocr`, `screen_understand`, `vision_analyze` | `tools/vision_tools.py:1753,1892,1220` | Gated on `aetheros_vision` runtime |
| File tools | `read_file/write_file/patch/search_files` (`tools/file_tools.py:1583-1586`) | ripgrep-backed search; binary detection; UTF-8 implicit |

**Gap:** none of the PDF/DOCX/OCR libs are pinned in `pyproject.toml` — all optional imports with graceful degradation.

### 1.4 Security boundaries (REUSE — these are the trust floor)

| Layer | API | Notes |
|---|---|---|
| SSRF | `tools/url_safety.py`: `is_safe_url` / `async_is_safe_url` (:314/:396), `is_always_blocked_url` (:213), scheme allowlist, DNS all-answers check, fail-closed; metadata endpoints never bypassable | Pre-flight only in web_extract; per-hop redirect re-validation exists in `vision_tools` event hooks + `skills_hub._guarded_http_get` manual loop; browser does post-nav check |
| Domain policy | `tools/website_policy.py`: `check_website_access` (:232), `security.website_blocklist.*`, 30s TTL cache, fail-open by default | Enforced post-redirect by Firecrawl provider |
| Prompt-injection patterns | `tools/threat_patterns.py`: `scan_for_threats(content, scope)` (:187), scopes all/context/strict, invisible-unicode detection | Applied to context files + memory writes; **deliberately NOT applied to tool results** |
| Untrusted-content wrapping | `agent/tool_dispatch_helpers.py:320` `make_tool_result_message` wraps `web_search`/`web_extract`/`browser_*`/`mcp_*` results in `<untrusted_tool_result>` DATA-not-instructions delimiters | Applied at every tool-result append site |
| Command approval | `tools/approval.py` `check_dangerous_command`/`check_all_command_guards` (:1068/:1309), hardline floor, yolo freeze, gateway round-trip ("silence is not consent") | Master 16 surface |
| Write approval | `tools/write_approval.py` `evaluate_gate` (:253), staged pending records | memory/skills gates |
| Tirith command scanner | `tools/tirith_security.py` `check_command_security` (:697) | Windows unsupported → silent fallback |

### 1.5 Memory / knowledge

- Core memory: file-backed `MEMORY.md`/`USER.md` (`tools/memory_tool.py`); action-dispatched add/replace/remove/**keyword-only search** (:573). Provenance schema exists but optional: `MemoryEntryMetadata{source, confidence, timestamp, write_origin, ...}` (:53-64).
- Orchestrator: `agent/memory_manager.py` `MemoryManager` (:252), one external provider max, background sync, `<memory-context>` fenced block.
- Provider plugins (8 bundled, closed set): honcho, mem0, supermemory, byterover, hindsight, holographic, openviking, retaindb.
- Session store: SQLite FTS5 `SessionDB.search_messages` (`aetheros_state.py:3294`).

### 1.6 Scheduler / checkpoints / delegation

- Cron: `cron/jobs.py` (`create_job` :592 — schedule formats duration/every/cron-expr/ISO-once; job fields incl. `script`, `context_from`, `workdir`, multi-platform delivery) + `cron/scheduler.py` `tick`/`run_job` (:2148/:1308). 3-min hard interrupt invariant.
- Checkpoints: shadow-git store, `CheckpointManager.ensure_checkpoint/diff/restore` (`tools/checkpoint_manager.py:627/715/765`). FS snapshots — not research-state-aware.
- Delegation: `delegate_task(goal | tasks[], toolsets, role)` (`tools/delegate_tool.py:1977`), leaf/orchestrator roles, depth cap. Synchronous, not durable.

### 1.7 MCP

`tools/mcp_tool.py` (~4k LOC): stdio/SSE/streamable-http transports, daemon event loop, auto-reconnect, OAuth 2.1 PKCE manager (`mcp_oauth_manager.py`), input-schema normalization (:3164), description-injection scan (:403), credential stripping in errors (:351), auth-header strip on cross-origin redirects (:1776), catalog installer (`aetheros_cli/mcp_catalog.py`).

### 1.8 EXISTING research/knowledge engines (duplication risk — consolidate target)

| Module | What it has | Wired to core? |
|---|---|---|
| `aetheros_intelligence/research.py` `ResearchMode` (:76) | web/docs/github/knowledge/files fan-out; `ResearchFinding{source,title,content,url,relevance}`; URL dedup (:463); reports **in-memory only**; no provenance/claims/citations | Yes — CLI `aetheros analyze research` (`aetheros_cli/intelligence_cmds.py:294`) + web_intelligence_api |
| `aetheros_knowledge/deep_research.py` `DeepResearchEngine` (:20) | iterative search→ingest→claim cycles, budgets, trusted-domain weighting; needs sentence-transformers stack | No |
| `aetheros_automation/browser_automation/research_mode.py` | third variant | No |
| Knowledge graphs ×4 | `aetheros_memory/knowledge_graph.py`, `aetheros_automation/knowledge/knowledge_graph.py` (richest: EntityType/RelationType/confidence), `memory/knowledge_graph.py`, `aetheros_platform/knowledge/graph.py` | No — zero references from run_agent/cli/model_tools |
| Orchestration ×2 | `agent/orchestration/` (modern adapters) vs `aetheros_automation/orchestrator/` (Phase 16) | Runtime delegation actually goes through `tools/delegate_tool.py` |

---

## 2. Storage Inventory

| Store | Tech | Path |
|---|---|---|
| Sessions/messages | SQLite WAL + FTS5 | `get_aetheros_home()/sessions.db` (via `SessionDB`) |
| Memory | Markdown files + locks | `get_aetheros_home()/memories/` |
| Cron jobs | JSON file + lock | `get_aetheros_home()/cron/jobs.json`, `.tick.lock` |
| Kanban | SQLite | kanban.db |
| Checkpoints | bare git store | `get_aetheros_home()/checkpoints/store/` |
| Pending approvals | staged JSON | `get_aetheros_home()/pending/{memory,skills}/` |
| **Research state** | **none — nothing persistent exists** | — |

## 3. Test Coverage Map (relevant suites)

- Web: `tests/tools/test_web_providers*.py`, `test_web_tools_{config,tavily}.py`, `test_web_keyless_default_fallback.py`, `tests/plugins/web/test_web_search_provider_plugins.py`, `tests/integration/test_web_tools.py`, `tests/tools/test_x_search_tool.py`
- Security: `tests/tools/test_{url_safety,website_policy,threat_patterns,tirith_security,approval,write_approval}.py`, untrusted wrapper in `tests/agent/test_tool_dispatch_helpers.py`
- Browser (31 files) incl. `test_browser_ssrf_local.py`, `test_browser_secret_exfil.py`, `test_master15_browser_transfer.py`
- Vision/docs: `tests/aetheros_vision/test_documents.py` (**text formats only — no PDF/DOCX fixtures**), `tests/tools/test_vision_runtime_tools.py`
- Runner: `scripts/run_tests.sh` (hermetic parity, subprocess-per-test isolation)

## 4. Missing Functionality (gap analysis vs Master 17 phases)

1. **No research object / state machine / persistence** — no ResearchTask, no transitions log, no resume. (Phases 1-2, 58-61)
2. **No source objects or provenance** — `web_search` returns bare tuples; fetch timestamp/content-hash/source-type/trust-signals absent everywhere except x_search citations. (Phases 8-9)
3. **No URL canonicalization / cross-call dedup** (Phases 10-11)
4. **No claims / evidence / citation objects; no citation validation**; fabricated-citation guard exists *only* as x_search degradation detection. (Phases 24-29)
5. **No source-quality scoring / type classification / independence detection** (Phases 20-23)
6. **No contradiction/uncertainty modeling** (Phases 44-47)
7. **Injection scanning not applied to fetched research content** — threat_patterns guards prompts/memory but research pipeline lacks a content-scan step. (Phase 15)
8. **No robots.txt handling, no politeness/rate limiting, no result caching/TTL/freshness tracking anywhere in web path** (Phases 12, 62-63)
9. **PDF page attribution broken; tables lost on some parser paths; no doc-format test fixtures** (Phases 32, 34)
10. **Knowledge graph: 4 unintegrated implementations, no entity resolution** (Phases 50-52)
11. **Research agents = delegation only; no specialized research roles** (Phases 69-72)

## 5. Duplicate Functionality (consolidation notes)

Three research engines, four knowledge graphs, two orchestration stacks exist. Per the contribution rubric ("extend, don't duplicate", "design one shared interface"), Master 17 implementation must **not** create a fourth engine: it should provide the missing state/provenance layer and compose the existing search provider registry + security stack, leaving consolidation of the legacy engines as explicitly-scoped follow-up.

## 6. Integration Points Selected

| Rung (Footprint Ladder) | Choice |
|---|---|
| Search/fetch | `agent/web_search_registry.get_active_search_provider()` — replaceable providers, zero new backends |
| Safety | `tools/url_safety.async_is_safe_url`, `tools/website_policy.check_website_access`, `tools/threat_patterns.scan_for_threats` |
| Untrusted framing | existing `make_tool_result_message` delimiters stay authoritative for model-facing content |
| Persistence | new SQLite store under `get_aetheros_home()/research/` (profile-safe via `get_aetheros_home()`) |
| CLI surface | `aetheros research <verb>` subcommand module (pattern: `send_cmd.register_send_subparser`) |
| Agent surface | built-in skill (`skills/research/SKILL.md`) guiding use of CLI + existing web tools — **no new core model tools** |
| Long-running | future: cron jobs (`research.monitor`) — not in first slice |
| Subagents | future: delegate_task role presets — not in first slice |

## 7. Security Invariants Carried Forward

- All web content is UNTRUSTED DATA; injection patterns scanned before any content is stored as evidence.
- SSRF + domain policy checks on every URL before fetch; final-URL re-check after redirects where transport allows.
- Never fabricate sources/citations: evidence records must reference retrieved content hashes; "Evidence not found." is a legal report outcome.
- No credentials to providers beyond what existing provider plugins already use; no new env vars; config via `config.yaml` defaults only.
