# AetherOS Agent Hypervisor 1.0 — Architecture

Master 57 established the Agent Kernel as the trusted control substrate.
Master 58 adds the execution layer above it: the **Agent Hypervisor /
Capsule Runtime** (`kernel/core/hypervisor/`).

```text
                  AETHEROS
                     │
              AGENT KERNEL  (intent, authority, policy, audit)
                     │
              AGENT HYPERVISOR  (capsules, isolation, enforcement)
                     │
        ┌────────────┼────────────┐
        │            │            │
    Capsule A    Capsule B    Capsule C
        │            │            │
      Agent        Agent        Agent
        │            │            │
     Tools        Models       Memory
        │            │            │
        └────────────┼────────────┘
                     │
              HOST / NODES
```

## Rule

> An agent does not receive the machine. An agent receives a capsule.

> The capsule does not own authority. The Kernel temporarily grants
> bounded authority to the capsule.

> Isolation is not a UI promise. Isolation is enforced by real runtime
> mechanisms — and where a stronger primitive is unavailable, AetherOS
> says so instead of pretending.

## Components

| Module | Responsibility |
|---|---|
| `types.py` | Capsule data model: lifecycle, profiles, mounts, network, snapshots, receipts, contracts |
| `profiles.py` | 14 standard profiles (defaults, never bypasses) |
| `guards.py` | Path-escape + SSRF/DNS-rebinding defense (pure, deterministic) |
| `isolation.py` | Provider abstraction + capability detection (honest levels) |
| `filesystem.py` | Virtual FS roots, mounts, COW, teardown |
| `secrets.py` | Capability-mediated SecretBroker (no plaintext to agents) |
| `risk.py` | Deterministic risk + blast radius (never LLM-judged) |
| `hypervisor.py` | `AgentHypervisor`: lifecycle, admission, mediation, recovery |
| `api.py` | Typed `capsules.*` facade |
| `benchmark.py` | Real-measurement benchmark suite |

## Lifecycle

```text
REQUESTED → ADMISSION_CHECK → PROVISIONING → INITIALIZING → READY
→ RUNNING ⇄ SUSPENDED → CHECKPOINTING / MIGRATING / RECOVERING
→ COMPLETED → DESTROYED        (+ FAILED / QUARANTINED / TERMINATED)
```

Every transition emits a `capsule.lifecycle.transition` Kernel event and
an audit entry. See `AETHEROS_AGENT_CAPSULE.md`.

## Admission

```text
Intent → Identity → Authority → Policy → Risk → Capabilities
→ Resource availability → Isolation requirements → Capsule admission
```

The model never self-authorizes: admission runs entirely kernel-side, the
capsule authority is a subset of the agent authority (`CapsuleAuthority ⊆
AgentAuthority ⊆ ParentAuthority ⊆ UserAuthority`), and anything not in
the sealed capability manifest is unavailable (deny-by-default).

## Enforcement points

All capsule capability calls flow through `AgentHypervisor.invoke()`:
operability → manifest gate → circuit breaker → rate limit → resource
budgets → network/screen/secret policy → kernel invocation → chained
receipt + egress record. See `AETHEROS_CAPSULE_SECURITY.md`.
