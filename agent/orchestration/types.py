"""Shared type definitions for AetherOS Orchestration Layer.

These types are used across all orchestration components to ensure
consistent interfaces and data structures.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# =============================================================================
# Enums
# =============================================================================


class TaskStatus(Enum):
    """Lifecycle states for a task."""

    PENDING = "pending"
    QUEUED = "queued"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    REQUIRES_APPROVAL = "requires_approval"
    TIMEOUT = "timeout"
    EMERGENCY_STOPPED = "emergency_stopped"
    EXPIRED = "expired"


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = 0
    NORMAL = 50
    HIGH = 75
    CRITICAL = 100
    BACKGROUND = -50


class AgentRole(Enum):
    """Standardized agent roles across AetherOS."""

    COORDINATOR = "coordinator"
    PLANNER = "planner"
    DEVELOPER = "developer"
    CODING = "coding"
    BROWSER = "browser"
    RESEARCH = "research"
    WRITER = "writer"
    QA = "qa"
    DEPLOYMENT = "deployment"
    SECURITY = "security"
    MEMORY = "memory"
    CREATIVE = "creative"
    DATA = "data"
    COMMUNICATION = "communication"
    VERIFICATION = "verification"
    CRITIC = "critic"
    MONITORING = "monitoring"
    RECOVERY = "recovery"
    SYNTHESIS = "synthesis"
    ANALYSIS = "analysis"
    REVIEW = "review"
    FILE = "file"
    VISION = "vision"
    AUDIO = "audio"
    VIDEO = "video"
    COMPUTER = "computer"
    CUSTOM = "custom"


class AgentHealthStatus(Enum):
    """Health status for agents."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AgentLifecycleState(Enum):
    """Lifecycle states for agent instances."""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    PAUSED = "paused"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"


class ApprovalAction(Enum):
    """Types of actions requiring approval."""

    DANGEROUS_ACTION = "dangerous_action"
    DESTRUCTIVE_ACTION = "destructive_action"
    SENSITIVE_DATA = "sensitive_data"
    EXTERNAL_COMMUNICATION = "external_communication"
    PAYMENT = "payment"
    ACCOUNT_CHANGE = "account_change"
    PERMISSION_ESCALATION = "permission_escalation"
    UNCERTAIN_DECISION = "uncertain_decision"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    NETWORK_ACCESS = "network_access"
    CODE_EXECUTION = "code_execution"


class ApprovalResponse(Enum):
    """Possible responses to approval requests."""

    APPROVE_ONCE = "approve_once"
    APPROVE_SESSION = "approve_session"
    ALWAYS_ALLOW = "always_allow"
    DENY = "deny"
    DENY_SESSION = "deny_session"


