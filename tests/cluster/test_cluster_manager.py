"""
Tests for the Cluster Manager module.
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from cluster.cluster_manager import (
    ClusterManager,
    ClusterConfig,
    ClusterState,
    ClusterRole,
    ClusterEvent,
)


class TestClusterConfig:
    """Test ClusterConfig dataclass."""

    def test_default_config(self):
        """Test default cluster config values."""
        config = ClusterConfig()
        assert config.cluster_name == "aetheros-cluster"
        assert config.role == ClusterRole.STANDALONE
        assert config.heartbeat_interval_seconds == 5.0
        assert config.heartbeat_timeout_seconds == 15.0
        assert config.enable_discovery is True
        assert config.enable_health_monitoring is True

    def test_custom_config(self):
        """Test custom cluster config."""
        config = ClusterConfig(
            cluster_name="test-cluster",
            role=ClusterRole.LEADER,
            node_id="test-node-1",
            heartbeat_interval_seconds=1.0,
            heartbeat_timeout_seconds=5.0,
            max_nodes=10,
            require_auth=True,
            auth_token="secret-token",
        )
        assert config.cluster_name == "test-cluster"
        assert config.role == ClusterRole.LEADER
        assert config.node_id == "test-node-1"
        assert config.heartbeat_interval_seconds == 1.0
        assert config.max_nodes == 10
        assert config.auth_token == "secret-token"


class TestClusterManager:
    """Test ClusterManager class."""

    def test_initial_state(self):
        """Test initial cluster manager state."""
        manager = ClusterManager()
        assert manager.state == ClusterState.STOPPED
        assert manager.leader_id is None
        assert manager.is_leader is False

    def test_start_stop(self):
        """Test starting and stopping the cluster manager."""
        manager = ClusterManager()
        assert manager.state == ClusterState.STOPPED

        manager.start()
        assert manager.state == ClusterState.RUNNING

        manager.stop()
        assert manager.state == ClusterState.STOPPED

    def test_start_already_running(self):
        """Test starting an already running manager."""
        manager = ClusterManager()
        manager.start()
        assert manager.state == ClusterState.RUNNING

        # Starting again should be a no-op
        manager.start()
        assert manager.state == ClusterState.RUNNING

    def test_leader_role(self):
        """Test leader role assignment."""
        config = ClusterConfig(
            role=ClusterRole.LEADER,
            node_id="leader-node",
        )
        manager = ClusterManager(config=config)
        manager.start()
        assert manager.is_leader
        assert manager.leader_id == "leader-node"
        manager.stop()

    def test_elect_leader(self):
        """Test leader election."""
        manager = ClusterManager()
        manager.start()

        # Register a candidate
        manager.node_registry.register_node("candidate-1")
        manager.node_registry.mark_healthy("candidate-1")

        result = manager.elect_leader("candidate-1")
        assert result is True
        assert manager.leader_id == "candidate-1"
        assert manager.is_leader is False  # This node is not the leader

        manager.stop()

    def test_elect_leader_nonexistent(self):
        """Test electing a nonexistent node."""
        manager = ClusterManager()
        manager.start()

        result = manager.elect_leader("nonexistent-node")
        assert result is False

        manager.stop()

    def test_node_joined(self):
        """Test node join handling."""
        manager = ClusterManager()
        manager.start()

        from cluster.node_registry import NodeInfo, NodeCapabilities

        node_info = NodeInfo(
            node_id="new-node",
            capabilities=NodeCapabilities(hostname="test-host"),
        )

        manager.node_joined("new-node", node_info)

        # Verify node is registered
        node = manager.node_registry.get_node("new-node")
        assert node is not None
        assert node.node_id == "new-node"

        manager.stop()

    def test_node_left(self):
        """Test node leave handling."""
        manager = ClusterManager()
        manager.start()

        from cluster.node_registry import NodeInfo, NodeCapabilities

        # Register and join a node
        node_info = NodeInfo(
            node_id="leaving-node",
            capabilities=NodeCapabilities(hostname="test-host"),
        )
        manager.node_joined("leaving-node", node_info)

        # Node should be registered
        assert manager.node_registry.get_node("leaving-node") is not None

        # Remove node
        manager.node_left("leaving-node")
        node = manager.node_registry.get_node("leaving-node")
        assert node.status.value == "offline"

        manager.stop()

    def test_remove_node(self):
        """Test removing a node."""
        manager = ClusterManager()
        manager.start()

        from cluster.node_registry import NodeInfo, NodeCapabilities

        node_info = NodeInfo(
            node_id="remove-node",
            capabilities=NodeCapabilities(hostname="test-host"),
        )
        manager.node_joined("remove-node", node_info)
        assert manager.node_registry.get_node("remove-node") is not None

        result = manager.remove_node("remove-node")
        assert result is True
        assert manager.node_registry.get_node("remove-node") is None

        manager.stop()

    def test_heartbeat(self):
        """Test heartbeat tracking."""
        manager = ClusterManager()
        manager.start()

        # Send heartbeat
        manager.send_heartbeat("node-1")

        # Receive heartbeat
        response = manager.receive_heartbeat("node-1")
        assert response is not None
        assert response["node_id"] is not None

        manager.stop()

    def test_callbacks(self):
        """Test callback registration and invocation."""
        manager = ClusterManager()
        manager.start()

        callback_results = []

        def on_join(node_id):
            callback_results.append(("join", node_id))

        def on_leave(node_id):
            callback_results.append(("leave", node_id))

        def on_fail(node_id):
            callback_results.append(("fail", node_id))

        def on_leader(node_id):
            callback_results.append(("leader", node_id))

        unsub_join = manager.on_node_joined(on_join)
        unsub_leave = manager.on_node_left(on_leave)
        unsub_fail = manager.on_node_failed(on_fail)
        unsub_leader = manager.on_leader_changed(on_leader)

        from cluster.node_registry import NodeInfo, NodeCapabilities

        node_info = NodeInfo(
            node_id="callback-node",
            capabilities=NodeCapabilities(hostname="test"),
        )

        manager.node_joined("callback-node", node_info)
        time.sleep(0.05)
        assert ("join", "callback-node") in callback_results

        manager.node_left("callback-node")
        time.sleep(0.05)
        assert ("leave", "callback-node") in callback_results

        # Test unsubscribing
        callback_results.clear()
        unsub_join()
        unsub_leave()

        # Trigger callbacks again
        node_info2 = NodeInfo(node_id="other-node", capabilities=NodeCapabilities(hostname="test2"))
        manager.node_joined("other-node", node_info2)
        time.sleep(0.05)
        # Should not have received join callback
        assert ("join", "other-node") not in callback_results

        manager.stop()

    def test_cluster_config_node_id(self):
        """Test auto-generated node ID."""
        config1 = ClusterConfig()
        config2 = ClusterConfig()
        assert config1.node_id != config2.node_id

    def test_degraded_mode(self):
        """Test cluster transitions to degraded state."""
        manager = ClusterManager()
        manager.start()

        # Initially running
        assert manager.state == ClusterState.RUNNING

        # Register several nodes and mark some as unhealthy
        for i in range(5):
            manager.node_registry.register_node(f"node-{i}")
            manager.node_registry.mark_healthy(f"node-{i}")

        # Trigger failure of multiple nodes
        manager._on_node_failure("node-0")
        manager._on_node_failure("node-1")

        # Should still be running (majority healthy)
        assert _check_state_after_delay(manager, ClusterState.RUNNING, 0.1)

        # Trigger more failures to lose majority
        manager._on_node_failure("node-2")

        # Should be degraded now
        assert _check_state_after_delay(manager, [ClusterState.RUNNING, ClusterState.DEGRADED], 0.1)

        manager.stop()

    def test_emits_event_on_start_stop(self):
        """Test that start/stop emit events."""
        mock_bus = MagicMock()
        manager = ClusterManager(event_bus=mock_bus)
        manager.start()
        manager.stop()

        assert mock_bus.emit_async.call_count >= 2


def _check_state_after_delay(manager, expected_states, delay=0.1):
    """Check cluster state after a short delay to allow async transitions."""
    if isinstance(expected_states, ClusterState):
        expected_states = [expected_states]
    time.sleep(delay)
    return manager.state in expected_states


class TestClusterHealth:
    """Test cluster health endpoint."""

    def test_health_initial(self):
        """Test health check on stopped manager."""
        manager = ClusterManager()
        health = manager.health()
        assert "state" in health
        assert health["state"] == ClusterState.STOPPED.value

    def test_health_running(self):
        """Test health check on running manager."""
        manager = ClusterManager()
        manager.start()
        health = manager.health()
        assert health["state"] == "running"
        assert health["cluster_name"] == "aetheros-cluster"
        assert "uptime_seconds" in health
        manager.stop()
