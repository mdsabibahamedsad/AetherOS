"""Automation models (Master 43 sections 2-3, 16-19, 24, 29-30).

Canonical AutomationDefinition + RunRecord with versioning, autonomy
levels, action risk tiers, approval/expiry semantics, idempotency.
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class AutoType(str, enum.Enum):
    SCHEDULED = "scheduled"
    RECURRING = "recurring"
    EVENT_TRIGGERED = "event_triggered"
    FILE_TRIGGERED = "file_triggered"
    WEB_TRIGGERED = "web_triggered"
    REPOSITORY_TRIGGERED = "repository_triggered"
    TASK_TRIGGERED = "task_triggered"
    MEMORY_TRIGGERED = "memory_triggered"
    RESEARCH_TRIGGERED = "research_triggered"
    SYSTEM_TRIGGERED = "system_triggered"
    MANUAL = "manual"
    CONDITIONAL = "conditional"
    WATCHER = "watcher"


class AutoState(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISABLED = "disabled"


class RunState(str, enum.Enum):
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_EVENT = "waiting_event"
    WAITING_NETWORK = "waiting_network"
    RETRYING = "retrying"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AutonomyLevel(int, enum.Enum):
    OFF = 0
    NOTIFY = 1
    SUGGEST = 2
    AUTO_READ = 3
    AUTO_EXECUTE = 4
    SUPERVISED = 5


class ActionRisk(str, enum.Enum):
    READ = "read"
    LOW_RISK_WRITE = "low_risk_write"
    HIGH_RISK_WRITE = "high_risk_write"
    DESTRUCTIVE = "destructive"
    EXTERNAL_COMMUNICATION = "external_communication"
    FINANCIAL = "financial"
    SECURITY_SENSITIVE = "security_sensitive"


class ApprovalPolicy(str, enum.Enum):
    ALWAYS_APPROVE = "always_approve"
    APPROVE_ONCE = "approve_once"
    PRE_APPROVED = "pre_approved"
    NEVER_ALLOWED = "never_allowed"


class MissedPolicy(str, enum.Enum):
    SKIP = "skip"
    RUN_ON_START = "run_on_start"
    RUN_LATEST_ONLY = "run_latest_only"
    CATCH_UP = "catch_up"
    ASK_USER = "ask_user"


class NotifyMode(str, enum.Enum):
    IMMEDIATE = "immediate"
    DIGEST = "digest"
    DAILY = "daily"
    WEEKLY = "weekly"
    ONLY_IMPORTANT = "only_important"
    SILENT = "silent"


class ChangeClass(str, enum.Enum):
    NO_CHANGE = "no_change"
    MINOR_CHANGE = "minor_change"
    MEANINGFUL_CHANGE = "meaningful_change"
    MAJOR_CHANGE = "major_change"
    CRITICAL_CHANGE = "critical_change"


# Risk -> minimum autonomy level allowed to perform without approval.
RISK_MIN_AUTONOMY = {
    ActionRisk.READ: AutonomyLevel.AUTO_READ,
    ActionRisk.LOW_RISK_WRITE: AutonomyLevel.AUTO_EXECUTE,
    ActionRisk.HIGH_RISK_WRITE: AutonomyLevel.SUPERVISED,
    ActionRisk.DESTRUCTIVE: AutonomyLevel.SUPERVISED,
    ActionRisk.EXTERNAL_COMMUNICATION: AutonomyLevel.SUPERVISED,
    ActionRisk.FINANCIAL: AutonomyLevel.SUPERVISED,
    ActionRisk.SECURITY_SENSITIVE: AutonomyLevel.SUPERVISED,
}

# Risk -> default approval policy.
RISK_DEFAULT_APPROVAL = {
    ActionRisk.READ: ApprovalPolicy.PRE_APPROVED,
    ActionRisk.LOW_RISK_WRITE: ApprovalPolicy.PRE_APPROVED,
    ActionRisk.HIGH_RISK_WRITE: ApprovalPolicy.ALWAYS_APPROVE,
    ActionRisk.DESTRUCTIVE: ApprovalPolicy.ALWAYS_APPROVE,
    ActionRisk.EXTERNAL_COMMUNICATION: ApprovalPolicy.ALWAYS_APPROVE,
    ActionRisk.FINANCIAL: ApprovalPolicy.ALWAYS_APPROVE,
    ActionRisk.SECURITY_SENSITIVE: ApprovalPolicy.ALWAYS_APPROVE,
}


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_base_s: float = 30.0
    backoff_max_s: float = 3600.0
    jitter: bool = True
    retryable: List[str] = field(default_factory=lambda: [
        "model_failure", "network_failure", "tool_failure", "timeout"])
    non_retryable: List[str] = field(default_factory=lambda: [
        "permission_denied", "security_block", "invalid_definition"])


@dataclass
class ResourceLimits:
    max_duration_s: float = 3600.0
    max_agents: int = 5
    max_parallel_tasks: int = 3
    max_tokens: int = 30000
    max_cost_usd: float = 0.50
    max_tool_calls: int = 100
    max_network_requests: int = 50
    max_memory_mb: float = 512.0
    max_retries: int = 3


GLOBAL_LIMITS = ResourceLimits(
    max_duration_s=6 * 3600.0, max_agents=20, max_parallel_tasks=10,
    max_tokens=500000, max_cost_usd=10.0, max_tool_calls=2000,
    max_network_requests=1000, max_memory_mb=2048.0, max_retries=5)


@dataclass
class AutomationDefinition:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    enabled: bool = False  # DRAFT by default; activation requires approval
    trusted: bool = False  # imports begin UNTRUSTED
    owner: str = ""
    scope: str = "user"
    project_id: str = ""
    auto_type: AutoType = AutoType.SCHEDULED
    trigger: Dict[str, Any] = field(default_factory=dict)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    workflow: List[Dict[str, Any]] = field(default_factory=list)
    agent_policy: Dict[str, Any] = field(default_factory=dict)
    tool_policy: Dict[str, Any] = field(default_factory=dict)
    memory_policy: Dict[str, Any] = field(default_factory=dict)
    approval_policy: str = ApprovalPolicy.ALWAYS_APPROVE.value
    notification_policy: str = NotifyMode.IMMEDIATE.value
    autonomy_level: int = int(AutonomyLevel.NOTIFY)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    timeout_s: float = 3600.0
    budget: Dict[str, Any] = field(default_factory=dict)
    concurrency_key: str = ""
    concurrency_policy: str = "queue"  # queue|skip|merge|cancel
    timezone: str = "UTC"
    missed_policy: str = MissedPolicy.SKIP.value
    version: int = 1
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_run: float = 0.0
    next_run: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def state(self) -> AutoState:
        if not self.enabled:
            return AutoState.DISABLED if self.last_run else AutoState.DRAFT
        return AutoState.ACTIVE

    def snapshot_version(self) -> None:
        self.history.append({"version": self.version, "at": time.time(),
                             "trigger": dict(self.trigger),
                             "workflow": [dict(s) for s in self.workflow],
                             "tools": list(self.tool_policy.get("tools", []))})

    def to_dict(self) -> Dict[str, Any]:
        d = {k: getattr(self, k) for k in (
            "id", "name", "description", "enabled", "trusted", "owner",
            "scope", "project_id", "trigger", "conditions", "workflow",
            "agent_policy", "tool_policy", "memory_policy",
            "approval_policy", "notification_policy", "autonomy_level",
            "timeout_s", "budget", "concurrency_key", "concurrency_policy",
            "timezone", "missed_policy", "version", "history",
            "created_at", "updated_at", "last_run", "next_run", "metadata")}
        d["auto_type"] = self.auto_type.value
        d["retry_policy"] = {"max_attempts": self.retry_policy.max_attempts,
                             "backoff_base_s": self.retry_policy.backoff_base_s,
                             "backoff_max_s": self.retry_policy.backoff_max_s,
                             "jitter": self.retry_policy.jitter}
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AutomationDefinition":
        a = cls()
        for k in ("id", "name", "description", "enabled", "trusted", "owner",
                  "scope", "project_id", "approval_policy",
                  "notification_policy", "autonomy_level", "timeout_s",
                  "budget", "concurrency_key", "concurrency_policy",
                  "timezone", "missed_policy", "version", "created_at",
                  "updated_at", "last_run", "next_run"):
            if k in d:
                setattr(a, k, d[k])
        a.auto_type = AutoType(str(d.get("auto_type", "scheduled")))
        a.trigger = dict(d.get("trigger", {}))
        a.conditions = list(d.get("conditions", []))
        a.workflow = list(d.get("workflow", []))
        a.agent_policy = dict(d.get("agent_policy", {}))
        a.tool_policy = dict(d.get("tool_policy", {}))
        a.memory_policy = dict(d.get("memory_policy", {}))
        rp = d.get("retry_policy", {})
        if rp:
            a.retry_policy = RetryPolicy(
                max_attempts=int(rp.get("max_attempts", 3)),
                backoff_base_s=float(rp.get("backoff_base_s", 30.0)),
                backoff_max_s=float(rp.get("backoff_max_s", 3600.0)),
                jitter=bool(rp.get("jitter", True)))
        a.history = list(d.get("history", []))
        a.metadata = dict(d.get("metadata", {}))
        return a


@dataclass
class RunRecord:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    idempotency_key: str = ""
    automation_id: str = ""
    trigger_kind: str = ""
    state: RunState = RunState.QUEUED
    attempt: int = 0
    steps: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    approvals: List[str] = field(default_factory=list)
    error: str = ""
    failure_kind: str = ""
    cost_usd: float = 0.0
    tokens: int = 0
    tool_calls: int = 0
    dry_run: bool = False
    causal_chain: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0

    def ensure_key(self) -> str:
        if not self.idempotency_key:
            self.idempotency_key = f"{self.automation_id}:{self.execution_id}"
        return self.idempotency_key

    def to_dict(self) -> Dict[str, Any]:
        d = {k: getattr(self, k) for k in (
            "run_id", "execution_id", "idempotency_key", "automation_id",
            "trigger_kind", "attempt", "steps", "artifacts", "approvals",
            "error", "failure_kind", "cost_usd", "tokens", "tool_calls",
            "dry_run", "causal_chain", "created_at", "started_at",
            "completed_at")}
        d["state"] = self.state.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RunRecord":
        r = cls()
        for k in ("run_id", "execution_id", "idempotency_key",
                  "automation_id", "trigger_kind", "attempt", "error",
                  "failure_kind", "cost_usd", "tokens", "tool_calls",
                  "dry_run", "created_at", "started_at", "completed_at"):
            if k in d:
                setattr(r, k, d[k])
        r.state = RunState(str(d.get("state", "queued")))
        r.steps = list(d.get("steps", []))
        r.artifacts = list(d.get("artifacts", []))
        r.approvals = list(d.get("approvals", []))
        r.causal_chain = list(d.get("causal_chain", []))
        return r
