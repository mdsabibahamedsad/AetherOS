#!/usr/bin/env python3
"""
Capability Kernel — Core Data Models

Shared data structures used across all capability kernel components.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union
from pathlib import Path


class CapabilityCategory(enum.Enum):
    """High-level capability categories for routing and UI organization."""
    COMPUTER_CONTROL = "computer_control"
    WEB_BROWSER = "web_browser"
    FILE_SYSTEM = "file_system"
    TERMINAL = "terminal"
    CODING = "coding"
    RESEARCH = "research"
    KNOWLEDGE = "knowledge"
    MEMORY = "memory"
    COMMUNICATION = "communication"
    CALENDAR = "calendar"
    AUTOMATION = "automation"
    MULTI_AGENT = "multi_agent"
    MODEL_ORCHESTRATION = "model_orchestration"
    MCP_PLUGIN = "mcp_plugin"
    VOICE = "voice"
    MULTIMODAL = "multimodal"
    CREATIVE = "creative"
    DATA_ANALYSIS = "data_analysis"
    SYSTEM_INTEGRATION = "system_integration"
    SECURITY = "security"
    PERSONAL_ASSISTANT = "personal_assistant"


class RiskLevel(enum.Enum):
    """Risk classification for capabilities and actions."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __lt__(self, other: RiskLevel) -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        return order[self.value] < order[other.value]

    def __le__(self, other: RiskLevel) -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        return order[self.value] <= order[other.value]


class TaskState(enum.Enum):
    """Unified task lifecycle states."""
    CREATED = "created"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    EXECUTING = "executing"
    OBSERVING = "observing"
    VERIFYING = "verifying"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    WAITING_EXTERNAL = "waiting_external"


class TaskSource(enum.Enum):
    """Source of a task request."""
    CHAT = "chat"
    VOICE = "voice"
    JARVIS = "jarvis"
    GLOBAL_HOTKEY = "global_hotkey"
    COMMAND_PALETTE = "command_palette"
    AUTOMATION = "automation"
    SCHEDULED_TASK = "scheduled_task"
    API = "api"
    MCP = "mcp"
    EXTERNAL_TRIGGER = "external_trigger"
    CRON = "cron"
    WEBHOOK = "webhook"


@dataclass
class ToolReference:
    """Reference to a registered tool."""
    name: str
    toolset: str
    schema: Dict[str, Any]
    handler: str  # dotted path to handler function
    check_fn: str | None = None
    requires_env: List[str] = field(default_factory=list)
    is_async: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    permissions: List[str] = field(default_factory=list)
    confirmation_required: bool = False
    sandbox_config: Dict[str, Any] = field(default_factory=dict)
    timeout_config: Dict[str, Any] = field(default_factory=dict)
    retry_config: Dict[str, Any] = field(default_factory=dict)
    supports_streaming: bool = False
    supports_cancellation: bool = False
    supports_background_execution: bool = False
    output_schema: Dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class ModelReference:
    """Reference to a model provider."""
    name: str
    provider: str
    capabilities: List[str] = field(default_factory=list)
    max_tokens: int = 0
    supports_vision: bool = False
    supports_tools: bool = False
    supports_reasoning: bool = False
    supports_streaming: bool = False
    latency_class: str = "standard"  # fast, standard, slow
    cost_class: str = "standard"     # free, low, standard, high
    privacy_level: str = "cloud"     # local, private, cloud


@dataclass
class CapabilityProvider:
    """Provider of a capability (tool, model, MCP, plugin, etc.)."""
    id: str
    name: str
    type: str  # "tool", "model", "mcp", "plugin", "skill", "builtin"
    metadata: Dict[str, Any] = field(default_factory=dict)
    health_status: str = "unknown"
    last_health_check: float = 0.0


@dataclass
class CapabilitySpec:
    """Full specification of a capability."""
    id: str
    name: str
    description: str
    category: CapabilityCategory
    version: str = "1.0.0"
    
    # Input/output schemas
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    
    # Provider references
    tools: List[ToolReference] = field(default_factory=list)
    models: List[ModelReference] = field(default_factory=list)
    providers: List[CapabilityProvider] = field(default_factory=list)
    
    # Execution requirements
    required_permissions: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    confirmation_required: bool = False
    approval_policy: str = "auto"  # auto, user, admin
    
    # Execution environment
    execution_environment: str = "default"  # local, docker, remote, sandbox
    sandbox_config: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    
    # Retry and recovery
    retry_config: Dict[str, Any] = field(default_factory=dict)
    recovery_strategies: List[str] = field(default_factory=list)
    
    # Verification
    verification_strategies: List[str] = field(default_factory=list)
    
    # Availability
    available: bool = True
    availability_check: str | None = None  # dotted path to check function
    tags: List[str] = field(default_factory=list)
    
    # Observability
    observability_enabled: bool = True


