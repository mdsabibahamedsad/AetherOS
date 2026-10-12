"""
Agent Worker — executes tasks by spawning subagents via the kernel.

The worker wraps the existing delegate_task mechanism and kernel executor
to provide a unified interface for running agents within the swarm.
It handles agent lifecycle, result collection, output trimming, and error
handling for subagent execution.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result from running an agent on a task.

    Attributes:
        task_id: The task ID this result belongs to
        agent_type: The agent type that executed
        status: Execution status (completed, error, timeout, cancelled)
        output: The agent's output/response
        error: Error message if failed
        duration_seconds: Execution duration
        token_usage: Token usage stats
        tool_calls: Number of tool calls made
    """
    task_id: str = ""
    agent_type: str = ""
    status: str = "completed"
    output: str = ""
    error: Optional[str] = None
    duration_seconds: float = 0.0
    token_usage: Dict[str, int] = field(default_factory=dict)
    tool_calls: int = 0


class AgentWorker:
    """Executes tasks by spawning subagents.

    Provides a unified interface that abstracts away the details of
    agent creation, execution, and result collection. Can use either
    the kernel's executor or the delegate_task mechanism.

    Usage:
        worker = AgentWorker(event_bus)
        result = worker.run_agent(
            goal="Implement user authentication",
            agent_type="coding-agent",
        )
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._active: Dict[str, AgentResult] = {}

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run_agent(self, goal: str, agent_type: str,
                  context: Dict[str, Any] = None,
                  task_id: str = None,
                  timeout: float = 600.0,
                  plan_context: Dict[str, Any] = None) -> AgentResult:
        """Run an agent on a task.

        Uses the existing delegate_task mechanism to spawn a subagent
        with the appropriate tools and context for the agent type.

        Args:
            goal: The goal/objective for the agent
            agent_type: The agent type to use (e.g. "coding-agent")
            context: Optional additional context
            task_id: Optional task ID
            timeout: Max execution time in seconds
            plan_context: Plan-level shared context

        Returns:
            AgentResult with execution outcome
        """
        exec_id = task_id or uuid.uuid4().hex[:12]
        start = time.time()

        result = AgentResult(
            task_id=exec_id,
            agent_type=agent_type,
            status="running",
        )

        with self._lock:
            self._active[exec_id] = result

        if self._event_bus:
            self._event_bus.emit_async("swarm.worker_task_started", {
                "task_id": exec_id,
                "agent_type": agent_type,
                "goal": goal[:100],
            })

        try:
            output = self._execute_via_delegate(
                goal=goal,
                agent_type=agent_type,
                context=context,
                plan_context=plan_context or {},
            )

            elapsed = time.time() - start
            result.status = "completed"
            result.output = output or ""
            result.duration_seconds = elapsed

        except TimeoutError:
            elapsed = time.time() - start
            result.status = "timeout"
            result.error = f"Task timed out after {timeout}s"
            result.duration_seconds = elapsed

        except Exception as exc:
            elapsed = time.time() - start
            result.status = "error"
            result.error = str(exc)
            result.duration_seconds = elapsed
            logger.error("Worker: agent '%s' failed: %s", agent_type, exc)

        finally:
            with self._lock:
                self._active[exec_id] = result

        if self._event_bus:
            self._event_bus.emit_async("swarm.worker_task_completed", {
                "task_id": exec_id,
                "agent_type": agent_type,
                "status": result.status,
                "duration": result.duration_seconds,
            })

        return result

    def _execute_via_delegate(self, goal: str, agent_type: str,
                              context: Dict[str, Any] = None,
                              plan_context: Dict[str, Any] = None) -> Optional[str]:
        """Execute a task by delegating to a subagent.

        Attempts to use the kernel executor first, then falls back
        to direct delegate_task call.
        """
        # Try kernel executor first
        try:
            from kernel import Kernel

            # Look for a running kernel instance
            # In production, the kernel is passed via context
            kernel = (context or {}).get("kernel") if context else None

            if kernel and hasattr(kernel, "executor"):
                exec_result = kernel.executor.run_agent(
                    agent=None,
                    prompt=goal,
                    timeout_seconds=600,
                )
                if exec_result.status.value == "completed":
                    return exec_result.output
        except Exception:
            pass

        # Fallback: Try the delegate_task mechanism
        try:
            from tools.delegate_tool import delegate_task

            # Build toolsets based on agent type
            toolsets = self._get_toolsets_for_agent(agent_type)

            # Build context
            context_str = ""
            if context:
                context_str = "\n".join(
                    f"{k}: {v}" for k, v in context.items()
                    if isinstance(v, str)
                )

            result_json = delegate_task(
                goal=goal,
                context=context_str or None,
                toolsets=toolsets,
                parent_agent=(context or {}).get("parent_agent"),
            )

            # Parse result
            import json
            try:
                parsed = json.loads(result_json)
                if isinstance(parsed, dict):
                    return parsed.get("summary") or parsed.get("final_response") or result_json
                return result_json
            except (json.JSONDecodeError, TypeError):
                return result_json

        except Exception as exc:
            logger.warning("Worker: delegate_task failed: %s", exc)
            raise

    @staticmethod
    def _get_toolsets_for_agent(agent_type: str) -> List[str]:
        """Get the appropriate toolsets for an agent type."""
        toolset_map = {
            "planning-agent": ["web", "terminal", "file"],
            "coding-agent": ["terminal", "file"],
            "research-agent": ["web", "file"],
            "browser-agent": ["browser", "web", "terminal"],
            "filesystem-agent": ["file", "terminal"],
            "terminal-agent": ["terminal", "file"],
            "documentation-agent": ["file", "web"],
            "testing-agent": ["terminal", "file"],
            "review-agent": ["file", "terminal"],
            "debug-agent": ["terminal", "file", "web"],
            "memory-agent": ["file", "terminal"],
            "plugin-agent": ["file", "terminal"],
            "mcp-agent": ["file", "terminal"],
        }
        return toolset_map.get(agent_type, ["terminal", "file"])

    # ------------------------------------------------------------------
    # State & monitoring
    # ------------------------------------------------------------------

    def get_result(self, task_id: str) -> Optional[AgentResult]:
        """Get the result for a task."""
        with self._lock:
            return self._active.get(task_id)

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get currently active/running tasks."""
        with self._lock:
            return [
                {
                    "task_id": rid,
                    "agent_type": r.agent_type,
                    "status": r.status,
                    "duration": r.duration_seconds,
                }
                for rid, r in self._active.items()
                if r.status == "running"
            ]

    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        with self._lock:
            total = len(self._active)
            completed = sum(1 for r in self._active.values() if r.status == "completed")
            failed = sum(1 for r in self._active.values() if r.status == "error")
            return {
                "total_runs": total,
                "completed": completed,
                "failed": failed,
                "active": sum(1 for r in self._active.values() if r.status == "running"),
            }

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        with self._lock:
            result = self._active.get(task_id)
            if result and result.status == "running":
                result.status = "cancelled"
                result.error = "Task cancelled by user"
                return True
            return False
