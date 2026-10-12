"""
Tests for the Node Discovery module.
"""

import pytest

from cluster.node_registry import NodeRegistry
from cluster.node_discovery import (
    NodeDiscovery,
    ManualDiscoveryProvider,
    DiscoveryResult,
)


class TestManualDiscoveryProvider:
    """Test ManualDiscoveryProvider."""

    def test_empty_nodes(self):
        """Test discovery with no nodes configured."""
        provider = ManualDiscoveryProvider()
        results = provider.discover()
        assert len(results) == 0

    def test_single_node(self):
        """Test discovery with a single configured node."""
        provider = ManualDiscoveryProvider([
            {"node_id": "node-1", "hostname": "10.0.0.1", "port": 9876},
        ])
        results = provider.discover()
        assert len(results) == 1
        assert results[0].node_id == "node-1"
        assert results[0].hostname == "10.0.0.1"
        assert results[0].port == 9876

    def test_multiple_nodes(self):
        """Test discovery with multiple nodes."""
        nodes = [
            {"node_id": "node-1", "hostname": "10.0.0.1"},
            {"node_id": "node-2", "hostname": "10.0.0.2", "port": 9877},
            {"node_id": "node-3", "hostname": "10.0.0.3", "auth_token": "secret"},
        ]
        provider = ManualDiscoveryProvider(nodes)
        results = provider.discover()
        assert len(results) == 3

    def test_add_node(self):
        """Test adding a node at runtime."""
        provider = ManualDiscoveryProvider()
        provider.add_node("10.0.0.1", port=9876, node_id="runtime-node")
        results = provider.discover()
        assert len(results) == 1
        assert results[0].node_id == "runtime-node"

    def test_remove_node(self):
        """Test removing a node."""
        provider = ManualDiscoveryProvider([
            {"node_id": "keep", "hostname": "10.0.0.1"},
            {"node_id": "remove", "hostname": "10.0.0.2"},
        ])
        assert provider.remove_node("10.0.0.2") is True
        results = provider.discover()
        assert len(results) == 1
        assert results[0].node_id == "keep"

    def test_remove_nonexistent(self):
        """Test removing a nonexistent node."""
        provider = ManualDiscoveryProvider([
            {"node_id": "node-1", "hostname": "10.0.0.1"},
        ])
        assert provider.remove_node("nonexistent") is False


