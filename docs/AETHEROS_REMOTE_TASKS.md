# Remote Tasks (Master 46 §§23–27, 34–37)

`RemoteTask` fields: `taskId`, origin/owner/target agents, user/org,
purpose, requirements, permissions, dataScope, budget, deadline,
priority (`critical/high/normal/low` — never bypasses security), status,
idempotency key, contract version, events, artifacts, result,
provenance, audit.

## Lifecycle

`discovered → proposed → authorized → submitted → accepted → running →
(waiting | input_required | approval_required) → completed | failed |
cancelled | expired | rejected | timed_out`, with only the legal edges
in `_ALLOWED` (`tasks.py`). Illegal jumps raise; `reconcile()` adopts
remote state only along a legal edge and otherwise keeps local state
with a note — progress is never fabricated.

## Delegation pipeline (`gateway.delegate`)

1. capability check 2. trust check 3. permission check 4. DLP/privacy
   scan (**fail-fast, before approvals**) 5. budget/destination checks
6. approval gate (pause → `approval_required`) 7. idempotent submission.

## Durability

Tasks persist in SQLite (`tasks.sqlite`), so delegation survives desktop
restart, network interruption, and remote outage: on return, `poll()`
queries remote state and reconciles, then resumes the event stream and
recovers artifacts. Retries reuse the idempotency key; the store is
consulted before any resubmission, so side-effecting tasks are never
blindly duplicated. The queue is bounded (`queue_depth`, default cap
100); a full queue refuses new work loudly.

## Streaming

`message/stream` (SSE) events normalize to the AetherOS event model:
`TASK_ACCEPTED / TASK_STARTED / PROGRESS / MESSAGE / ARTIFACT /
INPUT_REQUIRED / APPROVAL_REQUIRED / TASK_COMPLETED / TASK_FAILED`.
`INPUT_REQUIRED` surfaces missing data/clarification to the user;
fabricated answers are forbidden. `APPROVAL_REQUIRED` pauses for
Approve / Reject / Modify / Take Over / Cancel.

## Results are verified, not trusted

`COMPLETED` triggers schema checks, artifact hash/size validation,
quarantine release, provenance recording (origin agent/task/source/
timestamp/hash/transformations), and optional cross-agent review
(A produces → B reviews → C resolves, only when justified).
