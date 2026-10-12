"""
Integration tests for the cluster module.

Tests multi-node scenarios including:
  - Node lifecycle (join, health, leave)
  - Task scheduling and routing
  - State synchronization
  - Error handling and recovery
"""

import time
import pytest

from cluster.cluster_manager import (
    ClusterManager,
    ClusterConfig,
    ClusterRole,
)
from cluster.node_registry import NodeRegistry, NodeCapabilities
from cluster.load_balancer import LoadBalancer
from cluster.scheduler import DistributedScheduler, ExecutionTarget
from cluster.state_sync import StateSynchronizer
from cluster.topology import ClusterTopology, TopologyNode
from cluster.artifact_sync import ArtifactSynchronizer


class TestSingleNodeWorkflow:
    """Test basic single-node cluster workflow."""

    def test_full_lifecycle(self):
        """Test complete single-node lifecycle."""
        config = ClusterConfig(
            cluster_name="single-test",
            role=ClusterRole.LEADER,
        )
        manager = ClusterManager(config=config)
        manager.start()
        assert manager.state.value == "running"
        assert manager.node_count >= 1
        manager.stop()
        assert manager.state.value == "stopped"

    def test_cluster_health_status(self):
        """Test cluster health reporting."""
        config = ClusterConfig(cluster_name="health-test")
        manager = ClusterManager(config=config)
        manager.start()
        health = manager.health()
        assert health["cluster_name"] == "health-test"
        assert health["state"] == "running"
        assert "uptime_seconds" in health
        manager.stop()

    def test_multiple_component_integration(self):
        """Test integration of multiple cluster components."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        topology = ClusterTopology()
        scheduler = DistributedScheduler(registry, balancer, topology=topology)

        # Register nodes
        for i in range(3):
            caps = NodeCapabilities(
                hostname=f"worker-{i}",
                cpu_count=4 + i * 4,
                memory_mb=8192 * (i + 1),
                supported_tools=["terminal"],
            )
            registry.register_node(f"worker-{i}", capabilities=caps)
            registry.mark_healthy(f"worker-{i}")

        # Schedule a task
        decision = scheduler.schedule_task("integ-test")
        assert decision is not None
        assert decision.target in (ExecutionTarget.REMOTE, ExecutionTarget.LOCAL)

        # Check stats
        stats = scheduler.get_stats()
        assert stats["total_scheduled"] >= 1


class TestMultiNodeRouting:
    """Test task routing across multiple nodes."""

    def test_capability_routing(self):
        """Test routing tasks based on capabilities."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        # Node with GPU
        gpu_caps = NodeCapabilities(hostname="gpu-server", gpu_count=4,
                                     supported_tools=["terminal", "ml"])
        registry.register_node("gpu-server", capabilities=gpu_caps)
        registry.mark_healthy("gpu-server")

        # Regular node
        reg_caps = NodeCapabilities(hostname="regular", cpu_count=4,
                                     supported_tools=["terminal"])
        registry.register_node("regular", capabilities=reg_caps)
        registry.mark_healthy("regular")

        # Task requiring GPU
        decision = scheduler.schedule_task("ml-task", require_gpu=True)
        assert decision.target == ExecutionTarget.REMOTE
        assert decision.target_node_id == "gpu-server"

        # Task without GPU requirement can go to either node
        decision = scheduler.schedule_task("normal-task")
        assert decision.target in (ExecutionTarget.REMOTE, ExecutionTarget.LOCAL)

    def test_tool_based_routing(self):
        """Test routing based on tool requirements."""
        registry = NodeRegistry()
        balancer = LoadBalancer()
        scheduler = DistributedScheduler(registry, balancer)

        node_a = NodeCapabilities(hostname="node-a", supported_tools=["terminal", "browser"])
        node_b = NodeCapabilities(hostname="node-b", supported_tools=["terminal"])

        registry.register_node("node-a", capabilities=node_a)
        registry.register_node("node-b", capabilities=node_b)
        registry.mark_healthy("node-a")
        registry.mark_healthy("node-b")

        # Task requiring browser should go to node-a
        decision = scheduler.schedule_task("browser-task", required_tools=["browser"])
        assert decision.target_node_id == "node-a"


