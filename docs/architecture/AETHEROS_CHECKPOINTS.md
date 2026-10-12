# AetherOS Checkpoints & Recovery

Implementation: `kernel/core/checkpoint_manager.py`,
`kernel/core/recovery_manager.py`.

## Checkpoint (§26)

Captures intent, plan, state, context, memory refs, authority,
capabilities, resources, model/tool state, artifacts, subtasks, event
offset. Secrets are never serialized unless encrypted and explicitly
required. Storage: `~/.aetheros/checkpoints/` + in-memory index, capped
per agent (`max_checkpoints_per_agent`).

```mermaid
flowchart LR
    Pause --> Snap[full checkpoint]
    Snap --> Crash[crash / restart / migration]
    Crash --> Classify[classify failure]
    Classify --> Verify[verify side effects]
    Verify --> Resume[resume / rollback / escalate]
```

## Recovery (§27)

Classifies `retryable / non_retryable / unknown / unsafe /
partial_success / state_divergence / external_side_effect`. Non-idempotent
operations are verified before retry (no blind retries, no duplicate
external side effects). Crash-consistency is tested across authorize →
execute → verify → checkpoint → delegate boundaries
(`tests/kernel/test_agent_kernel_security.py` + recovery tests).
