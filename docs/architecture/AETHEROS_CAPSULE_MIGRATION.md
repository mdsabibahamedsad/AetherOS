# AetherOS Capsule Migration

Implementation: `kernel/core/hypervisor/hypervisor.py`
(`migrate_capsule`, `placement`, `restore_snapshot`).

## Cycle (§47)

```text
pause → checkpoint → verify destination → transfer → restore
→ verify → resume
```

Local migration executes the full cycle: pause (or operability check),
integrity-sealed snapshot, destination provider compatibility check,
in-place restore with integrity verification, authority revalidation,
resume. Any failure triggers rollback (§49): source snapshot restore,
authority revalidation, resource release, audit event.

## Security (§48, §105)

The destination must prove identity, trust, capability/policy
compatibility, runtime version, and resource availability before
receiving anything. Migration is denied when private data cannot leave
the node (local-only/cloud-denied policy), the device is local-only
(physical/actuators), credentials cannot transfer, policy differs,
destination trust is insufficient, or the runtime is incompatible.
Remote destinations additionally require node pairing + mTLS, which is
not configured in 1.0 — remote migration honestly returns
`REQUIRES_CONFIGURATION` and moves nothing.

## Distributed capsules (§106–§107)

Parent + worker capsules (`swarm_children`) model multi-node work: the
parent coordinates, workers carry reduced authority, and worker results
are expected to carry worker/capsule/task ids, input/output hashes,
model/tool versions, timestamps, and status for parent verification
(receipts provide this envelope today).

## Handoff and takeover (§90–§91)

Handoff revalidates: the receiving agent must independently hold every
capsule capability or the transfer is denied; only explicitly permitted
state moves. Takeover suspends conflicting agent actions and records the
human-control window; release is explicit.
