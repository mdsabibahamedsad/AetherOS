# A2A Developer Guide

Status: EXPERIMENTAL subset (`aetheros_platform/a2a.py`,
protocol `0.3.0-compat`; no official A2A SDK installed — the wire
protocol is implemented directly over httpx).

## What works (proven over real HTTP by `test_mcp_a2a.py`)

Agent Card (`local_card`, `validate_card` against `schemas.py::AgentCard`),
discovery (`A2AClient.fetch_card`), capability advertisement, task
creation with server ledger (`A2ATaskStore`), task states
(submitted/working/input-required/completed/failed/canceled), messages,
artifacts refs, SSE shape, API-key auth, identity/delegation records,
cancellation, idempotent duplicates (same key → same task, no duplicate
state), provenance.

## Trust rules (enforced, tested)

- Remote agents are NEVER auto-trusted: cards default `untrusted`;
  `TRUSTED_AGENTS` is an explicit allow-list.
- Poisoned cards (prompt-injection descriptions, claimed `trusted`) validate
  structurally but gain nothing: `test_a2a_poisoned_card_rejected`.
- Gateway endpoints: `GET /api/v1/a2a/card` (public), `POST
  /api/v1/a2a/tasks` (scope `a2a:write`).

Example: `aetheros_platform/examples/a2a_agent.py` (card → fetch →
submit → result, executed in CI). Scaffold: `init a2a`.
