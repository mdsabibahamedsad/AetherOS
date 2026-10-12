"""
AetherOS Kernel v2.0 — Multi-Agent AI Operating System Layer

The kernel is the central orchestrator with full multi-agent support:
  Agent Manager        — register, start, stop, pause, resume, restart agents
  Agent Registry       — complete metadata for every agent
  Planner              — goal decomposition, dependency graphs, execution plans
  Coordinator          — assign tasks, track progress, balance workloads
  Executor             — parallel, sequential, conditional execution with retries
  TaskGraph            — DAG-based task representation with full tracking
  InterAgentBus        — message bus, shared memory, events, task handoff
  SupervisorAgent      — continuous monitoring, health, deadlock detection
  ReviewerAgent        — automated review of code, research, docs, plans
  CriticAgent          — challenge assumptions, detect hallucinations
  ReflectionEngine     — post-execution analysis, learning, improvement
  ApprovalLayer        — human gating for high-risk actions
  ArtifactManager      — versioned artifact storage and retrieval
  SchedulingEngine     — immediate, delayed, recurring, cron, event-based
  EventBus             — pub/sub communication backbone
  ContextManager       — shared context across agents
  PermissionManager    — centralized permission checking
  LifecycleManager     — component startup and shutdown
  StateManager         — kernel state persistence and recovery
"""
from __future__ import annotations

from kernel.kernel import Kernel, KernelConfig

from kernel.lifecycle import LifecycleManager, ComponentState, ServiceRegistration
from kernel.registry import AgentRegistry as ComponentRegistry, ComponentEntry
from kernel.event_bus import EventBus, Event, EventPriority, EventSubscription
from kernel.scheduler import KernelScheduler, ScheduledJob, JobPriority
from kernel.planner import Planner, Plan, PlanStep, PlanStatus
from kernel.executor import Executor, ExecutionResult, ExecutionStatus
from kernel.router import Router, RouteEntry
from kernel.workspace import WorkspaceManager, Workspace
from kernel.context import ContextManager, SharedContext
from kernel.permissions import PermissionManager, PermissionCheck, PermissionAction, PermissionLevel, PermissionRule
from kernel.task_graph import TaskGraph, TaskNode, TaskDependency, GraphStatus
from kernel.telemetry import TelemetryCollector, MetricPoint
from kernel.state_manager import StateManager

from kernel.agent_manager import AgentManager, AgentInstance, AgentLifecycleStatus, AgentHealthStatus, AgentMetadata
from kernel.agent_registry import AgentRegistry, RegistryEntry
from kernel.inter_agent import InterAgentBus, AgentMessage, MessageType, MessagePriority, SharedMemoryEntry, TaskHandoff
from kernel.supervisor import SupervisorAgent, SupervisorAlert, AlertCategory, AlertSeverity
from kernel.reviewer import ReviewerAgent, ReviewResult, ReviewFinding, ReviewSeverity, ReviewCategory
from kernel.critic import CriticAgent, Criticism, CriticismCategory, CriticismSeverity, ReasoningTrace
from kernel.reflection import ReflectionEngine, ReflectionResult, Lesson, LessonCategory, LessonSeverity
from kernel.approval import ApprovalLayer, ApprovalRequest, ApprovalAction, ApprovalStatus, ApprovalPriority, ApprovalPolicy
from kernel.artifact_manager import ArtifactManager, Artifact, ArtifactVersion, ArtifactType, ArtifactVisibility
from kernel.scheduling_engine import SchedulingEngine, ScheduleEntry, ScheduleType, ScheduleStatus

from agents.specialized_agents import (
    SPECIALIZED_AGENT_DEFINITIONS, list_agent_types, list_agent_capabilities,
    create_specialized_agent, ResearchAgent, CodingAgent, DebugAgent,
    ReviewAgent, DocumentationAgent, PlanningAgent, MemoryAgent,
    VisionAgent, VoiceAgent, BrowserAgent, DesktopAgent, AutomationAgent,
)

__all__ = [
    "Kernel", "KernelConfig",
    "LifecycleManager", "ComponentState", "ServiceRegistration",
    "ComponentRegistry", "ComponentEntry",
    "EventBus", "Event", "EventPriority", "EventSubscription",
    "KernelScheduler", "ScheduledJob", "JobPriority",
    "Planner", "Plan", "PlanStep", "PlanStatus",
    "Executor", "ExecutionResult", "ExecutionStatus",
    "Router", "RouteEntry",
    "WorkspaceManager", "Workspace",
    "ContextManager", "SharedContext",
    "PermissionManager", "PermissionCheck", "PermissionAction", "PermissionLevel", "PermissionRule",
    "TaskGraph", "TaskNode", "TaskDependency", "GraphStatus",
    "TelemetryCollector", "MetricPoint",
    "StateManager",
    "AgentManager", "AgentInstance", "AgentLifecycleStatus", "AgentHealthStatus", "AgentMetadata",
    "AgentRegistry", "RegistryEntry",
    "InterAgentBus", "AgentMessage", "MessageType", "MessagePriority", "SharedMemoryEntry", "TaskHandoff",
    "SupervisorAgent", "SupervisorAlert", "AlertCategory", "AlertSeverity",
    "ReviewerAgent", "ReviewResult", "ReviewFinding", "ReviewSeverity", "ReviewCategory",
    "CriticAgent", "Criticism", "CriticismCategory", "CriticismSeverity", "ReasoningTrace",
    "ReflectionEngine", "ReflectionResult", "Lesson", "LessonCategory", "LessonSeverity",
    "ApprovalLayer", "ApprovalRequest", "ApprovalAction", "ApprovalStatus", "ApprovalPriority", "ApprovalPolicy",
    "ArtifactManager", "Artifact", "ArtifactVersion", "ArtifactType", "ArtifactVisibility",
    "SchedulingEngine", "ScheduleEntry", "ScheduleType", "ScheduleStatus",
    "SPECIALIZED_AGENT_DEFINITIONS", "list_agent_types", "list_agent_capabilities",
    "create_specialized_agent", "ResearchAgent", "CodingAgent", "DebugAgent",
    "ReviewAgent", "DocumentationAgent", "PlanningAgent", "MemoryAgent",
    "VisionAgent", "VoiceAgent", "BrowserAgent", "DesktopAgent", "AutomationAgent",
]

__version__ = "2.0.0"