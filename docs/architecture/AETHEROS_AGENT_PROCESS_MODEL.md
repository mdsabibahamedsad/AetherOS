# AetherOS Agent Process Model

Source: `kernel/core/types.py` (`AgentProcess`, `AgentIdentity`,
`AgentLifecycleState`, `AgentPriority`), `kernel/core/agent_process_manager.py`.

## AgentProcess

Every agent is a first-class runtime entity (`AgentProcess`) with:

```text
AgentProcess {
    agent_id: str              // new_id("agent")
    process_id: str            // new_id("proc")
    parent_agent_id: str | null
    tenant_id: str
    identity: AgentIdentity
    intent: Intent
    authority: AuthorityGrant
    capabilities: List[str]
    state: AgentLifecycleState
    priority: AgentPriority
    resource_budget: ResourceBudget
    resource_allocation: ResourceAllocation
    context_budget: int        // tokens
    memory_scope: str          // "agent:<agent_id>"
    model_policy: Dict
    tool_policy: Dict
    network_policy: Dict
    filesystem_policy: Dict
    device_policy: Dict
    security_profile: str
    lifecycle_state: AgentLifecycleState
    checkpoint_id: str | null
    provenance: Dict
    metrics: Dict
    created_at, updated_at, started_at, completed_at: float | null
    error: str | null
}
```

## AgentIdentity

```text
AgentIdentity {
    agent_id: str              // new_id("agent")
    identity_type: str         // agent | human | service | device | delegated
    public_key: str
    key_id: str
    issuer: str                // "aetheros-kernel"
    subject: str
    display_name: str
    version: int
    trust_level: int           // 0=unknown .. 5=system
    organization: str
    tenant: str
    capabilities: List[str]
    scopes: List[str]
    status: str                // active | suspended | revoked | expired | quarantined
    created_at, expires_at: float
    metadata: Dict
}
```

## Lifecycle (validated transitions)

```
CREATED → ADMITTED → INITIALIZING → READY
                             ↓
                         RUNNING ⇄ WAITING
                              ↓
                         BLOCKED ↔ RUNNING
                              ↓
                         PAUSED ↔ READY
                              ↓
                     CHECKPOINTING → READY | RECOVERING
                              ↓
                         RECOVERING → READY | FAILED
                              ↓
                         COMPLETED → TERMINATED
                         FAILED → TERMINATED | RECOVERING
                         CANCELLED → TERMINATED
```

Transitions validated by `AgentProcess.transition(new_state)` — invalid
transitions raise `ValueError`. Every transition emits
`agent.lifecycle.transition` on the event bus.

## AgentProcessManager

`kernel/core/agent_process_manager.py` bridges kernel `AgentProcess`
with the concrete `AIAgent` runtime (`run_agent.py`).

- `initialize_agent(process)`: creates `AIAgent` (or stub if
  `AETHEROS_KERNEL_REAL_AGENT != 1`), registers runtime, transitions to
  `READY`.
- `execute_task(agent_id, task)`: runs `agent.run_conversation(task)`,
  handles transitions `READY→RUNNING→COMPLETED/FAILED`, emits events,
  records receipts.
- `terminate_agent(process)`: graceful shutdown, resource release,
  `TERMINATED` transition.

## Stub Runtime (default)

`AETHEROS_KERNEL_REAL_AGENT=1` opts into live `AIAgent` (which pulls
credentials, models, tools at startup). Default is an isolated stub
runtime that returns `[stub] <task>` — safe for tests and CI.

```python
if os.getenv("AETHEROS_KERNEL_REAL_AGENT", "0") != "1":
    return _stub("isolated stub runtime")
```

## Delegation

`AuthorityManager.delegate_authority(parent_agent_id, child_agent_id,
intent, parent_grant_id)` enforces:
- Child capabilities ⊆ Parent capabilities
- Child resources ⊆ Parent resources
- Child scopes ⊆ Parent scopes
- No credential inheritance by default
- Delegation depth ≤ `kernel.config.max_agent_depth` (default 5)
- Revocation cascades: revoking parent revokes all descendants