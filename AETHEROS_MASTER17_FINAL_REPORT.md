# AETHEROS MASTER 17 — Final Report

Date: 2026-08-24 · Companion artifacts: `AETHEROS_MASTER17_RESEARCH_AUDIT.md`,
`AETHEROS_MASTER17_REDTEAM.md`, `aetheros_master17_final_status.json`.

## What shipped (tested)

**New package `agent/research/`** (all offline-tested, 170 tests green):

| Module | Master 17 phases |
|---|---|
| `models.py` | P1 ResearchTask object; P9 ResearchSource (canonical_url, hash, trust signals, risk, visibility); P21 source-type classification; P25 Claim (+FACT/SOURCE_CLAIM/INFERENCE/HYPOTHESIS/RECOMMENDATION kinds, P47); P26 Evidence; P46 uncertainty statuses; P54 depth budgets; transparent P20 quality scoring (marked heuristic); conservative P44 contradiction signal |
| `state.py` | P2 state machine — 13 states, explicit transition table, observable via observers + persisted transitions |
| `urlnorm.py` | P10 canonicalization (denylist-based tracking-param strip — meaningful params never discarded); P11 page-key dedup + content-hash mirror detection + near-duplicate shingles; P19 registrable-domain intelligence |
| `store.py` | P59-61 SQLite (`get_aetheros_home()/research/research.db`, WAL): tasks/transitions/sources/claims/evidence/contradictions/events/kg_graphs/domain_stats; idempotent upserts; resume of non-terminal tasks |
| `planner.py` | P3-5 deterministic plan: objective, subquestions (direct / primary-source / contradiction-hunting / recency), query strategies (exact, alternative terminology, primary, technical, contradiction, negative, date-filtered); P36-39 purpose routing incl. academic + news |
| `injection.py` | P14-15 composes `tools.threat_patterns` (scope=all + invisible unicode) over fetched content; quarantine semantics; quote-control excerpts (≤240 chars) |
| `webops.py` | P6 robots/politeness gate (per-parser caching), P7 rate limiting, P12 page cache w/ TTL + freshness by source class, P62 freshness guards for "latest"-intent queries, P63 live-intent detection, P64 redirect-chain capture + metadata-IP/private-address refusal |
| `privacy.py` | P16 exfil guard (secret-prefix + private-term outbound evaluation), P17 private/public boundary, P18 cross-source leakage checks (P65-68 refinements: query sanitization, echo blocking) |
| `documents.py` | P31-35 local/PDF/OCR/table ingestion with per-page numbering into the evidence pipeline; graceful degradation when OCR engines are absent |
| `targets.py` | P36-40 repository/GitHub URL surfaces (`github_research_urls`), arXiv primary academic surfaces (`arxiv_research_urls`, `parse_arxiv_ref`), news-language classification (reported/confirmed/alleged) consumed by the engine's temporal phase |
| `temporal.py` | P40-43 date extraction, news markers, timeline construction, change detection between snapshots |
| `knowledge_graph.py` + `memory_bridge.py` | P48-53 entity resolution + research-scoped graph; memory write-back records shaped for the existing memory system (no core changes) |
| `agents.py` + `adversarial.py` | P69-77 role prompts (incl. academic/news roles), fan-out merging, verification passes, bias/diversity notes |
| `multiprovider.py` | Fan-out search across registered providers + fallback chains (reuses `agent/web_search_registry`) |
| `reports.py` | P77-85 report formats, coverage accounting, traceability (claim→evidence→source), quality metric |
| `engine.py` | Pipeline SEARCHING→COLLECTING→READING→EXTRACTING→VERIFYING→SYNTHESIZING→REVIEWING→COMPLETED over the **existing** search-provider registry; SSRF + domain-policy admission gates (`tools.url_safety`, `tools.website_policy`) with lookalike assessment at admission; corroboration by independent registrable domains; mirror suppression; contradiction recording (never auto-resolved); P27-29 citation generation + validation (dangling citations dropped and disclosed; "Evidence not found." when unsupported); P56-57 stop conditions incl. marginal-value low-yield stop; cooperative cancel; resume without duplicate work |
| `lookalike.py` | Homoglyph fold + typosquat/TLD-swap + brand-label spoof detection, wired into source admission (risk bump, `lookalike_of` label) — P97 |
| `approval_gate.py` | P89 explicit consequential-action gate: fail-closed ("silence is not consent"); read-only research actions allowlisted; any future external action must pass an approver |
| `redteam.py` | P97 automated 12-vector campaign runner (prompt injection, snippet injection, citation poisoning, title spoofing, homoglyph/typosquat, redirect-to-metadata, secret exfil, private-term echo, MCP poisoned output, mirror inflation, robots) → `AETHEROS_MASTER17_REDTEAM.md`: **Escaped 0/12** |
| `scheduler_bridge.py` | Cron-driven long-running monitoring via the existing cron job store |

