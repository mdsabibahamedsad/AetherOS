"""Recovery and Crash Handling for AetherOS Orchestration Layer.

Implements Phases 36-43, 89 of Master Prompt 11: failure classification,
retry policies, fallback agents/models, checkpoints, resume, cancellation,
pause/resume, deadlines, crash recovery, and stall detection.
"""

from __future__ import annotations

import asyncio
import logging
import os
import pickle
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from pathlib import Path

from agent.orchestration.types import (
    TaskSpec,
    TaskResult,
    TaskStatus,
    FailureType,
    Checkpoint,
    BudgetSnapshot,
)
from agent.orchestration.budget import BudgetController

logger = logging.getLogger(__name__)


# =============================================================================
# Recovery Types
# =============================================================================


class RecoveryStrategy(Enum):
    """Strategies for recovering from failures."""

    RETRY = "retry"                    # Retry same task
    FALLBACK_AGENT = "fallback_agent"  # Try different agent
    FALLBACK_MODEL = "fallback_model"  # Try different model
    DECOMPOSE = "decompose"            # Break into smaller tasks
    ESCALATE = "escalate"              # Escalate to human
    SKIP = "skip"                      # Skip and continue
    ABORT = "abort"                    # Abort entire plan


class CheckpointType(Enum):
    """Types of checkpoints."""

    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    SUBTASK_COMPLETE = "subtask_complete"
    PLAN_VERSION = "plan_version"
    PERIODIC = "periodic"
    PRE_HANDOFF = "pre_handoff"
    PRE_APPROVAL = "pre_approval"


@dataclass
class RetryPolicy:
    """Policy for retrying failed tasks."""

    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: float = 0.1
    retryable_failures: Set[FailureType] = field(default_factory=lambda: {
        FailureType.TIMEOUT,
        FailureType.RATE_LIMIT,
        FailureType.PROVIDER_ERROR,
        FailureType.NETWORK_ERROR,
        FailureType.RESOURCE_EXHAUSTED,
    })
    non_retryable_failures: Set[FailureType] = field(default_factory=lambda: {
        FailureType.AUTH_ERROR,
        FailureType.PERMISSION_DENIED,
        FailureType.VALIDATION_ERROR,
    })


@dataclass
class FallbackConfig:
    """Configuration for fallback agents/models."""

    fallback_agents: List[str] = field(default_factory=list)  # Agent IDs
    fallback_models: List[str] = field(default_factory=list)  # Model names
    fallback_toolsets: List[str] = field(default_factory=list)
    require_same_capabilities: bool = True
    preserve_privacy: bool = True


@dataclass
class RecoveryAction:
    """A recovery action to take."""

    strategy: RecoveryStrategy
    reason: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher = tried first


@dataclass
class StallDetectionConfig:
    """Configuration for stall detection."""

    no_progress_timeout: float = 300.0  # 5 minutes
    repeated_error_threshold: int = 3
    repeated_error_window: float = 60.0  # seconds
    unresponsive_provider_timeout: float = 120.0
    dead_agent_timeout: float = 600.0  # 10 minutes


# =============================================================================
# Checkpoint Manager
# =============================================================================


