# AetherOS Verification

Source: `kernel/core/capability_invoker.py` (verification strategies),
`kernel/core/observability_engine.py` (traces), `kernel/core/audit_engine.py`,
`kernel/core/provenance_engine.py`.

## Verification Strategies (CapabilityInvoker)

| Strategy | Behavior |
|---|---|
| `observe` | result exists (not None) |
| `verify` | result exists + no error |
| `attest` | **UNVERIFIED** unless provider registers custom verifier with cryptographic proof |

Default: `observe`. Capability descriptors declare `verification_strategy`.

## Provenance

`ProvenanceEngine` tracks nodes/edges:
```text
ProvenanceType: USER_PROVIDED, MODEL_GENERATED, TOOL_RETURNED, WEB_DERIVED,
                MEMORY_DERIVED, SENSOR_DERIVED, DEVICE_DERIVED, AGENT_DERIVED,
                HUMAN_APPROVED, SYSTEM_DERIVED, INFERRED, SIMULATED, PREDICTED,
                VERIFIED, UNVERIFIED
```
- `create_node(content, type, agent_id)` → `ProvenanceNode`
- `add_edge(from_id, to_id, relation)` → `ProvenanceEdge`
- `get_lineage(node_id)` → ancestors
- `verify_provenance_chain(node_id)` → tamper detection

## Audit Engine

Hash-chained log (`AuditEntry` with `previous_hash`, `entry_hash`):
```python
audit_engine.log(event_type, actor_id, action, target, outcome,
                 details, provenance)
```
- `verify_chain()` validates integrity from genesis
- Retention configurable; immutable once written

## ObservabilityEngine

Traces: `trace_id`, `span_id`, `parent_span_id`, events, tags, logs.
Metrics: counters, histograms, gauges with callbacks.
Sampling: `trace_sampling_rate` (default 1.0).

## Verification Invariant

> Observation ≠ Verification. Verification requires independent
> evidence (tool return, filesystem state, API response, hash,
> artifact existence, structured assertion). The model saying "I did X"
> is never proof.

`CapabilityInvoker._verify_execute` checks result exists + no error.
`_verify_attest` returns UNVERIFIED without provider attestation.
Replay mode `OBSERVE_ONLY` shows recorded actions; external effects
marked `BLOCKED_EXTERNAL` — never re-executed.

## Verification Invariant (tested)

- `test_replay_cannot_execute_external_side_effects`: external caps
  marked `BLOCKED_EXTERNAL` in DRY_RUN
- `test_verification_honesty`: `_verify_attest` returns UNVERIFIED
- `test_observation_is_not_verification`: tool output ≠ fact without
  independent check