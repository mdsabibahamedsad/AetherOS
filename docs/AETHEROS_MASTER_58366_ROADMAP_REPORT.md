# AETHEROS MASTER 58366 — Roadmap Report (2026-10-12)

## 1. Actual repository baseline
Electron desktop over one gateway-agent runtime (`session.create` +
`prompt.submit` for Home/Chat/Jarvis; local exact-match intents gated by
policy). Registry + fallback chains + delegation roles + scanners +
`<untrusted_tool_result>` delimiters all traced with tests. Full inventory
with call paths: evidence `00_BASELINE_INVENTORY` (19 capabilities;
58365 vision report absent — proceeded from 58363/58364).

## 2. Verified existing capabilities
Canonical routing, provider registry + fallback, tools/MCP (UI + trust
wrapping), delegation, task state machine, cancel/recovery distinction,
memory/skills/curator, terminal/files, scheduler hardening, approval gates
both channels, audit command chain, full desktop shell. Live execution of
these remains gateway-dependent (previously recorded).

## 3. Missing / partial
MISSING: desktop task restart persistence. PARTIAL: browser nav gaps,
voice (unwitnessed live), knowledge/diagnostics simulations (backend scope),
packaging (no provenance), remote E2E. REJECTED: visual workflow builder
(backend supports jobs, not graphs), new runtimes/frameworks, renderer secrets.

## 4. Ranked roadmap
P0: H-2 done this phase; action-task persistence deferred (backend design
call); live fallback drill blocked on creds. P1: Models fallback-health UI,
live voice, memory eval, browser wiring, log persistence — each names its
unblocker. P2: distribution trust, sync E2E (see `03_BACKLOG`).

## 5. Selected target
H-2 task lifecycle actions in Tasks view — the "polished but unusable" gap:
runtime methods existed, UI exposed only "view".

## 6. Code changes & tests
`app/tasks/index.tsx` (+actions/handlers/TaskRow/helpers),
`tasks-partition.test.ts` (+4). Typecheck clean; **137/908 vitest PASS**
(+4); touched lint 0 errors. No backend/security/dependency/release changes.

## 7. External blockers & next actions
Live gateway/providers/mic → credentialed dev session, six-row matrix once.
Packaged rebuild → git checkout, `--publish never`, stamp/hash/launch.
Competitor live-doc check → re-run matrix notes when web search available
(recommendations rest on repo gaps regardless).

## 8. Next recommended Master topic
Credentialed live-execution session (A2/B/D-live + voice) — the only phase
that can move the remaining P0/P1 items; no further autonomous audit phase
is justified.

## Status
`AETHEROS_ROADMAP_BASELINED`
