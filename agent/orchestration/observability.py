"""Observability System for AetherOS Orchestration Layer.

Implements Phases 61-67 of Master Prompt 11: structured events, live progress,
user-facing explanations, task timeline, and task/agent inspectors.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

from agent.orchestration.types import (
    TaskSpec,
    TaskResult,
    TaskStatus,
    TaskPriority,
    AgentIdentity,
    AgentRole,
    VerificationReport,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Event Types
# =============================================================================


class OrchestrationEventType(Enum):
    """Types of orchestration events."""

    # Task lifecycle
    TASK_CREATED = "task_created"
    TASK_QUEUED = "task_queued"
    TASK_PLANNING = "task_planning"
    TASK_READY = "task_ready"
    TASK_STARTED = "task_started"
    TASK_WAITING = "task_waiting"
    TASK_BLOCKED = "task_blocked"
    TASK_VERIFYING = "task_verifying"
    TASK_REQUIRES_APPROVAL = "task_requires_approval"
    TASK_PAUSED = "task_paused"
    TASK_RESUMED = "task_resumed"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_TIMED_OUT = "task_timed_out"
    TASK_EMERGENCY_STOPPED = "task_emergency_stopped"

    # Plan lifecycle
    PLAN_CREATED = "plan_created"
    PLAN_UPDATED = "plan_updated"
    PLAN_VERSIONED = "plan_versioned"

    # Agent lifecycle
    AGENT_ASSIGNED = "agent_assigned"
    AGENT_STARTED = "agent_started"
    AGENT_FINISHED = "agent_finished"
    AGENT_HEALTH_CHANGED = "agent_health_changed"

    # Tool lifecycle
    TOOL_STARTED = "tool_started"
    TOOL_FINISHED = "tool_finished"
    TOOL_FAILED = "tool_failed"

    # Handoff
    HANDOFF_INITIATED = "handoff_initiated"
    HANDOFF_COMPLETED = "handoff_completed"
    HANDOFF_FAILED = "handoff_failed"

    # Verification
    VERIFICATION_STARTED = "verification_started"
    VERIFICATION_FINISHED = "verification_finished"
    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"

    # Approval
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    APPROVAL_EXPIRED = "approval_expired"

    # Budget
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"

    # Retry/Fallback
    RETRY_ATTEMPT = "retry_attempt"
    FALLBACK_USED = "fallback_used"

    # System
    CHECKPOINT_CREATED = "checkpoint_created"
    CHECKPOINT_RESTORED = "checkpoint_restored"
    RECOVERY_INITIATED = "recovery_initiated"


@dataclass
class OrchestrationEvent:
    """Structured orchestration event."""

    event_id: str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    event_type: OrchestrationEventType = OrchestrationEventType.TASK_CREATED
    timestamp: float = field(default_factory=time.time)
    task_id: str = ""
    plan_id: str = ""
    agent_id: str = ""
    user_id: str = ""
    project_id: str = ""
    session_id: str = ""
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    level: str = "info"  # debug, info, warning, error
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "task_id": self.task_id,
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "message": self.message,
            "data": self.data,
            "level": self.level,
            "tags": self.tags,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


# =============================================================================
# Event Store
# =============================================================================


class EventStore:
    """Stores and queries orchestration events."""

    def __init__(self, max_events: int = 100000):
        self._events: List[OrchestrationEvent] = []
        self._max_events = max_events
        self._indexes: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(list))
        self._lock = asyncio.Lock()

    async def add(self, event: OrchestrationEvent) -> None:
        """Add an event to the store."""
        async with self._lock:
            index = len(self._events)
            self._events.append(event)

            # Update indexes
            self._indexes["task_id"][event.task_id].append(index)
            self._indexes["plan_id"][event.plan_id].append(index)
            self._indexes["agent_id"][event.agent_id].append(index)
            self._indexes["user_id"][event.user_id].append(index)
            self._indexes["event_type"][event.event_type.value].append(index)
            self._indexes["session_id"][event.session_id].append(index)

            # Trim if needed
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
                self._rebuild_indexes()

    def _rebuild_indexes(self) -> None:
        """Rebuild indexes after trimming."""
        self._indexes.clear()
        for i, event in enumerate(self._events):
            self._indexes["task_id"][event.task_id].append(i)
            self._indexes["plan_id"][event.plan_id].append(i)
            self._indexes["agent_id"][event.agent_id].append(i)
            self._indexes["user_id"][event.user_id].append(i)
            self._indexes["event_type"][event.event_type.value].append(i)
            self._indexes["session_id"][event.session_id].append(i)

    async def query(
        self,
        task_id: str = "",
        plan_id: str = "",
        agent_id: str = "",
        user_id: str = "",
        event_type: OrchestrationEventType = None,
        session_id: str = "",
        start_time: float = 0,
        end_time: float = 0,
        limit: int = 100,
    ) -> List[OrchestrationEvent]:
        """Query events with filters."""
        # Start with all events
        candidates = set(range(len(self._events)))

        # Apply filters via indexes
        if task_id and task_id in self._indexes["task_id"]:
            candidates &= set(self._indexes["task_id"][task_id])
        if plan_id and plan_id in self._indexes["plan_id"]:
            candidates &= set(self._indexes["plan_id"][plan_id])
        if agent_id and agent_id in self._indexes["agent_id"]:
            candidates &= set(self._indexes["agent_id"][agent_id])
        if user_id and user_id in self._indexes["user_id"]:
            candidates &= set(self._indexes["user_id"][user_id])
        if event_type and event_type.value in self._indexes["event_type"]:
            candidates &= set(self._indexes["event_type"][event_type.value])
        if session_id and session_id in self._indexes["session_id"]:
            candidates &= set(self._indexes["session_id"][session_id])

        # Filter by time
        results = []
        for idx in sorted(candidates, reverse=True):
            event = self._events[idx]
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            results.append(event)
            if len(results) >= limit:
                break

        return results

    async def get_task_timeline(self, task_id: str) -> List[OrchestrationEvent]:
        """Get complete timeline for a task."""
        return await self.query(task_id=task_id, limit=1000)


# =============================================================================
# Event Emitter
# =============================================================================


class EventEmitter:
    """Emits orchestration events with callbacks."""

    def __init__(self, event_store: Optional[EventStore] = None):
        self._store = event_store or EventStore()
        self._callbacks: Dict[OrchestrationEventType, List[Callable[[OrchestrationEvent], None]]] = defaultdict(list)
        self._wildcard_callbacks: List[Callable[[OrchestrationEvent], None]] = []

    def on(self, event_type: OrchestrationEventType, callback: Callable[[OrchestrationEvent], None]) -> None:
        """Register callback for event type."""
        self._callbacks[event_type].append(callback)

    def on_any(self, callback: Callable[[OrchestrationEvent], None]) -> None:
        """Register callback for all events."""
        self._wildcard_callbacks.append(callback)

    def off(self, event_type: OrchestrationEventType, callback: Callable[[OrchestrationEvent], None]) -> bool:
        """Unregister callback."""
        if event_type in self._callbacks:
            try:
                self._callbacks[event_type].remove(callback)
                return True
            except ValueError:
                pass
        return False

    async def emit(self, event: OrchestrationEvent) -> None:
        """Emit an event."""
        # Store event
        await self._store.add(event)

        # Call specific callbacks
        for callback in self._callbacks.get(event.event_type, []):
            try:
                await self._safe_call(callback, event)
            except Exception as e:
                logger.warning(f"Event callback failed for {event.event_type}: {e}")

        # Call wildcard callbacks
        for callback in self._wildcard_callbacks:
            try:
                await self._safe_call(callback, event)
            except Exception as e:
                logger.warning(f"Wildcard callback failed: {e}")

    async def _safe_call(self, callback: Callable, event: OrchestrationEvent) -> None:
        """Safely call callback (sync or async)."""
        if asyncio.iscoroutinefunction(callback):
            await callback(event)
        else:
            callback(event)

    def get_store(self) -> EventStore:
        """Get the event store."""
        return self._store


# =============================================================================
# Live Progress Tracker
# =============================================================================


@dataclass
class TaskProgress:
    """Live progress for a task."""

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0  # 0.0 - 1.0
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    current_agent: str = ""
    current_tool: str = ""
    started_at: float = 0
    updated_at: float = field(default_factory=time.time)
    estimated_completion: float = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ProgressTracker:
    """Tracks live progress of tasks."""

    def __init__(self, event_emitter: Optional[EventEmitter] = None):
        self._progress: Dict[str, TaskProgress] = {}
        self._emitter = event_emitter
        self._callbacks: List[Callable[[TaskProgress], None]] = []
        self._lock = asyncio.Lock()

    def register_callback(self, callback: Callable[[TaskProgress], None]) -> None:
        """Register progress update callback."""
        self._callbacks.append(callback)

    async def update(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[float] = None,
        current_step: str = "",
        total_steps: int = 0,
        completed_steps: int = 0,
        current_agent: str = "",
        current_tool: str = "",
        estimated_completion: float = 0,
        error: str = "",
        warning: str = "",
    ) -> None:
        """Update task progress."""
        async with self._lock:
            prog = self._progress.get(task_id)
            if not prog:
                prog = TaskProgress(task_id=task_id)
                self._progress[task_id] = prog

            if status:
                prog.status = status
            if progress is not None:
                prog.progress = max(0.0, min(1.0, progress))
            if current_step:
                prog.current_step = current_step
            if total_steps:
                prog.total_steps = total_steps
            if completed_steps:
                prog.completed_steps = completed_steps
            if current_agent:
                prog.current_agent = current_agent
            if current_tool:
                prog.current_tool = current_tool
            if estimated_completion:
                prog.estimated_completion = estimated_completion
            if error:
                prog.errors.append(error)
            if warning:
                prog.warnings.append(warning)

            prog.updated_at = time.time()

            # Emit event
            if self._emitter:
                await self._emitter.emit(OrchestrationEvent(
                    event_type=self._status_to_event_type(prog.status),
                    task_id=task_id,
                    message=f"Progress: {prog.progress*100:.0f}% - {prog.current_step}",
                    data=prog.__dict__,
                ))

        # Notify callbacks
        for cb in self._callbacks:
            try:
                cb(prog)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    def _status_to_event_type(self, status: TaskStatus) -> OrchestrationEventType:
        mapping = {
            TaskStatus.PENDING: OrchestrationEventType.TASK_CREATED,
            TaskStatus.QUEUED: OrchestrationEventType.TASK_QUEUED,
            TaskStatus.PLANNING: OrchestrationEventType.TASK_PLANNING,
            TaskStatus.READY: OrchestrationEventType.TASK_READY,
            TaskStatus.RUNNING: OrchestrationEventType.TASK_STARTED,
            TaskStatus.WAITING: OrchestrationEventType.TASK_WAITING,
            TaskStatus.BLOCKED: OrchestrationEventType.TASK_BLOCKED,
            TaskStatus.VERIFYING: OrchestrationEventType.TASK_VERIFYING,
            TaskStatus.REQUIRES_APPROVAL: OrchestrationEventType.TASK_REQUIRES_APPROVAL,
            TaskStatus.PAUSED: OrchestrationEventType.TASK_PAUSED,
            TaskStatus.COMPLETED: OrchestrationEventType.TASK_COMPLETED,
            TaskStatus.FAILED: OrchestrationEventType.TASK_FAILED,
            TaskStatus.CANCELLED: OrchestrationEventType.TASK_CANCELLED,
            TaskStatus.TIMEOUT: OrchestrationEventType.TASK_TIMED_OUT,
            TaskStatus.EMERGENCY_STOPPED: OrchestrationEventType.TASK_EMERGENCY_STOPPED,
        }
        return mapping.get(status, OrchestrationEventType.TASK_CREATED)

    def get_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Get current progress for a task."""
        return self._progress.get(task_id)

    def get_all_progress(self) -> List[TaskProgress]:
        """Get progress for all tasks."""
        return list(self._progress.values())

    def clear(self, task_id: str) -> None:
        """Clear progress for a task."""
        self._progress.pop(task_id, None)


