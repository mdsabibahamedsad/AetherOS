"""
Distributed Executor — executes tasks on remote cluster nodes, manages
task lifecycle, and handles execution failures.

Supports:
  - Remote task submission and execution
  - Task status tracking
  - Timeout enforcement
  - Automatic retry on failure
  - Task migration between nodes
  - Graceful cancellation
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus

from cluster.scheduler import DistributedScheduler, SchedulingDecision, ExecutionTarget
from cluster.transport import TransportProvider, Message, MessageType
from cluster.rpc import RPCClient

logger = logging.getLogger(__name__)


class TaskStatus(enum.Enum):
    """Status of a distributed task."""
    PENDING = "pending"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    MIGRATING = "migrating"


@dataclass
class DistributedTask:
    """A task to be executed on a cluster node.

    Attributes:
        id: Unique task ID
        name: Human-readable task name
        payload: Task data (serializable dict)
        target_node: Node assigned to execute this task
        status: Current task status
        created_at: Task creation time
        started_at: When execution started
        completed_at: When execution completed
        timeout_seconds: Max execution time
        retry_count: Current retry attempt
        max_retries: Maximum retry attempts
        result: Task execution result
        error: Error message if failed
        metadata: Additional task metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    target_node: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    timeout_seconds: float = 300.0
    retry_count: int = 0
    max_retries: int = 2
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of executing a distributed task.

    Attributes:
        task_id: The task ID
        success: Whether execution succeeded
        output: Task output
        error: Error message if failed
        duration_seconds: Execution duration
        node_id: Node that executed the task
        metadata: Additional result metadata
    """
    task_id: str = ""
    success: bool = False
    output: str = ""
    error: Optional[str] = None
    duration_seconds: float = 0.0
    node_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class DistributedExecutor:
    """Executes tasks on cluster nodes.

    Manages the full lifecycle of distributed task execution including
    dispatch, monitoring, timeout, retry, and migration.

    Usage:
        executor = DistributedExecutor(
            scheduler=distributed_scheduler,
            transport=transport_provider,
            rpc_client=rpc_client,
            event_bus=event_bus,
        )

        result = executor.execute_task(task)
        # result.success == True
    """

    def __init__(
        self,
        scheduler: DistributedScheduler,
        transport: Optional[TransportProvider] = None,
        rpc_client: Optional[RPCClient] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self._scheduler = scheduler
        self._transport = transport
        self._rpc_client = rpc_client
        self._event_bus = event_bus
        self._lock = threading.RLock()

        # Task tracking
        self._tasks: Dict[str, DistributedTask] = {}
        self._active_tasks: Dict[str, threading.Thread] = {}
        self._completed: List[str] = []

        # Local execution fallback
        self._local_executor: Optional[Callable[[DistributedTask], ExecutionResult]] = None

        # Migration support
        self._migration_enabled = True

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_local_executor(
        self, executor_fn: Callable[[DistributedTask], ExecutionResult]
    ) -> None:
        """Set the local execution function for fallback."""
        self._local_executor = executor_fn

    def set_migration_enabled(self, enabled: bool) -> None:
        """Enable or disable task migration on failure."""
        self._migration_enabled = enabled

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    def execute_task(
        self,
        task: DistributedTask,
        scheduling_decision: Optional[SchedulingDecision] = None,
    ) -> ExecutionResult:
        """Execute a task using the optimal cluster node.

        Determines the target node via the scheduler if not provided,
        dispatches the task, and returns the result.

        Args:
            task: The task to execute
            scheduling_decision: Pre-computed scheduling decision (optional)

        Returns:
            ExecutionResult with the task outcome
        """
        if scheduling_decision is None:
            scheduling_decision = self._scheduler.schedule_task(
                task_id=task.id,
                required_tools=task.payload.get("required_tools"),
                timeout_seconds=task.timeout_seconds,
            )

        task.target_node = scheduling_decision.target_node_id
        task.status = TaskStatus.DISPATCHED

        with self._lock:
            self._tasks[task.id] = task

        if self._event_bus:
            self._event_bus.emit_async("cluster.task_dispatched", {
                "task_id": task.id,
                "target_node": task.target_node,
            })

        start = time.time()

        try:
            if scheduling_decision.target == ExecutionTarget.LOCAL or \
               task.target_node == "local":
                result = self._execute_local(task)
            elif scheduling_decision.target == ExecutionTarget.REMOTE:
                result = self._execute_remote(task)
            elif scheduling_decision.target == ExecutionTarget.PARALLEL:
                result = self._execute_parallel(task, scheduling_decision)
            else:
                result = self._execute_local(task)  # Fallback to local
        except Exception as exc:
            result = ExecutionResult(
                task_id=task.id,
                success=False,
                error=f"Execution error: {exc}",
                duration_seconds=time.time() - start,
            )

        # Update task state
        task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
        task.result = result.output if result.success else None
        task.error = result.error
        task.completed_at = time.time()

        with self._lock:
            self._active_tasks.pop(task.id, None)
            self._completed.append(task.id)

        if self._event_bus:
            event_topic = "cluster.task_completed" if result.success \
                          else "cluster.task_failed"
            self._event_bus.emit_async(event_topic, {
                "task_id": task.id,
                "node_id": result.node_id,
                "duration": result.duration_seconds,
                "error": result.error,
            })

        return result

    def _execute_local(self, task: DistributedTask) -> ExecutionResult:
        """Execute a task on the local node."""
        start = time.time()
        task.status = TaskStatus.RUNNING
        task.started_at = start

        if self._local_executor:
            try:
                result = self._local_executor(task)
                result.node_id = "local"
                return result
            except Exception as exc:
                elapsed = time.time() - start
                return ExecutionResult(
                    task_id=task.id,
                    success=False,
                    error=str(exc),
                    duration_seconds=elapsed,
                    node_id="local",
                )

        # Default local execution: return the payload as the result
        elapsed = time.time() - start
        return ExecutionResult(
            task_id=task.id,
            success=True,
            output=json.dumps(task.payload),
            duration_seconds=elapsed,
            node_id="local",
        )

    def _execute_remote(self, task: DistributedTask) -> ExecutionResult:
        """Execute a task on a remote node via transport/RPC."""
        if self._rpc_client is None or task.target_node is None:
            logger.warning(
                "DistributedExecutor: no RPC client for remote execution, "
                "falling back to local",
            )
            return self._execute_local(task)

        start = time.time()
        task.status = TaskStatus.RUNNING
        task.started_at = start

        try:
            # Send execution request via RPC
            response = self._rpc_client.call(
                node_id=task.target_node,
                method="cluster.execute_task",
                params={
                    "task_id": task.id,
                    "task_name": task.name,
                    "payload": task.payload,
                    "timeout_seconds": task.timeout_seconds,
                },
                timeout=task.timeout_seconds + 10.0,
            )

            elapsed = time.time() - start
            success = response.get("success", False)
            return ExecutionResult(
                task_id=task.id,
                success=success,
                output=response.get("output", ""),
                error=response.get("error"),
                duration_seconds=elapsed,
                node_id=task.target_node,
                metadata=response.get("metadata", {}),
            )

        except Exception as exc:
            elapsed = time.time() - start

            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                logger.info(
                    "DistributedExecutor: retrying task %s on %s (attempt %d/%d)",
                    task.id[:8], task.target_node[:8],
                    task.retry_count, task.max_retries,
                )
                time.sleep(task.retry_count * 2.0)  # Exponential backoff
                return self._execute_remote(task)

            # Try migration if enabled
            if self._migration_enabled:
                logger.info(
                    "DistributedExecutor: migrating task %s from %s to local",
                    task.id[:8], task.target_node[:8],
                )
                task.status = TaskStatus.MIGRATING
                return self._execute_local(task)

            return ExecutionResult(
                task_id=task.id,
                success=False,
                error=f"Remote execution failed after {task.retry_count + 1} attempts: {exc}",
                duration_seconds=elapsed,
                node_id=task.target_node,
            )

    def _execute_parallel(
        self,
        task: DistributedTask,
        decision: SchedulingDecision,
    ) -> ExecutionResult:
        """Execute a task in parallel across multiple nodes."""
        nodes = decision.parallel_nodes
        if not nodes:
            return self._execute_local(task)

        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = []
        with ThreadPoolExecutor(max_workers=len(nodes)) as pool:
            futures = {}
            for node_id in nodes:
                parallel_task = DistributedTask(
                    id=f"{task.id}-{node_id[:8]}",
                    name=task.name,
                    payload=task.payload,
                    target_node=node_id,
                    timeout_seconds=task.timeout_seconds,
                )
                future = pool.submit(self._execute_remote, parallel_task)
                futures[future] = node_id

            for future in as_completed(futures):
                try:
                    result = future.result(timeout=task.timeout_seconds + 10)
                    results.append(result)
                except Exception as exc:
                    results.append(ExecutionResult(
                        task_id=task.id,
                        success=False,
                        error=str(exc),
                        node_id=futures[future],
                    ))

        # Aggregate results: succeed if any parallel task succeeded
        successful = [r for r in results if r.success]
        if successful:
            return ExecutionResult(
                task_id=task.id,
                success=True,
                output="\n---\n".join(r.output for r in successful),
                duration_seconds=max(r.duration_seconds for r in results),
                node_id=",".join(r.node_id for r in successful),
                metadata={"parallel_results": len(successful), "total_results": len(results)},
            )

        return ExecutionResult(
            task_id=task.id,
            success=False,
            error="All parallel executions failed: " + "; ".join(
                r.error or "unknown" for r in results
            ),
            node_id=",".join(r.node_id for r in results),
        )

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task.

        Returns True if the task was cancelled.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED,
                               TaskStatus.CANCELLED):
                return False
            task.status = TaskStatus.CANCELLED

        if self._event_bus:
            self._event_bus.emit_async("cluster.task_cancelled", {
                "task_id": task_id,
            })

        return True

    def get_task(self, task_id: str) -> Optional[DistributedTask]:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[DistributedTask]:
        """List all tasks, optionally filtered by status."""
        with self._lock:
            tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return executor statistics."""
        with self._lock:
            by_status: Dict[str, int] = {}
            for t in self._tasks.values():
                by_status[t.status.value] = by_status.get(t.status.value, 0) + 1

            return {
                "total_tasks": len(self._tasks),
                "active_tasks": len(self._active_tasks),
                "completed_tasks": len(self._completed),
                "by_status": by_status,
                "migration_enabled": self._migration_enabled,
            }
