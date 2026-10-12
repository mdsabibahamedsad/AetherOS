"""
Tests for the Load Balancer module.
"""

import pytest

from cluster.load_balancer import LoadBalancer, LoadBalancingStrategy, BalancerDecision
from cluster.node_registry import NodeInfo, NodeCapabilities


def _make_node_info(node_id: str, cpu: int = 4, memory: int = 16384,
                    tools: list = None, gpu: int = 0) -> NodeInfo:
    """Helper to create a NodeInfo for tests."""
    return NodeInfo(
        node_id=node_id,
        capabilities=NodeCapabilities(
            hostname=node_id,
            cpu_count=cpu,
            memory_mb=memory,
            gpu_count=gpu,
            supported_tools=tools or [],
        ),
    )


class TestLoadBalancer:
    """Test LoadBalancer class."""

    def test_round_robin(self):
        """Test round-robin strategy."""
        balancer = LoadBalancer(LoadBalancingStrategy.ROUND_ROBIN)
        nodes = [_make_node_info(f"node-{i}") for i in range(3)]

        # Round robin should cycle through nodes
        d1 = balancer.select_node(nodes)
        d2 = balancer.select_node(nodes)
        d3 = balancer.select_node(nodes)

        assert d1.node_id != d2.node_id or d2.node_id != d3.node_id

    def test_least_loaded(self):
        """Test least-loaded strategy."""
        balancer = LoadBalancer(LoadBalancingStrategy.LEAST_LOADED)
        nodes = [_make_node_info("node-1"), _make_node_info("node-2")]

        # Add load to node-1
        balancer.update_load("node-1", 5)
        balancer.update_load("node-2", 1)

        decision = balancer.select_node(nodes)
        assert decision.node_id == "node-2"  # Least loaded

    def test_resource_based(self):
        """Test resource-based strategy."""
        balancer = LoadBalancer(LoadBalancingStrategy.RESOURCE_BASED)
        nodes = [_make_node_info("node-1"), _make_node_info("node-2")]

        # node-1 has high resource usage
        balancer.update_resource_usage("node-1", 0.9)
        balancer.update_resource_usage("node-2", 0.2)

        decision = balancer.select_node(nodes)
        assert decision.node_id == "node-2"  # More free resources

    def test_random_strategy(self):
        """Test random strategy."""
        balancer = LoadBalancer(LoadBalancingStrategy.RANDOM)
        nodes = [_make_node_info("node-1")]

        decision = balancer.select_node(nodes)
        assert decision.node_id == "node-1"

    def test_lowest_latency(self):
        """Test lowest-latency strategy."""
        balancer = LoadBalancer(LoadBalancingStrategy.LOWEST_LATENCY)
        nodes = [_make_node_info("node-1"), _make_node_info("node-2")]

        balancer.set_latency("node-1", 100.0)
        balancer.set_latency("node-2", 5.0)

        decision = balancer.select_node(nodes)
        assert decision.node_id == "node-2"  # Lower latency

    def test_capability_based(self):
        """Test capability-based strategy."""
        balancer = LoadBalancer(LoadBalancingStrategy.CAPABILITY_BASED)
        nodes = [
            _make_node_info("small", cpu=2, memory=2048),
            _make_node_info("large", cpu=16, memory=65536, gpu=2),
        ]

        decision = balancer.select_node(nodes)
        assert decision.node_id == "large"  # More capable

    def test_filter_by_required_tools(self):
        """Test filtering nodes by required tools."""
        balancer = LoadBalancer()

        n1 = _make_node_info("node-1", tools=["terminal"])
        n2 = _make_node_info("node-2", tools=["terminal", "browser"])

        decision = balancer.select_node([n1, n2], required_tools=["browser"])
        assert decision.node_id == "node-2"

    def test_empty_candidates(self):
        """Test selection with no candidates."""
        balancer = LoadBalancer()
        assert balancer.select_node([]) is None

    def test_exclude_nodes_without_tools(self):
        """Test that nodes without required tools are excluded."""
        balancer = LoadBalancer()

        n1 = _make_node_info("node-1", tools=["terminal"])
        n2 = _make_node_info("node-2", tools=[])

        decision = balancer.select_node([n1, n2], required_tools=["terminal"])
        assert decision.node_id == "node-1"

    def test_get_load_map(self):
        """Test load map reporting."""
        balancer = LoadBalancer()
        balancer.update_load("node-1", 3)
        balancer.update_load("node-2", 7)

        load_map = balancer.get_load_map()
        assert load_map["node-1"] == 3
        assert load_map["node-2"] == 7

    def test_reset(self):
        """Test resetting load balancer."""
        balancer = LoadBalancer()
        balancer.update_load("node-1", 5)
        balancer.reset()

        load_map = balancer.get_load_map()
        assert len(load_map) == 0

    def test_set_strategy(self):
        """Test changing strategy at runtime."""
        balancer = LoadBalancer()
        assert balancer.get_strategy() == LoadBalancingStrategy.ROUND_ROBIN

        balancer.set_strategy(LoadBalancingStrategy.LEAST_LOADED)
        assert balancer.get_strategy() == LoadBalancingStrategy.LEAST_LOADED

    def test_weighted_strategy(self):
        """Test weighted strategy."""
        balancer = LoadBalancer(LoadBalancingStrategy.WEIGHTED)
        nodes = [_make_node_info("node-1"), _make_node_info("node-2")]

        balancer.set_weight("node-1", 0.1)
        balancer.set_weight("node-2", 10.0)

        # node-2 should be selected more often due to higher weight
        decisions = [balancer.select_node(nodes).node_id for _ in range(20)]
        weighted_count = decisions.count("node-2")
        other_count = decisions.count("node-1")
        assert weighted_count > other_count