# =============================================================================
# User-Facing Explanation Generator
# =============================================================================


class ExplanationGenerator:
    """Generates user-facing explanations of what the orchestrator is doing."""

    @staticmethod
    def explain_task_status(progress: TaskProgress) -> str:
        """Generate explanation for task status."""
        explanations = {
            TaskStatus.PENDING: "Task is waiting to be scheduled",
            TaskStatus.QUEUED: "Task is queued for execution",
            TaskStatus.PLANNING: "Planning how to accomplish the task",
            TaskStatus.READY: "Task is ready to start",
            TaskStatus.RUNNING: f"Executing: {progress.current_step or 'working...'}",
            TaskStatus.WAITING: "Waiting for external resource or dependency",
            TaskStatus.BLOCKED: f"Blocked: {progress.errors[-1] if progress.errors else 'unknown reason'}",
            TaskStatus.VERIFYING: "Verifying results",
            TaskStatus.REQUIRES_APPROVAL: "Waiting for your approval to continue",
            TaskStatus.PAUSED: "Task paused",
            TaskStatus.COMPLETED: "Task completed successfully",
            TaskStatus.FAILED: f"Task failed: {progress.errors[-1] if progress.errors else 'unknown error'}",
            TaskStatus.CANCELLED: "Task was cancelled",
            TaskStatus.TIMEOUT: "Task timed out",
        }
        return explanations.get(progress.status, f"Status: {progress.status.value}")

    @staticmethod
    def explain_agent_action(agent_role: AgentRole, action: str, tool: str = "") -> str:
        """Explain what an agent is doing."""
        role_descriptions = {
            AgentRole.COORDINATOR: "Coordinating the overall task",
            AgentRole.PLANNER: "Planning the approach",
            AgentRole.DEVELOPER: "Writing or modifying code",
            AgentRole.CODING: "Implementing code",
            AgentRole.BROWSER: "Browsing the web",
            AgentRole.RESEARCH: "Researching information",
            AgentRole.WRITER: "Writing content",
            AgentRole.QA: "Running tests and quality checks",
            AgentRole.DEPLOYMENT: "Handling deployment",
            AgentRole.SECURITY: "Performing security checks",
            AgentRole.MEMORY: "Managing memory and knowledge",
            AgentRole.CREATIVE: "Creative work",
            AgentRole.DATA: "Analyzing data",
            AgentRole.COMMUNICATION: "Sending messages",
            AgentRole.REVIEW: "Reviewing work",
            AgentRole.FILE: "File operations",
            AgentRole.VISION: "Analyzing images",
            AgentRole.AUDIO: "Processing audio",
            AgentRole.VIDEO: "Processing video",
            AgentRole.COMPUTER: "Controlling computer",
        }

        base = role_descriptions.get(agent_role, f"Agent ({agent_role.value})")
        if action:
            base += f" - {action}"
        if tool:
            base += f" using {tool}"
        return base

    @staticmethod
    def explain_plan(plan: Dict[str, Any]) -> str:
        """Explain a plan in user-friendly terms."""
        lines = [f"Plan: {plan.get('goal', 'Unknown goal')}"]

        subtasks = plan.get("subtasks", [])
        if subtasks:
            lines.append(f"Steps ({len(subtasks)}):")
            for i, task in enumerate(subtasks, 1):
                role = task.get("preferred_agent_role", "unknown")
                lines.append(f"  {i}. {task.get('goal', 'Unknown')} [{role}]")

        return "\n".join(lines)

    @staticmethod
    def explain_handoff(handoff: Dict[str, Any]) -> str:
        """Explain an agent handoff."""
        return (
            f"Handing off from {handoff.get('source_agent', 'unknown')} "
            f"to {handoff.get('target_agent', 'unknown')}: "
            f"{handoff.get('reason', 'Continuing work')}"
        )

    @staticmethod
    def explain_verification(report: VerificationReport) -> str:
        """Explain verification results."""
        if report.verified:
            return f"✅ Verified with {report.confidence*100:.0f}% confidence"
        else:
            issues = "; ".join(report.discrepancies[:3])
            return f"❌ Verification failed ({report.confidence*100:.0f}%): {issues}"