@dataclass
class VerificationStrategy:
    """Strategy for verifying capability execution results."""
    name: str
    description: str
    handler: str  # dotted path to verification function
    applies_to: List[str] = field(default_factory=list)  # capability IDs or categories
    required: bool = False  # if True, verification failure = task failure


@dataclass
class RecoveryStrategy:
    """Strategy for recovering from execution failures."""
    name: str
    description: str
    handler: str  # dotted path to recovery function
    applies_to: List[str] = field(default_factory=list)  # error types or capability IDs
    max_attempts: int = 3
    backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    fallback_capability: str | None = None


@dataclass
class CapabilityEntry:
    """Registry entry for a capability (extends CapabilitySpec with runtime data)."""
    spec: CapabilitySpec
    registered_at: datetime = field(default_factory=datetime.now)
    last_used_at: float = 0.0
    use_count: int = 0
    error_count: int = 0
    total_execution_time: float = 0.0
    consecutive_failures: int = 0
    health_status: str = "unknown"  # unknown, healthy, degraded, unhealthy
    last_health_check: float = 0.0
    schema_valid: bool = False


@dataclass
class TaskRequest:
    """Normalized task request entering the command gateway."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: TaskSource = TaskSource.CHAT
    user_intent: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    requested_capabilities: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    permissions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # higher = more urgent
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    correlation_id: str | None = None  # for tracing related tasks


@dataclass
class TaskStep:
    """Single step in a task execution plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    capability_id: str = ""
    tool_name: str = ""
    model_name: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    expected_output: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # step IDs that must complete first
    state: TaskState = TaskState.CREATED
    result: Dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    verification_result: Dict[str, Any] | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskProgress:
    """Real-time progress information for a task."""
    task_id: str
    state: TaskState
    current_step: str | None = None
    steps_completed: int = 0
    steps_total: int = 0
    percent_complete: float = 0.0
    current_action: str = ""
    estimated_remaining_seconds: float | None = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class PlanStep:
    """A single step in a plan."""
    id: str
    name: str
    description: str
    capability_id: str
    tool_name: str
    input_template: Dict[str, Any]  # Template with placeholders
    dependencies: List[str] = field(default_factory=list)
    expected_output: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """A multi-step execution plan."""
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Task:
    """Unified task representation with full lifecycle."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    goal: str = ""
    request: TaskRequest | None = None
    
    # Planning
    plan: List[TaskStep] = field(default_factory=list)
    current_step_index: int = 0
    
    # Execution
    state: TaskState = TaskState.CREATED
    progress: TaskProgress | None = None
    
    # Results
    result: Dict[str, Any] | None = None
    error: str | None = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Verification
    verification_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Recovery
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def get_current_step(self) -> TaskStep | None:
        """Get the currently executing step."""
        if 0 <= self.current_step_index < len(self.plan):
            return self.plan[self.current_step_index]
        return None
    
    def get_next_pending_step(self) -> TaskStep | None:
        """Get the next step that can be executed (dependencies met)."""
        for i, step in enumerate(self.plan):
            if step.state == TaskState.CREATED:
                # Check if all dependencies are completed
                deps_met = all(
                    self.plan[dep_idx].state == TaskState.COMPLETED
                    for dep_idx in step.dependencies
                    if dep_idx < len(self.plan)
                )
                if deps_met:
                    return step
        return None
    
    def can_execute_next(self) -> bool:
        """Check if there's a step ready to execute."""
        return self.get_next_pending_step() is not None


@dataclass
class ExecutionResult:
    """Result of executing a capability step."""
    step_id: str
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    execution_time_ms: float = 0.0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    model_calls: List[Dict[str, Any]] = field(default_factory=list)
    observations: Dict[str, Any] = field(default_factory=dict)
    verification: Dict[str, Any] | None = None
    recovery_applied: str | None = None


@dataclass
class PermissionDecision:
    """Result of a permission check."""
    allowed: bool
    risk_level: RiskLevel
    required_approval: str = "none"  # none, user, admin
    reason: str = ""
    conditions: List[str] = field(default_factory=list)
    expires_at: datetime | None = None


@dataclass
class RoutingDecision:
    """Result of capability routing."""
    capability_id: str
    tool_name: str | None = None
    model_name: str | None = None
    provider_id: str | None = None
    confidence: float = 1.0
    reasoning: str = ""
    alternatives: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_latency_ms: int = 0


# JSON serialization helpers
def to_json_serializable(obj: Any) -> Any:
    """Convert dataclass/enum objects to JSON-serializable form."""
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (list, tuple, set)):
        return [to_json_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: to_json_serializable(v) for k, v in obj.items()}
    if hasattr(obj, '__dataclass_fields__'):
        return {f: to_json_serializable(getattr(obj, f)) for f in obj.__dataclass_fields__}
    return obj