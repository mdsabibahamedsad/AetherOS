from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from typing import Any

from aetheros_automation.models.models import (
    AgentRole, ApprovalAction, ApprovalResponse,
    ExecutionMode, FailureType, GraphExecutionMode, RiskLevel,
    Task, TaskPriority, TaskStatus, Workflow,
)


@dataclass
class OrchestrationPlan:
    id: str = ""
    goal: str = ""
    description: str = ""
    subtasks: list[OrchestrationTask] = field(default_factory=list)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    required_tools: list[str] = field(default_factory=list)
    required_agents: list[AgentRole] = field(default_factory=list)
    required_permissions: list[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_time: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    created_at: float = 0.0
    execution_graph: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionState:
    plan_id: str = ""
    current_task_id: str = ""
    completed_tasks: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)
    failed_tasks: list[str] = field(default_factory=list)
    running_tasks: list[str] = field(default_factory=list)
    paused: bool = False
    cancelled: bool = False
    checkpoint_path: str = ""
    started_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class AgentMessage:
    id: str = ""
    sender_id: str = ""
    receiver_id: str = ""
    message_type: str = "text"
    content: str = ""
    data: Any = None
    task_id: str = ""
    created_at: float = 0.0


@dataclass
class OrchestrationTask:
    id: str = ""
    name: str = ""
    description: str = ""
    agent_role: AgentRole = AgentRole.COORDINATOR
    model: str = ""
    provider: str = ""
    tools: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    execution_mode: GraphExecutionMode = GraphExecutionMode.SEQUENTIAL
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    result: Any = None
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    requires_approval: bool = False
    approval_actions: list[ApprovalAction] = field(default_factory=list)
    approval_response: ApprovalResponse | None = None
    checkpoint_data: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    estimated_duration: float = 0.0
    actual_duration: float = 0.0
    cost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentAssignment:
    agent_id: str = ""
    role: AgentRole = AgentRole.COORDINATOR
    name: str = ""
    model: str = ""
    provider: str = ""
    tools: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    knowledge: list[str] = field(default_factory=list)
    limits: dict[str, Any] = field(default_factory=dict)
    personality: str = ""
    instructions: str = ""
    parent_agent_id: str = ""
    is_sub_agent: bool = False
