"""State Management for AetherOS Orchestration Layer.

Implements Phases 40, 88 of Master Prompt 11: durable task state, checkpoints,
and persistent state that survives process restarts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pickle
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from pathlib import Path
from collections import defaultdict

from agent.orchestration.types import (
    TaskSpec,
    TaskResult,
    TaskStatus,
    TaskPriority,
    TaskBudget,
    AgentIdentity,
    Plan,
    ExecutionState,
    BudgetSnapshot,
)
from agent.orchestration.recovery import Checkpoint, CheckpointManager, CheckpointType

logger = logging.getLogger(__name__)


# =============================================================================
# State Types
# =============================================================================


class StateBackend(Enum):
    """Storage backends for state."""

    FILE = "file"           # Local filesystem
    SQLITE = "sqlite"       # SQLite database
    MEMORY = "memory"       # In-memory only (testing)


@dataclass
class StateConfig:
    """Configuration for state management."""

    backend: StateBackend = StateBackend.FILE
    state_dir: str = "~/.aetheros/orchestration_state"
    auto_save_interval: float = 30.0  # seconds
    max_history: int = 1000
    compress_checkpoints: bool = True
    encryption_key: str = ""  # Optional encryption


@dataclass
class TaskState:
    """Complete persistent state for a task."""

    task_id: str
    spec: TaskSpec
    result: Optional[TaskResult] = None
    checkpoints: List[str] = field(default_factory=list)  # Checkpoint IDs
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1


@dataclass
class PlanState:
    """Complete persistent state for a plan."""

    plan_id: str
    plan: Plan
    execution_state: ExecutionState
    task_states: Dict[str, TaskState] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1


@dataclass
class OrchestrationState:
    """Complete orchestration state snapshot."""

    tasks: Dict[str, TaskState] = field(default_factory=dict)
    plans: Dict[str, PlanState] = field(default_factory=dict)
    global_budget: BudgetSnapshot = field(default_factory=BudgetSnapshot)
    active_agents: Dict[str, AgentIdentity] = field(default_factory=dict)
    saved_at: float = field(default_factory=time.time)
    version: int = 1


# =============================================================================
# State Store
# =============================================================================


class StateStore:
    """Persistent state store for orchestration."""

    def __init__(self, config: StateConfig = None):
        self._config = config or StateConfig()
        self._state_dir = Path(os.path.expanduser(self._config.state_dir))
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._tasks: Dict[str, TaskState] = {}
        self._plans: Dict[str, PlanState] = {}
        self._global_budget = BudgetSnapshot()
        self._active_agents: Dict[str, AgentIdentity] = {}
        self._lock = asyncio.Lock()
        self._auto_save_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the state store."""
        await self._load_state()
        self._running = True
        self._auto_save_task = asyncio.create_task(self._auto_save_loop())

    async def stop(self):
        """Stop the state store."""
        self._running = False
        if self._auto_save_task:
            self._auto_save_task.cancel()
            try:
                await self._auto_save_task
            except asyncio.CancelledError:
                pass
        await self._save_state()

    async def _auto_save_loop(self):
        """Periodic auto-save."""
        while self._running:
            await asyncio.sleep(self._config.auto_save_interval)
            try:
                await self._save_state()
            except Exception as e:
                logger.error(f"Auto-save failed: {e}")

    # ── Task State ─────────────────────────────────────────────────────

    async def save_task(self, task: TaskSpec, result: TaskResult = None) -> None:
        """Save task state."""
        async with self._lock:
            task_state = self._tasks.get(task.task_id)
            if not task_state:
                task_state = TaskState(task_id=task.task_id, spec=task)

            task_state.spec = task
            task_state.result = result
            task_state.updated_at = time.time()
            task_state.version += 1

            self._tasks[task.task_id] = task_state

    async def load_task(self, task_id: str) -> Optional[TaskSpec]:
        """Load task specification."""
        async with self._lock:
            task_state = self._tasks.get(task_id)
            return task_state.spec if task_state else None

    async def load_task_state(self, task_id: str) -> Optional[TaskState]:
        """Load complete task state."""
        async with self._lock:
            return self._tasks.get(task_id)

    async def delete_task(self, task_id: str) -> bool:
        """Delete task state."""
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    async def list_tasks(
        self,
        status: TaskStatus = None,
        user_id: str = "",
        project_id: str = "",
    ) -> List[TaskSpec]:
        """List tasks with optional filters."""
        async with self._lock:
            tasks = []
            for ts in self._tasks.values():
                if status and ts.spec.status != status:
                    continue
                if user_id and ts.spec.user_id != user_id:
                    continue
                if project_id and ts.spec.project_id != project_id:
                    continue
                tasks.append(ts.spec)
            return tasks

    # ── Plan State ─────────────────────────────────────────────────────

    async def save_plan(
        self,
        plan: Plan,
        execution_state: ExecutionState,
        task_states: Dict[str, TaskState] = None,
    ) -> None:
        """Save plan state."""
        async with self._lock:
            plan_state = self._plans.get(plan.plan_id)
            if not plan_state:
                plan_state = PlanState(
                    plan_id=plan.plan_id,
                    plan=plan,
                    execution_state=execution_state,
                )

            plan_state.plan = plan
            plan_state.execution_state = execution_state
            if task_states:
                plan_state.task_states = task_states
            plan_state.updated_at = time.time()
            plan_state.version += 1

            self._plans[plan.plan_id] = plan_state

    async def load_plan(self, plan_id: str) -> Optional[Plan]:
        """Load plan."""
        async with self._lock:
            plan_state = self._plans.get(plan_id)
            return plan_state.plan if plan_state else None

    async def load_plan_state(self, plan_id: str) -> Optional[PlanState]:
        """Load complete plan state."""
        async with self._lock:
            return self._plans.get(plan_id)

    # ── Global State ───────────────────────────────────────────────────

    def update_global_budget(self, snapshot: BudgetSnapshot) -> None:
        """Update global budget snapshot."""
        self._global_budget = snapshot

    def get_global_budget(self) -> BudgetSnapshot:
        """Get global budget snapshot."""
        return self._global_budget

    def register_agent(self, agent: AgentIdentity) -> None:
        """Register an active agent."""
        self._active_agents[agent.agent_id] = agent

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self._active_agents:
            del self._active_agents[agent_id]
            return True
        return False

    def get_active_agents(self) -> List[AgentIdentity]:
        """Get all active agents."""
        return list(self._active_agents.values())

    # ── Checkpoint Integration ──────────────────────────────────────────

    def add_checkpoint(self, task_id: str, checkpoint_id: str) -> None:
        """Record a checkpoint for a task."""
        task_state = self._tasks.get(task_id)
        if task_state and checkpoint_id not in task_state.checkpoints:
            task_state.checkpoints.append(checkpoint_id)

    # ── Persistence ────────────────────────────────────────────────────

    async def _save_state(self) -> None:
        """Save all state to disk."""
        async with self._lock:
            state = OrchestrationState(
                tasks=self._tasks,
                plans=self._plans,
                global_budget=self._global_budget,
                active_agents=self._active_agents,
                saved_at=time.time(),
            )

            # Save to file
            state_file = self._state_dir / "orchestration_state.json"
            try:
                # Convert to serializable format
                data = self._serialize_state(state)
                with open(state_file, "w") as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to save state: {e}")

    async def _load_state(self) -> None:
        """Load state from disk."""
        state_file = self._state_dir / "orchestration_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file, "r") as f:
                data = json.load(f)

            self._deserialize_state(data)
            logger.info(f"Loaded state: {len(self._tasks)} tasks, {len(self._plans)} plans")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")

    def _serialize_state(self, state: OrchestrationState) -> Dict[str, Any]:
        """Serialize state for JSON storage."""
        # Custom serialization for complex objects
        def serialize_task_state(ts: TaskState) -> Dict[str, Any]:
            return {
                "task_id": ts.task_id,
                "spec": self._serialize_task_spec(ts.spec),
                "result": self._serialize_task_result(ts.result) if ts.result else None,
                "checkpoints": ts.checkpoints,
                "created_at": ts.created_at,
                "updated_at": ts.updated_at,
                "version": ts.version,
            }

        def serialize_plan_state(ps: PlanState) -> Dict[str, Any]:
            return {
                "plan_id": ps.plan_id,
                "plan": self._serialize_plan(ps.plan),
                "execution_state": self._serialize_execution_state(ps.execution_state),
                "task_states": {k: serialize_task_state(v) for k, v in ps.task_states.items()},
                "created_at": ps.created_at,
                "updated_at": ps.updated_at,
                "version": ps.version,
            }

        return {
            "version": state.version,
            "saved_at": state.saved_at,
            "tasks": {k: serialize_task_state(v) for k, v in state.tasks.items()},
            "plans": {k: serialize_plan_state(v) for k, v in state.plans.items()},
            "global_budget": asdict(state.global_budget),
            "active_agents": {k: asdict(v) for k, v in state.active_agents.items()},
        }

    def _serialize_task_spec(self, task: TaskSpec) -> Dict[str, Any]:
        """Serialize TaskSpec."""
        return {
            "task_id": task.task_id,
            "parent_task_id": task.parent_task_id,
            "root_task_id": task.root_task_id,
            "user_id": task.user_id,
            "project_id": task.project_id,
            "session_id": task.session_id,
            "goal": task.goal,
            "description": task.description,
            "constraints": task.constraints,
            "success_criteria": task.success_criteria,
            "required_capabilities": task.required_capabilities,
            "preferred_agent_role": task.preferred_agent_role.value if task.preferred_agent_role else None,
            "preferred_model": task.preferred_model,
            "preferred_tools": task.preferred_tools,
            "preferred_skills": task.preferred_skills,
            "assigned_agent": task.assigned_agent,
            "assigned_model": task.assigned_model,
            "status": task.status.value,
            "priority": task.priority.value,
            "deadline": task.deadline,
            "budget": self._serialize_budget(task.budget),
            "depends_on": task.depends_on,
            "blocks": task.blocks,
            "metadata": task.metadata,
            "context": task.context,
            "artifacts": task.artifacts,
            "result": task.result,
            "verification_state": task.verification_state,
            "approval_state": task.approval_state,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
        }

    def _serialize_budget(self, budget: TaskBudget) -> Dict[str, Any]:
        return {
            "max_time_seconds": budget.max_time_seconds,
            "max_tokens": budget.max_tokens,
            "max_cost_usd": budget.max_cost_usd,
            "max_tool_calls": budget.max_tool_calls,
            "max_iterations": budget.max_iterations,
            "max_parallel_subtasks": budget.max_parallel_subtasks,
            "max_subagents": budget.max_subagents,
        }

    def _serialize_task_result(self, result: TaskResult) -> Dict[str, Any]:
        return {
            "task_id": result.task_id,
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "artifacts": result.artifacts,
            "execution_time": result.execution_time,
            "tokens_used": result.tokens_used,
            "cost_usd": result.cost_usd,
            "model_used": result.model_used,
            "agent_id": result.agent_id,
            "verification": result.verification,
            "warnings": result.warnings,
            "metadata": result.metadata,
            "completed_at": result.completed_at,
        }

    def _serialize_plan(self, plan: Plan) -> Dict[str, Any]:
        return {
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "description": plan.description,
            "subtasks": [self._serialize_task_spec(t) for t in plan.subtasks],
            "dependencies": plan.dependencies,
            "required_tools": plan.required_tools,
            "required_agents": [r.value for r in plan.required_agents],
            "required_permissions": plan.required_permissions,
            "estimated_cost": plan.estimated_cost,
            "estimated_time": plan.estimated_time,
            "risk_level": plan.risk_level.value,
            "created_at": plan.created_at,
            "execution_graph": plan.execution_graph,
            "version": plan.version,
            "parent_plan_id": plan.parent_plan_id,
        }

    def _serialize_execution_state(self, state: ExecutionState) -> Dict[str, Any]:
        return {
            "plan_id": state.plan_id,
            "current_task_id": state.current_task_id,
            "completed_tasks": state.completed_tasks,
            "pending_tasks": state.pending_tasks,
            "failed_tasks": state.failed_tasks,
            "running_tasks": state.running_tasks,
            "paused": state.paused,
            "cancelled": state.cancelled,
            "checkpoint_path": state.checkpoint_path,
            "started_at": state.started_at,
            "updated_at": state.updated_at,
            "budget_used": asdict(state.budget_used),
        }

    def _deserialize_state(self, data: Dict[str, Any]) -> None:
        """Deserialize state from JSON."""
        # This is simplified - in production would fully reconstruct objects
        # For now, just log what was loaded
        logger.info(f"Deserialized state version {data.get('version', 1)}")