class CheckpointManager:
    """Manages checkpoints for task recovery."""

    def __init__(
        self,
        checkpoint_dir: str = "~/.aetheros/checkpoints",
        max_checkpoints_per_task: int = 10,
    ):
        self._checkpoint_dir = Path(os.path.expanduser(checkpoint_dir))
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._max_checkpoints = max_checkpoints_per_task
        self._checkpoints: Dict[str, List[Checkpoint]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def create_checkpoint(
        self,
        task: TaskSpec,
        checkpoint_type: CheckpointType = CheckpointType.PERIODIC,
        additional_data: Dict[str, Any] = None,
    ) -> Checkpoint:
        """Create a checkpoint for a task."""
        checkpoint = Checkpoint(
            checkpoint_id=f"cp-{uuid.uuid4().hex[:12]}",
            task_id=task.task_id,
            plan_id=task.metadata.get("plan_id", ""),
            checkpoint_type=checkpoint_type,
            task_state=self._serialize_task_state(task),
            budget_snapshot=task.budget.to_snapshot() if hasattr(task.budget, 'to_snapshot') else BudgetSnapshot(),
            completed_subtasks=task.metadata.get("completed_subtasks", []),
            artifacts=task.artifacts,
            memory_refs=task.metadata.get("memory_refs", []),
            next_steps=task.metadata.get("next_steps", []),
            created_at=time.time(),
            metadata=additional_data or {},
        )

        # Save to disk
        await self._save_checkpoint(checkpoint)

        # Track in memory
        self._checkpoints[task.task_id].append(checkpoint)

        # Trim old checkpoints
        if len(self._checkpoints[task.task_id]) > self._max_checkpoints:
            old = self._checkpoints[task.task_id].pop(0)
            await self._delete_checkpoint(old.checkpoint_id)

        logger.info(f"Created checkpoint {checkpoint.checkpoint_id} for task {task.task_id}")
        return checkpoint

    async def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to disk."""
        path = self._checkpoint_dir / f"{checkpoint.checkpoint_id}.pkl"
        try:
            # Use pickle for complex objects
            with open(path, "wb") as f:
                pickle.dump(checkpoint, f)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    async def _delete_checkpoint(self, checkpoint_id: str) -> None:
        """Delete checkpoint from disk."""
        path = self._checkpoint_dir / f"{checkpoint_id}.pkl"
        try:
            path.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to delete checkpoint: {e}")

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load a checkpoint from disk."""
        path = self._checkpoint_dir / f"{checkpoint_id}.pkl"
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load checkpoint {checkpoint_id}: {e}")
            return None

    async def get_latest_checkpoint(self, task_id: str) -> Optional[Checkpoint]:
        """Get the latest checkpoint for a task."""
        checkpoints = self._checkpoints.get(task_id, [])
        if checkpoints:
            return checkpoints[-1]

        # Try loading from disk
        for path in sorted(self._checkpoint_dir.glob("*.pkl"), reverse=True):
            cp = await self.load_checkpoint(path.stem)
            if cp and cp.task_id == task_id:
                return cp

        return None

    async def get_checkpoints_for_task(self, task_id: str) -> List[Checkpoint]:
        """Get all checkpoints for a task."""
        return list(self._checkpoints.get(task_id, []))

    async def restore_task_from_checkpoint(
        self,
        checkpoint: Checkpoint,
        task_factory: Callable[[], TaskSpec],
    ) -> TaskSpec:
        """Restore a task from a checkpoint."""
        task = task_factory()
        task.task_id = checkpoint.task_id
        task.status = TaskStatus.READY
        task.metadata.update({
            "restored_from_checkpoint": checkpoint.checkpoint_id,
            "completed_subtasks": checkpoint.completed_subtasks,
            "artifacts": checkpoint.artifacts,
            "memory_refs": checkpoint.memory_refs,
            "next_steps": checkpoint.next_steps,
        })
        task.artifacts = checkpoint.artifacts

        logger.info(f"Restored task {task.task_id} from checkpoint {checkpoint.checkpoint_id}")
        return task

    def _serialize_task_state(self, task: TaskSpec) -> Dict[str, Any]:
        """Serialize task state for checkpoint."""
        return {
            "task_id": task.task_id,
            "parent_task_id": task.parent_task_id,
            "root_task_id": task.root_task_id,
            "status": task.status.value,
            "goal": task.goal,
            "description": task.description,
            "constraints": task.constraints,
            "success_criteria": task.success_criteria,
            "required_capabilities": task.required_capabilities,
            "assigned_agent": task.assigned_agent,
            "assigned_model": task.assigned_model,
            "context": task.context,
            "metadata": task.metadata,
        }


# =============================================================================
# Retry Handler
# =============================================================================


class RetryHandler:
    """Handles task retries with exponential backoff."""

    def __init__(self, policy: RetryPolicy = None):
        self._policy = policy or RetryPolicy()

    def should_retry(self, failure_type: FailureType, attempt: int) -> bool:
        """Determine if a failure should be retried."""
        if attempt >= self._policy.max_attempts:
            return False

        if failure_type in self._policy.non_retryable_failures:
            return False

        if failure_type in self._policy.retryable_failures:
            return True

        # Unknown failure type - retry by default
        return True

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = min(
            self._policy.base_delay * (self._policy.exponential_base ** attempt),
            self._policy.max_delay,
        )
        # Add jitter
        import random
        delay *= (1 + random.uniform(-self._policy.jitter, self._policy.jitter))
        return delay

    async def execute_with_retry(
        self,
        task: TaskSpec,
        executor: Callable[[TaskSpec], Any],
        failure_classifier: Callable[[Exception], FailureType],
    ) -> TaskResult:
        """Execute a task with retry logic."""
        last_error = None

        for attempt in range(self._policy.max_attempts):
            try:
                result = await executor(task)
                if isinstance(result, TaskResult) and result.success:
                    return result
                elif isinstance(result, TaskResult):
                    last_error = result.error
                    failure_type = failure_classifier(Exception(result.error))
                else:
                    return result  # Non-TaskResult result

            except Exception as e:
                last_error = str(e)
                failure_type = failure_classifier(e)

            if not self.should_retry(failure_type, attempt):
                break

            if attempt < self._policy.max_attempts - 1:
                delay = self.get_delay(attempt)
                logger.info(f"Retrying task {task.task_id} in {delay:.1f}s (attempt {attempt+2}/{self._policy.max_attempts})")
                await asyncio.sleep(delay)

        return TaskResult(
            task_id=task.task_id,
            success=False,
            error=f"Failed after {self._policy.max_attempts} attempts: {last_error}",
        )


# =============================================================================
# Fallback Handler
# =============================================================================


class FallbackHandler:
    """Handles fallback to alternative agents/models."""

    def __init__(self, config: FallbackConfig = None):
        self._config = config or FallbackConfig()

    async def get_fallback_agent(
        self,
        failed_agent_id: str,
        required_capabilities: List[str],
        agent_registry: Any,
    ) -> Optional[str]:
        """Get a fallback agent."""
        for agent_id in self._config.fallback_agents:
            if agent_id == failed_agent_id:
                continue

            # Check if agent has required capabilities
            # This would query the agent registry
            if self._config.require_same_capabilities:
                # In production: verify capabilities
                pass

            return agent_id

        return None

    async def get_fallback_model(
        self,
        failed_model: str,
        required_capabilities: List[str],
        model_router: Any,
    ) -> Optional[str]:
        """Get a fallback model."""
        for model in self._config.fallback_models:
            if model == failed_model:
                continue

            # Check model capabilities
            # In production: use model router

            return model

        return None

    async def execute_with_fallback(
        self,
        task: TaskSpec,
        primary_executor: Callable,
        fallback_executor: Callable,
        failure_classifier: Callable[[Exception], FailureType],
    ) -> TaskResult:
        """Execute with fallback on failure."""
        try:
            return await primary_executor(task)
        except Exception as e:
            failure_type = failure_classifier(e)
            logger.warning(f"Primary executor failed: {e}, trying fallback")

            # Try fallback agent
            if self._config.fallback_agents:
                task.metadata["fallback_agent"] = True
                return await fallback_executor(task)

        return TaskResult(
            task_id=task.task_id,
            success=False,
            error=f"All fallbacks exhausted: {e}",
        )


# =============================================================================
# Stall Detector
# =============================================================================


class StallDetector:
    """Detects stalled tasks and agents."""

    def __init__(self, config: StallDetectionConfig = None):
        self._config = config or StallDetectionConfig()
        self._task_progress: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def record_progress(
        self,
        task_id: str,
        agent_id: str,
        progress: float,
        step: str = "",
    ) -> None:
        """Record task progress."""
        now = time.time()
        self._task_progress[task_id] = {
            "agent_id": agent_id,
            "progress": progress,
            "step": step,
            "last_update": now,
            "error_count": self._task_progress.get(task_id, {}).get("error_count", 0),
            "recent_errors": self._task_progress.get(task_id, {}).get("recent_errors", []),
        }

    def record_error(self, task_id: str, error: str) -> None:
        """Record an error for stall detection."""
        if task_id in self._task_progress:
            self._task_progress[task_id]["error_count"] += 1
            self._task_progress[task_id]["recent_errors"].append({
                "error": error,
                "time": time.time(),
            })
            # Trim old errors
            cutoff = time.time() - self._config.repeated_error_window
            self._task_progress[task_id]["recent_errors"] = [
                e for e in self._task_progress[task_id]["recent_errors"]
                if e["time"] > cutoff
            ]

    def check_stalls(self) -> List[Dict[str, Any]]:
        """Check for stalled tasks."""
        now = time.time()
        stalls = []

        for task_id, info in self._task_progress.items():
            # Check no progress
            if now - info["last_update"] > self._config.no_progress_timeout:
                stalls.append({
                    "task_id": task_id,
                    "agent_id": info["agent_id"],
                    "type": "no_progress",
                    "duration": now - info["last_update"],
                    "last_step": info["step"],
                })

            # Check repeated errors
            if len(info["recent_errors"]) >= self._config.repeated_error_threshold:
                stalls.append({
                    "task_id": task_id,
                    "agent_id": info["agent_id"],
                    "type": "repeated_errors",
                    "error_count": info["error_count"],
                    "recent_errors": info["recent_errors"],
                })

        return stalls

    def clear_task(self, task_id: str) -> None:
        """Clear tracking for a task."""
        self._task_progress.pop(task_id, None)


# =============================================================================
# Deadline Manager
# =============================================================================


class DeadlineManager:
    """Manages task deadlines and deadline-driven actions."""

    def __init__(self):
        self._deadlines: Dict[str, float] = {}  # task_id -> deadline
        self._callbacks: Dict[str, List[Callable[[str], None]]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start deadline monitoring."""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """Stop deadline monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    def set_deadline(
        self,
        task_id: str,
        deadline: float,
        callback: Callable[[str], None] = None,
    ) -> None:
        """Set a deadline for a task."""
        self._deadlines[task_id] = deadline
        if callback:
            self._callbacks[task_id].append(callback)

    def clear_deadline(self, task_id: str) -> None:
        """Clear a task's deadline."""
        self._deadlines.pop(task_id, None)
        self._callbacks.pop(task_id, None)

    def get_remaining(self, task_id: str) -> Optional[float]:
        """Get remaining time until deadline."""
        deadline = self._deadlines.get(task_id)
        if deadline:
            return max(0, deadline - time.time())
        return None

    def is_overdue(self, task_id: str) -> bool:
        """Check if a task is past its deadline."""
        deadline = self._deadlines.get(task_id)
        if deadline:
            return time.time() > deadline
        return False

    async def _monitor_loop(self):
        """Monitor deadlines."""
        while self._running:
            now = time.time()
            overdue = []

            async with self._lock:
                for task_id, deadline in list(self._deadlines.items()):
                    if now >= deadline:
                        overdue.append(task_id)

            for task_id in overdue:
                await self._handle_deadline(task_id)

            await asyncio.sleep(1)

    async def _handle_deadline(self, task_id: str):
        """Handle a task reaching its deadline."""
        callbacks = self._callbacks.pop(task_id, [])
        for cb in callbacks:
            try:
                cb(task_id)
            except Exception as e:
                logger.warning(f"Deadline callback failed for {task_id}: {e}")

        self._deadlines.pop(task_id, None)
        logger.warning(f"Deadline reached for task {task_id}")


# =============================================================================
# Crash Recovery
# =============================================================================


class CrashRecovery:
    """Handles crash recovery for tasks and orchestration state."""

    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        state_dir: str = "~/.aetheros/recovery",
    ):
        self._checkpoints = checkpoint_manager
        self._state_dir = Path(os.path.expanduser(state_dir))
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._active_tasks: Dict[str, TaskSpec] = {}
        self._recovery_log: List[Dict[str, Any]] = []

    def register_task(self, task: TaskSpec) -> None:
        """Register a task for crash recovery."""
        self._active_tasks[task.task_id] = task
        self._persist_state()

    def unregister_task(self, task_id: str) -> None:
        """Unregister a completed task."""
        self._active_tasks.pop(task_id, None)
        self._persist_state()

    def _persist_state(self) -> None:
        """Persist active task state to disk."""
        try:
            state_file = self._state_dir / "active_tasks.pkl"
            with open(state_file, "wb") as f:
                pickle.dump(self._active_tasks, f)
        except Exception as e:
            logger.error(f"Failed to persist recovery state: {e}")

    async def recover_tasks(self) -> List[TaskSpec]:
        """Recover tasks from persisted state."""
        recovered = []

        # Load persisted state
        state_file = self._state_dir / "active_tasks.pkl"
        if state_file.exists():
            try:
                with open(state_file, "rb") as f:
                    self._active_tasks = pickle.load(f)
            except Exception as e:
                logger.error(f"Failed to load recovery state: {e}")
                return []

        # Recover each task
        for task_id, task in self._active_tasks.items():
            if task.status in (TaskStatus.RUNNING, TaskStatus.WAITING, TaskStatus.BLOCKED):
                # Try to restore from checkpoint
                checkpoint = await self._checkpoints.get_latest_checkpoint(task_id)
                if checkpoint:
                    restored = await self._checkpoints.restore_task_from_checkpoint(
                        checkpoint,
                        lambda: task,
                    )
                    restored.status = TaskStatus.READY
                    restored.metadata["recovered_from_crash"] = True
                    restored.metadata["recovery_time"] = time.time()
                    recovered.append(restored)
                    self._recovery_log.append({
                        "task_id": task_id,
                        "checkpoint": checkpoint.checkpoint_id,
                        "recovered_at": time.time(),
                    })
                else:
                    # No checkpoint - mark as failed
                    task.status = TaskStatus.FAILED
                    task.error = "Task interrupted by crash, no checkpoint available"
                    self._recovery_log.append({
                        "task_id": task_id,
                        "recovered": False,
                        "reason": "no_checkpoint",
                        "time": time.time(),
                    })

        logger.info(f"Crash recovery: {len(recovered)} tasks recovered, {len(self._active_tasks) - len(recovered)} failed")
        return recovered

    def get_recovery_log(self) -> List[Dict[str, Any]]:
        """Get recovery log."""
        return list(self._recovery_log)


# =============================================================================
# Recovery Orchestrator
# =============================================================================


class RecoveryOrchestrator:
    """Orchestrates recovery actions for failed tasks."""

    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        retry_handler: RetryHandler,
        fallback_handler: FallbackHandler,
        stall_detector: StallDetector,
        deadline_manager: DeadlineManager,
        crash_recovery: CrashRecovery,
        budget_controller: BudgetController = None,
    ):
        self._checkpoints = checkpoint_manager
        self._retry = retry_handler
        self._fallback = fallback_handler
        self._stall = stall_detector
        self._deadlines = deadline_manager
        self._crash = crash_recovery
        self._budget = budget_controller
        self._recovery_history: List[Dict[str, Any]] = []

    async def handle_failure(
        self,
        task: TaskSpec,
        error: Exception,
        failure_classifier: Callable[[Exception], FailureType],
    ) -> RecoveryAction:
        """Determine and execute recovery action for a failed task."""
        failure_type = failure_classifier(error)

        # Check for stall
        stalls = self._stall.check_stalls()
        task_stalls = [s for s in stalls if s["task_id"] == task.task_id]

        # Check deadline
        deadline_exceeded = self._deadlines.is_overdue(task.task_id)

        # Determine recovery strategy
        actions = self._determine_recovery_actions(
            task, failure_type, task_stalls, deadline_exceeded
        )

        # Execute first viable action
        for action in actions:
            success = await self._execute_recovery_action(task, action)
            if success:
                self._recovery_history.append({
                    "task_id": task.task_id,
                    "strategy": action.strategy.value,
                    "reason": action.reason,
                    "success": True,
                    "time": time.time(),
                })
                return action

        # All failed
        self._recovery_history.append({
            "task_id": task.task_id,
            "strategy": "none",
            "reason": "All recovery actions failed",
            "success": False,
            "time": time.time(),
        })

        return RecoveryAction(
            strategy=RecoveryStrategy.ABORT,
            reason="All recovery actions failed",
        )

    def _determine_recovery_actions(
        self,
        task: TaskSpec,
        failure_type: FailureType,
        stalls: List[Dict],
        deadline_exceeded: bool,
    ) -> List[RecoveryAction]:
        """Determine appropriate recovery actions."""
        actions = []

        # Check if retryable
        if self._retry.should_retry(failure_type, task.metadata.get("retry_count", 0)):
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                reason=f"Retryable failure: {failure_type.value}",
                priority=10,
            ))

        # Check for fallback agent
        if self._fallback._config.fallback_agents:
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK_AGENT,
                reason="Fallback agent available",
                priority=8,
            ))

        # Check for fallback model
        if self._fallback._config.fallback_models:
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK_MODEL,
                reason="Fallback model available",
                priority=7,
            ))

        # If stalled, try decompose
        if stalls:
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.DECOMPOSE,
                reason=f"Task stalled: {stalls[0]['type']}",
                priority=5,
            ))

        # If deadline exceeded, escalate
        if deadline_exceeded:
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.ESCALATE,
                reason="Deadline exceeded",
                priority=3,
            ))

        # Sort by priority
        actions.sort(key=lambda a: a.priority, reverse=True)
        return actions

    async def _execute_recovery_action(
        self,
        task: TaskSpec,
        action: RecoveryAction,
    ) -> bool:
        """Execute a recovery action."""
        try:
            if action.strategy == RecoveryStrategy.RETRY:
                task.metadata["retry_count"] = task.metadata.get("retry_count", 0) + 1
                task.status = TaskStatus.READY
                return True

            elif action.strategy == RecoveryStrategy.FALLBACK_AGENT:
                # Would switch to fallback agent
                task.metadata["use_fallback_agent"] = True
                task.status = TaskStatus.READY
                return True

            elif action.strategy == RecoveryStrategy.FALLBACK_MODEL:
                task.metadata["use_fallback_model"] = True
                task.status = TaskStatus.READY
                return True

            elif action.strategy == RecoveryStrategy.DECOMPOSE:
                # Would trigger re-planning
                task.metadata["needs_replan"] = True
                task.status = TaskStatus.PLANNING
                return True

            elif action.strategy == RecoveryStrategy.ESCALATE:
                task.status = TaskStatus.REQUIRES_APPROVAL
                return True

            elif action.strategy == RecoveryStrategy.SKIP:
                task.status = TaskStatus.COMPLETED
                task.result = {"skipped": True, "reason": action.reason}
                return True

        except Exception as e:
            logger.error(f"Recovery action {action.strategy} failed: {e}")
            return False

        return False

    def get_recovery_history(self) -> List[Dict[str, Any]]:
        """Get recovery history."""
        return list(self._recovery_history)


