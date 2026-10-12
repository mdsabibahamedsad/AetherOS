"""Swarm canonical models (Master 42 sections 3-4, 16-17, 34).

Extends (not duplicates) aetheros_automation.models + orchestrator.types:
SwarmTask carries budgets, idempotency, verification policy and lineage;
AgentInstance carries lifecycle, health, hierarchy and telemetry refs.
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class SwarmTaskState(str, enum.Enum):
    CREATED = "created"
    QUEUED = "queued"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    PAUSED = "paused"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_VERIFICATION = "awaiting_verification"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_VALID_TRANSITIONS: Dict[SwarmTaskState, frozenset] = {
    SwarmTaskState.CREATED: frozenset({SwarmTaskState.QUEUED, SwarmTaskState.CANCELLED}),
    SwarmTaskState.QUEUED: frozenset({SwarmTaskState.READY, SwarmTaskState.CANCELLED, SwarmTaskState.PAUSED}),
    SwarmTaskState.READY: frozenset({SwarmTaskState.RUNNING, SwarmTaskState.CANCELLED, SwarmTaskState.PAUSED}),
    SwarmTaskState.RUNNING: frozenset({SwarmTaskState.WAITING, SwarmTaskState.BLOCKED,
                                       SwarmTaskState.AWAITING_APPROVAL, SwarmTaskState.AWAITING_VERIFICATION,
                                       SwarmTaskState.COMPLETED, SwarmTaskState.FAILED,
                                       SwarmTaskState.CANCELLED, SwarmTaskState.PAUSED}),
    SwarmTaskState.WAITING: frozenset({SwarmTaskState.RUNNING, SwarmTaskState.CANCELLED, SwarmTaskState.FAILED}),
    SwarmTaskState.BLOCKED: frozenset({SwarmTaskState.QUEUED, SwarmTaskState.CANCELLED, SwarmTaskState.FAILED}),
    SwarmTaskState.PAUSED: frozenset({SwarmTaskState.QUEUED, SwarmTaskState.CANCELLED}),
    SwarmTaskState.AWAITING_APPROVAL: frozenset({SwarmTaskState.RUNNING, SwarmTaskState.CANCELLED, SwarmTaskState.FAILED}),
    SwarmTaskState.AWAITING_VERIFICATION: frozenset({SwarmTaskState.COMPLETED, SwarmTaskState.RUNNING,
                                                     SwarmTaskState.FAILED, SwarmTaskState.CANCELLED}),
    SwarmTaskState.COMPLETED: frozenset(),
    SwarmTaskState.FAILED: frozenset({SwarmTaskState.QUEUED, SwarmTaskState.CANCELLED}),
    SwarmTaskState.CANCELLED: frozenset(),
}


class Topology(str, enum.Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    SUPERVISOR = "supervisor"
    HIERARCHICAL = "hierarchical"
    DAG = "dag"
    DEBATE = "debate"
    REVIEW_LOOP = "review_loop"
    MAP_REDUCE = "map_reduce"
    SWARM = "swarm"
    HYBRID = "hybrid"
    SINGLE = "single"


class AgentLifecycle(str, enum.Enum):
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TERMINATED = "terminated"


_AGENT_TRANSITIONS: Dict[AgentLifecycle, frozenset] = {
    AgentLifecycle.CREATED: frozenset({AgentLifecycle.INITIALIZING, AgentLifecycle.CANCELLED}),
    AgentLifecycle.INITIALIZING: frozenset({AgentLifecycle.READY, AgentLifecycle.FAILED, AgentLifecycle.CANCELLED}),
    AgentLifecycle.READY: frozenset({AgentLifecycle.RUNNING, AgentLifecycle.PAUSED, AgentLifecycle.CANCELLED}),
    AgentLifecycle.RUNNING: frozenset({AgentLifecycle.WAITING, AgentLifecycle.BLOCKED, AgentLifecycle.PAUSED,
                                       AgentLifecycle.COMPLETED, AgentLifecycle.FAILED, AgentLifecycle.CANCELLED}),
    AgentLifecycle.WAITING: frozenset({AgentLifecycle.RUNNING, AgentLifecycle.CANCELLED, AgentLifecycle.FAILED}),
    AgentLifecycle.BLOCKED: frozenset({AgentLifecycle.READY, AgentLifecycle.CANCELLED, AgentLifecycle.FAILED}),
    AgentLifecycle.PAUSED: frozenset({AgentLifecycle.READY, AgentLifecycle.CANCELLED}),
    AgentLifecycle.COMPLETED: frozenset({AgentLifecycle.TERMINATED}),
    AgentLifecycle.FAILED: frozenset({AgentLifecycle.READY, AgentLifecycle.TERMINATED}),
    AgentLifecycle.CANCELLED: frozenset({AgentLifecycle.TERMINATED}),
    AgentLifecycle.TERMINATED: frozenset(),
}


class MsgType(str, enum.Enum):
    TASK = "task"
    RESULT = "result"
    REQUEST = "request"
    RESPONSE = "response"
    QUESTION = "question"
    HANDOFF = "handoff"
    PROGRESS = "progress"
    BLOCKED = "blocked"
    ERROR = "error"
    REVIEW = "review"
    VERIFICATION = "verification"
    CANCEL = "cancel"
    PAUSE = "pause"
    RESUME = "resume"


class FailureKind(str, enum.Enum):
    MODEL_FAILURE = "model_failure"
    TOOL_FAILURE = "tool_failure"
    NETWORK_FAILURE = "network_failure"
    TIMEOUT = "timeout"
    CONTEXT_OVERFLOW = "context_overflow"
    PERMISSION_DENIED = "permission_denied"
    INVALID_OUTPUT = "invalid_output"
    VERIFICATION_FAILURE = "verification_failure"
    DEPENDENCY_FAILURE = "dependency_failure"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    SECURITY_BLOCK = "security_block"


class SideEffectTier(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"


class ConsensusMode(str, enum.Enum):
    CONSENSUS = "consensus"
    EVIDENCE_WEIGHTED = "evidence_weighted"
    ORCHESTRATOR_DECISION = "orchestrator_decision"
    USER_DECISION = "user_decision"
    UNRESOLVED = "unresolved"


@dataclass
class TaskBudget:
    max_tokens: int = 8000
    max_cost_usd: float = 0.25
    max_duration_s: float = 600.0
    max_tool_calls: int = 20
    max_retries: int = 2
    tokens_used: int = 0
    cost_used_usd: float = 0.0
    tool_calls_used: int = 0

    def exhausted(self) -> bool:
        return (self.tokens_used >= self.max_tokens
                or self.cost_used_usd >= self.max_cost_usd
                or self.tool_calls_used >= self.max_tool_calls)

    def to_dict(self) -> Dict[str, Any]:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}


@dataclass
class VerificationPolicy:
    required: bool = False
    method: str = "oracle"  # oracle|tests|schema|source|hash|execution|review|none
    retries: int = 1


@dataclass
class SwarmTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_task_id: str = ""
    root_task_id: str = ""
    goal: str = ""
    description: str = ""
    type: str = "general"
    priority: int = 1
    state: SwarmTaskState = SwarmTaskState.CREATED
    dependencies: List[str] = field(default_factory=list)
    assigned_agent: str = ""
    required_role: str = ""
    allowed_tools: List[str] = field(default_factory=list)
    side_effect_tier: SideEffectTier = SideEffectTier.READ
    context_policy: str = "minimal"
    input_artifacts: List[str] = field(default_factory=list)
    output_artifacts: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    expected_output: str = ""
    verification: VerificationPolicy = field(default_factory=VerificationPolicy)
    budget: TaskBudget = field(default_factory=TaskBudget)
    timeout_s: float = 600.0
    idempotency_key: str = ""
    depth: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    result_id: str = ""
    error: str = ""
    failure_kind: str = ""
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def set_state(self, nxt: SwarmTaskState) -> None:
        allowed = _VALID_TRANSITIONS.get(self.state, frozenset())
        if nxt not in allowed:
            raise ValueError(f"invalid task transition {self.state.value} -> {nxt.value}")
        self.state = nxt

    def ensure_idempotency_key(self) -> str:
        if not self.idempotency_key:
            self.idempotency_key = f"{self.id}:{self.retry_count}"
        return self.idempotency_key

    def to_dict(self) -> Dict[str, Any]:
        d = {k: getattr(self, k) for k in (
            "id", "parent_task_id", "root_task_id", "goal", "description",
            "type", "priority", "dependencies", "assigned_agent",
            "required_role", "allowed_tools", "context_policy",
            "input_artifacts", "output_artifacts", "evidence",
            "expected_output", "timeout_s", "idempotency_key", "depth",
            "created_at", "started_at", "completed_at", "result_id",
            "error", "failure_kind", "retry_count", "metadata")}
        d["state"] = self.state.value
        d["side_effect_tier"] = self.side_effect_tier.value
        d["verification"] = {"required": self.verification.required,
                             "method": self.verification.method,
                             "retries": self.verification.retries}
        d["budget"] = self.budget.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SwarmTask":
        t = cls()
        for k in ("id", "parent_task_id", "root_task_id", "goal", "description",
                  "type", "priority", "assigned_agent", "required_role",
                  "context_policy", "expected_output", "timeout_s",
                  "idempotency_key", "depth", "created_at", "started_at",
                  "completed_at", "result_id", "error", "failure_kind",
                  "retry_count"):
            if k in d:
                setattr(t, k, d[k])
        t.state = SwarmTaskState(str(d.get("state", t.state.value)))
        t.side_effect_tier = SideEffectTier(str(d.get("side_effect_tier", "read")))
        t.dependencies = list(d.get("dependencies", []))
        t.allowed_tools = list(d.get("allowed_tools", []))
        t.input_artifacts = list(d.get("input_artifacts", []))
        t.output_artifacts = list(d.get("output_artifacts", []))
        t.evidence = list(d.get("evidence", []))
        v = d.get("verification", {})
        t.verification = VerificationPolicy(required=bool(v.get("required", False)),
                                            method=str(v.get("method", "oracle")),
                                            retries=int(v.get("retries", 1)))
        b = d.get("budget", {})
        for k in t.budget.__dataclass_fields__:
            if k in b:
                setattr(t.budget, k, b[k])
        t.metadata = dict(d.get("metadata", {}))
        return t


@dataclass
class AgentInstance:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "coder"
    capabilities: List[str] = field(default_factory=list)
    model: str = ""
    provider: str = ""
    system_policy: str = ""
    tools: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    memory_scope: str = "task"
    project_id: str = ""
    task_id: str = ""
    budget: TaskBudget = field(default_factory=TaskBudget)
    status: AgentLifecycle = AgentLifecycle.CREATED
    health: str = "unknown"
    parent_agent: str = ""
    child_agents: List[str] = field(default_factory=list)
    depth: int = 0
    artifacts: List[str] = field(default_factory=list)
    tokens_used: int = 0
    cost_used_usd: float = 0.0
    tool_calls_used: int = 0
    latency_s: float = 0.0
    current_action: str = ""
    errors: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def set_status(self, nxt: AgentLifecycle) -> None:
        allowed = _AGENT_TRANSITIONS.get(self.status, frozenset())
        if nxt not in allowed:
            raise ValueError(f"invalid agent transition {self.status.value} -> {nxt.value}")
        self.status = nxt

    def to_dict(self) -> Dict[str, Any]:
        d = {k: getattr(self, k) for k in (
            "id", "role", "capabilities", "model", "provider",
            "system_policy", "tools", "permissions", "memory_scope",
            "project_id", "task_id", "health", "parent_agent",
            "child_agents", "depth", "artifacts", "tokens_used",
            "cost_used_usd", "tool_calls_used", "latency_s",
            "current_action", "errors", "created_at")}
        d["status"] = self.status.value
        d["budget"] = self.budget.to_dict()
        return d


@dataclass
class AgentResult:
    task_id: str = ""
    agent_id: str = ""
    status: str = "ok"  # ok|failed|blocked|needs_approval
    summary: str = ""
    findings: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    recommended_next_steps: List[str] = field(default_factory=list)
    verification_status: str = "unverified"
    confidence: float = 0.5
    tokens_used: int = 0
    cost_used_usd: float = 0.0
    tool_calls_used: int = 0
    latency_s: float = 0.0
    idempotency_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass
class AgentMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    recipient: str = ""
    message_type: MsgType = MsgType.TASK
    task_id: str = ""
    correlation_id: str = ""
    content: str = ""
    artifacts: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    priority: int = 1
    timestamp: float = field(default_factory=time.time)
    ttl_s: float = 3600.0
    seq: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = {k: getattr(self, k) for k in (
            "id", "sender", "recipient", "task_id", "correlation_id",
            "content", "artifacts", "evidence", "priority",
            "timestamp", "ttl_s", "seq")}
        d["message_type"] = self.message_type.value
        return d