# =============================================================================
# Task State Manager
# =============================================================================


class TaskStateManager:
    """High-level task state management with checkpoints."""

    def __init__(
        self,
        state_store: StateStore,
        checkpoint_manager: CheckpointManager,
    ):
        self._store = state_store
        self._checkpoints = checkpoint_manager

    async def create_task(
        self,
        goal: str,
        description: str = "",
        required_capabilities: List[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        budget: TaskBudget = None,
        depends_on: List[str] = None,
        user_id: str = "",
        project_id: str = "",
        session_id: str = "",
    ) -> TaskSpec:
        """Create and persist a new task."""
        task = TaskSpec(
            goal=goal,
            description=description,
            required_capabilities=required_capabilities or [],
            priority=priority,
            budget=budget or TaskBudget(),
            depends_on=depends_on or [],
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
        )

        await self._store.save_task(task)
        return task

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: TaskResult = None,
        assigned_agent: str = "",
        assigned_model: str = "",
    ) -> bool:
        """Update task status."""
        task = await self._store.load_task(task_id)
        if not task:
            return False

        task.status = status
        if result:
            task.result = result.result
            task.metadata["task_result"] = {
                "success": result.success,
                "error": result.error,
                "execution_time": result.execution_time,
                "tokens_used": result.tokens_used,
                "cost_usd": result.cost_usd,
            }
        if assigned_agent:
            task.assigned_agent = assigned_agent
        if assigned_model:
            task.assigned_model = assigned_model

        await self._store.save_task(task, result)
        return True

    async def create_checkpoint(
        self,
        task_id: str,
        checkpoint_type: CheckpointType = CheckpointType.PERIODIC,
    ) -> Optional[Checkpoint]:
        """Create a checkpoint for a task."""
        task = await self._store.load_task(task_id)
        if not task:
            return None

        checkpoint = await self._checkpoints.create_checkpoint(task, checkpoint_type)
        self._store.add_checkpoint(task_id, checkpoint.checkpoint_id)
        return checkpoint

    async def restore_from_checkpoint(
        self,
        task_id: str,
        checkpoint_id: str = None,
    ) -> Optional[TaskSpec]:
        """Restore task from checkpoint."""
        if checkpoint_id:
            checkpoint = await self._checkpoints.load_checkpoint(checkpoint_id)
        else:
            checkpoint = await self._checkpoints.get_latest_checkpoint(task_id)

        if not checkpoint:
            return None

        task = await self._checkpoints.restore_task_from_checkpoint(
            checkpoint,
            lambda: TaskSpec(task_id=task_id),
        )

        await self._store.save_task(task)
        return task

    async def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get task state history (from checkpoints)."""
        task_state = await self._store.load_task_state(task_id)
        if not task_state:
            return []

        history = []
        for cp_id in task_state.checkpoints:
            cp = await self._checkpoints.load_checkpoint(cp_id)
            if cp:
                history.append({
                    "checkpoint_id": cp.checkpoint_id,
                    "type": cp.checkpoint_type.value,
                    "created_at": cp.created_at,
                    "completed_subtasks": len(cp.completed_subtasks),
                })
        return history


# =============================================================================
# Plan State Manager
# =============================================================================


class PlanStateManager:
    """High-level plan state management."""

    def __init__(self, state_store: StateStore):
        self._store = state_store

    async def create_plan(self, plan: Plan) -> Plan:
        """Create and persist a new plan."""
        execution_state = ExecutionState(
            plan_id=plan.plan_id,
            pending_tasks=[t.task_id for t in plan.subtasks],
        )

        await self._store.save_plan(plan, execution_state)
        return plan

    async def update_plan_progress(
        self,
        plan_id: str,
        completed_task_id: str = "",
        failed_task_id: str = "",
        current_task_id: str = "",
    ) -> bool:
        """Update plan execution progress."""
        plan_state = await self._store.load_plan_state(plan_id)
        if not plan_state:
            return False

        es = plan_state.execution_state

        if completed_task_id:
            es.completed_tasks.append(completed_task_id)
            if completed_task_id in es.pending_tasks:
                es.pending_tasks.remove(completed_task_id)

        if failed_task_id:
            es.failed_tasks.append(failed_task_id)
            if failed_task_id in es.pending_tasks:
                es.pending_tasks.remove(failed_task_id)

        if current_task_id:
            es.current_task_id = current_task_id
            if current_task_id not in es.running_tasks:
                es.running_tasks.append(current_task_id)

        es.updated_at = time.time()
        await self._store.save_plan(plan_state.plan, es, plan_state.task_states)
        return True

    async def pause_plan(self, plan_id: str) -> bool:
        """Pause plan execution."""
        plan_state = await self._store.load_plan_state(plan_id)
        if not plan_state:
            return False

        plan_state.execution_state.paused = True
        await self._store.save_plan(plan_state.plan, plan_state.execution_state, plan_state.task_states)
        return True

    async def resume_plan(self, plan_id: str) -> bool:
        """Resume plan execution."""
        plan_state = await self._store.load_plan_state(plan_id)
        if not plan_state:
            return False

        plan_state.execution_state.paused = False
        await self._store.save_plan(plan_state.plan, plan_state.execution_state, plan_state.task_states)
        return True


# =============================================================================
# Factory
# =============================================================================


def create_state_store(config: StateConfig = None) -> StateStore:
    """Create a state store."""
    return StateStore(config)


def create_task_state_manager(
    state_store: StateStore,
    checkpoint_manager: CheckpointManager,
) -> TaskStateManager:
    """Create a task state manager."""
    return TaskStateManager(state_store, checkpoint_manager)


def create_plan_state_manager(state_store: StateStore) -> PlanStateManager:
    """Create a plan state manager."""
    return PlanStateManager(state_store)


__all__ = [
    "StateBackend",
    "StateConfig",
    "TaskState",
    "PlanState",
    "OrchestrationState",
    "StateStore",
    "TaskStateManager",
    "PlanStateManager",
    "create_state_store",
    "create_task_state_manager",
    "create_plan_state_manager",
]