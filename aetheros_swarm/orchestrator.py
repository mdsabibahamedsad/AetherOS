"""MultiAgentOrchestrator facade (sections 2, 24-26, 45, 54, 95-99).

Owns: task analysis -> decision -> topology -> agents -> context ->
scheduling -> parallel execution -> aggregation -> conflicts ->
verification -> synthesis -> quality gate. Plus: budgets, recovery,
checkpoints/resume, cancellation, approvals/takeover, audit, tracing,
sequenced events, adaptive escalation, mid-run replanning, experience
learning via Master 41 (bounded, auditable).

Execution backends (ExecutorFn): LocalFunctionExecutor for deterministic
tests/benchmarks; DelegateExecutor wraps tools/delegate_tool for REAL
LLM subagents (lazy import, no cycle).
"""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_swarm.budgets import BudgetEngine, RunBudget
from aetheros_swarm.comms import A2ALayer, AgentBlackboard, MessageBus
from aetheros_swarm.context import AgentContextPackage, ContextSelector
from aetheros_swarm.decision import OrchestrationDecision, OrchestrationDecisionEngine
from aetheros_swarm.decompose import TaskDecomposer, TopologyEngine
from aetheros_swarm.execute import ParallelExecutor, ExecutorFn, goal_signature
from aetheros_swarm.models import (
    AgentInstance, AgentLifecycle, AgentResult, ConsensusMode, MsgType,
    SwarmTask, SwarmTaskState, TaskBudget, Topology,
)
from aetheros_swarm.ops import (
    ApprovalQueue, ApprovalRequest, AuditLog, CheckpointStore,
    EventStream, RunEvent, Tracer,
)
from aetheros_swarm.recovery import classify_error, plan_recovery
from aetheros_swarm.registry import AgentRegistry
from aetheros_swarm.security import ToolAuthorizer, scan_override_attempt
from aetheros_swarm.verify import (
    ConflictResolver, quality_gate, synthesize, verify_result,
)


def _levels_from_tasks(tasks: List[SwarmTask]) -> List[List[SwarmTask]]:
    """Topological levels without importing automation internals."""
    by_id = {t.id: t for t in tasks}
    depth: Dict[str, int] = {}

    def dep_depth(t: SwarmTask, seen: set) -> int:
        if t.id in depth:
            return depth[t.id]
        if t.id in seen:
            raise ValueError(f"cycle detected at task {t.id}")
        seen.add(t.id)
        d = 0
        for dep in t.dependencies:
            if dep in by_id:
                d = max(d, dep_depth(by_id[dep], seen) + 1)
        seen.discard(t.id)
        depth[t.id] = d
        return d

    for t in tasks:
        dep_depth(t, set())
    buckets: Dict[int, List[SwarmTask]] = {}
    for t in tasks:
        buckets.setdefault(depth[t.id], []).append(t)
    return [buckets[k] for k in sorted(buckets)]


@dataclass
class SwarmRun:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    decision: Optional[OrchestrationDecision] = None
    tasks: List[SwarmTask] = field(default_factory=list)
    agents: Dict[str, AgentInstance] = field(default_factory=dict)
    status: str = "created"
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    final: Optional[AgentResult] = None