class GraphExecutionMode(Enum):
    """Execution modes for task graphs."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    DEPENDENT = "dependent"
    RETRY = "retry"
    FALLBACK = "fallback"
    HUMAN_APPROVAL = "human_approval"


class RiskLevel(Enum):
    """Risk assessment levels."""

    READ_ONLY = "read_only"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FailureType(Enum):
    """Classification of failure types for computer use."""

    TRANSIENT = "transient"
    PERMISSION_DENIED = "permission_denied"
    TARGET_UNAVAILABLE = "target_unavailable"
    CONFIDENCE_TOO_LOW = "confidence_too_low"
    PROMPT_INJECTION = "prompt_injection"
    SECURITY_VIOLATION = "security_violation"
    NAVIGATION_FAILED = "navigation_failed"
    VERIFICATION_FAILED = "verification_failed"
    TIMEOUT = "timeout"
    BACKEND_ERROR = "backend_error"
    UNKNOWN = "unknown"


class ComputerState:
    """Canonical state model for computer use (Master Prompt 39 Phase 2)."""

    session_id: str
    platform: str  # "macos", "windows", "linux", "browser"
    active_window: Optional[str] = None
    active_application: Optional[str] = None
    browser: Optional["ComputerBrowserState"] = None
    screen: Optional["ScreenSnapshot"] = None
    cursor: Optional[Dict[str, Any]] = None
    selection: Optional[Dict[str, Any]] = None
    focused_element: Optional[Dict[str, Any]] = None
    accessibility_tree: Optional[Dict[str, Any]] = None
    dom_snapshot: Optional[Dict[str, Any]] = None
    screenshot: Optional[Dict[str, Any]] = None
    url: str = ""
    title: str = ""
    security_state: str = "unknown"  # "safe", "suspicious", "blocked"
    last_action: str = ""
    last_observation: str = ""
    last_verification: str = ""
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0  # Agent's confidence in current state


@dataclass
class ScreenSnapshot:
    """Snapshot of screen capture."""

    width: int = 0
    height: int = 0
    mode: str = "som"  # "som", "vision", "ax"
    png_b64: Optional[str] = None
    elements: List[Dict[str, Any]] = field(default_factory=list)
    app: str = ""
    window_title: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class ComputerBrowserState:
    """Browser-specific state within ComputerState."""

    tabs: List[Dict[str, Any]] = field(default_factory=list)
    active_tab_id: str = ""
    url: str = ""
    title: str = ""
    dom_snapshot: Optional[Dict[str, Any]] = None
    accessibility_tree: Optional[Dict[str, Any]] = None
    last_navigation: str = ""
    security_state: str = "unknown"


@dataclass
class Observation:
    """Canonical observation from a computer action (Master Prompt 39 Phase 3)."""

    observation_id: str = field(default_factory=lambda: f"obs-{uuid.uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)
    screen: Optional[ScreenSnapshot] = None
    active_window: str = ""
    application: str = ""
    url: str = ""
    title: str = ""
    dom_snapshot: Optional[Dict[str, Any]] = None
    accessibility_snapshot: Optional[Dict[str, Any]] = None
    visual_snapshot: Optional[ScreenSnapshot] = None
    focused_element: Optional[Dict[str, Any]] = None
    cursor: Optional[Dict[str, Any]] = None
    changed_regions: List[Dict[str, Any]] = field(default_factory=list)
    security_state: str = "unknown"

    def to_summary(self) -> str:
        """Compact summary for model context."""
        parts = []
        if self.title:
            parts.append(f"title={self.title}")
        if self.url:
            parts.append(f"url={self.url}")
        if self.active_window:
            parts.append(f"window={self.active_window}")
        if self.dom_snapshot:
            elements = self.dom_snapshot.get("interactable_elements", [])
            if elements:
                parts.append(f"elements={len(elements)}")
        if self.accessibility_snapshot:
            parts.append(f"ax_nodes={len(self.accessibility_snapshot.get('nodes', []))}")
        return " | ".join(parts) if parts else ""


# Update RiskLevel to include computer-specific risks
RiskLevel.COMPUTER_LOW = "computer_low"
RiskLevel.COMPUTER_MEDIUM = "computer_medium"
RiskLevel.COMPUTER_HIGH = "computer_high"
RiskLevel.COMPUTER_CRITICAL = "computer_critical"


class FailureType(Enum):
    """Classification of failure types."""

    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    PROVIDER_ERROR = "provider_error"
    TOOL_ERROR = "tool_error"
    PERMISSION_DENIED = "permission_denied"
    MODEL_ERROR = "model_error"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    USER_ERROR = "user_error"
    PLANNING_ERROR = "planning_error"
    AGENT_ERROR = "agent_error"
    POLICY_ERROR = "policy_error"
    SECURITY_ERROR = "security_error"
    VERIFICATION_FAILURE = "verification_failure"
    UNKNOWN = "unknown"


class ValidationOperator(Enum):
    """Operators for validation rules."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    MATCHES_REGEX = "matches_regex"
    IN = "in"
    NOT_IN = "not_in"


@dataclass
class ValidationRule:
    """A validation rule for plan/task validation."""
    field: str = ""
    operator: ValidationOperator = ValidationOperator.EXISTS
    expected_value: Any = None
    error_message: str = ""
    severity: str = "error"  # "info", "warning", "error", "critical"


# =============================================================================
# Plan Versioning Types
# =============================================================================


@dataclass
class PlanVersion:
    """A versioned snapshot of a plan."""
    version: int
    plan_id: str
    goal: str
    subtasks: List[Dict[str, Any]]
    dependencies: Dict[str, List[str]]
    required_tools: List[str]
    required_agents: List[str]
    required_permissions: List[str]
    estimated_cost: float
    estimated_time: float
    risk_level: str
    execution_graph: Dict[str, Any]
    created_at: float
    reason: str = ""
    changed_by: str = ""
    diff_from_previous: Optional[Dict[str, Any]] = None


@dataclass
class ReplanContext:
    """Context for adaptive replanning."""
    plan_id: str
    trigger: str  # "failure", "new_evidence", "requirement_change", "environment_change"
    failed_task_id: Optional[str] = None
    error_details: Optional[str] = None
    new_evidence: Optional[Dict[str, Any]] = None
    requirement_changes: Optional[List[str]] = None
    environment_changes: Optional[Dict[str, Any]] = None
    partial_results: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# Core Data Classes