# =============================================================================
# Pause/Resume Manager
# =============================================================================


class PauseResumeManager:
    """Manages task pause and resume operations."""

    def __init__(self, checkpoint_manager: CheckpointManager):
        self._checkpoints = checkpoint_manager
        self._paused_tasks: Dict[str, Dict[str, Any]] = {}

    async def pause_task(self, task: TaskSpec, reason: str = "") -> bool:
        """Pause a running task."""
        # Create checkpoint
        checkpoint = await self._checkpoints.create_checkpoint(
            task,
            CheckpointType.PERIODIC,
            {"pause_reason": reason},
        )

        self._paused_tasks[task.task_id] = {
            "task": task,
            "checkpoint_id": checkpoint.checkpoint_id,
            "paused_at": time.time(),
            "reason": reason,
        }

        task.status = TaskStatus.PAUSED
        return True

    async def resume_task(self, task_id: str, task_factory: Callable[[], TaskSpec]) -> Optional[TaskSpec]:
        """Resume a paused task."""
        paused = self._paused_tasks.get(task_id)
        if not paused:
            return None

        checkpoint = await self._checkpoints.load_checkpoint(paused["checkpoint_id"])
        if not checkpoint:
            return None

        task = await self._checkpoints.restore_task_from_checkpoint(
            checkpoint,
            task_factory,
        )
        task.status = TaskStatus.READY

        self._paused_tasks.pop(task_id, None)
        return task

    def is_paused(self, task_id: str) -> bool:
        """Check if a task is paused."""
        return task_id in self._paused_tasks

    def get_paused_tasks(self) -> List[str]:
        """Get all paused task IDs."""
        return list(self._paused_tasks.keys())