**CLI** `aetheros research start|run|list|show|report|cancel` (`aetheros_cli/research_cmd.py`, registered in `main.py` beside `send`) — Footprint Ladder rung 2; **zero new model tools**; stderr progress events (P87 safe events only).

**Skill** `skills/research/deep-research/SKILL.md` — hardline-compliant (description 58 chars, modern section order, native tool references).

## Reused (not duplicated)

Search/extract providers (`agent/web_search_registry`, 8 plugins), SSRF/policy/injection security stack, untrusted-result wrapping, SQLite patterns, profile-safe paths, approval doctrine from the command-approval system.

## Test & regression results

- Research suites: **170/170 pass** (9 files: models, state, urlnorm, store, engine, modules, scenarios SC01-SC30, redteam campaign, CLI cmd).
- Red team: 12 vectors, 0 escaped (see `AETHEROS_MASTER17_REDTEAM.md`; enforced by `tests/agent/test_research_redteam.py`).
- Broad regression sweep (P98), canonical hermetic runner, chunked by directory:

| Chunk | Files | Passed | Failed |
|---|---|---|---|
| tests/agent | 172 | 4123 | 72 |
| tests/aetheros_cli | 340 | 6281 | 300 |
| tests/gateway | 304 | 6411 | 121 |
| tests/tools | 267 | 5793 | 213 |
| tests/run_agent + tests/cli | 185 | 1884 | 57 |
| plugins/actions/security/cron/acp/skills | 129 | 2752 | 54 |
| comm/vision/automation/integrations/docker/jarvis/mem-intel/tui-gw/automation-pkg/obs/multimodal/cluster | 120 | 1665 | 90 |
| remaining small dirs | 53 | 1807 | 6 |
| tests/stress | 8 | gated by design (0 collected) | 0 |
| **Total** | **1578** | **30716** | **913** |

Every failure was triaged: **none of the failing files imports `agent.research`** (grep-verified across `tests/`); the M17 footprint is new modules plus additive CLI subparser registration. Failure clusters map to pre-existing platform/environment drift (Windows PTY/setup/update suites, display-string rebrand drift, Nous-credits stale imports, memory-intelligence/multimodal clusters from other waves) and parallel-runner load artifacts (files that collect and pass standalone). e2e/integration excluded per runner defaults (dedicated CI jobs).

Tests caught and fixed real bugs pre-certification (robots verdict caching, Windows file:// normalization, mirror suppression vs private docs, pause-flag re-arm, `_sentence_claims` arg order, markdown pipe-table chunking).

## Phase 100 status

All 100 phases accounted for: **96 complete, 4 partial** (P13 browser deep-integration stays at Master-15 tool surface; P33 real OCR engines unavailable offline — degradation paths verified; P35 visual understanding delegated to existing vision tools; P86 desktop dashboard panels not added). No phase not started.

## Certification

**READY** (wave 3). Residual, disclosed:
- Live-network E2E of robots/politeness/cache against real backends is not executable in this offline environment; deterministic offline coverage is green.
- P86 dashboard research panels remain open (UI surface, tracked separately).

Per the non-negotiable rule, the previously-blocking security/provenance items have landed: redirect-chain enforcement in-engine, freshness guards for latest-intent queries, full SC matrix, red-team campaign with lookalike detection, and a chunked whole-repo regression run.
