"""
Swarm Orchestrator — manages the lifecycle of the multi-agent swarm.

The orchestrator is the main entry point for the swarm system. It:
  - Starts and stops the swarm
  - Manages agent lifecycle (registration, activation, deactivation)
  - Coordinates task execution across agents
  - Monitors swarm health
  - Handles failure recovery at the swarm level

Integrates with the AetherOS Kernel for event bus, registry, and
execution infrastructure.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus
from swarm.registry import SwarmAgentRegistry
from swarm.capabilities import CapabilityRegistry
from swarm.planner import SwarmPlanner
from swarm.task_allocator import TaskAllocator
from swarm.dispatcher import TaskDispatcher
from swarm.worker import AgentWorker
from swarm.coordinator import Coordinator
from swarm.communication import InterAgentMessageBus
from swarm.consensus import ConsensusEngine
from swarm.conflict_resolution import ConflictResolver
from swarm.execution_monitor import ExecutionMonitor
from swarm.result_merger import ResultMerger
from swarm.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class SwarmState(enum.Enum):
    """States of the swarm orchestrator."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


class SwarmEvent(enum.Enum):
    """Events emitted by the swarm orchestrator."""
    SWARM_STARTED = "swarm.started"
    SWARM_STOPPED = "swarm.stopped"
    SWARM_FAILED = "swarm.failed"
    AGENT_REGISTERED = "swarm.agent_registered"
    AGENT_DEREGISTERED = "swarm.agent_deregistered"
    WORKFLOW_STARTED = "swarm.workflow_started"
    WORKFLOW_COMPLETED = "swarm.workflow_completed"


@dataclass
class SwarmConfig:
    """Configuration for the swarm system.

    Attributes:
        max_concurrent_agents: Max parallel agent executions
        enable_consensus: Enable consensus engine for disagreeing agents
        enable_conflict_resolution: Enable conflict detection/resolution
        enable_communication: Enable inter-agent messaging
        auto_register_agents: Register built-in agent types on start
        default_timeout_seconds: Default agent execution timeout
        max_retries_per_task: Default max retries per task
    """
    max_concurrent_agents: int = 3
    enable_consensus: bool = True
    enable_conflict_resolution: bool = True
    enable_communication: bool = True
    auto_register_agents: bool = True
    default_timeout_seconds: float = 600.0
    max_retries_per_task: int = 0


