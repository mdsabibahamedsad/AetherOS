# AetherOS State Model

## Execution state vs memory (§3A-B)

Execution state: current step, execution graph position, tool state, pending
approval, checkpoint pointer, retry state, resource lease, recovery marker.
Memory: preferences, project facts, lessons, semantic knowledge, approved
memories with provenance/confidence/trust/version/status.

## Task persistence

`records(domain='task')` + `TaskRepository.transition()` (CAS + durable
`task.state_transition` event in one transaction). Generations increase
monotonically; stale writers rejected.

## Agent persistence

`AgentRepository`: register → lifecycle events; transitions transactional.
Crash: lease expiry marks interruption; `startup_scan()` triages; authority
revalidated before resume.

## Authority persistence (§31)

`authority_grants`: subject/capability/delegate/policy_version/issued/
expires/revoked/version. `is_valid()` = present AND not revoked AND not
expired. Restore copies only temporally-valid, non-live-revoked grants.

## Audit persistence (§32-33)

`audit_log` append-only; survives restart/crash (same WAL DB, committed
transactions). Security audit 365d, debug 30d, temp traces 7d.

## Configuration (§29-30)

Layers SYSTEM < USER < PROJECT < TASK < AGENT < DEVICE; each value has
source/version/scope/timestamp. Security-critical changes emit
`config.changed` + audit. Migrations versioned; failure fails safe (no
unsafe defaults).

## Storage Center UI (§102-103)

Backend payload: `aetheros_data.api.storage_status()` (stats + health +
metrics). Desktop/TUI render from this payload; no fake data. A full React
Storage Center is PARTIAL (API + CLI shipped, dashboard widget pending).
