"""
State Synchronizer — synchronizes minimal state across cluster nodes.

Synchronizes:
  - Task state and progress
  - Workflow state
  - Execution checkpoints
  - Progress updates

Only synchronizes the minimum necessary data to avoid network overhead.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class SyncOp(enum.Enum):
    """Types of state synchronization operations."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SNAPSHOT = "snapshot"
    MERGE = "merge"
    LOCK = "lock"
    UNLOCK = "unlock"


class ConflictStrategy(enum.Enum):
    """Strategies for resolving state conflicts."""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MERGE = "merge"
    LEADER_AUTHORITY = "leader_authority"
    MANUAL = "manual"


@dataclass
class StateSnapshot:
    """A snapshot of state to be synchronized.

    Attributes:
        id: Unique snapshot ID
        source_node: Node that produced this snapshot
        state_type: Type of state (task, workflow, checkpoint, progress)
        key: State key within the type
        data: State data payload
        version: State version for conflict detection
        timestamp: When the snapshot was created
        ttl_seconds: TTL after which the snapshot expires
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_node: str = ""
    state_type: str = ""  # task, workflow, checkpoint, progress
    key: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    timestamp: float = field(default_factory=time.time)
    ttl_seconds: float = 3600.0


class StateSynchronizer:
    """Synchronizes state between cluster nodes.

    Maintains a local state store and propagates changes to other nodes.
    Only synchronizes the minimum necessary data.

    Usage:
        sync = StateSynchronizer(event_bus)

        # Update local state and propagate
        sync.update_state("task", "task-123", {"status": "running"})

        # Take a checkpoint
        checkpoint = sync.create_checkpoint("workflow-1", {...})

        # Resolve conflicts
        sync.set_conflict_strategy(ConflictStrategy.LAST_WRITE_WINS)
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        node_id: str = "",
    ):
        self._event_bus = event_bus
        self._node_id = node_id
        self._lock = threading.RLock()

        # Local state store: state_type -> key -> (version, data, timestamp)
        self._store: Dict[str, Dict[str, tuple]] = {}
        # Conflict strategy
        self._conflict_strategy = ConflictStrategy.LAST_WRITE_WINS
        # Snapshots pending propagation
        self._pending_snapshots: List[StateSnapshot] = []
        # Remote sync handlers
        self._sync_handlers: List[Callable[[StateSnapshot], None]] = []
        # Checkpoints
        self._checkpoints: Dict[str, List[StateSnapshot]] = {}
        # Max snapshots to batch
        self._batch_size = 50

        # State change listeners
        self._state_listeners: Dict[str, List[Callable]] = {
            "task": [],
            "workflow": [],
            "checkpoint": [],
            "progress": [],
        }

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_conflict_strategy(self, strategy: ConflictStrategy) -> None:
        """Set the conflict resolution strategy."""
        self._conflict_strategy = strategy

    def set_batch_size(self, size: int) -> None:
        """Set the maximum number of snapshots to batch."""
        self._batch_size = max(1, size)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def update_state(
        self,
        state_type: str,
        key: str,
        data: Dict[str, Any],
        propagate: bool = True,
    ) -> StateSnapshot:
        """Update a state entry and optionally propagate.

        Args:
            state_type: Type of state (task, workflow, checkpoint, progress)
            key: State key
            data: State data
            propagate: Whether to propagate to other nodes

        Returns:
            The created StateSnapshot
        """
        now = time.time()

        with self._lock:
            store_type = self._store.setdefault(state_type, {})
            existing = store_type.get(key)

            if existing:
                version, _, _ = existing
                new_version = version + 1
            else:
                new_version = 1

            store_type[key] = (new_version, dict(data), now)

        snapshot = StateSnapshot(
            source_node=self._node_id,
            state_type=state_type,
            key=key,
            data=dict(data),
            version=new_version,
            timestamp=now,
        )

        if propagate:
            with self._lock:
                self._pending_snapshots.append(snapshot)
                if len(self._pending_snapshots) >= self._batch_size:
                    self._flush_pending()

        # Notify listeners
        self._notify_listeners(state_type, snapshot)

        return snapshot

    def get_state(self, state_type: str, key: str) -> Optional[Dict[str, Any]]:
        """Get state by type and key."""
        with self._lock:
            store_type = self._store.get(state_type)
            if not store_type:
                return None
            entry = store_type.get(key)
            if not entry:
                return None
            _, data, _ = entry
            return dict(data)

    def get_all_state(self, state_type: str) -> Dict[str, Dict[str, Any]]:
        """Get all state entries of a given type."""
        with self._lock:
            store_type = self._store.get(state_type, {})
            return {
                key: dict(data)
                for key, (_, data, _) in store_type.items()
            }

    def delete_state(self, state_type: str, key: str,
                     propagate: bool = True) -> bool:
        """Delete a state entry."""
        with self._lock:
            store_type = self._store.get(state_type)
            if not store_type or key not in store_type:
                return False
            del store_type[key]

        if propagate:
            snapshot = StateSnapshot(
                source_node=self._node_id,
                state_type=state_type,
                key=key,
                data={},
                version=0,
            )
            with self._lock:
                self._pending_snapshots.append(snapshot)

        return True

    # ------------------------------------------------------------------
    # Checkpoints
    # ------------------------------------------------------------------

    def create_checkpoint(self, workflow_id: str,
                          data: Dict[str, Any]) -> StateSnapshot:
        """Create an execution checkpoint.

        Args:
            workflow_id: Workflow to checkpoint
            data: Checkpoint data

        Returns:
            The created StateSnapshot
        """
        snapshot = self.update_state(
            state_type="checkpoint",
            key=f"{workflow_id}:{uuid.uuid4().hex[:8]}",
            data=data,
            propagate=True,
        )

        with self._lock:
            self._checkpoints.setdefault(workflow_id, []).append(snapshot)

        return snapshot

    def list_checkpoints(self, workflow_id: str) -> List[StateSnapshot]:
        """List checkpoints for a workflow."""
        with self._lock:
            return list(self._checkpoints.get(workflow_id, []))

    def restore_checkpoint(self, workflow_id: str,
                           checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Restore state from a checkpoint."""
        with self._lock:
            checkpoints = self._checkpoints.get(workflow_id, [])
            for cp in checkpoints:
                if cp.id == checkpoint_id:
                    return dict(cp.data)
        return None

    # ------------------------------------------------------------------
    # Conflict resolution
    # ------------------------------------------------------------------

    def resolve_conflict(
        self,
        local: StateSnapshot,
        remote: StateSnapshot,
    ) -> StateSnapshot:
        """Resolve a conflict between local and remote state snapshots.

        Uses the configured conflict strategy.
        """
        if self._conflict_strategy == ConflictStrategy.LAST_WRITE_WINS:
            winner = remote if remote.timestamp > local.timestamp else local
        elif self._conflict_strategy == ConflictStrategy.FIRST_WRITE_WINS:
            winner = local if local.timestamp < remote.timestamp else remote
        elif self._conflict_strategy == ConflictStrategy.LEADER_AUTHORITY:
            # Local is always authoritative
            winner = local
        elif self._conflict_strategy == ConflictStrategy.MERGE:
            # Simple merge: combine both data dicts
            merged_data = {**local.data, **remote.data}
            winner = StateSnapshot(
                source_node=self._node_id,
                state_type=local.state_type,
                key=local.key,
                data=merged_data,
                version=max(local.version, remote.version) + 1,
            )
        else:
            winner = local

        logger.debug(
            "StateSync: resolved conflict for %s/%s using %s",
            local.state_type, local.key, self._conflict_strategy.value,
        )
        return winner

    # ------------------------------------------------------------------
    # Propagation
    # ------------------------------------------------------------------

    def apply_remote_snapshot(self, snapshot: StateSnapshot) -> None:
        """Apply a snapshot received from a remote node.

        Handles conflict detection and resolution.
        """
        with self._lock:
            store_type = self._store.setdefault(snapshot.state_type, {})
            existing = store_type.get(snapshot.key)

            if existing:
                existing_version, existing_data, existing_time = existing
                # Check for conflict
                if snapshot.version <= existing_version:
                    # Stale update — resolve
                    local = StateSnapshot(
                        source_node=self._node_id,
                        state_type=snapshot.state_type,
                        key=snapshot.key,
                        data=dict(existing_data),
                        version=existing_version,
                        timestamp=existing_time,
                    )
                    resolved = self.resolve_conflict(local, snapshot)
                    store_type[snapshot.key] = (
                        resolved.version,
                        resolved.data,
                        resolved.timestamp,
                    )
                else:
                    store_type[snapshot.key] = (
                        snapshot.version,
                        snapshot.data,
                        snapshot.timestamp,
                    )
            else:
                store_type[snapshot.key] = (
                    snapshot.version,
                    snapshot.data,
                    snapshot.timestamp,
                )

        self._notify_listeners(snapshot.state_type, snapshot)

    def apply_remote_batch(self, snapshots: List[StateSnapshot]) -> int:
        """Apply multiple snapshots from a remote node.

        Returns the number of snapshots applied.
        """
        count = 0
        for snapshot in snapshots:
            try:
                self.apply_remote_snapshot(snapshot)
                count += 1
            except Exception as exc:
                logger.warning(
                    "StateSync: failed to apply %s/%s: %s",
                    snapshot.state_type, snapshot.key, exc,
                )
        return count

    def flush(self) -> List[StateSnapshot]:
        """Flush all pending snapshots for propagation.

        Dispatches pending snapshots to registered sync handlers and
        returns the list of pending snapshots.
        """
        with self._lock:
            snapshots = list(self._pending_snapshots)
            self._pending_snapshots.clear()

        for handler in self._sync_handlers:
            try:
                handler(snapshots)
            except Exception as exc:
                logger.warning("StateSync: handler failed during flush: %s", exc)

        return snapshots

    def _flush_pending(self) -> None:
        """Flush pending snapshots to sync handlers."""
        snapshots = list(self._pending_snapshots)
        self._pending_snapshots.clear()

        for handler in self._sync_handlers:
            try:
                handler(snapshots)
            except Exception as exc:
                logger.warning("StateSync: handler failed during flush: %s", exc)

    # ------------------------------------------------------------------
    # Sync handlers
    # ------------------------------------------------------------------

    def add_sync_handler(self, handler: Callable[[List[StateSnapshot]], None]) -> None:
        """Add a handler that will receive sync snapshots."""
        with self._lock:
            self._sync_handlers.append(handler)

    def remove_sync_handler(self, handler: Callable) -> bool:
        """Remove a sync handler."""
        with self._lock:
            if handler in self._sync_handlers:
                self._sync_handlers.remove(handler)
                return True
            return False

    # ------------------------------------------------------------------
    # State listeners
    # ------------------------------------------------------------------

    def on_state_change(self, state_type: str,
                        callback: Callable[[StateSnapshot], None]) -> Callable:
        """Register a callback for state changes of a given type.

        Returns an unsubscribe function.
        """
        with self._lock:
            self._state_listeners.setdefault(state_type, []).append(callback)
        return lambda: self._state_listeners[state_type].remove(callback) \
            if callback in self._state_listeners.get(state_type, []) else None

    def _notify_listeners(self, state_type: str, snapshot: StateSnapshot) -> None:
        """Notify registered state change listeners."""
        with self._lock:
            listeners = list(self._state_listeners.get(state_type, []))
        for cb in listeners:
            try:
                cb(snapshot)
            except Exception as exc:
                logger.debug("StateSync: listener failed: %s", exc)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return state synchronizer statistics."""
        with self._lock:
            state_counts = {
                st: len(entries)
                for st, entries in self._store.items()
            }
            return {
                "total_states": sum(state_counts.values()),
                "by_type": state_counts,
                "pending_snapshots": len(self._pending_snapshots),
                "checkpoints": sum(len(cp) for cp in self._checkpoints.values()),
                "conflict_strategy": self._conflict_strategy.value,
            }
