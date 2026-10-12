# AetherOS Automation — Operations (Master 43)

## Run states & automation states

DRAFT/ACTIVE/PAUSED/RUNNING/WAITING/BLOCKED/FAILED/COMPLETED/CANCELLED/
DISABLED; per-run QUEUED→…→COMPLETED/FAILED/CANCELLED with WAITING_*,
RETRYING, VERIFYING intermediates.

## Approvals

Scoped, expiring, per action+resource+automation+user. Bound to swarm
ApprovalQueue semantics (fail-safe deny). UI approve/reject via
`automation.*` IPC + agent tools.

## Notifications & digest

Modes immediate/digest/daily/weekly/only_important/silent. DigestEngine
groups into "N important in M" with evidence + affected project +
recommended action fields from the note body.

## Memory & learning

Completed runs optionally write bounded lessons via injected
`memory_create` (Master 41). Inferred notification preferences must never
override explicit settings — no such override path exists.

## Retention & privacy

`prune_runs(keep_s)`, automation delete, export without secrets.
Health from measured failures/blocks/stale schedules — never fake.

## Power/offline/multi-device

- `power_mode` setting (power_saver/balanced/performance); scheduler is
  caller-driven so throttling = tick cadence (host-owned).
- Offline: LOCAL_EXECUTABLE vs NETWORK_REQUIRED → WAITING_NETWORK;
  recovery via reconcile on reconnect.
- Multi-device: idempotency keys + concurrency keys prevent duplicates;
  native distributed locks NOT implemented (documented limitation).

## Native service

NOT implemented as OS services; background execution = host process
threads. No native-service claim made anywhere.
