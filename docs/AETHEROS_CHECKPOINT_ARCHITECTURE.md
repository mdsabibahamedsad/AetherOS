# AetherOS Checkpoint Architecture (§15-17)

Checkpoint fields: checkpoint_id, task_id, agent_id, generation, created_at,
state_version, execution_position, plan_reference, context_reference,
memory_references, resource_state, authority_reference, pending_operations,
pending_approvals, recovery_metadata, integrity_hash. Deterministic
representation; never a process-memory dump.

Frequency (§16): meaningful boundaries — before risky action, after important
transition, after tool group, before suspension/handoff/long op/external side
effect. Never per-token.

Validation (§17, `CheckpointManager.validate`): schema version, task/agent
identity, authority validity (live `AuthorityStore.is_valid`), generation
sanity, integrity hash, expiration. Stale authority ⇒ checkpoint rejected
for resume (reconcile instead).
