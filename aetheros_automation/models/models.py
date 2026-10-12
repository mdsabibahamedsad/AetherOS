from __future__ import annotations

import time, uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ExecutionMode(Enum):
    MANUAL = "manual"
    ASSISTED = "assisted"
    SEMI_AUTONOMOUS = "semi_autonomous"
    FULLY_AUTONOMOUS = "fully_autonomous"


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    BLOCKED = "blocked"
    ROLLED_BACK = "rolled_back"
    TIMEOUT = "timeout"
    EMERGENCY_STOPPED = "emergency_stopped"


class AgentRole(Enum):
    PLANNER = "planner"
    DEVELOPER = "developer"
    BROWSER = "browser"
    RESEARCH = "research"
    WRITER = "writer"
    QA = "qa"
    DEPLOYMENT = "deployment"
    SECURITY = "security"
    MEMORY = "memory"
    COORDINATOR = "coordinator"
    CREATIVE = "creative"
    DATA = "data"
    COMMUNICATION = "communication"
    REVIEW = "review"
    CODING = "coding"
    FILE = "file"


class GraphExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    DEPENDENT = "dependent"
    RETRY = "retry"
    FALLBACK = "fallback"
    HUMAN_APPROVAL = "human_approval"


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FailureType(Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    PROVIDER_ERROR = "provider_error"
    TOOL_ERROR = "tool_error"
    PERMISSION_DENIED = "permission_denied"
    MODEL_ERROR = "model_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


class ApprovalAction(Enum):
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
    APPROVE_ONCE = "approve_once"
    APPROVE_SESSION = "approve_session"
    ALWAYS_ALLOW = "always_allow"
    DENY = "deny"
    DENY_SESSION = "deny_session"


class Permission(Enum):
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    FILESYSTEM_DELETE = "filesystem_delete"
    NETWORK = "network"
    BROWSER = "browser"
    MICROPHONE = "microphone"
    CAMERA = "camera"
    LOCATION = "location"
    NOTIFICATIONS = "notifications"
    CLIPBOARD = "clipboard"
    TERMINAL = "terminal"
    EXECUTE_CODE = "execute_code"
    INSTALL_SOFTWARE = "install_software"
    SEND_EMAIL = "send_email"
    PUBLISH_CODE = "publish_code"
    DEPLOY = "deploy"
    SHUTDOWN = "shutdown"
    PAYMENT = "payment"


@dataclass
class AutomationConfig:
    execution_mode: ExecutionMode = ExecutionMode.ASSISTED
    max_concurrent_tasks: int = 5
    task_timeout: float = 3600.0
    retry_limit: int = 3
    checkpoint_interval: float = 30.0
    enable_undo: bool = True
    enable_checkpoints: bool = True
    enable_live_display: bool = True
    sandbox_enabled: bool = True
    auto_rollback_on_failure: bool = False
    emergency_stop_key: str = "ctrl+shift+x"
    mobile_notifications: bool = False
    default_agent: AgentRole = AgentRole.COORDINATOR


@dataclass
class Task:
    id: str = ""
    name: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    steps: list[TaskStep] = field(default_factory=list)
    agent: AgentRole = AgentRole.COORDINATOR
    dependencies: list[str] = field(default_factory=list)
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    assigned_to: str = ""
    result: str = ""
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    requires_approval: bool = False
    approval_granted: bool = False
    approval_required_for: list[str] = field(default_factory=list)
    checkpoint_data: dict = field(default_factory=dict)
    parent_task_id: str = ""
    subtasks: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    estimated_duration: float = 0.0
    actual_duration: float = 0.0
    progress: float = 0.0
    priority: int = 0
    timeout: Optional[float] = None
    logs: list[LogEntry] = field(default_factory=list)
    undo_actions: list[UndoAction] = field(default_factory=list)


@dataclass
class TaskStep:
    id: str = ""
    name: str = ""
    action: str = ""
    params: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    retry_count: int = 0


@dataclass
class LogEntry:
    timestamp: float = 0.0
    level: str = "info"
    message: str = ""
    source: str = ""


@dataclass
class UndoAction:
    id: str = ""
    action_type: str = ""
    description: str = ""
    data: dict = field(default_factory=dict)
    timestamp: float = 0.0
    restored: bool = False


@dataclass
class ApprovalRequest:
    id: str = ""
    task_id: str = ""
    action: str = ""
    description: str = ""
    details: dict = field(default_factory=dict)
    status: str = "pending"
    created_at: float = 0.0
    responded_at: float = 0.0
    response: str = ""
    responded_by: str = ""


@dataclass
class Workflow:
    id: str = ""
    name: str = ""
    description: str = ""
    tasks: list[Task] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    checkpoint_path: str = ""
    graph: dict = field(default_factory=dict)


@dataclass
class AgentContext:
    role: AgentRole = AgentRole.COORDINATOR
    task_id: str = ""
    instructions: str = ""
    tools: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    parent_id: str = ""


@dataclass
class BrowserConfig:
    browser_type: str = "chrome"
    headless: bool = False
    user_data_dir: str = ""
    proxy: str = ""
    timeout: float = 30.0
    viewport_width: int = 1280
    viewport_height: int = 720


@dataclass
class FileOperation:
    action: str = "read"
    source_path: str = ""
    dest_path: str = ""
    content: str = ""
    recursive: bool = False
    compress_format: str = "zip"
    encrypt_method: str = "aes"


@dataclass
class DocumentSpec:
    title: str = ""
    format: str = "markdown"
    content: str = ""
    template: str = ""
    output_path: str = ""


@dataclass
class EmailSpec:
    to: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    subject: str = ""
    body: str = ""
    attachments: list[str] = field(default_factory=list)
    action: str = "send"


@dataclass
class CalendarEvent:
    title: str = ""
    description: str = ""
    start_time: str = ""
    end_time: str = ""
    attendees: list[str] = field(default_factory=list)
    location: str = ""
    reminders: list[int] = field(default_factory=list)
    action: str = "create"