# =============================================================================
# Cancellation Manager
# =============================================================================


class CancellationManager:
    """Manages task cancellation with propagation."""

    def __init__(self):
        self._cancelled: Set[str] = set()
        self._cancellation_tokens: Dict[str, asyncio.Event] = {}
        self._propagation_callbacks: Dict[str, List[Callable[[str], None]]] = defaultdict(list)

    def cancel(self, task_id: str, reason: str = "", propagate: bool = True) -> None:
        """Cancel a task."""
        self._cancelled.add(task_id)

        # Create cancellation token
        if task_id not in self._cancellation_tokens:
            self._cancellation_tokens[task_id] = asyncio.Event()
        self._cancellation_tokens[task_id].set()

        # Propagate to children
        if propagate:
            for callback in self._propagation_callbacks.get(task_id, []):
                try:
                    callback(task_id)
                except Exception as e:
                    logger.warning(f"Cancellation propagation failed: {e}")

        logger.info(f"Task cancelled: {task_id} ({reason})")

    def is_cancelled(self, task_id: str) -> bool:
        """Check if a task is cancelled."""
        return task_id in self._cancelled

    def get_token(self, task_id: str) -> asyncio.Event:
        """Get cancellation token for a task."""
        if task_id not in self._cancellation_tokens:
            self._cancellation_tokens[task_id] = asyncio.Event()
        return self._cancellation_tokens[task_id]

    def register_propagation(self, parent_task_id: str, callback: Callable[[str], None]) -> None:
        """Register callback for cancellation propagation."""
        self._propagation_callbacks[parent_task_id].append(callback)

    def clear(self, task_id: str) -> None:
        """Clear cancellation state."""
        self._cancelled.discard(task_id)
        if task_id in self._cancellation_tokens:
            self._cancellation_tokens[task_id].clear()