# =============================================================================


@dataclass
class AgentIdentity:
    """Immutable identity for an agent instance."""

    agent_id: str = field(default_factory=lambda: f"agent-{uuid.uuid4().hex[:12]}")
    role: AgentRole = AgentRole.COORDINATOR
    name: str = ""
    version: str = "1.0.0"
    instance_id: str = field(default_factory=lambda: f"inst-{uuid.uuid4().hex[:8]}")


@dataclass
class AgentVersion:
    """Version information for an agent."""

    version: str = "1.0.0"
    build_date: str = ""
    commit_hash: str = ""
    api_version: str = "1.0"
    compatible_versions: List[str] = field(default_factory=list)


@dataclass
class AgentCapabilities:
    """Capabilities that an agent exposes."""

    capabilities: List[str] = field(default_factory=list)
    details: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    permissions: List[str] = field(default_factory=list)

    def add(self, capability: str, detail: Optional[Dict[str, Any]] = None) -> None:
        if capability not in self.capabilities:
            self.capabilities.append(capability)
        if detail:
            self.details[capability] = detail

    def has(self, capability: str) -> bool:
        return capability in self.capabilities

    def get(self, capability: str) -> Optional[Dict[str, Any]]:
        return self.details.get(capability)

    def set_schemas(self, input_schema: Dict[str, Any], output_schema: Dict[str, Any]) -> None:
        """Set input and output schemas for the agent."""
        self.input_schema = input_schema
        self.output_schema = output_schema

    def add_permission(self, permission: str) -> None:
        """Add a permission to the agent."""
        if permission not in self.permissions:
            self.permissions.append(permission)


@dataclass
class AgentMetadata:
    """Metadata about an agent."""

    description: str = ""
    author: str = ""
    license: str = ""
    tags: List[str] = field(default_factory=list)
    homepage: str = ""
    repository: str = ""
    min_aetheros_version: str = "1.0.0"
    max_aetheros_version: str = ""
    supported_platforms: List[str] = field(default_factory=list)
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    model_requirements: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)


@dataclass
class AgentHealth:
    """Health status for an agent."""

    status: "AgentHealthStatus" = AgentHealthStatus.UNKNOWN
    agent_id: str = ""
    checked_at: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)
    checks: Dict[str, bool] = field(default_factory=dict)

    def is_healthy(self) -> bool:
        return self.status == AgentHealthStatus.HEALTHY


@dataclass
class TaskSpec:
    """Universal task specification."""

    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:12]}")
    parent_task_id: str = ""
    root_task_id: str = ""
    user_id: str = ""
    project_id: str = ""
    session_id: str = ""
    workspace_id: str = ""  # NEW: workspace identifier

    goal: str = ""
    description: str = ""
    constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)

    required_capabilities: List[str] = field(default_factory=list)
    preferred_agent_role: Optional[AgentRole] = None
    preferred_model: str = ""
    preferred_tools: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)

    # Assignment fields
    assigned_agent: str = ""
    assigned_model: str = ""

    # Status tracking
    status: TaskStatus = TaskStatus.PENDING

    priority: TaskPriority = TaskPriority.NORMAL
    deadline: Optional[float] = None  # Unix timestamp
    budget: "TaskBudget" = field(default_factory=lambda: TaskBudget())

    depends_on: List[str] = field(default_factory=list)  # Task IDs
    blocks: List[str] = field(default_factory=list)  # Task IDs

    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)  # Runtime context
    observations: List[str] = field(default_factory=list)  # NEW: observation log
    artifacts: List[str] = field(default_factory=list)  # Expected artifact IDs

    # Plan and execution graph
    plan: str = ""  # JSON string or description of the plan
    execution_graph_id: str = ""  # Reference to task graph

    # Results and verification
    result: Any = None
    verification_state: str = ""  # "pending", "verified", "failed", "skipped"
    approval_state: str = ""  # "none", "pending", "approved", "denied"

    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    started_at: float = 0
    completed_at: float = 0

    def with_id(self, task_id: str) -> "TaskSpec":
        """Return a copy with a specific task ID."""
        new = TaskSpec(
            task_id=task_id,
            parent_task_id=self.parent_task_id,
            root_task_id=self.root_task_id,
            user_id=self.user_id,
            project_id=self.project_id,
            session_id=self.session_id,
            workspace_id=self.workspace_id,  # NEW
            goal=self.goal,
            description=self.description,
            constraints=self.constraints,
            success_criteria=self.success_criteria,
            required_capabilities=self.required_capabilities,
            preferred_agent_role=self.preferred_agent_role,
            preferred_model=self.preferred_model,
            preferred_tools=self.preferred_tools,
            preferred_skills=self.preferred_skills,
            assigned_agent=self.assigned_agent,
            assigned_model=self.assigned_model,
            status=self.status,
            priority=self.priority,
            deadline=self.deadline,
            budget=self.budget,
            depends_on=self.depends_on,
            blocks=self.blocks,
            metadata=self.metadata,
            context=self.context,
            observations=self.observations,  # NEW
            artifacts=self.artifacts,
            result=self.result,
            verification_state=self.verification_state,
            approval_state=self.approval_state,
            started_at=self.started_at,
            completed_at=self.completed_at,
        )
        return new


