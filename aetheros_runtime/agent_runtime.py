"""Agent Runtime — planner, executor, critic, reflector, supervisor, coordinator.

Each agent role runs independently with its own context and lifecycle.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aetheros_runtime.agents")


class AgentRole(enum.Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    REFLECTOR = "reflector"
    SUPERVISOR = "supervisor"
    COORDINATOR = "coordinator"


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: AgentRole = AgentRole.EXECUTOR
    goal: str = ""
    context: str = ""
    result: Optional[str] = None
    status: str = "pending"
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    parent_id: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed_ms(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        if self.started_at:
            return (time.time() - self.started_at) * 1000
        return 0.0


@dataclass
class AgentResult:
    success: bool
    output: str = ""
    error: str = ""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_elapsed_ms: float = 0.0


AgentHandler = Callable[[AgentTask], str]


class AgentRuntime:
    """Multi-agent runtime with independent roles.

    Each role (planner, executor, critic, reflector, supervisor, coordinator)
    runs independently with its own handler and lifecycle.
    """

    DEFAULT_HANDLERS: Dict[AgentRole, str] = {
        AgentRole.PLANNER: "Plans tasks and decomposes complex goals",
        AgentRole.EXECUTOR: "Executes tasks and produces results",
        AgentRole.CRITIC: "Reviews outputs for quality and correctness",
        AgentRole.REFLECTOR: "Analyzes results and suggests improvements",
        AgentRole.SUPERVISOR: "Oversees task execution and approves decisions",
        AgentRole.COORDINATOR: "Coordinates between multiple agents",
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._handlers: Dict[AgentRole, AgentHandler] = {}
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._tasks: Dict[str, AgentTask] = {}
        self._task_history: List[AgentTask] = []
        self._max_history: int = 500

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_handler(self, role: AgentRole, handler: AgentHandler) -> None:
        with self._lock:
            self._handlers[role] = handler

    def register_agent(self, agent_id: str, role: AgentRole, metadata: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._agents[agent_id] = {
                "id": agent_id,
                "role": role,
                "metadata": metadata or {},
                "tasks_completed": 0,
                "tasks_failed": 0,
                "created_at": time.time(),
            }

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._agents.values())

    def remove_agent(self, agent_id: str) -> bool:
        with self._lock:
            return self._agents.pop(agent_id, None) is not None

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    def create_task(
        self,
        goal: str,
        role: AgentRole = AgentRole.EXECUTOR,
        context: str = "",
        parent_id: Optional[str] = None,
    ) -> AgentTask:
        task = AgentTask(role=role, goal=goal, context=context, parent_id=parent_id)
        with self._lock:
            self._tasks[task.id] = task
        logger.info("Task created: %s (%s)", task.id[:8], role.value)
        return task

    def execute_task(self, task_id: str, agent_id: str = "") -> AgentTask:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")

        task.started_at = time.time()
        task.status = "running"

        handler = self._handlers.get(task.role)
        if not handler:
            task.status = "failed"
            task.error = f"No handler for role: {task.role.value}"
            task.completed_at = time.time()
            self._record_task(task)
            return task

        try:
            result = handler(task)
            task.result = result
            task.status = "completed"
            task.completed_at = time.time()
            with self._lock:
                agent = self._agents.get(agent_id) if agent_id else None
                if agent:
                    agent["tasks_completed"] += 1
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
            task.completed_at = time.time()
            with self._lock:
                agent = self._agents.get(agent_id) if agent_id else None
                if agent:
                    agent["tasks_failed"] += 1

        self._record_task(task)
        return task

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status not in ("pending", "running"):
                return False
            task.status = "cancelled"
            task.completed_at = time.time()
            return True

    def get_pending_tasks(self) -> List[AgentTask]:
        with self._lock:
            return [t for t in self._tasks.values() if t.status == "pending"]

    def get_active_tasks(self) -> List[AgentTask]:
        with self._lock:
            return [t for t in self._tasks.values() if t.status == "running"]

    # ------------------------------------------------------------------
    # Workflow patterns
    # ------------------------------------------------------------------

    def plan_and_execute(self, goal: str) -> AgentResult:
        planner_task = self.create_task(goal, AgentRole.PLANNER)
        planner_task = self.execute_task(planner_task.id)

        if planner_task.status != "completed":
            return AgentResult(success=False, error=planner_task.error or "Planning failed")

        executor_task = self.create_task(goal, AgentRole.EXECUTOR, context=planner_task.result or "")
        executor_task = self.execute_task(executor_task.id)

        critic_task = self.create_task(
            f"Review: {goal}", AgentRole.CRITIC,
            context=f"Plan: {planner_task.result}\nResult: {executor_task.result}",
        )
        critic_task = self.execute_task(critic_task.id)

        return AgentResult(
            success=executor_task.status == "completed",
            output=executor_task.result or "",
            tasks_completed=sum(1 for t in [planner_task, executor_task, critic_task] if t.status == "completed"),
            tasks_failed=sum(1 for t in [planner_task, executor_task, critic_task] if t.status == "failed"),
        )

    def reflect(self, task_id: str) -> Optional[str]:
        task = self.get_task(task_id)
        if not task or not task.result:
            return None

        reflect_task = self.create_task(
            f"Reflect on: {task.goal}", AgentRole.REFLECTOR,
            context=f"Goal: {task.goal}\nResult: {task.result}",
        )
        reflect_task = self.execute_task(reflect_task.id)
        return reflect_task.result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _record_task(self, task: AgentTask) -> None:
        with self._lock:
            self._task_history.append(task)
            if len(self._task_history) > self._max_history:
                self._task_history.pop(0)

    def get_task_history(self, limit: int = 20) -> List[AgentTask]:
        with self._lock:
            return list(self._task_history[-limit:])

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._task_history)
            completed = sum(1 for t in self._task_history if t.status == "completed")
            failed = sum(1 for t in self._task_history if t.status == "failed")
            return {
                "agents": len(self._agents),
                "total_tasks": total,
                "completed": completed,
                "failed": failed,
                "active": len([t for t in self._tasks.values() if t.status == "running"]),
            }

    def summary(self) -> str:
        s = self.stats()
        return (
            f"Agent Runtime: {s['agents']} agents, "
            f"{s['total_tasks']} tasks ({s['completed']} completed, {s['failed']} failed, {s['active']} active)"
        )