# =============================================================================
# Task Timeline
# =============================================================================


class TaskTimeline:
    """Builds and manages task execution timelines."""

    def __init__(self, event_store: EventStore):
        self._store = event_store

    async def build_timeline(self, task_id: str) -> Dict[str, Any]:
        """Build a complete timeline for a task."""
        events = await self._store.query(task_id=task_id, limit=1000)

        timeline = {
            "task_id": task_id,
            "events": [],
            "phases": [],
            "duration": 0,
            "agents_involved": set(),
            "tools_used": set(),
            "verifications": [],
            "approvals": [],
            "handoffs": [],
        }

        start_time = None
        end_time = None

        for event in events:
            event_data = event.to_dict()
            timeline["events"].append(event_data)

            if start_time is None or event.timestamp < start_time:
                start_time = event.timestamp
            if end_time is None or event.timestamp > end_time:
                end_time = event.timestamp

            if event.agent_id:
                timeline["agents_involved"].add(event.agent_id)

            if event.event_type == OrchestrationEventType.TOOL_STARTED:
                tool = event.data.get("tool", "")
                if tool:
                    timeline["tools_used"].add(tool)

            if event.event_type in (OrchestrationEventType.VERIFICATION_STARTED,
                                    OrchestrationEventType.VERIFICATION_FINISHED,
                                    OrchestrationEventType.VERIFICATION_PASSED,
                                    OrchestrationEventType.VERIFICATION_FAILED):
                timeline["verifications"].append(event_data)

            if event.event_type in (OrchestrationEventType.APPROVAL_REQUESTED,
                                    OrchestrationEventType.APPROVAL_GRANTED,
                                    OrchestrationEventType.APPROVAL_DENIED):
                timeline["approvals"].append(event_data)

            if event.event_type in (OrchestrationEventType.HANDOFF_INITIATED,
                                    OrchestrationEventType.HANDOFF_COMPLETED,
                                    OrchestrationEventType.HANDOFF_FAILED):
                timeline["handoffs"].append(event_data)

        # Convert sets to lists
        timeline["agents_involved"] = list(timeline["agents_involved"])
        timeline["tools_used"] = list(timeline["tools_used"])

        if start_time and end_time:
            timeline["duration"] = end_time - start_time

        # Identify phases
        timeline["phases"] = self._identify_phases(events)

        return timeline

    def _identify_phases(self, events: List[OrchestrationEvent]) -> List[Dict[str, Any]]:
        """Identify major phases from events."""
        phases = []
        current_phase = None

        for event in events:
            phase_name = self._event_to_phase(event.event_type)
            if phase_name and phase_name != (current_phase["name"] if current_phase else None):
                if current_phase:
                    current_phase["end_time"] = event.timestamp
                    current_phase["duration"] = current_phase["end_time"] - current_phase["start_time"]
                    phases.append(current_phase)

                current_phase = {
                    "name": phase_name,
                    "start_time": event.timestamp,
                    "events": [event.to_dict()],
                }
            elif current_phase:
                current_phase["events"].append(event.to_dict())

        if current_phase:
            current_phase["end_time"] = events[-1].timestamp if events else current_phase["start_time"]
            current_phase["duration"] = current_phase["end_time"] - current_phase["start_time"]
            phases.append(current_phase)

        return phases

    def _event_to_phase(self, event_type: OrchestrationEventType) -> Optional[str]:
        """Map event type to phase name."""
        mapping = {
            OrchestrationEventType.TASK_CREATED: "Initialization",
            OrchestrationEventType.TASK_PLANNING: "Planning",
            OrchestrationEventType.TASK_STARTED: "Execution",
            OrchestrationEventType.TASK_VERIFYING: "Verification",
            OrchestrationEventType.TASK_REQUIRES_APPROVAL: "Approval",
            OrchestrationEventType.HANDOFF_INITIATED: "Handoff",
            OrchestrationEventType.TASK_COMPLETED: "Completion",
            OrchestrationEventType.TASK_FAILED: "Failure",
        }
        return mapping.get(event_type)