@dataclass
class TaskBudget:
    """Resource budget for a task."""

    max_time_seconds: float = 3600.0  # 1 hour default
    max_tokens: int = 100000
    max_cost_usd: float = 10.0
    max_tool_calls: int = 100
    max_iterations: int = 50
    max_parallel_subtasks: int = 3
    max_subagents: int = 3


@dataclass
class TaskResult:
    """Result of task execution."""

    task_id: str
    success: bool
    result: Any = None
    error: str = ""
    artifacts: List[str] = field(default_factory=list)  # Artifact IDs
    execution_time: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    model_used: str = ""
    agent_id: str = ""
    verification: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: float = field(default_factory=time.time)
    # Master 19 result contract (P22/P30) — additive, defaulted for compat.
    summary: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 0.5          # agent self-reported result confidence
    verification_needed: bool = False


@dataclass
class TaskGraph:
    """Directed acyclic graph of tasks."""

    nodes: Dict[str, "TaskNode"] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)  # (from, to)
    root_nodes: List[str] = field(default_factory=list)
    leaf_nodes: List[str] = field(default_factory=list)

    def add_node(self, node: "TaskNode") -> None:
        self.nodes[node.task_id] = node

    def add_edge(self, from_id: str, to_id: str) -> None:
        self.edges.append((from_id, to_id))

    def get_dependencies(self, task_id: str) -> List[str]:
        return [from_id for from_id, to_id in self.edges if to_id == task_id]

    def get_dependents(self, task_id: str) -> List[str]:
        return [to_id for from_id, to_id in self.edges if from_id == task_id]

    def topological_order(self) -> List[str]:
        """Return tasks in topological order."""
        # Kahn's algorithm
        in_degree = {nid: 0 for nid in self.nodes}
        for from_id, to_id in self.edges:
            in_degree[to_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for from_id, to_id in self.edges:
                if from_id == nid:
                    in_degree[to_id] -= 1
                    if in_degree[to_id] == 0:
                        queue.append(to_id)

        if len(order) != len(self.nodes):
            raise ValueError("Graph has cycles")

        return order


@dataclass
class TaskNode:
    """Node in a task graph."""

    task_id: str
    task: "TaskSpec" = None
    status: "TaskStatus" = TaskStatus.PENDING
    assigned_agent: str = ""
    result: Any = None
    error: str = ""
    started_at: float = 0
    completed_at: float = 0


@dataclass
class ExecutionState:
    """Execution state for a plan/task."""

    plan_id: str = ""
    current_task_id: str = ""
    completed_tasks: List[str] = field(default_factory=list)
    pending_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    running_tasks: List[str] = field(default_factory=list)
    paused: bool = False
    cancelled: bool = False
    checkpoint_path: str = ""
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    budget_used: "TaskBudget" = field(default_factory=TaskBudget)


@dataclass
class AgentMessage:
    """Message between agents."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: str = ""
    message_type: str = "text"
    content: str = ""
    data: Any = None
    task_id: str = ""
    created_at: float = field(default_factory=time.time)
    requires_response: bool = False
    response_to: str = ""  # Message ID being responded to


@dataclass
class HandoffContext:
    """Context packaged for agent handoff."""

    source_agent_id: str = ""
    target_agent_id: str = ""
    task_id: str = ""
    goal: str = ""
    summary: str = ""
    relevant_artifacts: List[str] = field(default_factory=list)
    relevant_memory: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Checkpoint:
    """Checkpoint for task recovery."""

    checkpoint_id: str = ""
    task_id: str = ""
    plan_id: str = ""
    checkpoint_type: str = "periodic"
    task_state: Dict[str, Any] = field(default_factory=dict)
    budget_snapshot: "BudgetSnapshot" = field(default_factory=lambda: BudgetSnapshot())
    completed_subtasks: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    memory_refs: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """Execution plan with tasks and dependencies."""

    plan_id: str = field(default_factory=lambda: f"plan-{uuid.uuid4().hex[:12]}")
    goal: str = ""
    description: str = ""
    subtasks: List[TaskSpec] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    required_tools: List[str] = field(default_factory=list)
    required_agents: List[AgentRole] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_time: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    created_at: float = field(default_factory=time.time)
    execution_graph: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    parent_plan_id: str = ""

    def add_task(self, task: TaskSpec) -> None:
        self.subtasks.append(task)

    def get_task(self, task_id: str) -> Optional[TaskSpec]:
        for task in self.subtasks:
            if task.task_id == task_id:
                return task
        return None


@dataclass
class VerificationReport:
    """Result of independent verification."""

    verified: bool
    confidence: float  # 0.0 - 1.0
    evidence: List[str] = field(default_factory=list)
    discrepancies: List[str] = field(default_factory=list)
    criteria_results: Dict[str, bool] = field(default_factory=dict)
    verifier_id: str = ""
    verified_at: float = field(default_factory=time.time)
    notes: str = ""


@dataclass
class ApprovalRequest:
    """Request for human approval."""

    request_id: str = field(default_factory=lambda: f"appr-{uuid.uuid4().hex[:12]}")
    task_id: str = ""
    agent_id: str = ""
    action: ApprovalAction = ApprovalAction.DANGEROUS_ACTION
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    status: str = "pending"  # pending, approved, denied, expired
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    responded_at: Optional[float] = None
    response: Optional[ApprovalResponse] = None
    responded_by: str = ""
    scope: str = "task"  # task, session, always


@dataclass
class BudgetSnapshot:
    """Resource budget snapshot at a point in time."""

    time_seconds: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    iterations: int = 0
    parallel_subtasks: int = 0
    subagents: int = 0


# =============================================================================
# Utility Functions
# =============================================================================


def create_task_spec(
    goal: str,
    description: str = "",
    role: Optional[AgentRole] = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    budget: Optional[TaskBudget] = None,
    depends_on: Optional[List[str]] = None,
    **kwargs,
) -> TaskSpec:
    """Factory function to create a TaskSpec with sensible defaults."""
    return TaskSpec(
        goal=goal,
        description=description,
        preferred_agent_role=role,
        priority=priority,
        budget=budget or TaskBudget(),
        depends_on=depends_on or [],
        **kwargs,
    )


def create_task_budget(
    max_time_seconds: float = 3600.0,
    max_tokens: int = 100000,
    max_cost_usd: float = 10.0,
    max_tool_calls: int = 100,
    max_iterations: int = 50,
) -> TaskBudget:
    """Create a task budget with custom limits."""
    return TaskBudget(
        max_time_seconds=max_time_seconds,
        max_tokens=max_tokens,
        max_cost_usd=max_cost_usd,
        max_tool_calls=max_tool_calls,
        max_iterations=max_iterations,
    )


def is_terminal_status(status: TaskStatus) -> bool:
    """Check if a task status is terminal (no further transitions)."""
    return status in (
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.TIMEOUT,
        TaskStatus.EMERGENCY_STOPPED,
        TaskStatus.EXPIRED,
    )


def can_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    """Check if a status transition is valid."""
    valid_transitions = {
        TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
        TaskStatus.QUEUED: {TaskStatus.PLANNING, TaskStatus.READY, TaskStatus.CANCELLED},
        TaskStatus.PLANNING: {TaskStatus.READY, TaskStatus.FAILED, TaskStatus.CANCELLED},
        TaskStatus.READY: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
        TaskStatus.RUNNING: {
            TaskStatus.WAITING,
            TaskStatus.BLOCKED,
            TaskStatus.VERIFYING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.PAUSED,
            TaskStatus.REQUIRES_APPROVAL,
        },
        TaskStatus.WAITING: {TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.CANCELLED, TaskStatus.TIMEOUT},
        TaskStatus.BLOCKED: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
        TaskStatus.VERIFYING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.REQUIRES_APPROVAL},
        TaskStatus.REQUIRES_APPROVAL: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
        TaskStatus.PAUSED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
        TaskStatus.EXPIRED: set(),  # EXPIRED is terminal
    }
    if from_status == TaskStatus.EXPIRED:
        return False  # No transitions out of EXPIRED
    return to_status in valid_transitions.get(from_status, set())


def generate_id(prefix: str = "id") -> str:
    """Generate a unique ID with prefix."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def now() -> float:
    """Current Unix timestamp."""
    return time.time()