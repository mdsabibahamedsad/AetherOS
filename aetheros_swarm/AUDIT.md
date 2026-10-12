"""Master 42 audit: existing orchestration architecture (source of truth).

Reusable (extended, not duplicated):
- aetheros_automation/orchestrator/graph.py::ExecutionGraphEngine — DAG
  levels, parallel groups, cycle detection, critical path, mermaid viz.
- aetheros_automation/models/models.py — TaskStatus, AgentRole,
  GraphExecutionMode, FailureType, ApprovalAction/Response, Permission,
  Task, ApprovalRequest, AgentContext.
- aetheros_automation/orchestrator/types.py — OrchestrationTask,
  AgentMessage (base), AgentAssignment, OrchestrationPlan, ExecutionState.
- aetheros_automation/{orchestrator/{checkpoint,recovery,memory,routing,
  security,approvals},approvals/} — checkpoint/recovery/memory-routing/
  security/approval substrate.
- tools/delegate_tool.py — REAL subagent spawning (AIAgent children,
  isolated context, restricted toolsets, ThreadPool, approval callbacks).
- Master 41 aetheros_memory_intelligence.service.MemoryService — scoped
  retrieval, project memory, experience lessons, provenance.
- tools/registry.py + MCP — tool discovery; check_fn = availability.
- Desktop apps/desktop/src/app/task-orchestrator/ — plan/execution-graph/
  approval/checkpoint/activity views.
- plugins/kanban — durable multi-worker dispatch loop pattern.

Missing (built new in aetheros_swarm/):
- Canonical swarm Task/AgentInstance with budgets, idempotency keys,
  verification policy, lineage (parent/root/depth).
- AgentRegistry (capability-driven, health) + 16 Master-42 roles.
- Single-vs-multi decision engine with coordination-cost model.
- TaskDecomposer (heuristic DAG builder) + topology engine (11 patterns).
- Parallel level-scheduled executor with cancellation/timeouts.
- Typed message bus + blackboard + structured handoff + A2A layer.
- Context packaging with provenance + isolation (memory-scoped).
- Budget engine (sub-budgets, reallocation within global cap).
- Typed failure recovery, idempotency enforcement, side-effect tiers.
- Review/verify/debate/conflict/synthesis/quality-gate loop.
- Checkpoint persist/restore, pause/resume, cancellation propagation.
- Approval queue + user takeover ops; immutable audit log; tracing/metrics;
  sequenced event stream.
- Least-privilege tool authorization, escalation/injection defenses,
  secret + data isolation.
- swarm.* agent tools + gateway IPC + Swarm Center UI.
- Deterministic oracle-based benchmarks (no LLM-judge-only certification).

Migration risks: delegate_tool blocks recursive delegation
(DELEGATE_BLOCKED_TOOLS removes delegate_task) — swarm hierarchy above
depth 1 uses the swarm executor, not nested delegate_task calls. The
swarm package lazy-imports delegate_tool to avoid import cycles.
"""
