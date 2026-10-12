# AetherOS Memory 2.0 — Operations (Master 41)

## Write policy (approval tiers)

- Auto-store: low-risk operational facts with strong evidence
  (`USER_STATED`/explicit, project facts).
- Suggest: inferred preferences, sensitive content → `suggested` (caller
  surfaces for confirmation; nothing persists silently).
- Require confirmation: consequential personal memories (sensitive class).
- Never: secrets/credentials (`refused`).

## Lifecycle

ACTIVE → STALE (age thresholds per type; user-confirmed
preference/fact exempt from age-decay) → EXPIRED (TTL/validity) or
SUPERSEDED (version chain) or ARCHIVED → DELETED (tombstone) → purge via
`purge_tombstones()`. `run_forgetting()` applies transitions.

Per-type TTL defaults: task state 30d, episodic 90d; user-confirmed
preferences persist until changed/deleted. Age alone never invalidates
stable facts.

## Consolidation & dreaming

`consolidate()` clusters ≥3 related active episodic records per project
into one summary record with `evidence_ids` + `consolidated_from` metadata.
Sources are never deleted. `dream()` runs the bounded `DreamingLoop`
(proposals only, preference proposals filtered, disableable via
`enabled=False`, observable via `status()`, interruptible `stop()`).

## Migration

`migrate_entries(v1_entries)` upgrades fabric entries idempotently
(skips invalid + already-present ids). `MemoryIntelligence.memory2()`
migrates on first use and audits the count.

## Observability

`MemoryMetrics`: `memory_reads`, `memory_writes`, `retrieval_latency_ms`,
`write_latency_ms` — measured counters only. Events: MEMORY_CREATED/
UPDATED/SUPERSEDED/DELETED/CONFLICTED/RETRIEVED/CONSOLIDATED,
ENTITY_CREATED/UPDATED, RELATIONSHIP_CREATED/UPDATED (deduped, `recent()`,
`counts()`).

## Failure recovery

- Record/graph writes are atomic (temp file + rename); torn writes don't
  corrupt the live set.
- Secondary-index failure can't corrupt primary records (single JSON doc
  is the primary; graph is independently persisted).
- Idempotent import (skips existing ids, rejects invalid).

## Desktop & privacy controls

Memory Center tabs (search/timeline/project/inspector/health) map 1:1 to
`memory2.*` IPC. Forget flows (record/topic/project/all), export (secrets
excluded), temporary mode, and per-memory explanation give users full
control. Unavailable backend shows an honest empty state — never fake data.