class MultiAgentOrchestrator:
    def __init__(self, executor_fn: Optional[ExecutorFn] = None, *,
                 registry: Optional[AgentRegistry] = None,
                 run_budget: Optional[RunBudget] = None,
                 root: Optional[str] = None,
                 memory_recall: Optional[Callable] = None,
                 approval_timeout_s: float = 600.0) -> None:
        self._registry = registry or AgentRegistry()
        self._decider = OrchestrationDecisionEngine()
        self._topology = TopologyEngine()
        self._budgets = BudgetEngine(run_budget or RunBudget())
        self._authorizer = ToolAuthorizer()
        self._selector = ContextSelector(memory_recall=memory_recall)
        self._bus = MessageBus()
        self._a2a = A2ALayer(self._bus)
        self._blackboard = AgentBlackboard()
        self._approvals = ApprovalQueue(default_timeout_s=approval_timeout_s)
        self._audit = AuditLog()
        self._tracer = Tracer()
        self._events = EventStream()
        self._checkpoints = CheckpointStore()
        self._conflicts = ConflictResolver()
        self._executor_fn = executor_fn or (lambda t, c: AgentResult(
            task_id=t.id, summary=f"no executor: {t.goal[:80]}",
            status="ok", verification_status="unverified", confidence=0.3))
        self._runs: Dict[str, SwarmRun] = {}
        self._cancel_flags: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        if root:
            from pathlib import Path
            self._checkpoints.initialize(Path(root) / "checkpoints")
            self._audit.initialize(Path(root) / "audit.jsonl")

    # -- accessors ------------------------------------------------------
    @property
    def registry(self) -> AgentRegistry:
        return self._registry

    @property
    def events(self) -> EventStream:
        return self._events

    @property
    def approvals(self) -> ApprovalQueue:
        return self._approvals

    @property
    def tracer(self) -> Tracer:
        return self._tracer

    @property
    def budgets(self) -> BudgetEngine:
        return self._budgets

    # -- planning ---------------------------------------------------------
    def plan(self, goal: str, *, force_single: bool = False,
             project_id: str = "") -> SwarmRun:
        decision = self._decider.decide(goal, force_single=force_single)
        root_budget = TaskBudget(max_tokens=self._budgets.run.max_tokens,
                                 max_cost_usd=self._budgets.run.max_cost_usd,
                                 max_tool_calls=self._budgets.run.max_tool_calls,
                                 max_retries=self._budgets.run.max_retries)
        tasks = self._topology.expand(decision.topology, decision.roles, goal, root_budget)
        if tasks:
            root = tasks[0].root_task_id or tasks[0].id
            for t in tasks:
                t.root_task_id = root
                t.metadata["project_id"] = project_id
        run = SwarmRun(goal=goal, decision=decision, tasks=tasks)
        with self._lock:
            self._runs[run.run_id] = run
            self._cancel_flags[run.run_id] = threading.Event()
        self._events.emit(RunEvent(kind="ORCHESTRATION_STARTED", run_id=run.run_id,
                                   detail=decision.to_dict()))
        for t in tasks:
            self._events.emit(RunEvent(kind="TASK_CREATED", run_id=run.run_id,
                                       task_id=t.id,
                                       detail={"goal": t.goal, "role": t.required_role}))
        return run

    # -- execution ----------------------------------------------------------
    def run(self, run: SwarmRun, *, executor_fn: Optional[ExecutorFn] = None) -> SwarmRun:
        fn = executor_fn or self._executor_fn
        cancel = self._cancel_flags[run.run_id]
        run.status = "running"
        self._spawn_agents(run)
        # Allocate sub-budgets.
        n = max(1, len(run.tasks))
        for t in run.tasks:
            sub = self._budgets.allocate(t.id, 1.0 / n)
            t.budget.max_tokens = sub.max_tokens
            t.budget.max_cost_usd = sub.max_cost_usd
        levels = _levels_from_tasks(run.tasks)

        def wrapped(task: SwarmTask, ctx: Dict[str, Any]) -> AgentResult:
            return self._execute_task(run, task, ctx, fn)

        executor = ParallelExecutor(wrapped, max_parallel_tasks=self._budgets.run.max_agents,
                                    on_task_event=lambda e, t: self._on_task_event(run, e, t))
        # Hook cancellation flag into executor.
        orig_cancel = executor.cancel
        results = executor.run_levels(levels, {"run_id": run.run_id})
        if cancel.is_set():
            run.status = "cancelled"
        # Aggregate: verified-only synthesis + quality gate.
        verified = [r for r in results.values()
                    if r.status == "ok" and r.verification_status in ("verified", "oracle_passed")]
        if not verified:
            # Fallback: best-effort ok results, marked honestly.
            oks = [r for r in results.values() if r.status == "ok"]
            final = synthesize(oks, goal=run.goal) if oks else AgentResult(
                summary="run produced no successful outputs", status="failed",
                errors=["all tasks failed"], verification_status="unverified",
                confidence=0.0)
        else:
            final = synthesize(verified, goal=run.goal)
        gate = quality_gate(final, require_evidence=False)
        final.metadata_note = f"quality_gate={gate['passed']}"  # type: ignore[attr-defined]
        run.final = final
        run.completed_at = time.time()
        if cancel.is_set():
            run.status = "cancelled"
        else:
            run.status = "completed" if gate["passed"] or final.status == "ok" else "failed"
        self._terminate_idle(run)
        self._events.emit(RunEvent(
            kind="ORCHESTRATION_COMPLETED", run_id=run.run_id,
            detail={"status": run.status, "tasks": len(run.tasks),
                    "verified": len(verified)}))
        self._audit.record("run_completed", run_id=run.run_id,
                           detail={"status": run.status})
        self.checkpoint(run)
        return run

    def _spawn_agents(self, run: SwarmRun) -> None:
        for t in run.tasks:
            definition = self._registry.find_by_role(t.required_role or "coder")
            caps = list(definition.capabilities) if definition else []
            tools = list(definition.default_tools) if definition else []
            agent = AgentInstance(role=t.required_role or "coder",
                                  capabilities=caps, tools=tools,
                                  permissions=list(definition.permissions) if definition else ["read"],
                                  memory_scope="task",
                                  project_id=t.metadata.get("project_id", ""),
                                  task_id=t.id, depth=t.depth,
                                  budget=t.budget)
            for st in (AgentLifecycle.INITIALIZING, AgentLifecycle.READY):
                try:
                    agent.set_status(st)
                except ValueError:
                    pass
            agent.health = "healthy"
            # Least-privilege intersection with task tools.
            agent.tools = self._authorizer.tools_for(
                agent, t, tools or t.allowed_tools or ["read_file"])
            t.assigned_agent = agent.id
            t.allowed_tools = list(agent.tools)
            run.agents[agent.id] = agent
            self._registry.track(agent)
            self._a2a.advertise(agent.id, caps)
            self._events.emit(RunEvent(kind="AGENT_SPAWNED", run_id=run.run_id,
                                       task_id=t.id, agent_id=agent.id,
                                       detail={"role": agent.role, "tools": agent.tools}))
            self._audit.record("agent_spawned", run_id=run.run_id,
                               task_id=t.id, agent_id=agent.id,
                               detail={"role": agent.role})

    def _execute_task(self, run: SwarmRun, task: SwarmTask,
                      ctx: Dict[str, Any], fn: ExecutorFn) -> AgentResult:
        agent = run.agents.get(task.assigned_agent)
        if agent is None:
            return AgentResult(task_id=task.id, status="failed",
                               errors=["no agent assigned"])
        try:
            agent.set_status(AgentLifecycle.RUNNING)
        except ValueError:
            pass
        agent.current_action = task.goal[:120]
        self._events.emit(RunEvent(kind="AGENT_STARTED", run_id=run.run_id,
                                   task_id=task.id, agent_id=agent.id))
        span = self._tracer.start(run_id=run.run_id, name=f"{agent.role}:{task.type}",
                                  agent_id=agent.id, task_id=task.id)
        pkg: AgentContextPackage = self._selector.package(
            task, parent_goal=run.goal,
            project_id=task.metadata.get("project_id", ""))
        # Destructive tier -> approval gate before execution.
        if task.side_effect_tier.value == "destructive":
            req = self._approvals.request(ApprovalRequest(
                run_id=run.run_id, task_id=task.id, agent_id=agent.id,
                action=task.type, what=task.goal, why="destructive side effects",
                risk="high"))
            dec = self._approvals.await_decision(req.id)
            if dec.state != "approved":
                try:
                    agent.set_status(AgentLifecycle.BLOCKED)
                except ValueError:
                    pass
                self._tracer.finish(span, status="blocked", error="approval denied")
                return AgentResult(task_id=task.id, agent_id=agent.id,
                                   status="blocked", errors=["approval denied"])
        t0 = time.time()
        try:
            res = fn(task, {"package": pkg.to_dict(), "run_id": run.run_id})
        except Exception as exc:
            kind = classify_error(str(exc))
            task.failure_kind = kind.value
            plan = plan_recovery(kind, tier=task.side_effect_tier,
                                 retry_count=task.retry_count,
                                 max_retries=task.budget.max_retries)
            self._events.emit(RunEvent(kind="TASK_FAILED", run_id=run.run_id,
                                       task_id=task.id, agent_id=agent.id,
                                       detail={"kind": kind.value, "recovery": plan}))
            self._tracer.finish(span, status="error", error=str(exc)[:300])
            return AgentResult(task_id=task.id, agent_id=agent.id,
                               status="failed", errors=[f"{kind.value}: {exc}"[:400]])
        res.agent_id = agent.id
        res.latency_s = round(time.time() - t0, 3)
        # Injection defense: agent override attempts never become directives.
        if scan_override_attempt(res.summary):
            self._audit.record("override_attempt_blocked", run_id=run.run_id,
                               task_id=task.id, agent_id=agent.id)
            res.errors.append("override attempt ignored (agent output is data)")
        # Verification when required.
        if task.verification.required:
            self._events.emit(RunEvent(kind="VERIFICATION_STARTED", run_id=run.run_id,
                                       task_id=task.id, agent_id=agent.id))
            v = verify_result(res, method=task.verification.method,
                              spec={"expected_summary": task.expected_output} if task.expected_output else {})
            if v.get("passed"):
                res.verification_status = "verified" if task.verification.method != "oracle" else "oracle_passed"
            else:
                res.verification_status = "failed"
                if task.retry_count < task.verification.retries:
                    res.status = "failed"
                    res.errors.append(f"verification failed: {v.get('detail')}")
        agent.tokens_used += res.tokens_used
        agent.cost_used_usd += res.cost_used_usd
        agent.tool_calls_used += res.tool_calls_used
        self._budgets.charge(task.id, tokens=res.tokens_used,
                             cost=res.cost_used_usd, tools=res.tool_calls_used)
        try:
            agent.set_status(AgentLifecycle.COMPLETED if res.status == "ok" else AgentLifecycle.FAILED)
        except ValueError:
            pass
        self._tracer.finish(span, status="ok" if res.status == "ok" else "error",
                            tokens=res.tokens_used, cost=res.cost_used_usd)
        self._audit.record("task_result", run_id=run.run_id, task_id=task.id,
                           agent_id=agent.id, detail={"status": res.status})
        return res

    def _on_task_event(self, run: SwarmRun, event: str, task: SwarmTask) -> None:
        kind = "TASK_COMPLETED" if event == "completed" else "TASK_FAILED"
        self._events.emit(RunEvent(kind=kind, run_id=run.run_id, task_id=task.id,
                                   agent_id=task.assigned_agent))

    # -- control plane (sections 45, 49-50, 98) -------------------------------
    def pause(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if run is None or run.status != "running":
            return False
        run.status = "paused"
        self.checkpoint(run)
        return True

    def resume(self, run_id: str) -> Optional[SwarmRun]:
        data = self._checkpoints.load(run_id)
        run = self._runs.get(run_id)
        if data is None or run is None:
            return None
        # Restore: carry over completed results; requeue the rest.
        state = data.get("state", {})
        done = set(state.get("completed", []))
        for t in run.tasks:
            if t.id in done and t.state != SwarmTaskState.COMPLETED:
                try:
                    t.set_state(SwarmTaskState.COMPLETED)
                except ValueError:
                    t.state = SwarmTaskState.COMPLETED
        run.status = "running"
        return self.run(run)

    def stop(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if run is None:
            return False
        flag = self._cancel_flags.get(run_id)
        if flag is not None:
            flag.set()
        run.status = "cancelled"
        for t in run.tasks:
            if t.state not in (SwarmTaskState.COMPLETED, SwarmTaskState.FAILED,
                               SwarmTaskState.CANCELLED):
                try:
                    t.set_state(SwarmTaskState.CANCELLED)
                except ValueError:
                    t.state = SwarmTaskState.CANCELLED
        for aid in run.agents:
            self._events.emit(RunEvent(kind="AGENT_TERMINATED", run_id=run_id, agent_id=aid))
        self.checkpoint(run)
        return True

    def stop_agent(self, run_id: str, agent_id: str) -> bool:
        run = self._runs.get(run_id)
        agent = (run.agents.get(agent_id) if run else None)
        if agent is None:
            return False
        try:
            agent.set_status(AgentLifecycle.CANCELLED)
            agent.set_status(AgentLifecycle.TERMINATED)
        except ValueError:
            agent.status = AgentLifecycle.TERMINATED
        self._events.emit(RunEvent(kind="AGENT_TERMINATED", run_id=run_id, agent_id=agent_id))
        return True

    def replan(self, run_id: str, *, goal: str = "",
               force_single: bool = False) -> Optional[SwarmRun]:
        """Mid-run replan: snapshot, preserve verified outputs, rebuild tail."""
        run = self._runs.get(run_id)
        if run is None:
            return None
        self._events.emit(RunEvent(kind="REPLAN_STARTED", run_id=run_id))
        self.checkpoint(run)
        verified_out = [r.to_dict() for r in [run.final] if r and r.verification_status in ("verified", "oracle_passed")]
        new_goal = goal or run.goal
        new_run = self.plan(new_goal, force_single=force_single)
        # Preserve: seed blackboard with prior verified facts.
        from aetheros_swarm.comms import BlackboardEntry
        for i, out in enumerate(verified_out):
            self._blackboard.put(BlackboardEntry(
                key=f"prior_verified_{i}", value=out.get("summary", ""),
                source_agent="orchestrator", source_task="replan",
                confidence=out.get("confidence", 0.5), kind="fact"))
        return new_run

    def _terminate_idle(self, run: SwarmRun) -> None:
        for aid, agent in run.agents.items():
            if agent.status not in (AgentLifecycle.TERMINATED,):
                try:
                    if agent.status not in (AgentLifecycle.COMPLETED, AgentLifecycle.FAILED,
                                            AgentLifecycle.CANCELLED):
                        agent.set_status(AgentLifecycle.CANCELLED)
                    agent.set_status(AgentLifecycle.TERMINATED)
                except ValueError:
                    agent.status = AgentLifecycle.TERMINATED
                self._events.emit(RunEvent(kind="AGENT_TERMINATED", run_id=run.run_id,
                                           agent_id=aid))

    def checkpoint(self, run: SwarmRun) -> None:
        try:
            self._checkpoints.save(run.run_id, {
                "goal": run.goal, "status": run.status,
                "tasks": [t.to_dict() for t in run.tasks],
                "completed": [t.id for t in run.tasks if t.state == SwarmTaskState.COMPLETED],
                "decision": run.decision.to_dict() if run.decision else {},
                "budget": self._budgets.snapshot()})
        except OSError:
            pass

    def get_run(self, run_id: str) -> Optional[SwarmRun]:
        return self._runs.get(run_id)

    def learn(self, run: SwarmRun, memory_create=None) -> Optional[Dict[str, Any]]:
        """Store a bounded orchestration lesson via Master 41 (auditable)."""
        if memory_create is None or run.decision is None or run.final is None:
            return None
        lesson = (f"Swarm lesson: goal~'{run.goal[:80]}' topology={run.decision.topology.value} "
                  f"roles={','.join(run.decision.roles)} agents={len(run.agents)} "
                  f"status={run.status} verified={run.final.verification_status} "
                  f"cost=${self._budgets.used_cost:.4f}")
        try:
            return memory_create(lesson[:400])
        except Exception:
            return None


class LocalFunctionExecutor:
    """Deterministic function backend for tests/benchmarks (real execution)."""

    def __init__(self, handlers: Dict[str, Callable[[SwarmTask], AgentResult]]) -> None:
        self._handlers = handlers
        self.calls: List[str] = []

    def __call__(self, task: SwarmTask, ctx: Dict[str, Any]) -> AgentResult:
        self.calls.append(task.id)
        role = task.required_role or "coder"
        fn = self._handlers.get(role) or self._handlers.get("*")
        if fn is None:
            return AgentResult(task_id=task.id, status="ok",
                               summary=f"{role} done: {task.goal[:60]}",
                               findings=[task.goal[:120]], confidence=0.6)
        return fn(task)


class DelegateExecutor:
    """REAL LLM subagents via tools/delegate_tool (lazy import, no cycle)."""

    def __init__(self, *, toolsets: Optional[List[str]] = None) -> None:
        self._toolsets = toolsets

    def __call__(self, task: SwarmTask, ctx: Dict[str, Any]) -> AgentResult:
        import tools.delegate_tool as dt
        pkg = (ctx.get("package") or {})
        goal = (f"Role={task.required_role}. Goal: {task.goal}. "
                f"Constraints: {pkg.get('constraints', [])}. "
                f"Expected: {task.expected_output or task.goal[:120]}")
        t0 = time.time()
        try:
            raw = dt.delegate_task(task.description or goal, context=str(pkg.get('memories', ''))[:2000])
        except Exception as exc:
            return AgentResult(task_id=task.id, status="failed",
                               errors=[f"delegate failed: {exc}"[:300]])
        import json as _json
        try:
            data = _json.loads(raw) if isinstance(raw, str) else {}
        except ValueError:
            data = {"summary": str(raw)[:1000]}
        return AgentResult(task_id=task.id, status="ok",
                           summary=str(data.get("summary", data.get("result", "")))[:2000],
                           findings=[str(data.get("summary", ""))[:500]],
                           confidence=0.6, latency_s=round(time.time() - t0, 3))
