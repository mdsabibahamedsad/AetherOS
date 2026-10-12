"""
Task Replicator — replicates tasks across cluster nodes for fault tolerance.

Supports multiple replication strategies:
  - PRIMARY_BACKUP: execute on primary, replicate to backup
  - ACTIVE_ACTIVE: execute on all replicas simultaneously
  - QUORUM: execute on N nodes, succeed if majority completes
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus
from cluster.executor import DistributedTask, ExecutionResult, TaskStatus
from cluster.node_registry import NodeRegistry, NodeInfo

logger = logging.getLogger(__name__)


class ReplicationStrategy(enum.Enum):
    """Strategies for task replication across nodes."""
    NONE = "none"
    PRIMARY_BACKUP = "primary_backup"
    ACTIVE_ACTIVE = "active_active"
    QUORUM = "quorum"


class ReplicaState(enum.Enum):
    """State of a task replica on a target node."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DIVERGED = "diverged"


@dataclass
class TaskReplica:
    """A replica of a task running on a specific node.

    Attributes:
        replica_id: Unique replica ID
        task_id: Parent task ID
        node_id: Node executing this replica
        state: Current replica state
        result: Execution result (when completed)
        started_at: When execution started
        completed_at: When execution completed
        error: Error message if failed
    """
    replica_id: str = ""
    task_id: str = ""
    node_id: str = ""
    state: ReplicaState = ReplicaState.PENDING
    result: Optional[ExecutionResult] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None


class TaskReplicator:
    """Replicates tasks across cluster nodes for fault tolerance.

    Usage:
        replicator = TaskReplicator(node_registry, event_bus)
        replicator.set_strategy(ReplicationStrategy.PRIMARY_BACKUP)

        # Replicate a task
        replicas = replicator.replicate(task, nodes=[...])
    """

    def __init__(
        self,
        node_registry: NodeRegistry,
        event_bus: Optional[EventBus] = None,
    ):
        self._node_registry = node_registry
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._strategy = ReplicationStrategy.NONE
        self._replicas: Dict[str, List[TaskReplica]] = {}
        self._replication_factor = 2  # Default: 1 primary + 1 backup

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_strategy(self, strategy: ReplicationStrategy) -> None:
        """Set the replication strategy."""
        self._strategy = strategy

    def get_strategy(self) -> ReplicationStrategy:
        """Get the current replication strategy."""
        return self._strategy

    def set_replication_factor(self, factor: int) -> None:
        """Set the replication factor (number of copies)."""
        self._replication_factor = max(1, factor)

    # ------------------------------------------------------------------
    # Replication
    # ------------------------------------------------------------------

    def replicate(
        self,
        task: DistributedTask,
        nodes: Optional[List[NodeInfo]] = None,
        strategy: Optional[ReplicationStrategy] = None,
    ) -> List[TaskReplica]:
        """Replicate a task across specified nodes.

        Args:
            task: The task to replicate
            nodes: Target nodes (auto-selected if None)
            strategy: Override the default strategy

        Returns:
            List of TaskReplica objects
        """
        effective_strategy = strategy or self._strategy

        if effective_strategy == ReplicationStrategy.NONE:
            return []

        # Select target nodes
        if nodes is None or len(nodes) < self._replication_factor:
            candidates = self._node_registry.list_healthy_nodes()
            nodes = candidates[:self._replication_factor]

        if not nodes:
            logger.warning("TaskReplicator: no nodes available for replication")
            return []

        replicas = []
        for node in nodes[:self._replication_factor]:
            replica = TaskReplica(
                replica_id=uuid.uuid4().hex[:12],
                task_id=task.id,
                node_id=node.node_id,
                state=ReplicaState.PENDING,
            )
            replicas.append(replica)

        with self._lock:
            self._replicas[task.id] = replicas

        logger.info(
            "TaskReplicator: replicating task %s to %d nodes (strategy=%s)",
            task.id[:8], len(replicas), effective_strategy.value,
        )

        if self._event_bus:
            self._event_bus.emit_async("cluster.task_replicated", {
                "task_id": task.id,
                "replica_count": len(replicas),
                "strategy": effective_strategy.value,
                "nodes": [r.node_id for r in replicas],
            })

        return replicas

    def update_replica(
        self,
        task_id: str,
        node_id: str,
        state: ReplicaState,
        result: Optional[ExecutionResult] = None,
    ) -> None:
        """Update the state of a task replica."""
        with self._lock:
            replicas = self._replicas.get(task_id, [])
            for replica in replicas:
                if replica.node_id == node_id:
                    replica.state = state
                    replica.result = result
                    if state in (ReplicaState.COMPLETED, ReplicaState.FAILED):
                        replica.completed_at = time.time()
                    break

    def get_replicas(self, task_id: str) -> List[TaskReplica]:
        """Get all replicas for a task."""
        with self._lock:
            return list(self._replicas.get(task_id, []))

    def count_successful(self, task_id: str) -> int:
        """Count successful replicas for a task."""
        with self._lock:
            replicas = self._replicas.get(task_id, [])
            return sum(1 for r in replicas if r.state == ReplicaState.COMPLETED)

    def has_quorum(self, task_id: str) -> bool:
        """Check if a task has reached quorum (majority completed)."""
        with self._lock:
            replicas = self._replicas.get(task_id, [])
            if not replicas:
                return False
            successful = sum(1 for r in replicas if r.state == ReplicaState.COMPLETED)
            return successful > len(replicas) // 2

    def get_stats(self) -> Dict[str, Any]:
        """Return replicator statistics."""
        with self._lock:
            return {
                "strategy": self._strategy.value,
                "replication_factor": self._replication_factor,
                "tracked_tasks": len(self._replicas),
                "total_replicas": sum(len(r) for r in self._replicas.values()),
            }