# =============================================================================
# Task Inspector
# =============================================================================


class TaskInspector:
    """Inspects task state, history, and details."""

    def __init__(
        self,
        event_store: EventStore,
        progress_tracker: ProgressTracker,
        budget_controller: Any = None,
    ):
        self._store = event_store
        self._progress = progress_tracker
        self._budget = budget_controller

    async def inspect_task(self, task_id: str) -> Dict[str, Any]:
        """Get comprehensive task inspection."""
        progress = self._progress.get_progress(task_id)
        timeline = await TaskTimeline(self._store).build_timeline(task_id)

        result = {
            "task_id": task_id,
            "current_status": progress.status.value if progress else "unknown",
            "progress": progress.progress if progress else 0,
            "current_step": progress.current_step if progress else "",
            "current_agent": progress.current_agent if progress else "",
            "current_tool": progress.current_tool if progress else "",
            "errors": progress.errors if progress else [],
            "warnings": progress.warnings if progress else [],
            "timeline": timeline,
        }

        if self._budget:
            # Would need task object for full budget status
            pass

        return result

    async def inspect_agent(self, agent_id: str) -> Dict[str, Any]:
        """Inspect an agent's current state."""
        events = await self._store.query(agent_id=agent_id, limit=100)

        active_tasks = set()
        for event in events:
            if event.task_id:
                active_tasks.add(event.task_id)

        return {
            "agent_id": agent_id,
            "active_tasks": list(active_tasks),
            "recent_events": [e.to_dict() for e in events[-20:]],
            "event_count": len(events),
        }


