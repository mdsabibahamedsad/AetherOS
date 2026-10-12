"""
AetherOS Multi-Agent Swarm & Orchestration System.

Extends the AetherOS Kernel with multi-agent coordination capabilities.
Enables multiple specialized agents to work together on the same goal
through structured planning, task allocation, parallel execution,
consensus, and result merging.

Architecture
-----------
The swarm layer sits on top of the kernel and extends it:

    User Goal
         │
         ▼
    ┌─────────────────────────────────────────────────────┐
    │              SwarmOrchestrator                        │
    │                                                       │
    │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
    │  │Planner   │─▶│Allocator │─▶│Dispatcher        │  │
    │  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
    │       │              │                 │              │
    │  ┌────▼─────┐  ┌────▼─────┐  ┌────────▼─────────┐  │
    │  │Registry  │  │Coordinator│  │Scheduler         │  │
    │  └──────────┘  └────┬─────┘  └───┬──────────────┘  │
    │       │              │            │                  │
    │  ┌────▼─────┐  ┌────▼─────┐  ┌───▼──────────────┐  │
    │  │Worker    │  │Consensus │  │ConflictResolver   │  │
    │  └────┬─────┘  └──────────┘  └──────────────────┘  │
    │       │                                              │
    │  ┌────▼─────┐  ┌──────────┐  ┌──────────────────┐  │
    │  │Monitor   │  │Merger   │  │Tracker           │  │
    │  └──────────┘  └──────────┘  └──────────────────┘  │
    └─────────────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────────────────┐
    │              AetherOS Kernel                         │
    │  EventBus │ Executor │ Planner │ Registry │ Context  │
    └─────────────────────────────────────────────────────┘

Designed to be optional — the existing single-agent mode works
unchanged. Multi-agent mode adds capability on top.
"""

from swarm.orchestrator import (
    SwarmOrchestrator,
    SwarmConfig,
    SwarmState,
    SwarmEvent,
)
from swarm.coordinator import Coordinator, WorkflowState
from swarm.planner import SwarmPlanner, SwarmPlan, AgentTask
from swarm.dispatcher import TaskDispatcher
from swarm.scheduler import SwarmScheduler
from swarm.worker import AgentWorker
from swarm.registry import (
    SwarmAgentRegistry,
    AgentTypeProfile,
    AGENT_TYPE_PLANNING,
    AGENT_TYPE_CODING,
    AGENT_TYPE_RESEARCH,
    AGENT_TYPE_BROWSER,
    AGENT_TYPE_FILESYSTEM,
    AGENT_TYPE_TERMINAL,
    AGENT_TYPE_DOCUMENTATION,
    AGENT_TYPE_TESTING,
    AGENT_TYPE_REVIEW,
    AGENT_TYPE_DEBUG,
    AGENT_TYPE_MEMORY,
    AGENT_TYPE_PLUGIN,
    AGENT_TYPE_MCP,
    BUILTIN_AGENT_TYPE_PROFILES,
)
from swarm.capabilities import (
    AgentCapability,
    CapabilityRegistry,
    CAPABILITY_CODING,
    CAPABILITY_RESEARCH,
    CAPABILITY_PLANNING,
    CAPABILITY_REVIEW,
    CAPABILITY_DEBUG,
    CAPABILITY_BROWSER,
    CAPABILITY_FILESYSTEM,
    CAPABILITY_TERMINAL,
    CAPABILITY_TESTING,
    CAPABILITY_DOCUMENTATION,
    CAPABILITY_MEMORY,
    CAPABILITY_MCP,
)
from swarm.communication import (
    InterAgentMessageBus,
    AgentMessage,
    MessageType,
)
from swarm.consensus import ConsensusEngine, ConsensusResult
from swarm.conflict_resolution import (
    ConflictResolver,
    ConflictType,
    ConflictRecord,
)
from swarm.task_allocator import TaskAllocator, Assignment
from swarm.execution_monitor import ExecutionMonitor
from swarm.result_merger import ResultMerger
from swarm.progress_tracker import ProgressTracker

__all__ = [
    "SwarmOrchestrator",
    "SwarmConfig",
    "SwarmState",
    "SwarmEvent",
    "Coordinator",
    "WorkflowState",
    "SwarmPlanner",
    "SwarmPlan",
    "AgentTask",
    "TaskDispatcher",
    "SwarmScheduler",
    "AgentWorker",
    "SwarmAgentRegistry",
    "AgentTypeProfile",
    "AGENT_TYPE_PLANNING",
    "AGENT_TYPE_CODING",
    "AGENT_TYPE_RESEARCH",
    "AGENT_TYPE_BROWSER",
    "AGENT_TYPE_FILESYSTEM",
    "AGENT_TYPE_TERMINAL",
    "AGENT_TYPE_DOCUMENTATION",
    "AGENT_TYPE_TESTING",
    "AGENT_TYPE_REVIEW",
    "AGENT_TYPE_DEBUG",
    "AGENT_TYPE_MEMORY",
    "AGENT_TYPE_PLUGIN",
    "AGENT_TYPE_MCP",
    "BUILTIN_AGENT_TYPE_PROFILES",
    "AgentCapability",
    "CapabilityRegistry",
    "CAPABILITY_CODING",
    "CAPABILITY_RESEARCH",
    "CAPABILITY_PLANNING",
    "CAPABILITY_REVIEW",
    "CAPABILITY_DEBUG",
    "CAPABILITY_BROWSER",
    "CAPABILITY_FILESYSTEM",
    "CAPABILITY_TERMINAL",
    "CAPABILITY_TESTING",
    "CAPABILITY_DOCUMENTATION",
    "CAPABILITY_MEMORY",
    "CAPABILITY_MCP",
    "InterAgentMessageBus",
    "AgentMessage",
    "MessageType",
    "ConsensusEngine",
    "ConsensusResult",
    "ConflictResolver",
    "ConflictType",
    "ConflictRecord",
    "TaskAllocator",
    "Assignment",
    "ExecutionMonitor",
    "ResultMerger",
    "ProgressTracker",
]
