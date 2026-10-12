"""
Progress Tracker — structured progress event emission for the swarm.

Provides fine-grained progress tracking and event emission for swarm
execution. Integrates with the kernel event bus to publish structured
progress events that consumers (UI, CLI, dashboard) can subscribe to.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks and emits structured progress events for swarm execution.

    Provides a clean API for reporting progress at multiple granularity
    levels and emits typed events through the kernel event bus.

    Usage:
        tracker = ProgressTracker(event_bus)
        tracker.report_workflow_started("wf-1", "Build project")
        tracker.report_task_assigned("wf-1", "task-1", "coding-agent")
        tracker.report_task_progress("wf-1", "task-1", 50)
        tracker.report_task_completed("wf-1", "task-1")
        tracker.report_workflow_completed("wf-1")
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._workflow_states: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Workflow events
    # ------------------------------------------------------------------

    def report_workflow_started(self, workflow_id: str, goal: str,
                                task_count: int = 0) -> None:
        """Report that a workflow has started."""
        with self._lock:
            self._workflow_states[workflow_id] = {
                "goal": goal,
                "task_count": task_count,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "started_at": time.time(),
            }

        self._emit("workflow.started", {
            "workflow_id": workflow_id,
            "goal": goal[:200],
            "task_count": task_count,
        })

    def report_workflow_progress(self, workflow_id: str,
                                 completed: int, failed: int,
                                 total: int) -> None:
        """Report workflow-level progress."""
        with self._lock:
            state = self._workflow_states.get(workflow_id)
            if state:
                state["completed_tasks"] = completed
                state["failed_tasks"] = failed

        pct = (completed / total * 100) if total > 0 else 0
        self._emit("workflow.progress", {
            "workflow_id": workflow_id,
            "completed": completed,
            "failed": failed,
            "total": total,
            "progress_pct": pct,
        })

    def report_workflow_completed(self, workflow_id: str,
                                  result: str = "") -> None:
        """Report that a workflow has completed."""
        self._emit("workflow.completed", {
            "workflow_id": workflow_id,
            "result_preview": result[:200] if result else "",
        })

    def report_workflow_failed(self, workflow_id: str, error: str) -> None:
        """Report that a workflow has failed."""
        self._emit("workflow.failed", {
            "workflow_id": workflow_id,
            "error": error[:200],
        })

    def report_workflow_cancelled(self, workflow_id: str) -> None:
        """Report that a workflow was cancelled."""
        self._emit("workflow.cancelled", {
            "workflow_id": workflow_id,
        })

    # ------------------------------------------------------------------
    # Task events
    # ------------------------------------------------------------------

    def report_task_assigned(self, workflow_id: str, task_id: str,
                             description: str, agent_type: str) -> None:
        """Report that a task was assigned to an agent type."""
        self._emit("task.assigned", {
            "workflow_id": workflow_id,
            "task_id": task_id,
            "description": description[:100],
            "agent_type": agent_type,
        })

    def report_task_started(self, workflow_id: str, task_id: str) -> None:
        """Report that a task has started execution."""
        self._emit("task.started", {
            "workflow_id": workflow_id,
            "task_id": task_id,
        })

    def report_task_progress(self, workflow_id: str, task_id: str,
                             progress_pct: float) -> None:
        """Report progress within a single task."""
        self._emit("task.progress", {
            "workflow_id": workflow_id,
            "task_id": task_id,
            "progress_pct": progress_pct,
        })

    def report_task_completed(self, workflow_id: str, task_id: str,
                              result_preview: str = "") -> None:
        """Report that a task completed successfully."""
        self._emit("task.completed", {
            "workflow_id": workflow_id,
            "task_id": task_id,
            "result_preview": result_preview[:200] if result_preview else "",
        })

    def report_task_failed(self, workflow_id: str, task_id: str,
                           error: str) -> None:
        """Report that a task failed."""
        self._emit("task.failed", {
            "workflow_id": workflow_id,
            "task_id": task_id,
            "error": error[:200],
        })

    def report_task_cancelled(self, workflow_id: str, task_id: str) -> None:
        """Report that a task was cancelled."""
        self._emit("task.cancelled", {
            "workflow_id": workflow_id,
            "task_id": task_id,
        })

    # ------------------------------------------------------------------
    # Agent events
    # ------------------------------------------------------------------

    def report_agent_started(self, workflow_id: str, agent_id: str,
                             agent_type: str, goal: str) -> None:
        """Report that an agent started working on a task."""
        self._emit("agent.started", {
            "workflow_id": workflow_id,
            "agent_id": agent_id,
            "agent_type": agent_type,
            "goal": goal[:100],
        })

    def report_agent_tool_call(self, workflow_id: str, agent_id: str,
                               tool_name: str) -> None:
        """Report that an agent is calling a tool."""
        self._emit("agent.tool_call", {
            "workflow_id": workflow_id,
            "agent_id": agent_id,
            "tool_name": tool_name,
        })

    def report_agent_completed(self, workflow_id: str, agent_id: str,
                               duration: float, tool_calls: int) -> None:
        """Report that an agent finished its work."""
        self._emit("agent.completed", {
            "workflow_id": workflow_id,
            "agent_id": agent_id,
            "duration_seconds": duration,
            "tool_calls": tool_calls,
        })

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit a progress event."""
        if self._event_bus:
            self._event_bus.emit_async(f"swarm.{event_type}", data)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the current state of a tracked workflow."""
        with self._lock:
            state = self._workflow_states.get(workflow_id)
            if state:
                return dict(state)
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        with self._lock:
            return {
                "tracked_workflows": len(self._workflow_states),
            }

    def cleanup(self) -> None:
        """Clear all tracked state."""
        with self._lock:
            self._workflow_states.clear()
