"""Workflow data models — pure dataclasses for the DAG-based workflow engine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


# =============================================================================
# Node Type Registry
# =============================================================================

class NodeCategory(Enum):
    TRIGGER = "trigger"
    AI = "ai"
    LOGIC = "logic"
    ACTION = "action"
    AGENT = "agent"
    MCP = "mcp"


class TriggerType(Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    CRON = "cron"
    WEBHOOK = "webhook"
    EMAIL = "email"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    GITHUB = "github"
    GITLAB = "gitlab"
    FILE_CREATED = "file_created"
    FOLDER_CHANGED = "folder_changed"
    API_REQUEST = "api_request"
    RSS = "rss"


class AINodeType(Enum):
    CHAT = "chat"
    REASONING = "reasoning"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    CODE_GENERATION = "code_generation"
    REVIEW_CODE = "review_code"
    FIX_CODE = "fix_code"
    RESEARCH = "research"
    MEMORY_SEARCH = "memory_search"
    KNOWLEDGE_SEARCH = "knowledge_search"
    IMAGE_ANALYSIS = "image_analysis"
    VISION = "vision"
    VOICE = "voice"
    SPEECH = "speech"


class LogicType(Enum):
    IF = "if"
    ELSE = "else"
    SWITCH = "switch"
    LOOP = "loop"
    FOR_EACH = "for_each"
    WAIT = "wait"
    DELAY = "delay"
    RETRY = "retry"
    ERROR_HANDLER = "error_handler"
    MERGE = "merge"
    SPLIT = "split"
    VARIABLES = "variables"


class ActionType(Enum):
    COPY = "copy"
    MOVE = "move"
    RENAME = "rename"
    DELETE = "delete"
    COMPRESS = "compress"
    EXTRACT = "extract"
    GIT_CLONE = "git_clone"
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"
    GIT_PULL = "git_pull"
    DOCKER = "docker"
    RUN_TERMINAL = "run_terminal"
    PYTHON = "python"
    SHELL = "shell"
    HTTP_REQUEST = "http_request"
    DATABASE = "database"
    EMAIL_SEND = "email_send"
    CALENDAR = "calendar"
    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"
    NOTION = "notion"
    JIRA = "jira"
    LINEAR = "linear"
    CLICKUP = "clickup"
    GITHUB_ISSUE = "github_issue"
    PULL_REQUEST = "pull_request"
    FILESYSTEM = "filesystem"


class AgentNodeType(Enum):
    RUN_AGENT = "run_agent"
    DELEGATE_TASK = "delegate_task"
    RESEARCH_AGENT = "research_agent"
    DEVELOPER_AGENT = "developer_agent"
    REVIEWER_AGENT = "reviewer_agent"
    TESTER_AGENT = "tester_agent"
    SECURITY_AGENT = "security_agent"
    WRITER_AGENT = "writer_agent"


class MCPNodeType(Enum):
    RUN_MCP_TOOL = "run_mcp_tool"
    CONNECT_MCP_SERVER = "connect_mcp_server"
    CALL_TOOL = "call_tool"
    RECEIVE_OUTPUT = "receive_output"


# =============================================================================
# Execution Status
# =============================================================================

class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class WorkflowStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    ERROR = "error"


# =============================================================================
# Core Node Model
# =============================================================================

@dataclass
class NodePosition:
    x: float = 0
    y: float = 0

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, d: dict) -> NodePosition:
        return cls(x=d.get("x", 0), y=d.get("y", 0))


@dataclass
class Connection:
    id: str = ""
    source_id: str = ""
    source_output: str = "output"
    target_id: str = ""
    target_input: str = "input"
    label: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {"id": self.id, "source_id": self.source_id,
                "source_output": self.source_output, "target_id": self.target_id,
                "target_input": self.target_input, "label": self.label}

    @classmethod
    def from_dict(cls, d: dict) -> Connection:
        return cls(id=d.get("id", ""), source_id=d.get("source_id", ""),
                   source_output=d.get("source_output", "output"),
                   target_id=d.get("target_id", ""),
                   target_input=d.get("target_input", "input"),
                   label=d.get("label", ""))


@dataclass
class WorkflowNode:
    id: str = ""
    type: str = ""                    # e.g. "trigger.manual", "ai.chat", "logic.if"
    category: str = NodeCategory.TRIGGER.value
    label: str = ""
    description: str = ""
    position: NodePosition = field(default_factory=NodePosition)
    config: dict = field(default_factory=dict)
    inputs: list[dict] = field(default_factory=lambda: [{"id": "input", "label": "Input", "type": "any"}])
    outputs: list[dict] = field(default_factory=lambda: [{"id": "output", "label": "Output", "type": "any"}])
    enabled: bool = True
    notes: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type, "category": self.category,
            "label": self.label, "description": self.description,
            "position": self.position.to_dict(), "config": self.config,
            "inputs": self.inputs, "outputs": self.outputs,
            "enabled": self.enabled, "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> WorkflowNode:
        return cls(
            id=d.get("id", ""), type=d.get("type", ""), category=d.get("category", ""),
            label=d.get("label", ""), description=d.get("description", ""),
            position=NodePosition.from_dict(d.get("position", {})),
            config=d.get("config", {}),
            inputs=d.get("inputs", [{"id": "input", "label": "Input", "type": "any"}]),
            outputs=d.get("outputs", [{"id": "output", "label": "Output", "type": "any"}]),
            enabled=d.get("enabled", True), notes=d.get("notes", ""),
        )


# =============================================================================
# Workflow Model
# =============================================================================

@dataclass
class ExecutionRecord:
    id: str = ""
    workflow_id: str = ""
    status: str = ExecutionStatus.PENDING.value
    trigger: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0
    nodes_total: int = 0
    nodes_completed: int = 0
    nodes_failed: int = 0
    logs: list[dict] = field(default_factory=list)
    error: str = ""
    input_data: dict = field(default_factory=dict)
    output_data: Any = None

    def to_dict(self) -> dict:
        return {"id": self.id, "workflow_id": self.workflow_id, "status": self.status,
                "trigger": self.trigger, "started_at": self.started_at,
                "completed_at": self.completed_at, "duration_ms": self.duration_ms,
                "nodes_total": self.nodes_total, "nodes_completed": self.nodes_completed,
                "nodes_failed": self.nodes_failed, "logs": self.logs, "error": self.error,
                "input_data": self.input_data, "output_data": self.output_data}

    @classmethod
    def from_dict(cls, d: dict) -> ExecutionRecord:
        return cls(id=d.get("id", ""), workflow_id=d.get("workflow_id", ""),
                   status=d.get("status", "pending"), trigger=d.get("trigger", ""),
                   started_at=d.get("started_at", ""), completed_at=d.get("completed_at", ""),
                   duration_ms=d.get("duration_ms", 0.0),
                   nodes_total=d.get("nodes_total", 0), nodes_completed=d.get("nodes_completed", 0),
                   nodes_failed=d.get("nodes_failed", 0), logs=d.get("logs", []),
                   error=d.get("error", ""), input_data=d.get("input_data", {}),
                   output_data=d.get("output_data"))


@dataclass
class WorkflowVersion:
    version: int = 1
    created_at: str = ""
    nodes: list[dict] = field(default_factory=list)
    connections: list[dict] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    comment: str = ""

    def to_dict(self) -> dict:
        return {"version": self.version, "created_at": self.created_at,
                "nodes": self.nodes, "connections": self.connections,
                "config": self.config, "comment": self.comment}

    @classmethod
    def from_dict(cls, d: dict) -> WorkflowVersion:
        return cls(version=d.get("version", 1), created_at=d.get("created_at", ""),
                   nodes=d.get("nodes", []), connections=d.get("connections", []),
                   config=d.get("config", {}), comment=d.get("comment", ""))


@dataclass
class WorkflowConfig:
    id: str = ""
    name: str = "New Workflow"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    category: str = "general"
    status: str = WorkflowStatus.DRAFT.value
    nodes: list[WorkflowNode] = field(default_factory=list)
    connections: list[Connection] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    version: int = 1
    versions: list[WorkflowVersion] = field(default_factory=list)
    schedule: str = ""
    error_policy: str = "stop"
    max_retries: int = 3
    timeout_seconds: int = 3600
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    background: bool = False

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "tags": self.tags, "category": self.category, "status": self.status.value if isinstance(self.status, WorkflowStatus) else self.status,
            "nodes": [n.to_dict() for n in self.nodes],
            "connections": [c.to_dict() for c in self.connections],
            "config": self.config, "version": self.version,
            "versions": [v.to_dict() for v in self.versions],
            "schedule": self.schedule,
            "error_policy": self.error_policy, "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "created_by": self.created_by, "background": self.background,
        }

    @classmethod
    def from_dict(cls, d: dict) -> WorkflowConfig:
        return cls(
            id=d.get("id", ""), name=d.get("name", "New Workflow"),
            description=d.get("description", ""), tags=d.get("tags", []),
            category=d.get("category", "general"),
            status=d.get("status", WorkflowStatus.DRAFT.value),
            nodes=[WorkflowNode.from_dict(n) for n in d.get("nodes", [])],
            connections=[Connection.from_dict(c) for c in d.get("connections", [])],
            config=d.get("config", {}), version=d.get("version", 1),
            versions=[WorkflowVersion.from_dict(v) for v in d.get("versions", [])],
            schedule=d.get("schedule", ""),
            error_policy=d.get("error_policy", "stop"),
            max_retries=d.get("max_retries", 3),
            timeout_seconds=d.get("timeout_seconds", 3600),
            created_at=d.get("created_at", ""), updated_at=d.get("updated_at", ""),
            created_by=d.get("created_by", ""), background=d.get("background", False),
        )

    def snapshot_version(self, comment: str = "") -> WorkflowVersion:
        return WorkflowVersion(
            version=len(self.versions) + 1,
            created_at=datetime.utcnow().isoformat() + "Z",
            nodes=[n.to_dict() for n in self.nodes],
            connections=[c.to_dict() for c in self.connections],
            config=dict(self.config),
            comment=comment,
        )
