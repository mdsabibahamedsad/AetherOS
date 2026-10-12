"""
Distributed Scheduler — extends the existing Aetheros scheduler for
distributed task execution across cluster nodes.

Decides between local execution, remote execution, parallel execution,
and fallback execution based on:
  - Latency requirements
  - Resource availability
  - Node capabilities
  - Task priority
  - Current load
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
from cron.scheduler import run_job  # Existing cron job runner

from cluster.node_registry import NodeRegistry, NodeInfo, NodeStatus
from cluster.load_balancer import LoadBalancer, BalancerDecision, LoadBalancingStrategy
from cluster.topology import ClusterTopology

logger = logging.getLogger(__name__)


class SchedulingStrategy(enum.Enum):
    """Strategy for scheduling tasks across the cluster."""
    LOCAL_ONLY = "local_only"
    REMOTE_ONLY = "remote_only"
    BALANCED = "balanced"
    LOWEST_LATENCY = "lowest_latency"
    MOST_RESOURCES = "most_resources"
    CAPABILITY_MATCH = "capability_match"
    FALLBACK = "fallback"


class ExecutionTarget(enum.Enum):
    """Where a task should be executed."""
    LOCAL = "local"
    REMOTE = "remote"
    PARALLEL = "parallel"
    FALLBACK = "fallback"


@dataclass
class SchedulingDecision:
    """Decision about where and how to execute a task.

    Attributes:
        task_id: The task being scheduled
        target: Where to execute
        target_node_id: Target node ID (None for local)
        strategy: The strategy used for this decision
        confidence: Confidence in this decision (0.0 - 1.0)
        reasoning: Why this decision was made
        estimated_latency_ms: Estimated execution latency
        fallback_nodes: Alternative nodes if primary fails
        parallel_nodes: Nodes for parallel execution (if applicable)
    """
    task_id: str = ""
    target: ExecutionTarget = ExecutionTarget.LOCAL
    target_node_id: Optional[str] = None
    strategy: SchedulingStrategy = SchedulingStrategy.BALANCED
    confidence: float = 1.0
    reasoning: str = ""
    estimated_latency_ms: float = 0.0
    fallback_nodes: List[str] = field(default_factory=list)
    parallel_nodes: List[str] = field(default_factory=list)


class DistributedScheduler:
    """Schedules tasks across the cluster based on requirements and node capabilities.

    Extends the existing AetherOS scheduler infrastructure with distributed
    scheduling decisions. Maintains backward compatibility — single-node
    mode works unchanged.

    Usage:
        scheduler = DistributedScheduler(node_registry, load_balancer, event_bus)

        # Schedule a single task
        decision = scheduler.schedule_task(
            task_id="task-1",
            required_tools=["terminal"],
            required_capabilities=["gpu"],
            priority=10,
        )
        # decision.target == ExecutionTarget.REMOTE
        # decision.target_node_id == "node-2"
    """

    def __init__(
        self,
        node_registry: NodeRegistry,
        load_balancer: LoadBalancer,
        event_bus: Optional[EventBus] = None,
        topology: Optional[ClusterTopology] = None,
    ):
        self._node_registry = node_registry
        self._load_balancer = load_balancer
        self._event_bus = event_bus
        self._topology = topology
        self._lock = threading.RLock()

        # Scheduling configuration
        self._prefer_local = True
        self._max_remote_latency_ms = 5000.0
        self._default_strategy = SchedulingStrategy.BALANCED

        # Task tracking
        self._scheduled_tasks: Dict[str, SchedulingDecision] = {}
        self._active_tasks: Dict[str, str] = {}  # task_id -> node_id
        self._completed_tasks: List[str] = []

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_default_strategy(self, strategy: SchedulingStrategy) -> None:
        """Set the default scheduling strategy."""
        self._default_strategy = strategy

    def set_prefer_local(self, prefer: bool) -> None:
        """Set whether to prefer local execution."""
        self._prefer_local = prefer

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def schedule_task(
        self,
        task_id: str,
        required_tools: Optional[List[str]] = None,
        required_plugins: Optional[List[str]] = None,
        required_capabilities: Optional[List[str]] = None,
        min_cpu: int = 0,
        min_memory_mb: int = 0,
        require_gpu: bool = False,
        priority: int = 50,
        strategy: Optional[SchedulingStrategy] = None,
        timeout_seconds: float = 300.0,
    ) -> SchedulingDecision:
        """Schedule a task for execution.

        Evaluates available nodes, their capabilities, and current load
        to determine the best execution target.

        Returns a SchedulingDecision with the recommended target.
        """
        task_id = task_id or uuid.uuid4().hex[:12]
        effective_strategy = strategy or self._default_strategy

        # Get this node's info (for local execution preference)
        local_node_id = "local"

        # Find candidate nodes
        candidates = self._node_registry.find_nodes(
            required_tools=required_tools,
            required_plugins=required_plugins,
            min_cpu=min_cpu,
            min_memory_mb=min_memory_mb,
            require_gpu=require_gpu,
            healthy_only=True,
        )

        if not candidates:
            fallback = self._build_fallback_decision(task_id, effective_strategy,
                                                     "No healthy nodes available")
            self._track_decision(fallback)
            return fallback

        # Check if local node is suitable
        local_suitable = self._is_local_suitable(
            required_tools, required_plugins,
            min_cpu, min_memory_mb, require_gpu,
        )

        # Quick decision: single node, it IS the local node, and local is suitable
        if (
            len(candidates) == 1
            and candidates[0].node_id == local_node_id
            and local_suitable
            and self._prefer_local
        ):
            decision = SchedulingDecision(
                task_id=task_id,
                target=ExecutionTarget.LOCAL,
                target_node_id=local_node_id,
                strategy=effective_strategy,
                confidence=1.0,
                reasoning="Only one node available and local execution is suitable",
            )
            self._track_decision(decision)
            return decision

        # Use load balancer for optimal assignment
        balancer_decision = self._load_balancer.select_node(
            candidates=candidates,
            required_tools=required_tools or [],
            priority=priority,
            strategy=self._map_to_balancer_strategy(effective_strategy),
        )

        if balancer_decision is None or not balancer_decision.node_id:
            decision = self._build_fallback_decision(
                task_id, effective_strategy,
                "Load balancer could not select a node",
            )
            self._track_decision(decision)
            return decision

        # Determine execution target
        target = ExecutionTarget.REMOTE
        if balancer_decision.node_id == local_node_id or balancer_decision.node_id == "local":
            target = ExecutionTarget.LOCAL

        # Find fallback nodes
        fallback_nodes = [
            n.node_id for n in candidates
            if n.node_id != balancer_decision.node_id
        ]

        decision = SchedulingDecision(
            task_id=task_id,
            target=target,
            target_node_id=balancer_decision.node_id,
            strategy=effective_strategy,
            confidence=balancer_decision.confidence,
            reasoning=balancer_decision.reasoning,
            estimated_latency_ms=balancer_decision.estimated_latency_ms,
            fallback_nodes=fallback_nodes[:3],  # Top 3 fallbacks
        )

        self._track_decision(decision)

        if self._event_bus:
            self._event_bus.emit_async("cluster.task_scheduled", {
                "task_id": task_id,
                "target": target.value,
                "target_node": balancer_decision.node_id,
                "confidence": decision.confidence,
            })

        logger.info(
            "DistributedScheduler: scheduled task %s -> %s on %s (%.0f%% confidence)",
            task_id[:8], target.value,
            balancer_decision.node_id[:8],
            decision.confidence * 100,
        )

        return decision

    def schedule_parallel(
        self,
        task_id: str,
        required_tools: Optional[List[str]] = None,
        min_nodes: int = 2,
        max_nodes: int = 5,
        strategy: Optional[SchedulingStrategy] = None,
    ) -> SchedulingDecision:
        """Schedule a task for parallel execution across multiple nodes.

        Returns a decision with multiple target nodes for parallel execution.
        """
        effective_strategy = strategy or SchedulingStrategy.LOWEST_LATENCY

        candidates = self._node_registry.find_nodes(
            required_tools=required_tools,
            healthy_only=True,
        )

        if not candidates:
            return self._build_fallback_decision(
                task_id, effective_strategy,
                "No healthy nodes available for parallel execution",
            )

        # Select up to max_nodes for parallel execution
        parallel_nodes = candidates[:max_nodes]

        decision = SchedulingDecision(
            task_id=task_id,
            target=ExecutionTarget.PARALLEL,
            strategy=effective_strategy,
            confidence=0.8,
            reasoning=f"Parallel execution across {len(parallel_nodes)} nodes",
            parallel_nodes=[n.node_id for n in parallel_nodes],
        )

        self._track_decision(decision)

        logger.info(
            "DistributedScheduler: parallel task %s across %d nodes",
            task_id[:8], len(parallel_nodes),
        )

        return decision

    def schedule_with_fallback(
        self,
        task_id: str,
        required_tools: Optional[List[str]] = None,
        fallback_strategy: SchedulingStrategy = SchedulingStrategy.LOCAL_ONLY,
        **kwargs,
    ) -> SchedulingDecision:
        """Schedule a task with automatic fallback if remote execution fails.

        First tries the optimal remote node, then falls back to local
        if remote fails.
        """
        # Try optimal scheduling
        decision = self.schedule_task(
            task_id=task_id,
            required_tools=required_tools,
            **kwargs,
        )

        if decision.target != ExecutionTarget.FALLBACK:
            return decision

        # Fallback to local
        fallback_decision = SchedulingDecision(
            task_id=task_id,
            target=ExecutionTarget.FALLBACK,
            target_node_id="local",
            strategy=fallback_strategy,
            confidence=0.5,
            reasoning=f"Primary scheduling failed, falling back to local execution. "
                      f"Original: {decision.reasoning}",
        )

        self._track_decision(fallback_decision)
        return fallback_decision

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_local_suitable(
        self,
        required_tools: Optional[List[str]] = None,
        required_plugins: Optional[List[str]] = None,
        min_cpu: int = 0,
        min_memory_mb: int = 0,
        require_gpu: bool = False,
    ) -> bool:
        """Check if the local node can satisfy the requirements.

        For local execution, we assume the local node is capable unless
        specific requirements are not met.
        """
        import os
        import platform as _platform

        if require_gpu:
            try:
                import torch
                if not torch.cuda.is_available():
                    return False
            except ImportError:
                # Can't verify GPU — assume available unless proven otherwise
                pass

        if min_cpu > 0:
            cpu_count = os.cpu_count() or 0
            if cpu_count < min_cpu:
                return False

        # For tools and plugins, local always has everything since
        # it runs the same Aetheros installation
        return True

    def _build_fallback_decision(
        self,
        task_id: str,
        strategy: SchedulingStrategy,
        reason: str,
    ) -> SchedulingDecision:
        """Build a fallback decision when scheduling fails."""
        return SchedulingDecision(
            task_id=task_id,
            target=ExecutionTarget.FALLBACK,
            target_node_id="local",
            strategy=SchedulingStrategy.FALLBACK,
            confidence=0.3,
            reasoning=f"Fallback: {reason}",
        )

    def _track_decision(self, decision: SchedulingDecision) -> None:
        """Track a scheduling decision."""
        with self._lock:
            self._scheduled_tasks[decision.task_id] = decision
            if decision.target == ExecutionTarget.REMOTE and decision.target_node_id:
                self._active_tasks[decision.task_id] = decision.target_node_id

    @staticmethod
    def _map_to_balancer_strategy(
        strategy: SchedulingStrategy,
    ) -> LoadBalancingStrategy:
        """Map a scheduling strategy to a load balancer strategy."""
        mapping = {
            SchedulingStrategy.LOCAL_ONLY: LoadBalancingStrategy.ROUND_ROBIN,
            SchedulingStrategy.BALANCED: LoadBalancingStrategy.LEAST_LOADED,
            SchedulingStrategy.LOWEST_LATENCY: LoadBalancingStrategy.LOWEST_LATENCY,
            SchedulingStrategy.MOST_RESOURCES: LoadBalancingStrategy.RESOURCE_BASED,
            SchedulingStrategy.CAPABILITY_MATCH: LoadBalancingStrategy.CAPABILITY_BASED,
        }
        return mapping.get(strategy, LoadBalancingStrategy.ROUND_ROBIN)

    # ------------------------------------------------------------------
    # Task tracking
    # ------------------------------------------------------------------

    def mark_completed(self, task_id: str) -> None:
        """Mark a task as completed."""
        with self._lock:
            self._active_tasks.pop(task_id, None)
            if task_id not in self._completed_tasks:
                self._completed_tasks.append(task_id)

    def mark_failed(self, task_id: str) -> None:
        """Mark a task as failed."""
        with self._lock:
            self._active_tasks.pop(task_id, None)

    def get_decision(self, task_id: str) -> Optional[SchedulingDecision]:
        """Get the scheduling decision for a task."""
        with self._lock:
            return self._scheduled_tasks.get(task_id)

    def get_active_tasks(self) -> Dict[str, str]:
        """Get currently active tasks and their assigned nodes."""
        with self._lock:
            return dict(self._active_tasks)

    def get_stats(self) -> Dict[str, Any]:
        """Return scheduler statistics."""
        with self._lock:
            return {
                "total_scheduled": len(self._scheduled_tasks),
                "active_tasks": len(self._active_tasks),
                "completed_tasks": len(self._completed_tasks),
                "default_strategy": self._default_strategy.value,
                "prefer_local": self._prefer_local,
            }