class TestNodeDiscovery:
    """Test NodeDiscovery class."""

    def test_create(self):
        """Test creating NodeDiscovery."""
        registry = NodeRegistry()
        discovery = NodeDiscovery(registry)
        assert discovery is not None
        assert len(discovery.list_providers()) == 0

    def test_add_provider(self):
        """Test adding a discovery provider."""
        registry = NodeRegistry()
        discovery = NodeDiscovery(registry)
        provider = ManualDiscoveryProvider()
        discovery.add_provider(provider)
        assert "ManualDiscoveryProvider" in discovery.list_providers()

    def test_remove_provider(self):
        """Test removing a discovery provider."""
        registry = NodeRegistry()
        discovery = NodeDiscovery(registry)
        provider = ManualDiscoveryProvider()
        discovery.add_provider(provider)
        assert discovery.remove_provider("ManualDiscoveryProvider") is True
        assert len(discovery.list_providers()) == 0

    def test_manual_discovery_no_auth(self):
        """Test manual discovery without auth."""
        registry = NodeRegistry()
        discovery = NodeDiscovery(registry, require_auth=False)
        provider = ManualDiscoveryProvider([
            {"node_id": "node-1", "hostname": "10.0.0.1"},
        ])
        discovery.add_provider(provider)
        results = discovery.run_discovery()
        assert len(results) > 0  # Should auto-register

        # Node should be registered
        node = registry.get_node("node-1")
        assert node is not None

    def test_manual_discovery_with_auth(self):
        """Test manual discovery with auth."""
        registry = NodeRegistry()
        discovery = NodeDiscovery(registry, require_auth=True, auth_token="cluster-secret")
        provider = ManualDiscoveryProvider([
            {"node_id": "node-1", "hostname": "10.0.0.1", "auth_token": "cluster-secret"},
        ])
        discovery.add_provider(provider)
        results = discovery.run_discovery()
        assert len(results) > 0

    def test_discovery_auth_mismatch(self):
        """Test discovery with mismatched auth token."""
        registry = NodeRegistry()
        discovery = NodeDiscovery(registry, require_auth=True, auth_token="cluster-secret")
        provider = ManualDiscoveryProvider([
            {"node_id": "node-1", "hostname": "10.0.0.1", "auth_token": "wrong-token"},
        ])
        discovery.add_provider(provider)
        results = discovery.run_discovery()
        # Node should be rejected (pending but not auto-registered)
        assert len(results) == 0 or discovery.list_pending()

    def test_pending_approval(self):
        """Test pending approval workflow."""
        registry = NodeRegistry()
        discovery = NodeDiscovery(registry, require_auth=True)

        # Set up an unauthenticated manual discovery
        provider = ManualDiscoveryProvider([
            {"node_id": "pending-node", "hostname": "10.0.0.1"},
        ])
        discovery.add_provider(provider)

        # Run discovery without auth token
        results = discovery.run_discovery()
        assert len(results) > 0

        # Node should be pending
        pending = discovery.list_pending()
        assert len(pending) > 0

        # Approve the node
        assert discovery.approve_node("pending-node") is True
        node = registry.get_node("pending-node")
        assert node is not None

    def test_reject_pending(self):
        """Test rejecting a pending node."""
        registry = NodeRegistry()
        discovery = NodeDiscovery(registry, require_auth=True)
        provider = ManualDiscoveryProvider([
            {"node_id": "reject-node", "hostname": "10.0.0.1"},
        ])
        discovery.add_provider(provider)
        discovery.run_discovery()

        assert discovery.reject_node("reject-node") is True
        assert registry.get_node("reject-node") is None

    def test_pending_approval_callback(self):
        """Test pending approval callback."""
        registry = NodeRegistry()
        discovery = NodeDiscovery(registry, require_auth=True)

        callback_results = []

        def on_pending(result):
            callback_results.append(result.node_id)

        discovery.on_pending_approval(on_pending)

        provider = ManualDiscoveryProvider([
            {"node_id": "callback-node", "hostname": "10.0.0.1"},
        ])
        discovery.add_provider(provider)
        discovery.run_discovery()

        assert len(callback_results) > 0
        assert "callback-node" in callback_results

    def test_start_stop(self):
        """Test starting and stopping discovery."""
        registry = NodeRegistry()
        discovery = NodeDiscovery(registry)
        provider = ManualDiscoveryProvider([])
        discovery.add_provider(provider)

        discovery.start()
        # Should be running without error
        discovery.stop()

    def test_discovery_multiple_providers(self):
        """Test using multiple providers."""
        registry = NodeRegistry()
        discovery = NodeDiscovery(registry, require_auth=False)

        p1 = ManualDiscoveryProvider([
            {"node_id": "node-a", "hostname": "10.0.0.1"},
        ])
        p2 = ManualDiscoveryProvider([
            {"node_id": "node-b", "hostname": "10.0.0.2"},
        ])
        discovery.add_provider(p1)
        discovery.add_provider(p2)

        discovery.run_discovery()

        assert registry.get_node("node-a") is not None
        assert registry.get_node("node-b") is not None

    def test_discovery_no_duplicates(self):
        """Test that discovered nodes aren't duplicated."""
        registry = NodeRegistry()
        discovery = NodeDiscovery(registry, require_auth=False)

        provider = ManualDiscoveryProvider([
            {"node_id": "node-1", "hostname": "10.0.0.1"},
        ])
        discovery.add_provider(provider)

        # Run discovery twice
        discovery.run_discovery()
        discovery.run_discovery()

        nodes = registry.list_nodes()
        assert len(nodes) == 1  # Should not duplicate
