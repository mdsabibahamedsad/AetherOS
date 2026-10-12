"""SwarmOrchestrator — synchronous, deterministic multi-agent execution
engine (P8-P14, P43-62, P84-87, P91).

Composes existing primitives instead of duplicating them: types/lifecycle
transitions, swarm_guards capability enforcement, catalog manifests,
blackboard/artifacts, synthesis validation, memory_os secret/injection
scanners. Execution is thread-based for independent-ready nodes; ordering
constraints stay sequential by construction.

Design stance: MAXIMUM USEFUL AUTONOMY WITH MINIMUM UNCONTROLLED RISK —
the orchestrator grants nothing an agent cannot prove a manifest for, and
completion is computed from verification facts, never claimed.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agent.orchestration.circuit_breaker import BreakerOpen, CircuitBreaker
from agent.orchestration.consensus import (
    CandidateResult,
    ConsensusOutcome,
    compare_results,
)
from agent.orchestration.swarm_guards import (
    CapabilityViolation,
    ExecutionIdentity,
    ExfiltrationBlocked,
    GrantedCapabilities,
    ImpersonationBlocked,
    SecretBoundaryViolation,
    check_handoff_payload,
    risk_from_capabilities,
)
from agent.orchestration.synthesis import (
    FinalStatus,
    FinalValidation,
    SynthesisResult,
    synthesize,
    validate_completion,
)
from agent.orchestration.types import FailureType, RiskLevel, TaskResult


# ---------------------------------------------------------------------------
# Side-effect model + approvals (P52-55)
# ---------------------------------------------------------------------------

class SideEffect:
    READ = "READ"
    ANALYZE = "ANALYZE"
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    DELETE = "DELETE"
    SEND = "SEND"
    PUBLISH = "PUBLISH"
    PURCHASE = "PURCHASE"
    EXECUTE = "EXECUTE"
    INSTALL = "INSTALL"
    DEPLOY = "DEPLOY"


#: P52/P53 — which side effects require human approval through the board.
CONSEQUENTIAL_EFFECTS = frozenset({
    SideEffect.DELETE, SideEffect.SEND, SideEffect.PUBLISH,
    SideEffect.PURCHASE, SideEffect.EXECUTE, SideEffect.INSTALL,
    SideEffect.DEPLOY,
})


@dataclass
class ApprovalGrant:
    request_id: str
    action: str
    task_id: str
    requested_by: str
    approved_by: str = ""
    approved_at: float = 0.0
    expires_at: float = 0.0
    scope: str = "single_use"
    used_count: int = 0

    def usable(self, at: float, *, action: str = "", task_id: str = "") -> bool:
        if self.approved_by == "":
            return False
        if at >= self.expires_at:
            return False                       # P55: expiry is binding
        if self.scope == "single_use" and self.used_count > 0:
            return False
        if action and self.action != action:
            return False
        if task_id and self.task_id != task_id:
            return False
        return True


class ApprovalBoard:
    """Fail-closed approval boundary (P53). Agents cannot self-approve."""

    def __init__(self, default_ttl_seconds: float = 3600.0):
        self.default_ttl = default_ttl_seconds
        self._grants: Dict[str, ApprovalGrant] = {}
        self._lock = threading.Lock()

    def request(self, *, action: str, task_id: str, requested_by: str) -> str:
        rid = uuid.uuid4().hex[:12]
        grant = ApprovalGrant(
            request_id=rid, action=action, task_id=task_id,
            requested_by=requested_by,
            expires_at=time.time() + self.default_ttl,
        )
        with self._lock:
            self._grants[rid] = grant
        return rid

    def decide(self, request_id: str, *, approved_by: str,
               approve: bool, ttl_seconds: Optional[float] = None) -> bool:
        with self._lock:
            g = self._grants.get(request_id)
            if g is None or approved_by == "":
                return False
            if not approve:
                g.approved_by = ""
                g.expires_at = 0.0
                return False
            g.approved_by = approved_by
            g.approved_at = time.time()
            g.expires_at = time.time() + (ttl_seconds
                                          if ttl_seconds is not None
                                          else self.default_ttl)
            return True

    def authorize(self, *, action: str, task_id: str,
                  requester: str, at: Optional[float] = None) -> bool:
        """Fail-closed check used before any consequential effect."""
        at = at if at is not None else time.time()
        with self._lock:
            for g in self._grants.values():
                if (g.action == action and g.task_id == task_id
                        and g.requested_by == requester
                        and g.usable(at, action=action, task_id=task_id)):
                    g.used_count += 1
                    return True
        return False

    def pending(self) -> List[str]:
        with self._lock:
            return [rid for rid, g in self._grants.items()
                    if g.approved_by == "" and g.expires_at > time.time()]


# ---------------------------------------------------------------------------
# Budgets (P56-58) + spawn protection (P59-61)
# ---------------------------------------------------------------------------

@dataclass
class NodeBudget:
    max_time_seconds: float = 600.0
    max_tool_calls: int = 25
    max_network_calls: int = 25
    max_files_changed: int = 5
    spent_tool_calls: int = 0
    spent_network_calls: int = 0
    spent_files_changed: int = 0
    started_at: float = 0.0

    def consume(self, *, tool_calls: int = 1, network_calls: int = 0,
                files_changed: int = 0, at: Optional[float] = None) -> bool:
        at = at if at is not None else time.time()
        if self.started_at and at - self.started_at > self.max_time_seconds:
            raise _BudgetExceeded("time")
        if self.spent_tool_calls + tool_calls > self.max_tool_calls:
            raise _BudgetExceeded("tool_calls")
        if self.spent_network_calls + network_calls > self.max_network_calls:
            raise _BudgetExceeded("network")
        if self.spent_files_changed + files_changed > self.max_files_changed:
            raise _BudgetExceeded("files")
        self.spent_tool_calls += tool_calls
        self.spent_network_calls += network_calls
        self.spent_files_changed += files_changed
        return True


class _BudgetExceeded(RuntimeError):
    pass


@dataclass
class GlobalBudget:
    """P57 — children draw down a parent-owned pool; never exceed it."""

    total_tool_calls: int = 200
    remaining_tool_calls: int = 200
    allocations: Dict[str, int] = field(default_factory=dict)

    def allocate(self, node_key: str, amount: int) -> bool:
        if amount > self.remaining_tool_calls:
            return False
        self.remaining_tool_calls -= amount
        self.allocations[node_key] = self.allocations.get(node_key, 0) + amount
        return True

    def release_unused(self, node_key: str) -> int:
        """P58 — only the ORCHESTRATOR rebalances unused allocation."""
        amt = self.allocations.pop(node_key, 0)
        self.remaining_tool_calls += amt
        return amt


# ---------------------------------------------------------------------------
# Task nodes / results
# ---------------------------------------------------------------------------

@dataclass
class SwarmNode:
    node_key: str
    objective: str
    agent_id: str
    required_capabilities: frozenset
    side_effects: frozenset
    success_criteria: List[str]
    depends_on: List[str]
    budget: NodeBudget
    priority: int = 2                 # P68: 0=CRITICAL .. 4=BACKGROUND
    deadline_seconds: Optional[float] = None
    requires_verification: bool = False
    idempotency_key: str = ""

    # runtime
    status: str = "CREATED"           # P10 subset mapped onto orchestration flow
    attempts: int = 0
    result: Optional[TaskResult] = None
    failure: str = ""
    failure_kind: FailureType = FailureType.UNKNOWN
    verified: bool = False
    completed_at: float = 0.0

    @property
    def terminal(self) -> bool:
        return self.status in ("COMPLETED", "FAILED", "CANCELLED")


def _idem(objective: str, criteria: List[str]) -> str:
    blob = json.dumps([objective, sorted(criteria)], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def classify_exception(exc: BaseException) -> FailureType:
    """Map raw executor exceptions to failure classes (P47).

    Ordering matters: auth/policy/security shapes must win over the broad
    OSError family (PermissionError IS an OSError).
    """
    import socket

    if isinstance(exc, TimeoutError):
        return FailureType.TIMEOUT
    if isinstance(exc, PermissionError):
        return FailureType.PERMISSION_DENIED
    text = f"{type(exc).__name__}: {exc}".lower()
    if "unauthorized" in text or "forbidden" in text \
            or "authorization" in text or "auth_error" in text:
        return FailureType.PERMISSION_DENIED
    if "policy" in text:
        return FailureType.POLICY_ERROR
    if "security" in text:
        return FailureType.SECURITY_ERROR
    if isinstance(exc, (ConnectionError, OSError, socket.timeout)):
        return FailureType.NETWORK_ERROR
    if "rate limit" in text or "ratelimit" in text or "429" in text:
        return FailureType.RATE_LIMIT
    if "provider" in text:
        return FailureType.PROVIDER_ERROR
    return FailureType.AGENT_ERROR


ExecutorFn = Callable[[Dict[str, Any]], TaskResult]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class SwarmOrchestrator:
    """Synchronous orchestrator with thread-parallel fan-out of independent
    ready nodes."""

    def __init__(
        self,
        executors: Dict[str, ExecutorFn],
        *,
        max_parallel: int = 3,
        max_depth: int = 3,
        max_agents_per_task: int = 8,
        global_budget: Optional[GlobalBudget] = None,
        approval_board: Optional[ApprovalBoard] = None,
        checkpoint_dir: Optional[str] = None,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self.executors = executors
        self.max_parallel = max_parallel
        self.max_depth = max_depth
        self.max_agents_per_task = max_agents_per_task
        self.global_budget = global_budget or GlobalBudget()
        self.approvals = approval_board or ApprovalBoard()
        self.sleeper = sleeper
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.events: List[Tuple[float, str, Dict[str, Any]]] = []
        self.nodes: Dict[str, SwarmNode] = {}
        self.order: List[str] = []
        self.emergency_stopped = False
        self.cancelled = False
        self._identities: Dict[str, ExecutionIdentity] = {}
        self._active_agents = 0
        self._checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None
        if self._checkpoint_dir:
            self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.reputation: Dict[str, Dict[str, int]] = {}

    # -- events / trace (P80-82) -------------------------------------------------

    def _emit(self, kind: str, **detail: Any) -> None:
        self.events.append((time.time(), kind, detail))

    def trace(self) -> List[str]:
        return [f"{t:.3f} {k} {json.dumps(d, default=str, sort_keys=True)}"
                for t, k, d in self.events]

    # -- planning (P8-11) ----------------------------------------------------------

    def add_node(
        self,
        node_key: str,
        *,
        objective: str,
        agent_id: str,
        required_capabilities: Set[str],
        side_effects: Set[str] = (),
        success_criteria: Optional[List[str]] = None,
        depends_on: Optional[List[str]] = None,
        budget: Optional[NodeBudget] = None,
        priority: int = 2,
        deadline_seconds: Optional[float] = None,
        requires_verification: Optional[bool] = None,
    ) -> SwarmNode:
        caps = frozenset(required_capabilities)
        effects = frozenset(side_effects)
        risk = risk_from_capabilities(caps | set())
        needs_verify = requires_verification
        if needs_verify is None:
            needs_verify = risk.value in ("high", "critical")
        node = SwarmNode(
            node_key=node_key,
            objective=objective,
            agent_id=agent_id,
            required_capabilities=caps,
            side_effects=effects,
            success_criteria=list(success_criteria or []),
            depends_on=list(depends_on or []),
            budget=budget or NodeBudget(),
            priority=priority,
            deadline_seconds=deadline_seconds,
            requires_verification=needs_verify,
            idempotency_key=_idem(objective, list(success_criteria or [])),
        )
        self.nodes[node_key] = node
        self.order.append(node_key)
        self._emit("task_created", node=node_key, agent=agent_id,
                   risk=risk.value)
        return node

    def ready_set(self) -> List[SwarmNode]:
        out = []
        for key in self.order:
            n = self.nodes[key]
            if n.status != "CREATED":
                continue
            if all(self.nodes[d].status == "COMPLETED"
                   for d in n.depends_on):
                out.append(n)
        out.sort(key=lambda x: x.priority)
        return out

    # -- spawn protection (P59-61) ---------------------------------------------------

    def spawn_child(self, parent_identity: ExecutionIdentity,
                    *, child_agent: str, child_execution: str,
                    task_id: str, parent_depth: int) -> ExecutionIdentity:
        if self.emergency_stopped:
            raise RuntimeError("emergency stop active: no new agents")
        if self._active_agents + 1 > self.max_agents_per_task:
            raise RuntimeError(f"swarm size cap {self.max_agents_per_task} reached")
        child = ExecutionIdentity(
            agent_id=child_agent,
            execution_id=child_execution,
            parent_execution_id=parent_identity.execution_id,
            task_id=task_id,
            user_context=parent_identity.user_context,
        )
        parent_identity.validate_child(child, max_depth=self.max_depth,
                                       parent_depth=parent_depth)
        self._identities[child.execution_id] = child
        self._emit("agent_spawned", agent=child_agent,
                   execution=child.execution_id, depth=parent_depth + 1)
        return child

    # -- checkpoint / resume (P49-51) ---------------------------------------------------

    def checkpoint(self) -> Optional[str]:
        if not self._checkpoint_dir:
            return None
        payload = {
            "nodes": {
                k: {
                    "status": n.status,
                    "attempts": n.attempts,
                    "failure": n.failure,
                    "verified": n.verified,
                    "summary": (n.result.summary if n.result else ""),
                    "success": bool(n.result and n.result.success),
                } for k, n in self.nodes.items()
            },
            "order": list(self.order),
            "cancelled": self.cancelled,
        }
        fd, tmp = tempfile.mkstemp(dir=str(self._checkpoint_dir))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            path = self._checkpoint_dir / f"swarm-{int(time.time()*1000)}.json"
            os.replace(tmp, path)
            return str(path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            return None

    def restore(self, path: str) -> bool:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        changed = False
        for key, snap in data["nodes"].items():
            n = self.nodes.get(key)
            if n is None:
                continue
            if snap["status"] == "COMPLETED":
                n.status = "COMPLETED"
                n.verified = snap.get("verified", False)
                n.result = TaskResult(
                    task_id=key, success=True,
                    summary=snap.get("summary", ""),
                )
                changed = True
        return changed

    # -- execution (P13-14, P43-44, P53, P90) ----------------------------------------------

    def _breaker_for(self, key: str) -> CircuitBreaker:
        br = self.breakers.get(key)
        if br is None:
            br = self.breakers[key] = CircuitBreaker(key)
        return br

    def _run_one(self, node: SwarmNode) -> None:
        node.status = "ASSIGNED"
        node.attempts += 1
        node.budget.started_at = time.time()
        self._emit("agent_started", node=node.node_key, agent=node.agent_id)

        identity = self._identities.setdefault(
            f"exec:{node.node_key}:{node.attempts}",
            ExecutionIdentity(
                agent_id=node.agent_id,
                execution_id=f"exec:{node.node_key}:{node.attempts}",
                parent_execution_id="root",
                task_id="orchestration",
                user_context="default",
            ),
        )

        # consequential side effects require prior authorization (P53)
        for eff in sorted(node.side_effects):
            if eff in CONSEQUENTIAL_EFFECTS:
                if self.emergency_stopped:
                    node.status = "BLOCKED"
                    node.failure = "emergency stop: approvals frozen"
                    node.failure_kind = FailureType.POLICY_ERROR
                    return
                ok = self.approvals.authorize(
                    action=f"side_effect:{eff}", task_id=node.node_key,
                    requester=node.agent_id)
                if not ok:
                    self._emit("approval_requested", node=node.node_key,
                               effect=eff)
                    node.status = "BLOCKED"
                    node.failure = f"unauthorized consequential effect {eff}"
                    node.failure_kind = FailureType.POLICY_ERROR
                    return

        executor = self.executors.get(node.agent_id)
        breaker_key = f"{node.agent_id}"
        ctx: Dict[str, Any] = {
            "node": node,
            "identity": identity,
            "budget": node.budget,
            "orchestrator": self,
            "criteria": node.success_criteria,
        }

        def _invoke() -> TaskResult:
            return executor(ctx)  # type: ignore[misc]

        started = time.time()
        try:
            result = self._breaker_for(breaker_key).call(_invoke)
        except BreakerOpen as exc:
            node.status = "FAILED"
            node.failure = str(exc)
            node.failure_kind = FailureType.PROVIDER_ERROR
            self._emit("agent_failed", node=node.node_key, why="breaker_open")
            return
        except _BudgetExceeded as exc:
            node.status = "FAILED"
            node.failure = f"budget exceeded: {exc}"
            node.failure_kind = FailureType.RESOURCE_EXHAUSTED
            self._emit("agent_failed", node=node.node_key, why="budget")
            return
        except CapabilityViolation as exc:
            node.status = "FAILED"
            node.failure = str(exc)
            node.failure_kind = FailureType.POLICY_ERROR
            self._emit("agent_failed", node=node.node_key, why="capability")
            return
        except Exception as exc:  # executor-level crash
            latency = time.time() - started
            node.failure_kind = classify_exception(exc)
            if node.deadline_seconds and latency > node.deadline_seconds:
                node.failure_kind = FailureType.TIMEOUT
                node.failure = f"timeout after {latency:.1f}s"
            else:
                node.failure = f"{type(exc).__name__}: {exc}"
            node.status = "FAILED"
            self._emit("agent_failed", node=node.node_key,
                       why=node.failure_kind.value)
            return

        latency = time.time() - started
        if node.deadline_seconds and latency > node.deadline_seconds:
            node.status = "FAILED"
            node.failure = f"deadline exceeded ({latency:.1f}s)"
            node.failure_kind = FailureType.TIMEOUT
            return

        if not isinstance(result, TaskResult):
            node.status = "FAILED"
            node.failure = "executor returned non-contract result (P22)"
            node.failure_kind = FailureType.AGENT_ERROR
            return
        if not result.success:
            node.status = "FAILED"
            node.failure = result.error or "executor reported failure"
            node.failure_kind = FailureType.AGENT_ERROR
            self._emit("agent_failed", node=node.node_key)
            return

        node.result = result
        node.status = "VERIFYING" if node.requires_verification \
            else "COMPLETED"
        if node.status == "COMPLETED":
            node.completed_at = time.time()

    def _verify_one(self, node: SwarmNode) -> None:
        verifier = self.executors.get("swarm.verifier")
        if verifier is None:
            node.status = "FAILED"
            node.failure = "required verification but no verifier registered"
            node.failure_kind = FailureType.VERIFICATION_FAILURE
            return
        vres = verifier({"target": node, "result": node.result})
        ok = bool(vres.success)
        node.verified = ok
        if ok:
            node.status = "COMPLETED"
            node.completed_at = time.time()
            self._emit("agent_verified", node=node.node_key)
        else:
            node.status = "FAILED"
            node.failure = f"verification failed: {vres.error or 'criteria unmet'}"
            node.failure_kind = FailureType.VERIFICATION_FAILURE

    def _classify_and_maybe_retry(self, node: SwarmNode) -> bool:
        """P44-45 — bounded retry for retryable classes only."""
        retryable = {
            FailureType.TIMEOUT, FailureType.RATE_LIMIT,
            FailureType.NETWORK_ERROR, FailureType.PROVIDER_ERROR,
        }
        if node.failure_kind not in retryable:
            return False
        if node.attempts >= 3:
            return False
        backoff = min(8.0, 0.05 * (2 ** (node.attempts - 1)))
        node.status = "CREATED"          # back to ready queue (RETRYING)
        self._emit("task_replanned", node=node.node_key,
                   attempt=node.attempts + 1, backoff=backoff)
        self.sleeper(backoff)
        return True

    def run(self, *, checkpoint_every: bool = True) -> Dict[str, Any]:
        self._emit("task_planned", nodes=len(self.nodes))
        while not self.cancelled:
            ready = self.ready_set()
            if not ready:
                # drain: bounded retries for retryable failed nodes
                retried = any(
                    self._classify_and_maybe_retry(n)
                    for n in (self.nodes[k] for k in self.order)
                    if n.status == "FAILED"
                )
                if retried:
                    continue
                break

            batch = ready[: max(1, self.max_parallel)]
            threads: List[threading.Thread] = []
            for node in batch:
                node.status = "RUNNING"
                th = threading.Thread(target=self._run_one, args=(node,))
                threads.append(th)
                self._active_agents += 1
                th.start()
            for th in threads:
                th.join(120)
            self._active_agents = 0

            for node in batch:
                if node.status == "VERIFYING":
                    self._verify_one(node)
                elif node.status == "FAILED":
                    self._classify_and_maybe_retry(node)
            if checkpoint_every and self._checkpoint_dir:
                self.checkpoint()

        if self.cancelled:
            for n in self.nodes.values():
                if not n.terminal:
                    n.status = "CANCELLED"

        completed = sum(1 for n in self.nodes.values()
                        if n.status == "COMPLETED")
        failed = sum(1 for n in self.nodes.values() if n.status == "FAILED")
        self._emit("task_completed" if failed == 0 else "task_failed",
                   completed=completed, failed=failed)
        return {"completed": completed, "failed": failed,
                "total": len(self.nodes)}

    # -- human override (P84-86) -----------------------------------------------------

    def emergency_stop(self) -> None:
        self.emergency_stopped = True
        self._emit("emergency_stop")

    def cancel(self) -> None:
        self.cancelled = True
        self._emit("task_cancelled_requested")

    # -- consensus + finalization (P28-30, P88-90) --------------------------------------

    def collect_candidates(self, answers: Dict[str, CandidateResult]) -> Dict[str, Any]:
        verdict = compare_results(list(answers.values()))
        return {
            "outcome": verdict.outcome.value,
            "ratio": verdict.agreement_ratio,
            "plan": vars(_plan_for(verdict)),
        }


def _plan_for(verdict):
    from agent.orchestration.consensus import DisagreementPlan

    return DisagreementPlan.for_verdict(verdict)


def final_status_from(nodes: Dict[str, SwarmNode],
                      validation: FinalValidation,
                      contributions) -> SynthesisResult:
    """P90 wrapper ensuring computed (never claimed) completion."""
    return synthesize(contributions, validation=validation)
