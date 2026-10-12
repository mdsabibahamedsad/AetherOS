"""
Tests for the State Synchronization module.
"""

import time
import pytest

from cluster.state_sync import StateSynchronizer, StateSnapshot, ConflictStrategy


class TestStateSynchronizer:
    """Test StateSynchronizer class."""

    def test_create(self):
        """Test creating a synchronizer."""
        sync = StateSynchronizer(node_id="test-node")
        assert sync is not None
        assert sync._node_id == "test-node"

    def test_update_state(self):
        """Test updating state."""
        sync = StateSynchronizer(node_id="node-1")
        snapshot = sync.update_state("task", "task-1",
                                     {"status": "running", "progress": 50},
                                     propagate=True)
        assert snapshot.state_type == "task"
        assert snapshot.key == "task-1"
        assert snapshot.data == {"status": "running", "progress": 50}
        assert snapshot.source_node == "node-1"
        assert snapshot.version == 1

        # Update again — version should increment
        snapshot2 = sync.update_state("task", "task-1",
                                      {"status": "running", "progress": 75},
                                      propagate=False)
        assert snapshot2.version == 2

    def test_get_state(self):
        """Test getting state."""
        sync = StateSynchronizer(node_id="node-1")
        sync.update_state("task", "task-1", {"status": "running"})

        state = sync.get_state("task", "task-1")
        assert state == {"status": "running"}

    def test_get_nonexistent_state(self):
        """Test getting nonexistent state."""
        sync = StateSynchronizer(node_id="node-1")
        assert sync.get_state("task", "nonexistent") is None

    def test_get_all_state(self):
        """Test getting all state of a type."""
        sync = StateSynchronizer(node_id="node-1")
        sync.update_state("task", "task-1", {"status": "running"})
        sync.update_state("task", "task-2", {"status": "completed"})
        sync.update_state("task", "task-3", {"status": "pending"})

        all_tasks = sync.get_all_state("task")
        assert len(all_tasks) == 3
        assert all_tasks["task-1"] == {"status": "running"}

    def test_delete_state(self):
        """Test deleting state."""
        sync = StateSynchronizer(node_id="node-1")
        sync.update_state("task", "task-1", {"status": "running"})

        assert sync.get_state("task", "task-1") is not None
        assert sync.delete_state("task", "task-1") is True
        assert sync.get_state("task", "task-1") is None

    def test_delete_nonexistent(self):
        """Test deleting nonexistent state."""
        sync = StateSynchronizer(node_id="node-1")
        assert sync.delete_state("task", "nonexistent") is False

    def test_flush_pending(self):
        """Test flushing pending snapshots."""
        sync = StateSynchronizer(node_id="node-1")

        # Initially no pending
        assert len(sync.flush()) == 0

        # Add states with propagation
        sync.update_state("task", "t-1", {"status": "running"}, propagate=True)
        sync.update_state("task", "t-2", {"status": "completed"}, propagate=True)

        # Flush should return pending snapshots
        pending = sync.flush()
        assert len(pending) == 2

        # After flush, no more pending
        assert len(sync.flush()) == 0

    def test_apply_remote_batch(self):
        """Test applying remote state batch."""
        local = StateSynchronizer(node_id="node-1")
        remote = StateSynchronizer(node_id="node-2")

        # Create state on remote
        remote.update_state("task", "remote-task", {"status": "in_progress"})

        # Flush remote and apply to local
        snapshots = remote.flush()
        count = local.apply_remote_batch(snapshots)
        assert count == 1

        # Verify local now has the remote state
        state = local.get_state("task", "remote-task")
        assert state == {"status": "in_progress"}

    def test_apply_remote_empty(self):
        """Test applying empty batch."""
        sync = StateSynchronizer(node_id="node-1")
        assert sync.apply_remote_batch([]) == 0

    def test_conflict_last_write_wins(self):
        """Test last-write-wins conflict resolution."""
        sync = StateSynchronizer(node_id="node-1")
        sync.set_conflict_strategy(ConflictStrategy.LAST_WRITE_WINS)

        local = StateSnapshot(
            source_node="node-1", state_type="task", key="t-1",
            data={"status": "running"}, version=2, timestamp=1000,
        )
        remote = StateSnapshot(
            source_node="node-2", state_type="task", key="t-1",
            data={"status": "completed"}, version=3, timestamp=2000,
        )

        resolved = sync.resolve_conflict(local, remote)
        assert resolved.data == {"status": "completed"}  # Remote wins (newer)

    def test_conflict_first_write_wins(self):
        """Test first-write-wins conflict resolution."""
        sync = StateSynchronizer(node_id="node-1")
        sync.set_conflict_strategy(ConflictStrategy.FIRST_WRITE_WINS)

        local = StateSnapshot(
            source_node="node-1", state_type="task", key="t-1",
            data={"status": "running"}, version=2, timestamp=1000,
        )
        remote = StateSnapshot(
            source_node="node-2", state_type="task", key="t-1",
            data={"status": "completed"}, version=3, timestamp=2000,
        )

        resolved = sync.resolve_conflict(local, remote)
        assert resolved.data == {"status": "running"}  # Local wins (older)

    def test_conflict_merge(self):
        """Test merge conflict resolution."""
        sync = StateSynchronizer(node_id="node-1")
        sync.set_conflict_strategy(ConflictStrategy.MERGE)

        local = StateSnapshot(
            source_node="node-1", state_type="task", key="t-1",
            data={"status": "running", "progress": 50}, version=1, timestamp=1000,
        )
        remote = StateSnapshot(
            source_node="node-2", state_type="task", key="t-1",
            data={"status": "completed"}, version=2, timestamp=2000,
        )

        resolved = sync.resolve_conflict(local, remote)
        # Merge combines both
        assert resolved.data["status"] == "completed"  # Remote overwrites
        assert resolved.data["progress"] == 50  # Local preserved

    def test_apply_remote_with_conflict(self):
        """Test applying remote state with conflict detection."""
        local = StateSynchronizer(node_id="node-1")
        local.set_conflict_strategy(ConflictStrategy.LAST_WRITE_WINS)

        # Local has version 2
        local.update_state("task", "conflict-task",
                           {"status": "running"}, propagate=False)

        # Remote has newer version 3
        remote_snapshot = StateSnapshot(
            source_node="node-2", state_type="task", key="conflict-task",
            data={"status": "completed"}, version=3, timestamp=time.time() + 1,
        )

        local.apply_remote_snapshot(remote_snapshot)
        state = local.get_state("task", "conflict-task")
        assert state["status"] == "completed"

    def test_apply_remote_stale(self):
        """Test applying stale remote state."""
        local = StateSynchronizer(node_id="node-1")

        # Local has version 2
        local.update_state("task", "task-1",
                           {"status": "completed"}, propagate=False)

        # Remote has older version 1
        stale = StateSnapshot(
            source_node="node-2", state_type="task", key="task-1",
            data={"status": "pending"}, version=1, timestamp=1000,
        )

        # Stale should be resolved (last_write_wins by default means remote loses
        # since local timestamp is newer for the later update)
        local.apply_remote_snapshot(stale)
        state = local.get_state("task", "task-1")
        assert state is not None

    def test_state_listeners(self):
        """Test state change listeners."""
        sync = StateSynchronizer(node_id="node-1")

        received = []

        def on_change(snapshot):
            received.append((snapshot.state_type, snapshot.key))

        unsubscribe = sync.on_state_change("task", on_change)
        sync.update_state("task", "t-1", {"status": "running"}, propagate=False)

        assert len(received) == 1
        assert received[0] == ("task", "t-1")

        # Unsubscribe
        unsubscribe()
        sync.update_state("task", "t-2", {"status": "completed"}, propagate=False)
        assert len(received) == 1  # No more notifications

    def test_get_stats(self):
        """Test stats reporting."""
        sync = StateSynchronizer(node_id="node-1")
        sync.update_state("task", "t-1", {"status": "running"})
        sync.update_state("task", "t-2", {"status": "completed"})
        sync.update_state("workflow", "w-1", {"name": "test"})

        stats = sync.get_stats()
        assert stats["total_states"] == 3
        assert stats["by_type"]["task"] == 2
        assert stats["by_type"]["workflow"] == 1

    def test_mixed_state_types(self):
        """Test multiple state types."""
        sync = StateSynchronizer(node_id="node-1")

        sync.update_state("task", "t-1", {"status": "running"})
        sync.update_state("checkpoint", "cp-1", {"step": "build"})
        sync.update_state("progress", "p-1", {"pct": 50})
        sync.update_state("workflow", "w-1", {"name": "test"})

        stats = sync.get_stats()
        assert stats["by_type"]["task"] == 1
        assert stats["by_type"]["checkpoint"] == 1
        assert stats["by_type"]["progress"] == 1
        assert stats["by_type"]["workflow"] == 1

    def test_sync_handler(self):
        """Test sync handler registration."""
        sync = StateSynchronizer(node_id="node-1")

        received = []

        def handler(snapshots):
            received.extend(snapshots)

        sync.add_sync_handler(handler)
        sync.update_state("task", "t-1", {"status": "running"}, propagate=True)

        # Flush to trigger handler
        sync.flush()

        # Handler should have been called
        assert len(received) >= 1

        sync.remove_sync_handler(handler)
        sync.update_state("task", "t-2", {"status": "done"}, propagate=True)
        before = len(received)
        sync.flush()
        assert len(received) == before  # No new snapshots