# =============================================================================
# Factory
# =============================================================================


def create_recovery_system(
    checkpoint_dir: str = "~/.aetheros/checkpoints",
    retry_policy: RetryPolicy = None,
    fallback_config: FallbackConfig = None,
    stall_config: StallDetectionConfig = None,
) -> Dict[str, Any]:
    """Create a complete recovery system."""
    checkpoints = CheckpointManager(checkpoint_dir)
    retry = RetryHandler(retry_policy)
    fallback = FallbackHandler(fallback_config)
    stall = StallDetector(stall_config)
    deadlines = DeadlineManager()
    crash = CrashRecovery(checkpoints)
    pause_resume = PauseResumeManager(checkpoints)
    cancel = CancellationManager()

    return {
        "checkpoints": checkpoints,
        "retry": retry,
        "fallback": fallback,
        "stall_detector": stall,
        "deadlines": deadlines,
        "crash_recovery": crash,
        "pause_resume": pause_resume,
        "cancellation": cancel,
    }


__all__ = [
    "RecoveryStrategy",
    "CheckpointType",
    "RetryPolicy",
    "FallbackConfig",
    "RecoveryAction",
    "StallDetectionConfig",
    "CheckpointManager",
    "RetryHandler",
    "FallbackHandler",
    "StallDetector",
    "DeadlineManager",
    "CrashRecovery",
    "RecoveryOrchestrator",
    "PauseResumeManager",
    "CancellationManager",
    "create_recovery_system",
]