# =============================================================================
# Agent Inspector
# =============================================================================


class AgentInspector:
    """Inspects agent capabilities, status, and performance."""

    def __init__(
        self,
        event_store: EventStore,
        agent_registry: Any = None,
    ):
        self._store = event_store
        self._registry = agent_registry

    async def inspect_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive agent inspection."""
        events = await self._store.query(agent_id=agent_id, limit=500)

        # Calculate metrics
        task_events = [e for e in events if e.task_id]
        completed_tasks = set()
        failed_tasks = set()

        for e in task_events:
            if e.event_type in (OrchestrationEventType.TASK_COMPLETED, OrchestrationEventType.TASK_FINISHED):
                completed_tasks.add(e.task_id)
            elif e.event_type in (OrchestrationEventType.TASK_FAILED, OrchestrationEventType.TASK_CANCELLED):
                failed_tasks.add(e.task_id)

        total_tasks = len(completed_tasks) + len(failed_tasks)
        success_rate = len(completed_tasks) / total_tasks if total_tasks > 0 else 0

        # Tool usage
        tool_events = [e for e in events if e.event_type in (OrchestrationEventType.TOOL_STARTED, OrchestrationEventType.TOOL_FINISHED)]
        tools_used = defaultdict(int)
        for e in tool_events:
            tool = e.data.get("tool", "")
            if tool:
                tools_used[tool] += 1

        return {
            "agent_id": agent_id,
            "tasks_completed": len(completed_tasks),
            "tasks_failed": len(failed_tasks),
            "success_rate": success_rate,
            "tools_used": dict(tools_used),
            "recent_events": [e.to_dict() for e in events[-10:]],
            "total_events": len(events),
        }

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents with basic info."""
        # Get unique agent IDs from events
        all_events = await self._store.query(limit=10000)
        agent_ids = set(e.agent_id for e in all_events if e.agent_id)

        agents = []
        for aid in agent_ids:
            insp = await self.inspect_agent(aid)
            agents.append({
                "agent_id": aid,
                "tasks_completed": insp["tasks_completed"],
                "tasks_failed": insp["tasks_failed"],
                "success_rate": insp["success_rate"],
            })

        return agents


