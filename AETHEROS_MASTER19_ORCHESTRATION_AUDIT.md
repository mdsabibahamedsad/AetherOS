# AETHEROS MASTER 19 — ORCHESTRATION AUDIT (Phase 0)

Date: 2026-08-24 · Read-only; no code modified in this phase.
Purpose: inventory everything multi-agent/orchestration-related so Master 19
composes existing machinery instead of duplicating it (hard rule 14).

---

## 1. Existing architecture

### 1.1 `agent/orchestration/` — prior orchestration layer (imports cleanly; 218 exports; 26 basic tests green)
| Module | Provides |
|---|---|
| `types.py` | TaskStatus (14 states incl. QUEUED/WAITING/BLOCKED/VERIFYING/REQUIRES_APPROVAL/TIMEOUT), TaskPriority, AgentRole (14 roles), AgentHealthStatus/LifecycleState, ApprovalAction (12 kinds), RiskLevel (LOW/MED/HIGH/CRITICAL), FailureType (11 kinds), ValidationOperator/Rule, AgentIdentity/Version/Capabilities/Metadata/Health, TaskSpec/TaskBudget/TaskResult/TaskGraph/TaskNode, ExecutionState, AgentMessage, HandoffContext, Checkpoint, Plan, VerificationReport, ApprovalRequest, BudgetSnapshot + can_transition/is_terminal |
| `agent_interface.py` | AgentInterface Protocol + Supports* protocols (Planning/Handoff/Verification/Checkpointing/Streaming/Parallelism/ModelSelection/SkillSelection/ToolSelection/Memory/Multimodal), AgentAdapter, adapt_* helpers; references `adapters/` |
| `adapters/` | core_agent_adapter (wraps AIAgent), automation_agent_adapter (aetheros_automation), delegate_adapter (tools/delegate_tool) |
| `agent_registry.py` | AgentRegistration/AgentInstance/AgentRegistry + singleton |
| `router.py` / `selection.py` | CapabilityRouter (BestMatch/LeastLoaded/RoundRobin/CostOptimized/LatencyOptimized), UnifiedSelector (Agent/Model/Skill/Tool selectors) |
| `health.py` | HealthCheck categories + liveness/readiness/model/tool/resource/permissions/dependency checks, HealthAwareRouter |
| `decomposition.py` | RuleBasedDecomposer, LLMDecomposer, HybridDecomposer, RecursiveDecomposer, CapabilityInference, SubtaskSpec |
| `task_graph.py` | TaskGraphManager, ExecutionScheduler (GraphExecutionMode), CycleDetectedError, mermaid/graphviz export |
| `task_lifecycle.py` | transition table, LifecycleEvent(s), TaskStateMachine |
| `handoff.py` | HandoffRequest/Result, Sequential/Parallel/Conditional/Escalation/Review/Fallback handoffs, ContextPackager, **ContextIsolator** (allowlist key isolation) |
| `verification.py` | VerificationCriteria/Evidence/Level/Type, VerificationAgent, VerificationOrchestrator, CodingVerifier, ResearchVerifier, BrowserVerifier |
| `approval.py` | ApprovalScope (SINGLE_USE/TASK/SESSION/ALWAYS), ApprovalStatus (**incl. EXPIRED**), ApprovalPolicy (risk gate, expiration_hours, allowed_responders), ApprovalManager (async), DryRunExecutor/ActionPreview |
| `budget.py` | BudgetLimit/Usage/Manager, CostController, RateLimiter (token bucket), ConcurrencyController, RecursionController (max_depth/max_total_tasks), LoopDetector, BudgetController facade |
| `observability.py` | OrchestrationEventType (~40 events), EventStore/Emitter, ProgressTracker, TaskTimeline/Inspector, ExplanationGenerator |
| `queue.py` | TaskQueue (PRIORITY/FIFO), BackgroundTaskQueue, ScheduledTaskQueue, QueueManager |
| `recovery.py` | RecoveryStrategy, RetryPolicy, FallbackConfig/Handler, StallDetector+Config, DeadlineManager, **CheckpointManager (file-backed under ~/.aetheros/checkpoints)**, CrashRecovery, RecoveryOrchestrator, PauseResumeManager, CancellationManager |
| `state.py` | StateBackend, StateStore, Task/Plan/OrchestrationStateManager |
| `planner.py` | PlanValidator (+issues), PlanVersionManager, AdaptiveReplanner, PlanningEngine |
| `integration.py` | OrchestrationLayer facade + singleton |

### 1.2 Other orchestration stacks
- `tools/delegate_tool.py` — production delegation: `_run_single_child`, spawn
  pause (`set_spawn_paused`), MAX_DEPTH=1 default via
  `delegation.max_spawn_depth`, `_DEFAULT_MAX_CONCURRENT_CHILDREN=3`
  (`delegation.max_concurrent_children`), subagent approval callback gated by
  `delegation.subagent_auto_approve` (default deny).
