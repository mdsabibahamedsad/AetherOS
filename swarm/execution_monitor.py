"""
Execution Monitor — tracks and displays swarm execution progress.

Provides structured progress events and status tracking for:
  - Running agents (current task, status, duration)
  - Completed agents (result summary)
  - Failed agents (error details)
  - Current task position in plan
  - Estimated completion time
  - Resource usage

Emits structured progress events that can be consumed by the UI,
CLI, or dashboard.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus
from swarm.planner import AgentTask, AgentTaskStatus, SwarmPlan

logger = logging.getLogger(__name__)


@dataclass
class AgentProgress:
    """Progress information for a single agent task.

    Attributes:
        task_id: The task ID
        description: Task description
        agent_type: Assigned agent type
        status: Current status
        started_at: When execution started
        duration_seconds: How long it's been running
        result_preview: Preview of the result
        error: Error message if failed
    """
    task_id: str = ""
    description: str = ""
    agent_type: str = ""
    status: str = "pending"
    started_at: Optional[float] = None
    duration_seconds: float = 0.0
    result_preview: str = ""
    error: Optional[str] = None


class ExecutionMonitor:
    """Monitors and reports swarm execution progress.

    Tracks the state of all tasks in a workflow and provides
    structured progress reports. Can emit events for UI updates.

    Usage:
        monitor = ExecutionMonitor(event_bus)
        monitor.register_plan(plan)
        monitor.set_task_running(task.id, "coding-agent")
        report = monitor.get_report()
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._agents: Dict[str, AgentProgress] = {}
        self._plan_info: Dict[str, Dict[str, Any]] = {}
        self._start_time: Optional[float] = None
        self._callbacks: List[Callable[[str, AgentProgress], None]] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_plan(self, plan: SwarmPlan) -> None:
        """Register a plan for monitoring."""
        with self._lock:
            self._plan_info[plan.id] = {
                "goal": plan.goal,
                "total_tasks": len(plan.tasks),
                "started_at": time.time(),
            }
            if self._start_time is None:
                self._start_time = time.time()

            for task in plan.tasks:
                self._agents[task.id] = AgentProgress(
                    task_id=task.id,
                    description=task.description,
                    status="pending",
                )

        logger.info("Monitor: registered plan %s (%d tasks)", plan.id, len(plan.tasks))

        if self._event_bus:
            self._event_bus.emit_async("swarm.monitor_plan_registered", {
                "plan_id": plan.id,
                "task_count": len(plan.tasks),
            })

    def unregister_plan(self, plan_id: str) -> None:
        """Remove a plan from monitoring."""
        with self._lock:
            self._plan_info.pop(plan_id, None)
            # Keep task info for history, just remove plan metadata

    # ------------------------------------------------------------------
    # Status updates
    # ------------------------------------------------------------------

    def set_task_running(self, task_id: str, agent_type: str) -> None:
        """Mark a task as running."""
        with self._lock:
            agent = self._agents.get(task_id)
            if agent:
                agent.status = "running"
                agent.agent_type = agent_type
                agent.started_at = time.time()
                agent.duration_seconds = time.time() - (agent.started_at or time.time())

        self._notify(task_id, "running")

    def set_task_completed(self, task_id: str,
                           result: str = "") -> None:
        """Mark a task as completed."""
        with self._lock:
            agent = self._agents.get(task_id)
            if agent:
                agent.status = "completed"
                agent.result_preview = (result[:200] + "...") if len(result) > 200 else result
                if agent.started_at:
                    agent.duration_seconds = time.time() - agent.started_at

        self._notify(task_id, "completed")

    def set_task_failed(self, task_id: str, error: str) -> None:
        """Mark a task as failed."""
        with self._lock:
            agent = self._agents.get(task_id)
            if agent:
                agent.status = "failed"
                agent.error = error
                if agent.started_at:
                    agent.duration_seconds = time.time() - agent.started_at

        self._notify(task_id, "failed")

    def set_task_cancelled(self, task_id: str) -> None:
        """Mark a task as cancelled."""
        with self._lock:
            agent = self._agents.get(task_id)
            if agent:
                agent.status = "cancelled"

        self._notify(task_id, "cancelled")

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def get_report(self, plan_id: str = None) -> Dict[str, Any]:
        """Get a structured progress report.

        Returns summary stats and per-task details.
        """
        with self._lock:
            if plan_id:
                agents = {
                    tid: ap for tid, ap in self._agents.items()
                }
                plan = self._plan_info.get(plan_id, {})
            else:
                agents = dict(self._agents)
                plan = {}

        now = time.time()
        task_list = list(agents.values())
        total = len(task_list)
        completed = sum(1 for a in task_list if a.status == "completed")
        failed = sum(1 for a in task_list if a.status == "failed")
        running = sum(1 for a in task_list if a.status == "running")

        # Estimate completion
        elapsed = now - (self._start_time or now)
        etc = None
        if completed > 0 and elapsed > 0:
            rate = completed / elapsed
            remaining = total - completed
            etc = remaining / rate if rate > 0 else None

        return {
            "plan": plan,
            "stats": {
                "total": total,
                "completed": completed,
                "failed": failed,
                "running": running,
                "pending": total - completed - failed - running,
                "progress_pct": (completed / total * 100) if total > 0 else 0,
                "elapsed_seconds": elapsed,
                "estimated_completion_pct": etc,
            },
            "agents": [
                {
                    "task_id": a.task_id,
                    "description": a.description[:80],
                    "agent_type": a.agent_type,
                    "status": a.status,
                    "duration_seconds": a.duration_seconds,
                    "result_preview": a.result_preview[:100],
                    "error": a.error,
                }
                for a in task_list
            ],
        }

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def subscribe(self, callback: Callable[[str, AgentProgress], None]) -> Callable:
        """Subscribe to progress updates.

        The callback receives (event_type, agent_progress).
        Returns an unsubscribe function.
        """
        with self._lock:
            self._callbacks.append(callback)

        def unsubscribe():
            with self._lock:
                if callback in self._callbacks:
                    self._callbacks.remove(callback)

        return unsubscribe

    def _notify(self, task_id: str, event_type: str) -> None:
        """Notify subscribers of a progress update."""
        with self._lock:
            agent = self._agents.get(task_id)
            callbacks = list(self._callbacks)

        if agent:
            for cb in callbacks:
                try:
                    cb(event_type, agent)
                except Exception as exc:
                    logger.debug("Monitor: callback failed: %s", exc)

        if self._event_bus:
            self._event_bus.emit_async("swarm.monitor_update", {
                "task_id": task_id,
                "event_type": event_type,
                "status": agent.status if agent else "unknown",
            })

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        with self._lock:
            return {
                "tracked_agents": len(self._agents),
                "tracked_plans": len(self._plan_info),
                "subscribers": len(self._callbacks),
            }