class TestStateSync:
    """Test state synchronization."""

    def test_state_update_and_retrieve(self):
        """Test updating and retrieving state."""
        sync = StateSynchronizer(node_id="node-1")

        # Update state
        snapshot = sync.update_state("task", "task-1", {"status": "running"})
        assert snapshot.state_type == "task"
        assert snapshot.key == "task-1"

        # Retrieve state
        state = sync.get_state("task", "task-1")
        assert state == {"status": "running"}

    def test_remote_state_apply(self):
        """Test applying remote state."""
        local = StateSynchronizer(node_id="node-1")
        remote = StateSynchronizer(node_id="node-2")

        # Create state on remote
        remote.update_state("task", "task-1", {"status": "completed"})

        # Flush remote and apply to local
        snapshots = remote.flush()
        local.apply_remote_batch(snapshots)

        state = local.get_state("task", "task-1")
        assert state == {"status": "completed"}

    def test_conflict_resolution(self):
        """Test state conflict resolution."""
        from cluster.state_sync import ConflictStrategy, StateSnapshot
        import time

        sync = StateSynchronizer(node_id="node-1")

        # Local state
        local_snap = StateSnapshot(
            source_node="node-1",
            state_type="task",
            key="conflict-task",
            data={"status": "running", "progress": 50},
            version=2,
            timestamp=time.time(),
        )

        # Remote state (newer timestamp)
        remote_snap = StateSnapshot(
            source_node="node-2",
            state_type="task",
            key="conflict-task",
            data={"status": "completed", "progress": 100},
            version=3,
            timestamp=time.time() + 1,
        )

        # Last write wins
        sync.set_conflict_strategy(ConflictStrategy.LAST_WRITE_WINS)
        resolved = sync.resolve_conflict(local_snap, remote_snap)
        assert resolved.data == remote_snap.data

        # First write wins
        sync.set_conflict_strategy(ConflictStrategy.FIRST_WRITE_WINS)
        resolved = sync.resolve_conflict(local_snap, remote_snap)
        assert resolved.data == local_snap.data

    def test_checkpoint_create_and_restore(self):
        """Test checkpoint creation and restoration."""
        sync = StateSynchronizer(node_id="node-1")

        # Create checkpoint
        cp = sync.create_checkpoint("workflow-1", {"step": "planning", "data": {}})
        assert cp is not None

        # List checkpoints
        checkpoints = sync.list_checkpoints("workflow-1")
        assert len(checkpoints) == 1

        # Restore checkpoint
        data = sync.restore_checkpoint("workflow-1", cp.id)
        assert data == {"step": "planning", "data": {}}


class TestArtifactSync:
    """Test artifact synchronization."""

    def test_sync_skip_empty(self):
        """Test that empty/None paths are handled."""
        sync = ArtifactSynchronizer()
        # Non-existent file
        result = sync.sync_artifact("/nonexistent/file.txt", "remote-node", "/remote/file.txt")
        assert result is False

    def test_compute_artifact_nonexistent(self):
        """Test computing artifact for nonexistent file."""
        sync = ArtifactSynchronizer()
        artifact = sync.compute_artifact("/nonexistent/path.txt")
        assert artifact is None

    def test_stats(self):
        """Test artifact sync stats."""
        sync = ArtifactSynchronizer()
        stats = sync.get_stats()
        assert stats["total_syncs"] == 0
        assert stats["bytes_transferred"] == 0


class TestTopology:
    """Test cluster topology."""

    def test_single_node_topology(self):
        """Test single node topology."""
        topology = ClusterTopology()
        assert topology.get_topology_type().value == "standalone"
        assert topology.node_count() == 0

    def test_add_remove_nodes(self):
        """Test adding and removing nodes."""
        topology = ClusterTopology()
        topology.add_node(TopologyNode(node_id="node-1", hostname="10.0.0.1"))
        topology.add_node(TopologyNode(node_id="node-2", hostname="10.0.0.2"))
        assert topology.node_count() == 2

        topology.remove_node("node-1")
        assert topology.node_count() == 1

    def test_nearest_nodes(self):
        """Test getting nearest nodes by latency."""
        topology = ClusterTopology()
        topology.set_self("local")

        topology.add_node(TopologyNode(node_id="local", hostname="localhost"))
        topology.add_node(TopologyNode(node_id="far", hostname="10.0.0.100"))
        topology.add_node(TopologyNode(node_id="near", hostname="10.0.0.1"))

        # Set up links with latency
        from cluster.topology import TopologyLink
        topology.add_link(TopologyLink(source="local", target="near", latency_ms=1.0))
        topology.add_link(TopologyLink(source="local", target="far", latency_ms=50.0))

        nearest = topology.get_nearest_nodes("local", limit=2)
        # Nearest should be "near" (lower latency)
        assert len(nearest) >= 1
        if len(nearest) >= 2:
            assert nearest[0].node_id == "near"

    def test_mesh_detection(self):
        """Test mesh topology detection."""
        topology = ClusterTopology()
        from cluster.topology import TopologyLink

        nodes = ["A", "B", "C"]
        for n in nodes:
            topology.add_node(TopologyNode(node_id=n, hostname=n))

        # Add all links (complete mesh for 3 nodes = 3 links)
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                topology.add_link(TopologyLink(source=a, target=b, latency_ms=1.0))

        assert topology.get_topology_type().value == "mesh"