- `aetheros_automation/orchestrator/` — TaskOrchestrator(40k), planner(36k),
  agent_engine, execution_engine, store, approvals, checkpoint, recovery,
  routing, security, validation, templates, graph, limits.
- `aetheros_automation/multi_agent/` — small collaboration/messaging/
  sub_agent_manager modules.
- Kanban dispatcher/workers (board isolation via `AETHEROS_KANBAN_BOARD`),
  cron scheduler (job store + tick loop).

### 1.3 Security/approval/safety primitives to reuse
- `agent/research/approval_gate.py` (M17 fail-closed consequential-action gate),
  gateway approval round-trip, `acp_adapter/edit_approval.py`+
  `permissions.py`, command-approval doctrine.
- `agent/memory_os/security.py` (M18): secret patterns, injection patterns,
  AccessContext/actor kinds, read-authorization predicate — directly reusable
  for swarm message/handoff guarding.
- `aetheros_actions`: session-level **EMERGENCY_STOP** signal +
  `manager.emergency_stop_all()`; computer-use confirmation layers.
- `tools/url_safety.py`, `tools/website_policy.py`, tool registry `check_fn`
  gating, terminal environment backends (local/docker/ssh/modal/daytona/…).

### 1.4 Memory/research/computer-use (integration targets)
- M18 `agent/memory_os` MemoryManager + AccessContext (scopes, sensitivity,
  allow_agents) — authorized memory scopes for agents.
- M17 research engine + `agents.py` role prompts + multiprovider
  FanOutSearch/FallbackChain — research swarm substrate.
- Master 15 `aetheros_computer` pattern_memory/task_checkpoint/knowledge_bridge.

### 1.5 Existing tests
- `tests/orchestration/test_orchestration_basic.py` (26 passing),
  root-level scratch files test_router.py/test_planner.py,
  delegate tests under `tests/tools/test_delegate*.py`,
  kanban tests, automation orchestrator tests under
  `tests/aetheros_automation/`, stress scripts under `tests/stress/`.

## 2. Missing functionality (gaps this master closes)
1. **Shared blackboard** (P19) — task-scoped artifacts/facts/decisions/warnings.
2. **Artifact store with versioning/provenance/hash** (P20-21).
3. **Agent result contract completeness** (P22): summary/confidence/
   verification_needed as first-class fields.
4. **Critic agent** deliverable (P25) and **consensus/disagreement engine**
   with AGREEMENT/DISAGREEMENT/PARTIAL_AGREEMENT/INSUFFICIENT_EVIDENCE (P28-29).
5. **Confidence separation** result/evidence/verification/conclusion (P30).
6. **Research swarm / memory / computer-use bridges** into the orchestration
   layer (P31-34) — adapters exist only for core-agent/delegate/automation.
7. **Circuit breaker** (P46) — retry/backoff/stall exist; breaker does not.
8. **Idempotency keys** (P51) and explicit side-effect classification map to
   approval actions (P52).
9. **Swarm security guards**: runtime capability enforcement at assignment/use,
   message-injection scanning, cross-agent exfiltration guard, secret boundary
   (P74-79) — ContextIsolator covers key-allowlists only.
10. **Specialist catalog**: 15 named specialist manifests bound to real
    capabilities/adapters + risk derived from capabilities (P3, P6, P63-65).
11. **Performance/reputation stats** as routing-only signals (P66-67).
12. **Chaos harness** (P94) and golden scenarios/red-team suites (P91, P95).
13. **Emergency-stop bridge** to the orchestration pause/cancel managers (P85).

## 3. Duplicate functionality (avoid creating more)
Three orchestration stacks exist (`agent/orchestration`,
`aetheros_automation/orchestrator(+multi_agent)`, kanban/cron flows). Master 19
extends `agent/orchestration` only; no fourth stack, no new DB (JSON
checkpoints/blackboards under `get_aetheros_home()/swarm/` where persistence
is required).

## 4. Integration points
delegate_tool knobs ↔ budget/spawn guards; memory_os AccessContext ↔ blackboard
sharing/exfil guard; research engine ↔ ResearchAgent adapter; aetheros_computer
↔ ComputerUseAgent adapter; approval.py ↔ side-effect classifier;
PauseResume/CancellationManager ↔ emergency stop flag; observability EventStore
↔ new swarm events; CheckpointManager (file-backed) ↔ resume tests.

## 5. Known quirks to respect
- `memory_integration.py` calls sync APIs as async → always falls into except
  path (dead); replace usage rather than fix in place.
- Root-level `test_router.py`/`test_planner.py` are scratch scripts, not part
  of the suite.
- TaskStatus names differ from P10 wording (PENDING≈CREATED, READY≈PLANNED);
  mapping documented instead of mutating the load-bearing transition table.