class SwarmOrchestrator:
    """Main orchestrator for the AetherOS multi-agent swarm.

    Manages the complete lifecycle of the swarm system. Provides
    the main API for running multi-agent workflows.

    Usage:
        config = SwarmConfig(max_concurrent_agents=5)
        swarm = SwarmOrchestrator(kernel_event_bus, config)
        swarm.start()

        result = swarm.run_workflow("Build a web application")
        print(result["merged_result"])

        swarm.stop()
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        config: Optional[SwarmConfig] = None,
    ):
        self.config = config or SwarmConfig()
        self._event_bus = event_bus
        self._state = SwarmState.STOPPED
        self._lock = threading.RLock()
        self._start_time: Optional[float] = None
        self._shutdown_flag = False

        # Create subsystems
        self.message_bus = InterAgentMessageBus(event_bus)
        self.agent_registry = SwarmAgentRegistry(
            event_bus, load_builtins=config.auto_register_agents if config else True,
        )
        self.capability_registry = CapabilityRegistry(load_builtins=True)

        self.planner = SwarmPlanner(event_bus)
        self.worker = AgentWorker(event_bus)
        self.allocator = TaskAllocator(self.agent_registry, event_bus)
        self.dispatcher = TaskDispatcher(self.allocator, self.worker, event_bus)
        self.merger = ResultMerger()
        self.coordinator = Coordinator(self.planner, self.dispatcher, self.merger, event_bus)
        self.monitor = ExecutionMonitor(event_bus)
        self.progress_tracker = ProgressTracker(event_bus)
        self.consensus = ConsensusEngine(event_bus)
        self.conflict_resolver = ConflictResolver(event_bus)

        # Workflow tracking
        self._active_workflows: Dict[str, str] = {}  # workflow_id -> goal

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def state(self) -> SwarmState:
        """Get the current swarm state."""
        with self._lock:
            return self._state

    def start(self) -> None:
        """Start the swarm orchestrator.

        Initializes all subsystems and registers agent types.
        Emits SWARM_STARTED event.
        """
        with self._lock:
            if self._state == SwarmState.RUNNING:
                logger.warning("SwarmOrchestrator: already running")
                return
            self._state = SwarmState.STARTING

        logger.info("SwarmOrchestrator: starting...")
        self._start_time = time.time()

        # Verify agent types are registered
        agent_count = len(self.agent_registry.list_agent_types())
        logger.info(
            "SwarmOrchestrator: registered %d agent types, %d capabilities",
            agent_count,
            len(self.capability_registry.list_capabilities()),
        )

        with self._lock:
            self._state = SwarmState.RUNNING

        if self._event_bus:
            self._event_bus.emit(SwarmEvent.SWARM_STARTED.value, {
                "agent_types": agent_count,
                "max_concurrent": self.config.max_concurrent_agents,
                "consensus_enabled": self.config.enable_consensus,
            })

        logger.info(
            "SwarmOrchestrator: started (agents=%d, max_concurrent=%d)",
            agent_count, self.config.max_concurrent_agents,
        )

    def stop(self) -> None:
        """Stop the swarm orchestrator gracefully.

        Cancels any active workflows and shuts down subsystems.
        """
        with self._lock:
            if self._state != SwarmState.RUNNING:
                return
            self._state = SwarmState.STOPPING

        logger.info("SwarmOrchestrator: stopping...")

        # Cancel active workflows
        for wf_id in list(self._active_workflows.keys()):
            self.coordinator.cancel_workflow(wf_id)

        # Release all conflict locks
        self.conflict_resolver.release_all()

        with self._lock:
            self._state = SwarmState.STOPPED
            self._active_workflows.clear()

        if self._event_bus:
            self._event_bus.emit(SwarmEvent.SWARM_STOPPED.value, {})

        uptime = time.time() - (self._start_time or time.time())
        logger.info("SwarmOrchestrator: stopped (uptime: %.1fs)", uptime)

    def is_running(self) -> bool:
        """Check if the swarm is running."""
        return self.state == SwarmState.RUNNING

    # ------------------------------------------------------------------
    # Workflow execution
    # ------------------------------------------------------------------

    def run_workflow(self, goal: str,
                     context: Dict[str, Any] = None,
                     workflow_id: str = None,
                     progress_callback: Optional[Callable] = None,
                     max_parallel: Optional[int] = None) -> Dict[str, Any]:
        """Run a complete multi-agent workflow from goal to result.

        This is the main API for running multi-agent tasks.

        Args:
            goal: The high-level goal/objective
            context: Optional context (workspace, project info, etc.)
            workflow_id: Optional unique workflow ID
            progress_callback: Optional callback for progress events
            max_parallel: Max parallel agent executions

        Returns:
            Dict with merged result, task details, and workflow metadata
        """
        if self.state != SwarmState.RUNNING:
            return {
                "error": "Swarm is not running. Call start() first.",
                "status": "failed",
            }

        wf_id = workflow_id or uuid.uuid4().hex[:12]
        with self._lock:
            self._active_workflows[wf_id] = goal

        # Inject kernel context for worker
        workflow_context = {
            **(context or {}),
            "kernel": (context or {}).get("kernel"),
        }

        max_par = max_parallel or self.config.max_concurrent_agents

        if self._event_bus:
            self._event_bus.emit_async(SwarmEvent.WORKFLOW_STARTED.value, {
                "workflow_id": wf_id,
                "goal": goal[:200],
            })

        try:
            result = self.coordinator.run_goal(
                goal=goal,
                context=workflow_context,
                workflow_id=wf_id,
                progress_callback=progress_callback,
                max_parallel=max_par,
            )
        except Exception as exc:
            logger.error("SwarmOrchestrator: workflow %s failed: %s", wf_id, exc)
            result = {
                "workflow_id": wf_id,
                "goal": goal,
                "status": "failed",
                "error": str(exc),
                "merged_result": {"merged_output": "", "summary": f"Workflow failed: {exc}"},
                "tasks": [],
                "stats": {"total": 0, "completed": 0, "failed": 0},
            }

        if self._event_bus:
            self._event_bus.emit_async(SwarmEvent.WORKFLOW_COMPLETED.value, {
                "workflow_id": wf_id,
                "status": result.get("status", "unknown"),
            })

        with self._lock:
            self._active_workflows.pop(wf_id, None)

        return result

    # ------------------------------------------------------------------
    # Subsystem access
    # ------------------------------------------------------------------

    def get_coordinator(self) -> Coordinator:
        """Get the coordinator for the swarm."""
        return self.coordinator

    def get_planner(self) -> SwarmPlanner:
        """Get the planner for the swarm."""
        return self.planner

    def get_registry(self) -> SwarmAgentRegistry:
        """Get the agent type registry."""
        return self.agent_registry

    def get_monitor(self) -> ExecutionMonitor:
        """Get the execution monitor."""
        return self.monitor

    # ------------------------------------------------------------------
    # Status & health
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Get swarm health status."""
        return {
            "state": self.state.value,
            "running": self.is_running(),
            "uptime_seconds": time.time() - (self._start_time or time.time()),
            "agent_types": len(self.agent_registry.list_agent_types()),
            "capabilities": len(self.capability_registry.list_capabilities()),
            "active_workflows": len(self._active_workflows),
        }

    def status(self) -> Dict[str, Any]:
        """Get comprehensive swarm status."""
        return {
            "orchestrator": self.health(),
            "registry": self.agent_registry.snapshot(),
            "coordinator": self.coordinator.get_stats(),
            "dispatcher": self.dispatcher.get_stats(),
            "allocator": self.allocator.get_stats(),
            "worker": self.worker.get_stats(),
            "monitor": self.monitor.get_stats(),
            "consensus": self.consensus.get_stats(),
            "conflict_resolver": self.conflict_resolver.get_stats(),
            "message_bus": self.message_bus.get_stats(),
            "progress_tracker": self.progress_tracker.get_stats(),
        }

    # ------------------------------------------------------------------
    # Agent management (for plugins)
    # ------------------------------------------------------------------

    def register_agent_type(self, profile) -> bool:
        """Register a new agent type (e.g., from a plugin).

        Returns True if successful.
        """
        try:
            from swarm.registry import AgentTypeProfile

            if not isinstance(profile, AgentTypeProfile):
                profile = AgentTypeProfile(
                    name=str(getattr(profile, "name", "unknown")),
                    description=str(getattr(profile, "description", "")),
                    capabilities=set(getattr(profile, "capabilities", [])),
                )

            self.agent_registry.register(profile)
            logger.info("SwarmOrchestrator: registered agent type '%s'", profile.name)

            if self._event_bus:
                self._event_bus.emit_async(SwarmEvent.AGENT_REGISTERED.value, {
                    "name": profile.name,
                    "capabilities": list(profile.capabilities),
                })

            return True
        except Exception as exc:
            logger.error("SwarmOrchestrator: failed to register agent type: %s", exc)
            return False

    def deregister_agent_type(self, name: str) -> bool:
        """Remove a registered agent type."""
        result = self.agent_registry.deregister(name)
        if result and self._event_bus:
            self._event_bus.emit_async(SwarmEvent.AGENT_DEREGISTERED.value, {
                "name": name,
            })
        return result
