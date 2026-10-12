# AetherOS Recovery

Source: `kernel/core/recovery_manager.py`, `kernel/core/checkpoint_manager.py`,
`kernel/core/hypervisor/hypervisor.py`.

## RecoveryManager

```python
class RecoveryManager:
    def classify_failure(error, context) -> RecoveryAction
    def create_recovery_plan(agent_id, failure_type, context) -> RecoveryPlan
    def execute_recovery(plan) -> RecoveryResult
    def register_verifier(action, verifier)
    def register_recovery_callback(action, callback)
```

## RecoveryAction

```
RETRYABLE          // transient, safe to retry
NON_RETRYABLE      // permanent, never retry
UNKNOWN            // uncertain, escalate
UNSAFE             // side-effectful, must verify before retry
PARTIAL_SUCCESS    // some effects applied
STATE_DIVERGENCE   // state mismatch
EXTERNAL_SIDE_EFFECT // already affected world
```

## CheckpointManager

```python
class CheckpointManager:
    def create_checkpoint(agent_id, type="periodic") -> Checkpoint
    def create_full_checkpoint(process) -> Checkpoint  // captures full state
    def get_checkpoint(id) -> Checkpoint | None
    def list_checkpoints(agent_id) -> List[str]
    def delete_checkpoint(id) -> bool
    def register_state_capture(name, callback)
```

`Checkpoint` captures: intent, state, context, memory refs, authority,
capabilities, resources, model state, tool state, artifacts, subtasks,
event offset, metadata.

## Recovery Flow

```text
FAILURE
  ↓
classify_failure() → RecoveryAction
  ↓
create_recovery_plan()
  ↓
execute_recovery()
    ├─ RETRYABLE: backoff + retry (idempotent only)
    ├─ NON_RETRYABLE: rollback + alert
    ├─ UNKNOWN: escalate to human
    ├─ UNSAFE: verify side effects before retry
    ├─ PARTIAL_SUCCESS: resume from last verified step
    ├─ STATE_DIVERGENCE: restore checkpoint + reconcile
    └─ EXTERNAL_SIDE_EFFECT: verify + compensate
  ↓
VERIFY (observation + side-effect check)
  ↓
RESUME / ESCALATE / TERMINATE
```

## Checkpoint + Recovery Integration

- `AgentHypervisor.snapshot_capsule()` → `CapsuleSnapshot` (integrity-sealed)
- `restore_snapshot(hash)` → in-place (revalidate) or new capsule (migration)
- Agent checkpoints linked to capsule checkpoints via `event_offset`
- `RecoveryManager` reuses `CheckpointManager` snapshots

## Idempotency (§22)

Every side-effectful action carries `idempotency_key` (from
`CapabilityDescriptor.idempotency`). `RecoveryManager` checks before
retry — prevents duplicate external effects (payments, sends, deletes).

## Crash Consistency (§93)

Recovery tested across boundaries:
- before authorization
- after authorization / before execution
- during execution
- after execution / before verification
- during checkpoint
- during delegation

System avoids duplicate external side effects.

## Graceful Degradation (§78)

```
FULL → REDUCED (GPU/NPU unavailable) → OFFLINE (no cloud) → SAFE (local only)
```

Cloud-dependent actions show `UNAVAILABLE` — never silently fail.