"""
Tests for the Cluster Capability Registry module.
"""

import pytest

from cluster.capability_registry import (
    ClusterCapabilityRegistry,
    NodeCapability,
    CapabilityCategory,
)


class TestClusterCapabilityRegistry:
    """Test ClusterCapabilityRegistry."""

    def test_empty_registry(self):
        """Test empty registry."""
        reg = ClusterCapabilityRegistry()
        assert reg.get_stats()["tracked_nodes"] == 0
        assert reg.get_stats()["unique_capabilities"] == 0

    def test_register_node_capabilities(self):
        """Test registering capabilities for a node."""
        reg = ClusterCapabilityRegistry()

        capabilities = [
            NodeCapability(CapabilityCategory.HARDWARE, "gpu", "A100"),
            NodeCapability(CapabilityCategory.TOOLS, "browser"),
            NodeCapability(CapabilityCategory.HARDWARE, "cpu_32"),
        ]
        reg.register_node_capabilities("node-1", capabilities)

        assert reg.get_stats()["tracked_nodes"] == 1
        assert reg.get_stats()["unique_capabilities"] == 3

    def test_find_nodes_with_capability(self):
        """Test finding nodes by capability."""
        reg = ClusterCapabilityRegistry()

        reg.register_node_capabilities("node-1", [
            NodeCapability(CapabilityCategory.HARDWARE, "gpu"),
        ])
        reg.register_node_capabilities("node-2", [
            NodeCapability(CapabilityCategory.HARDWARE, "gpu"),
            NodeCapability(CapabilityCategory.TOOLS, "browser"),
        ])

        gpu_nodes = reg.find_nodes_with_capability("gpu")
        assert len(gpu_nodes) == 2

        browser_nodes = reg.find_nodes_with_capability("browser")
        assert len(browser_nodes) == 1
        assert "node-2" in browser_nodes

    def test_find_nodes_with_all(self):
        """Test finding nodes with ALL capabilities."""
        reg = ClusterCapabilityRegistry()

        reg.register_node_capabilities("node-1", [
            NodeCapability(CapabilityCategory.HARDWARE, "gpu"),
        ])
        reg.register_node_capabilities("node-2", [
            NodeCapability(CapabilityCategory.HARDWARE, "gpu"),
            NodeCapability(CapabilityCategory.TOOLS, "browser"),
        ])

        # Both gpu and browser
        nodes = reg.find_nodes_with_all(["gpu", "browser"])
        assert len(nodes) == 1
        assert "node-2" in nodes

        # Just gpu
        nodes = reg.find_nodes_with_all(["gpu"])
        assert len(nodes) == 2

        # Nonexistent
        nodes = reg.find_nodes_with_all(["nonexistent"])
        assert len(nodes) == 0

    def test_find_nodes_with_any(self):
        """Test finding nodes with ANY capability."""
        reg = ClusterCapabilityRegistry()

        reg.register_node_capabilities("node-1", [
            NodeCapability(CapabilityCategory.HARDWARE, "gpu"),
        ])
        reg.register_node_capabilities("node-2", [
            NodeCapability(CapabilityCategory.TOOLS, "browser"),
        ])
        reg.register_node_capabilities("node-3", [
            NodeCapability(CapabilityCategory.PLUGINS, "memory"),
        ])

        nodes = reg.find_nodes_with_any(["gpu", "browser"])
        assert len(nodes) == 2
        assert "node-1" in nodes
        assert "node-2" in nodes

    def test_has_capability(self):
        """Test checking node capability."""
        reg = ClusterCapabilityRegistry()
        reg.register_node_capabilities("node-1", [
            NodeCapability(CapabilityCategory.HARDWARE, "gpu"),
        ])

        assert reg.has_capability("node-1", "gpu") is True
        assert reg.has_capability("node-1", "browser") is False

    def test_get_node_capabilities(self):
        """Test getting capabilities for a node."""
        reg = ClusterCapabilityRegistry()

        caps = [
            NodeCapability(CapabilityCategory.HARDWARE, "gpu"),
            NodeCapability(CapabilityCategory.TOOLS, "terminal"),
        ]
        reg.register_node_capabilities("node-1", caps)

        result = reg.get_node_capabilities("node-1")
        assert len(result) == 2

    def test_remove_node(self):
        """Test removing a node's capabilities."""
        reg = ClusterCapabilityRegistry()
        reg.register_node_capabilities("node-1", [
            NodeCapability(CapabilityCategory.HARDWARE, "gpu"),
        ])

        assert reg.has_capability("node-1", "gpu") is True

        reg.remove_node("node-1")
        assert reg.has_capability("node-1", "gpu") is False

        # Check the node is gone
        assert len(reg.get_node_capabilities("node-1")) == 0

    def test_update_capabilities(self):
        """Test updating a node's capabilities."""
        reg = ClusterCapabilityRegistry()

        reg.register_node_capabilities("node-1", [
            NodeCapability(CapabilityCategory.HARDWARE, "gpu"),
        ])

        # Update with new capabilities
        reg.register_node_capabilities("node-1", [
            NodeCapability(CapabilityCategory.TOOLS, "browser"),
        ])

        # Old capability should be gone
        assert reg.has_capability("node-1", "gpu") is False
        # New capability should exist
        assert reg.has_capability("node-1", "browser") is True

    def test_capability_descriptions(self):
        """Test capability description lookup."""
        reg = ClusterCapabilityRegistry()

        cap = NodeCapability(
            CapabilityCategory.HARDWARE, "gpu",
            description="Graphics processing unit available",
        )
        reg.register_capability(cap.category, cap.name, cap.description)

        desc = reg.get_capability_description("gpu")
        assert desc == "Graphics processing unit available"

    def test_snapshot(self):
        """Test registry snapshot."""
        reg = ClusterCapabilityRegistry()
        reg.register_node_capabilities("node-1", [
            NodeCapability(CapabilityCategory.HARDWARE, "gpu"),
            NodeCapability(CapabilityCategory.TOOLS, "terminal"),
        ])

        snapshot = reg.snapshot()
        assert snapshot["total_nodes"] == 1
        assert snapshot["total_capabilities"] == 2
