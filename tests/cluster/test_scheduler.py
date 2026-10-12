"""
Tests for the Distributed Scheduler module.
"""

import pytest

from cluster.node_registry import NodeRegistry, NodeCapabilities
from cluster.load_balancer import LoadBalancer
from cluster.scheduler import (
    DistributedScheduler,
    SchedulingDecision,
    SchedulingStrategy,
    ExecutionTarget,
)
from cluster.topology import ClusterTopology


class TestDistributedScheduler:
    """Test DistributedScheduler class."""

    def test_schedule_local_only(self):
        """Test scheduling with single node."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        # Register local node
        caps = NodeCapabilities(hostname="local", cpu_count=4, supported_tools=["terminal"])
        registry.register_node("local", capabilities=caps)
        registry.mark_healthy("local")

        decision = scheduler.schedule_task("task-1")
        assert decision.target == ExecutionTarget.LOCAL
        assert decision.confidence > 0

    def test_schedule_no_nodes(self):
        """Test scheduling with no nodes registered."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        decision = scheduler.schedule_task("task-nope")
        assert decision.target == ExecutionTarget.FALLBACK
        assert decision.confidence < 0.5

    def test_schedule_remote_node(self):
        """Test scheduling to remote node."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        # Register a remote node
        caps = NodeCapabilities(hostname="remote-1", cpu_count=16, memory_mb=65536)
        registry.register_node("remote-1", capabilities=caps)
        registry.mark_healthy("remote-1")

        decision = scheduler.schedule_task("task-2")
        assert decision.target == ExecutionTarget.REMOTE
        assert decision.target_node_id == "remote-1"

    def test_schedule_with_fallback(self):
        """Test scheduling with fallback."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        # No nodes, should fallback
        decision = scheduler.schedule_with_fallback("task-3")
        assert decision.target in (ExecutionTarget.FALLBACK, ExecutionTarget.LOCAL)

    def test_schedule_with_tool_requirement(self):
        """Test scheduling with tool requirements."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        # Node with terminal but not browser
        caps = NodeCapabilities(hostname="worker", supported_tools=["terminal"])
        registry.register_node("worker", capabilities=caps)
        registry.mark_healthy("worker")

        # Should match terminal requirement
        decision = scheduler.schedule_task("task-4", required_tools=["terminal"])
        assert decision.target == ExecutionTarget.REMOTE

    def test_schedule_with_resource_requirements(self):
        """Test scheduling with resource requirements."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        caps = NodeCapabilities(hostname="big-node", cpu_count=32, memory_mb=131072)
        registry.register_node("big-node", capabilities=caps)
        registry.mark_healthy("big-node")

        # Should match high-resource requirement
        decision = scheduler.schedule_task("task-5", min_cpu=16, min_memory_mb=65536)
        assert decision.target == ExecutionTarget.REMOTE

    def test_parallel_scheduling(self):
        """Test parallel task scheduling."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        # Register multiple nodes
        for i in range(3):
            caps = NodeCapabilities(hostname=f"worker-{i}")
            registry.register_node(f"worker-{i}", capabilities=caps)
            registry.mark_healthy(f"worker-{i}")

        decision = scheduler.schedule_parallel("parallel-task", min_nodes=2)
        assert decision.target == ExecutionTarget.PARALLEL
        assert len(decision.parallel_nodes) >= 2

    def test_mark_completed(self):
        """Test marking tasks as completed."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        caps = NodeCapabilities(hostname="worker")
        registry.register_node("worker", capabilities=caps)
        registry.mark_healthy("worker")

        decision = scheduler.schedule_task("task-done")
        scheduler.mark_completed("task-done")

        stats = scheduler.get_stats()
        assert stats["completed_tasks"] >= 1

    def test_mark_failed(self):
        """Test marking tasks as failed."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        caps = NodeCapabilities(hostname="worker")
        registry.register_node("worker", capabilities=caps)
        registry.mark_healthy("worker")

        decision = scheduler.schedule_task("task-fail")
        scheduler.mark_failed("task-fail")

        stats = scheduler.get_stats()
        assert stats["active_tasks"] == 0

    def test_get_decision(self):
        """Test retrieving a scheduling decision."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        caps = NodeCapabilities(hostname="worker")
        registry.register_node("worker", capabilities=caps)
        registry.mark_healthy("worker")

        decision = scheduler.schedule_task("get-decision")
        retrieved = scheduler.get_decision("get-decision")
        assert retrieved is not None
        assert retrieved.task_id == "get-decision"

    def test_get_decision_nonexistent(self):
        """Test retrieving a nonexistent decision."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        assert scheduler.get_decision("nonexistent") is None

    def test_strategy_mapping(self):
        """Test strategy mapping."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        # Setting different strategies should work
        scheduler.set_default_strategy(SchedulingStrategy.LOWEST_LATENCY)
        assert scheduler.get_stats()["default_strategy"] == "lowest_latency"

    def test_get_active_tasks(self):
        """Test getting active tasks."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        caps = NodeCapabilities(hostname="worker")
        registry.register_node("worker", capabilities=caps)
        registry.mark_healthy("worker")

        scheduler.schedule_task("active-task")
        active = scheduler.get_active_tasks()
        assert "active-task" in active

    def test_schedule_local_preference(self):
        """Test that local execution is preferred."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        # Register local node
        local_caps = NodeCapabilities(hostname="local", cpu_count=4)
        registry.register_node("local", capabilities=local_caps)
        registry.mark_healthy("local")

        # With prefer_local=True, should choose local
        scheduler.set_prefer_local(True)
        decision = scheduler.schedule_task("local-pref")
        assert decision.target == ExecutionTarget.LOCAL

    def test_with_topology(self):
        """Test scheduler with topology."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        topology = ClusterTopology()
        scheduler = DistributedScheduler(registry, balancer, topology=topology)

        caps = NodeCapabilities(hostname="worker")
        registry.register_node("worker", capabilities=caps)
        registry.mark_healthy("worker")

        decision = scheduler.schedule_task("topo-task")
        assert decision is not None


class TestSchedulingDecision:
    """Test SchedulingDecision dataclass."""

    def test_default_decision(self):
        """Test default scheduling decision."""
        decision = SchedulingDecision(task_id="test")
        assert decision.task_id == "test"
        assert decision.target == ExecutionTarget.LOCAL
        assert decision.confidence == 1.0
        assert len(decision.fallback_nodes) == 0
        assert len(decision.parallel_nodes) == 0

    def test_remote_decision(self):
        """Test remote execution decision."""
        decision = SchedulingDecision(
            task_id="remote-test",
            target=ExecutionTarget.REMOTE,
            target_node_id="node-42",
            strategy=SchedulingStrategy.LOWEST_LATENCY,
            confidence=0.85,
            reasoning="Best latency match",
            estimated_latency_ms=12.5,
        )
        assert decision.task_id == "remote-test"
        assert decision.target == ExecutionTarget.REMOTE
        assert decision.target_node_id == "node-42"
        assert decision.strategy == SchedulingStrategy.LOWEST_LATENCY
        assert decision.confidence == 0.85
