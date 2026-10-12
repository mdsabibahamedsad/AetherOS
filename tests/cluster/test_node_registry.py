"""
Tests for the Node Registry module.
"""

import pytest

from cluster.node_registry import (
    NodeRegistry,
    NodeInfo,
    NodeCapabilities,
    NodeStatus,
)


class TestNodeCapabilities:
    """Test NodeCapabilities dataclass."""

    def test_default_capabilities(self):
        """Test default capabilities."""
        caps = NodeCapabilities()
        assert caps.hostname == ""
        assert caps.cpu_count == 0
        assert caps.memory_mb == 0
        assert caps.gpu_count == 0
        assert caps.supported_tools == []
        assert caps.supported_plugins == []

    def test_custom_capabilities(self):
        """Test custom capabilities."""
        caps = NodeCapabilities(
            hostname="server-1",
            platform="linux",
            python_version="3.11",
            cpu_count=8,
            memory_mb=32768,
            gpu_count=2,
            gpu_memory_mb=16384,
            supported_tools=["terminal", "web_search", "read_file"],
            supported_plugins=["memory.honcho", "image_gen.fal"],
            software_version="0.16.0",
        )
        assert caps.hostname == "server-1"
        assert caps.cpu_count == 8
        assert caps.memory_mb == 32768
        assert caps.gpu_count == 2
        assert len(caps.supported_tools) == 3
        assert caps.software_version == "0.16.0"


