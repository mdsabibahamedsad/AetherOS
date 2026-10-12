# AetherOS Swarm — Architecture (Master 42)

## Substrate reused (not duplicated)

- DAG levels/parallel-groups/cycles/critical-path: `ExecutionGraphEngine`
  (`aetheros_automation/orchestrator/graph.py`).
- Enums + base task/approval shapes: `aetheros_automation/models/models.py`,
  `orchestrator/types.py`.
- Real LLM subagents: `tools/delegate_tool.py` via `DelegateExecutor`
  (lazy import; depth-1 only since delegate blocks recursive delegation).
- Scoped memory + lessons: Master-41 `MemoryService` via
  `integrations.memory41_recall_adapter` and `orchestrator.learn()`.
- Tool availability: `tools/registry.py` check_fn; policy grants in swarm.

## New package `aetheros_swarm/`

| Module | Responsibility |
|---|---|
| models | SwarmTask (budgets, idempotency, verification, lineage), AgentInstance (lifecycle, health), AgentResult contract, AgentMessage, enums |
| registry | 16 roles + capability matching, health/heartbeat |
| decision | single-vs-multi + topology with coordination-cost model |
| decompose | heuristic TaskDecomposer + TopologyEngine (11 patterns) |
| comms | sequenced MessageBus, Blackboard (provenance-required), handoff builder, A2A layer |
| context | task-scoped ContextSelector (verified outputs only cross) |
| budgets | global caps, sub-budgets, reallocation within cap |
| execute | level-scheduled ThreadPool runner, dedup merge, idempotent skip, dependency gate, cancellation |
| recovery | FailureKind classification + strategy table (destructive never blind-retries) |
| verify | oracle/schema/hash/evidence verifiers, review loop, debate judge, ConflictResolver, synthesize (never upgrades), quality_gate |
| ops | checkpoints, approval queue (fail-safe expiry=deny), JSONL audit, tracer/trace-tree, sequenced event stream |
| security | ToolAuthorizer (least privilege, escalation denial), override-attempt scan, secret refusal, data isolation |
| orchestrator | MultiAgentOrchestrator facade + LocalFunctionExecutor + DelegateExecutor |
| integrations | memory41 adapter, evidence claims, role model chains, team compositions |

## Key invariants

- Multi-agent is NOT default: decision engine must prove value (margin 1.5×).
- Synthesis never upgrades unverified → verified (`mixed` otherwise).
- Agent output is data: override attempts blocked + audited.
- Cancellation propagates; checkpoints carry verified work forward.
- Budgets: measured accounting only; reallocation never exceeds global cap.
