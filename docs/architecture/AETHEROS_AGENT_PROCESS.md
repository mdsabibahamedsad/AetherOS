# AetherOS Agent Process

Source of truth: `kernel/core/types.py` — `AgentProcess`,
`AgentLifecycleState`; runtime: `kernel/core/agent_process_manager.py`.

## Identity

Every agent gets `AgentIdentity` (`agent_id`, key material, issuer,
trust level, tenant, scopes, status, expiry). Short-lived, revocable,
delegatable. Service accounts are scoped identities for automations —
never blind reuse of user credentials.

## Lifecycle

```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> ADMITTED
    ADMITTED --> INITIALIZING
    INITIALIZING --> READY
    READY --> RUNNING
    RUNNING --> WAITING
    RUNNING --> BLOCKED
    RUNNING --> PAUSED
    RUNNING --> CHECKPOINTING
    RUNNING --> COMPLETED
    RUNNING --> FAILED
    RUNNING --> CANCELLED
    PAUSED --> READY
    PAUSED --> RUNNING
    CHECKPOINTING --> READY
    FAILED --> RECOVERING
    RECOVERING --> READY
    COMPLETED --> TERMINATED
    FAILED --> TERMINATED
    CANCELLED --> TERMINATED
```

```text
CREATED → ADMITTED → INITIALIZING → READY → RUNNING → (WAITING | BLOCKED |
PAUSED | CHECKPOINTING | RECOVERING) → COMPLETED | FAILED | CANCELLED →
TERMINATED
```

Every transition is validated (`AgentProcess.transition()`) and emitted
on the event bus — no hidden lifecycle.

## Isolation (§5)

Isolated context, memory scope (`agent:<id>`), credentials (subset of
parent grant only), filesystem/network/tool/capability scopes, artifacts,
secrets, event subscriptions. Children never inherit authority implicitly:
`AuthorityManager.delegate_authority()` enforces
`ChildAuthority ⊆ ParentAuthority` plus delegation-depth limits, and
`PolicyEngine` re-checks (`child_authority_subset`, `delegation_depth`).

## Delegation

```mermaid
flowchart TB
    Parent --> Grant[Parent grant]
    Grant --> Sub[Subset enforcement]
    Sub --> Child[Child grant + depth+1]
    Child --> Revoke[Recursive revoke on parent revoke]
```