# =============================================================================
# Observability Facade
# =============================================================================


class ObservabilityManager:
    """Unified observability interface."""

    def __init__(self):
        self._store = EventStore()
        self._emitter = EventEmitter(self._store)
        self._progress = ProgressTracker(self._emitter)
        self._timeline = TaskTimeline(self._store)
        self._task_inspector = TaskInspector(self._store, self._progress)
        self._agent_inspector = AgentInspector(self._store)
        self._explanation = ExplanationGenerator()

    @property
    def events(self) -> EventEmitter:
        return self._emitter

    @property
    def progress(self) -> ProgressTracker:
        return self._progress

    @property
    def timeline(self) -> TaskTimeline:
        return self._timeline

    @property
    def tasks(self) -> TaskInspector:
        return self._task_inspector

    @property
    def agents(self) -> AgentInspector:
        return self._agent_inspector

    @property
    def explanation(self) -> ExplanationGenerator:
        return self._explanation

    async def emit_task_event(
        self,
        event_type: OrchestrationEventType,
        task_id: str,
        message: str = "",
        **kwargs,
    ) -> None:
        """Convenience method to emit task event."""
        await self._emitter.emit(OrchestrationEvent(
            event_type=event_type,
            task_id=task_id,
            message=message,
            data=kwargs,
        ))


# =============================================================================
# Factory
# =============================================================================


def create_observability_manager() -> ObservabilityManager:
    """Create observability manager with all components."""
    return ObservabilityManager()


__all__ = [
    "OrchestrationEventType",
    "OrchestrationEvent",
    "EventStore",
    "EventEmitter",
    "TaskProgress",
    "ProgressTracker",
    "ExplanationGenerator",
    "TaskTimeline",
    "TaskInspector",
    "AgentInspector",
    "ObservabilityManager",
    "create_observability_manager",
]