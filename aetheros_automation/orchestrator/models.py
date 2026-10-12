from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class OrchestratorState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "error"
    RUNNING = "running"
    COMPLETED = "completed"


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"
    RETRYING = "retrying"
    ROLLED_BACK = "rolled_back"


class TaskType(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    DEPENDENT = "dependent"
    RETRY = "retry"
    FALLBACK = "fallback"
    HUMAN_APPROVAL = "human_approval"
    SUB_AGENT = "sub_agent"
    AGENT_TASK = "agent_task"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    WAIT = "wait"
    NOTIFY = "notify"
    MERGE = "merge"
    SPLIT = "split"


class TaskPriority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NodeType(Enum):
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    MERGE = "merge"
    SUB_GRAPH = "sub_graph"
    AGENT = "agent"
    APPROVAL = "approval"
    RETRY = "retry"
    FALLBACK = "fallback"


class AgentRole(Enum):
    RESEARCH = "research"
    CODING = "coding"
    BROWSER = "browser"
    FILE = "file"
    DATA = "data"
    COMMUNICATION = "communication"
    PLANNING = "planning"
    REVIEW = "review"
    SECURITY = "security"
    CREATIVE = "creative"
    COORDINATOR = "coordinator"
    GENERAL = "general"


class ModelCapability(Enum):
    REASONING = "reasoning"
    CODING = "coding"
    VISION = "vision"
    AUDIO = "audio"
    VIDEO = "video"
    TOOL_USE = "tool_use"
    LARGE_CONTEXT = "large_context"
    FAST = "fast"
    CHEAP = "cheap"
    LOCAL = "local"
    PRIVATE = "private"


class TemplateCategory(Enum):
    RESEARCH_REPORT = "research_report"
    SOFTWARE_DEV = "software_development"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_CREATION = "content_creation"
    EMAIL_CAMPAIGN = "email_campaign"
    BUSINESS_AUTO = "business_automation"
    PERSONAL_ASSISTANT = "personal_assistant"
    CUSTOM = "custom"


@dataclass
class OrchestratorConfig:
    max_concurrent_tasks: int = 5
    max_sub_agents: int = 10
    max_parallel: int = 3
    max_retries: int = 3
    task_timeout: float = 3600.0
    checkpoint_interval: float = 60.0
    enable_checkpoints: bool = True
    enable_approvals: bool = True
    enable_audit: bool = True
    default_provider: str = ""
    default_model: str = ""
    fallback_provider: str = ""
    fallback_model: str = ""
    sandbox_enabled: bool = True
    max_cost: float = 0.0
    max_tokens: int = 0
    max_steps: int = 100
    offline_mode: bool = False
    remote_execution: bool = False
    privacy_mode: bool = False

    def to_dict(self) -> dict:
        return {k: str(v) if isinstance(v, Enum) else v
                for k, v in self.__dict__.items() if not k.startswith('_')}


@dataclass
class Objective:
    goal: str
    context: dict = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.MEDIUM
    output_format: str = ""
    deadline: Optional[float] = None
    max_budget: float = 0.0
    user_id: str = ""
    session_id: str = ""


@dataclass
class PlanStep:
    id: str = ""
    description: str = ""
    agent_role: AgentRole = AgentRole.GENERAL
    tools: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    estimated_duration: float = 60.0
    estimated_cost: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    parallelizable: bool = False
    fallback_steps: list[str] = field(default_factory=list)
    retry_count: int = 0
    validation_rules: list[str] = field(default_factory=list)


@dataclass
class Plan:
    id: str = ""
    goal: str = ""
    steps: list[PlanStep] = field(default_factory=list)
    tasks: list[OrchestrationTask] = field(default_factory=list)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    required_tools: list[str] = field(default_factory=list)
    required_agents: list[AgentRole] = field(default_factory=list)
    required_permissions: list[str] = field(default_factory=list)
    execution_graph: Optional[ExecutionGraph] = None
    estimated_cost: float = 0.0
    estimated_time: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    status: str = "pending"
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    checkpoint_id: str = ""
    error: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"plan_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()


@dataclass
class OrchestrationTask:
    id: str = ""
    name: str = ""
    description: str = ""
    task_type: TaskType = TaskType.SEQUENTIAL
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    risk_level: RiskLevel = RiskLevel.LOW
    agent_role: AgentRole = AgentRole.GENERAL
    agent_id: str = ""
    model: str = ""
    provider: str = ""
    tools: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    subtasks: list[OrchestrationTask] = field(default_factory=list)
    parent_id: str = ""
    input: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0
    fallback_task_id: str = ""
    timeout: float = 300.0
    estimated_duration: float = 60.0
    estimated_cost: float = 0.0
    actual_duration: float = 0.0
    progress: float = 0.0
    requires_approval: bool = False
    approval_status: str = ""
    checkpoint_data: dict = field(default_factory=dict)
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    logs: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    limits: Optional[AgentLimits] = None
    validation_rules: list[ValidationRule] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"task_{uuid.uuid4().hex[:12]}"


@dataclass
class GraphNode:
    id: str = ""
    task_id: str = ""
    node_type: NodeType = NodeType.TASK
    label: str = ""
    status: TaskStatus = TaskStatus.PENDING
    level: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str = ""
    target: str = ""
    edge_type: str = "dependency"
    condition: str = ""
    label: str = ""


@dataclass
class ExecutionGraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    levels: list[list[str]] = field(default_factory=list)
    entry_nodes: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentDefinition:
    role: AgentRole = AgentRole.GENERAL
    name: str = ""
    description: str = ""
    model: str = ""
    provider: str = ""
    tools: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    instructions: str = ""
    personality: str = ""
    max_sub_agents: int = 3
    max_steps: int = 50
    max_cost: float = 0.0
    memory_enabled: bool = True
    knowledge_enabled: bool = True
    temperature: float = 0.7
    allowed_parents: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentInstance:
    id: str = ""
    definition: AgentDefinition = field(default_factory=AgentDefinition)
    parent_id: str = ""
    session_id: str = ""
    status: str = "idle"
    current_task_id: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    stats: dict = field(default_factory=dict)


@dataclass
class SubAgentSpec:
    role: AgentRole = AgentRole.GENERAL
    name: str = ""
    instructions: str = ""
    tools: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    max_steps: int = 20
    timeout: float = 300.0
    parent_agent_id: str = ""
    scope: str = ""
    auto_terminate: bool = True


@dataclass
class AgentMessage:
    id: str = ""
    sender_id: str = ""
    recipient_id: str = ""
    message_type: str = "message"
    content: str = ""
    data: dict = field(default_factory=dict)
    task_id: str = ""
    timestamp: float = 0.0
    correlation_id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"msg_{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class CollaborationSession:
    id: str = ""
    plan_id: str = ""
    agents: list[str] = field(default_factory=list)
    messages: list[AgentMessage] = field(default_factory=list)
    status: str = "active"
    created_at: float = 0.0
    completed_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = f"collab_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()


@dataclass
class ModelRoute:
    task_type: str = ""
    recommended_model: str = ""
    recommended_provider: str = ""
    fallback_model: str = ""
    fallback_provider: str = ""
    reason: str = ""
    estimated_cost: float = 0.0
    context_size: int = 0
    supports_vision: bool = False
    supports_audio: bool = False
    supports_tools: bool = True
    is_local: bool = False
    latency_ms: int = 0


@dataclass
class FailurePolicy:
    max_retries: int = 3
    retry_delay: float = 1.0
    exponential_backoff: bool = True
    backoff_factor: float = 2.0
    use_fallback_model: bool = True
    use_fallback_agent: bool = True
    ask_user: bool = False
    checkpoint_on_failure: bool = True
    partial_recovery: bool = False


@dataclass
class Checkpoint:
    id: str = ""
    plan_id: str = ""
    plan_snapshot: dict = field(default_factory=dict)
    completed_task_ids: list[str] = field(default_factory=list)
    pending_task_ids: list[str] = field(default_factory=list)
    results: dict = field(default_factory=dict)
    agent_state: dict = field(default_factory=dict)
    execution_state: dict = field(default_factory=dict)
    files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    created_at: float = 0.0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"ckpt_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()


@dataclass
class ApprovalRequest:
    id: str = ""
    plan_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    action: str = ""
    description: str = ""
    reason: str = ""
    data_affected: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    status: str = "pending"
    created_at: float = 0.0
    responded_at: float = 0.0
    response: str = ""
    responded_by: str = ""
    session_id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"apr_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()


@dataclass
class ApprovalResponse:
    request_id: str = ""
    approved: bool = False
    duration: str = "once"
    user_id: str = ""
    notes: str = ""
    timestamp: float = 0.0


@dataclass
class TaskTemplate:
    id: str = ""
    name: str = ""
    description: str = ""
    category: TemplateCategory = TemplateCategory.CUSTOM
    steps: list[PlanStep] = field(default_factory=list)
    default_model: str = ""
    default_provider: str = ""
    required_tools: list[str] = field(default_factory=list)
    required_permissions: list[str] = field(default_factory=list)
    estimated_duration: float = 300.0
    estimated_cost: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    tags: list[str] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0
    usage_count: int = 0
    is_builtin: bool = False

    def __post_init__(self):
        if not self.id:
            self.id = f"tpl_{uuid.uuid4().hex[:12]}"


@dataclass
class NLCommand:
    raw_text: str = ""
    intent: str = ""
    goal: str = ""
    schedule: str = ""
    agents: list[AgentRole] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    output_format: str = ""
    constraints: list[str] = field(default_factory=list)
    parameters: dict = field(default_factory=dict)

    def to_objective(self) -> Objective:
        return Objective(
            goal=self.goal,
            constraints=self.constraints,
            output_format=self.output_format,
        )

    def to_schedule(self) -> Optional[dict]:
        if not self.schedule:
            return None
        return {
            "schedule": self.schedule,
            "goal": self.goal,
            "agents": [a.value for a in self.agents],
            "tools": self.tools,
            "permissions": self.permissions,
            "output_format": self.output_format,
        }


@dataclass
class AgentLimits:
    max_steps: int = 50
    max_time: float = 600.0
    max_cost: float = 0.0
    max_tokens: int = 100000
    max_sub_agents: int = 3
    max_parallel_tasks: int = 2
    max_tool_calls: int = 100
    max_context_size: int = 128000


@dataclass
class ValidationRule:
    field: str = ""
    operator: str = "exists"
    expected_value: Any = None
    error_message: str = ""


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


@dataclass
class OrchestrationResult:
    success: bool = True
    plan_id: str = ""
    status: str = "completed"
    output: dict = field(default_factory=dict)
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_duration: float = 0.0
    total_cost: float = 0.0
    error: str = ""
    errors: list[str] = field(default_factory=list)
    checkpoint_id: str = ""


@dataclass
class ExecutionStats:
    total_plans: int = 0
    completed_plans: int = 0
    failed_plans: int = 0
    running_plans: int = 0
    pending_plans: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_duration: float = 0.0
    total_cost: float = 0.0