class TestNodeRegistry:
    """Test NodeRegistry class."""

    def test_empty_registry(self):
        """Test empty registry."""
        registry = NodeRegistry()
        assert len(registry.list_nodes()) == 0
        assert registry.get_stats()["total_nodes"] == 0

    def test_register_node(self):
        """Test registering a node."""
        registry = NodeRegistry()
        caps = NodeCapabilities(hostname="node-1", cpu_count=4, memory_mb=16384)

        node = registry.register_node("node-1", capabilities=caps)
        assert node is not None
        assert node.node_id == "node-1"
        assert node.capabilities.hostname == "node-1"
        assert node.status == NodeStatus.JOINING

        # Verify it's in the list
        nodes = registry.list_nodes()
        assert "node-1" in nodes

    def test_register_duplicate(self):
        """Test registering a duplicate node updates existing."""
        registry = NodeRegistry()
        caps1 = NodeCapabilities(hostname="node-1", cpu_count=4)
        caps2 = NodeCapabilities(hostname="node-1-updated", cpu_count=8)

        registry.register_node("node-1", capabilities=caps1)
        registry.register_node("node-1", capabilities=caps2)

        node = registry.get_node("node-1")
        assert node.capabilities.cpu_count == 8  # Updated
        assert len(registry.list_nodes()) == 1  # Still only 1 node

    def test_deregister_node(self):
        """Test deregistering a node."""
        registry = NodeRegistry()
        registry.register_node("node-1", capabilities=NodeCapabilities(hostname="test"))

        assert registry.deregister_node("node-1") is True
        assert registry.get_node("node-1") is None

    def test_deregister_nonexistent(self):
        """Test deregistering a nonexistent node."""
        registry = NodeRegistry()
        assert registry.deregister_node("nonexistent") is False

    def test_find_nodes_with_tool(self):
        """Test finding nodes by tool support."""
        registry = NodeRegistry()

        node1_caps = NodeCapabilities(hostname="node-1", supported_tools=["terminal", "browser"])
        node2_caps = NodeCapabilities(hostname="node-2", supported_tools=["terminal"])
        node3_caps = NodeCapabilities(hostname="node-3", supported_tools=["web_search"])

        registry.register_node("node-1", capabilities=node1_caps)
        registry.register_node("node-2", capabilities=node2_caps)
        registry.register_node("node-3", capabilities=node3_caps)

        # All nodes marked healthy for find_nodes query
        registry.mark_healthy("node-1")
        registry.mark_healthy("node-2")
        registry.mark_healthy("node-3")

        # Find by tool
        nodes = registry.find_nodes(required_tools=["terminal"])
        assert len(nodes) == 2  # node-1 and node-2

        nodes = registry.find_nodes(required_tools=["browser"])
        assert len(nodes) == 1  # Just node-1

        nodes = registry.find_nodes(required_tools=["terminal", "browser"])
        assert len(nodes) == 1  # Just node-1

    def test_find_nodes_with_plugin(self):
        """Test finding nodes by plugin support."""
        registry = NodeRegistry()

        caps1 = NodeCapabilities(hostname="node-1", supported_plugins=["memory.honcho"])
        caps2 = NodeCapabilities(hostname="node-2", supported_plugins=["image_gen.fal"])

        registry.register_node("node-1", capabilities=caps1)
        registry.register_node("node-2", capabilities=caps2)
        registry.mark_healthy("node-1")
        registry.mark_healthy("node-2")

        nodes = registry.find_nodes(required_plugins=["memory.honcho"])
        assert len(nodes) == 1
        assert nodes[0].node_id == "node-1"

    def test_find_nodes_with_resources(self):
        """Test finding nodes by resource requirements."""
        registry = NodeRegistry()

        caps1 = NodeCapabilities(hostname="server-a", cpu_count=4, memory_mb=8192)
        caps2 = NodeCapabilities(hostname="server-b", cpu_count=16, memory_mb=65536)

        registry.register_node("server-a", capabilities=caps1)
        registry.register_node("server-b", capabilities=caps2)
        registry.mark_healthy("server-a")
        registry.mark_healthy("server-b")

        nodes = registry.find_nodes(min_cpu=8)
        assert len(nodes) == 1
        assert nodes[0].node_id == "server-b"

        nodes = registry.find_nodes(min_memory_mb=16384)
        assert len(nodes) == 1
        assert nodes[0].node_id == "server-b"

    def test_find_nodes_with_gpu(self):
        """Test finding nodes by GPU requirement."""
        registry = NodeRegistry()

        caps1 = NodeCapabilities(hostname="cpu-node", gpu_count=0)
        caps2 = NodeCapabilities(hostname="gpu-node", gpu_count=4)

        registry.register_node("cpu-node", capabilities=caps1)
        registry.register_node("gpu-node", capabilities=caps2)
        registry.mark_healthy("cpu-node")
        registry.mark_healthy("gpu-node")

        nodes = registry.find_nodes(require_gpu=True)
        assert len(nodes) == 1
        assert nodes[0].node_id == "gpu-node"

    def test_healthy_only_filter(self):
        """Test healthy-only filter."""
        registry = NodeRegistry()

        registry.register_node("healthy-node", capabilities=NodeCapabilities(hostname="h"))
        registry.register_node("unhealthy-node", capabilities=NodeCapabilities(hostname="u"))

        registry.mark_healthy("healthy-node")
        registry.mark_unhealthy("unhealthy-node")

        all_nodes = registry.find_nodes(healthy_only=False)
        assert len(all_nodes) == 2

        healthy_only = registry.find_nodes(healthy_only=True)
        assert len(healthy_only) == 1
        assert healthy_only[0].node_id == "healthy-node"

    def test_status_transitions(self):
        """Test node status transitions."""
        registry = NodeRegistry()
        registry.register_node("test-node", capabilities=NodeCapabilities(hostname="test"))

        assert registry.mark_healthy("test-node") is True
        assert registry.get_node("test-node").status == NodeStatus.HEALTHY

        assert registry.mark_unhealthy("test-node") is True
        assert registry.get_node("test-node").status == NodeStatus.UNHEALTHY

        assert registry.mark_degraded("test-node") is True
        assert registry.get_node("test-node").status == NodeStatus.DEGRADED

        assert registry.mark_offline("test-node") is True
        assert registry.get_node("test-node").status == NodeStatus.OFFLINE

    def test_snapshot(self):
        """Test registry snapshot."""
        registry = NodeRegistry()
        registry.register_node("node-1", capabilities=NodeCapabilities(hostname="h1", cpu_count=4))
        registry.register_node("node-2", capabilities=NodeCapabilities(hostname="h2", cpu_count=8))

        snapshot = registry.snapshot()
        assert snapshot["total_nodes"] == 2
        assert len(snapshot["nodes"]) == 2

    def test_find_nodes_with_tool_direct(self):
        """Test find_nodes_with_tool helper."""
        registry = NodeRegistry()
        caps = NodeCapabilities(hostname="test", supported_tools=["terminal", "browser"])
        registry.register_node("test-node", capabilities=caps)

        nodes = registry.find_nodes_with_tool("terminal")
        assert len(nodes) == 1
        assert nodes[0].node_id == "test-node"

        nodes = registry.find_nodes_with_tool("nonexistent")
        assert len(nodes) == 0

    def test_find_nodes_with_capability(self):
        """Test find_nodes_with_capability helper."""
        registry = NodeRegistry()
        caps = NodeCapabilities(hostname="test", custom={"has-gpu": True})
        registry.register_node("gpu-node", capabilities=caps)

        nodes = registry.find_nodes_with_capability("has-gpu")
        assert len(nodes) == 1

    def test_node_has_tool(self):
        """Test node_has_tool check."""
        registry = NodeRegistry()
        caps = NodeCapabilities(hostname="test", supported_tools=["terminal"])
        registry.register_node("test-node", capabilities=caps)

        assert registry.node_has_tool("test-node", "terminal") is True
        assert registry.node_has_tool("test-node", "browser") is False

    def test_multiple_nodes_same_tool(self):
        """Test multiple nodes with same tool."""
        registry = NodeRegistry()
        for i in range(3):
            caps = NodeCapabilities(hostname=f"node-{i}", supported_tools=["terminal"])
            registry.register_node(f"node-{i}", capabilities=caps)

        nodes = registry.find_nodes_with_tool("terminal")
        assert len(nodes) == 3
