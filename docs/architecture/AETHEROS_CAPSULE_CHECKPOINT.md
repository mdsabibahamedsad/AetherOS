# AetherOS Capsule Checkpoint, Replay & Audit

Implementation: `kernel/core/hypervisor/{types,hypervisor}.py`.

## Snapshot format (§50)

`AETHEROS_CAPSULE_SNAPSHOT_V1`: metadata, state, intent, authority,
capabilities, manifest hash, policy version + hash, resource limits,
filesystem metadata, network state, memory refs, artifacts, tool state,
event offset, runtime version, SHA-256 integrity hash. `verify()`
rejects version mismatch and tampering (tested: appended capability
fails verification, restore refused). Snapshots never carry secret
values — only fingerprints via authority metadata (§46).

## Checkpoints (§45–§46)

`snapshot_capsule()` captures agent/task/intent/authority/capabilities,
resource allocation, filesystem metadata, network state, memory refs,
artifacts, tool state, and event offset. Restore is in-place (revalidate
+ capability/manifest reset) or to a new capsule (migration target).

## Reproducibility & replay (§52–§54)

Snapshots record runtime/policy/capability versions, artifact hashes,
and the receipt chain (event sequence) for deterministic replay.
`replay()` modes: OBSERVE_ONLY (default — shows recorded actions,
executes zero), SIMULATION/DRY_RUN (read-only steps marked
WOULD_POLICY_CHECK; external side effects marked BLOCKED_EXTERNAL and
never executed — e.g. a recorded payment shows request/result, sends
nothing), FULL_EXECUTION (requires `authorize_full=True` plus fresh
human authorization; external effects re-authorized one by one).

## Termination (§92) and forensics (§93)

GRACEFUL (stop new actions → checkpoint → release → terminate),
IMMEDIATE, FORCED, EMERGENCY (privileged actions blocked at once;
kernel e-stop independent). Physical capsules command actuators to
their configured safe state instead of blindly cutting them (§41).
Quarantined capsules keep a `ForensicSnapshot` (configuration, policy,
event trace, process tree, network/filesystem metadata, artifacts,
security events — content-minimized, no secret values).

## Tamper-evident audit (§94) and receipts (§95)

Capsule creation, permission changes, capability requests, policy
decisions, resource changes, network/secret access, migration,
checkpoint, quarantine, and termination all flow into the kernel
`AuditEngine` (hash-chained). Every mediated action additionally mints a
`CapsuleReceipt` (action/capsule/agent/intent/capability/authority/
policy/input+result hashes/timestamp/verification) chained per capsule;
tests verify chain linkage across denials.

## Memory & world-model labeling (§42–§44, §96–§98)

Capsule memory scopes: EPHEMERAL (dies with the capsule), TASK,
PROJECT, PERSISTENT (retained only if explicitly committed — destroy
never promotes implicitly). Untrusted capsules need the `memory.write`
capability; writes carry source capsule/agent/task/confidence/
provenance/classification. Context never inherits across capsules
without grant. World-model content must be labeled OBSERVED / INFERRED /
PREDICTED / SIMULATED (`label_world_state` rejects anything else).
Research downloads enter as UNTRUSTED DATA; experiment capsules capture
hypothesis/variables/parameters/environment/versions/seeds/data/results/
artifacts/provenance for reproducibility (§99–§100, metadata envelope
provided; hardware measurements never faked).
