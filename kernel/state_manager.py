"""
State Manager — persists kernel state and enables crash recovery.

Persists:
  - Kernel state (component status, configuration)
  - Agent state (running executions, plans)
  - Running jobs
  - Execution history
  - Recovery checkpoints

Integrates with the existing SessionDB and checkpoint systems.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class StateSnapshot:
    """A snapshot of kernel state at a point in time.

    Attributes:
        id: Unique snapshot ID
        timestamp: When the snapshot was taken
        kind: Snapshot kind (auto, manual, recovery)
        data: The serialized state data
        metadata: Additional snapshot metadata
    """
    id: str
    timestamp: float
    kind: str = "auto"  # auto, manual, recovery
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateManager:
    """Persists and restores kernel state for crash recovery.

    Writes state to JSON files under AETHEROS_HOME/kernel/state/.
    Integrates with existing SessionDB and checkpoint systems.

    Usage:
        sm = StateManager(event_bus)

        # Save state
        sm.set("kernel.status", "running")
        sm.set("scheduler.jobs", [{"id": "job-1", ...}])

        # Persist to disk
        sm.persist()

        # Restore after restart
        sm.load()
        status = sm.get("kernel.status")  # "running"
    """

    def __init__(self, event_bus: Optional[EventBus] = None,
                 state_dir: str = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._state: Dict[str, Any] = {}
        self._dirty = False
        self._last_save_time = 0.0
        self._session_db = None  # Lazy-initialized by integrate_session_db()

        # Resolve state directory
        if state_dir:
            self._state_dir = Path(state_dir)
        else:
            try:
                from aetheros_constants import get_aetheros_home
                self._state_dir = get_aetheros_home() / "kernel" / "state"
            except Exception:
                self._state_dir = Path.home() / ".aetheros" / "kernel" / "state"

        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._state_dir / "kernel_state.json"
        self._snapshot_dir = self._state_dir / "snapshots"
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # State access
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from kernel state.

        Supports dot-notation for nested access:
            sm.get("scheduler.jobs") -> retrieves state["scheduler"]["jobs"]
        """
        with self._lock:
            return self._nested_get(self._state, key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in kernel state.

        Supports dot-notation for nested setting:
            sm.set("scheduler.last_tick", 1234567890.0)
        """
        with self._lock:
            self._nested_set(self._state, key, value)
            self._dirty = True

    def update(self, values: Dict[str, Any]) -> None:
        """Set multiple values at once."""
        with self._lock:
            for key, value in values.items():
                self._nested_set(self._state, key, value)
            self._dirty = True

    def delete(self, key: str) -> bool:
        """Delete a key from kernel state."""
        with self._lock:
            parts = key.split(".")
            target = self._state
            for part in parts[:-1]:
                if isinstance(target, dict):
                    target = target.get(part, {})
                else:
                    return False
            if isinstance(target, dict) and parts[-1] in target:
                del target[parts[-1]]
                self._dirty = True
                return True
            return False

    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of all kernel state."""
        with self._lock:
            return dict(self._state)

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def persist(self, force: bool = False) -> None:
        """Write kernel state to disk.

        Args:
            force: If True, write even if not dirty
        """
        with self._lock:
            if not self._dirty and not force:
                return
            try:
                with open(self._state_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "state": self._state,
                        "updated_at": time.time(),
                        "version": 1,
                    }, f, indent=2, default=str)
                self._dirty = False
                self._last_save_time = time.time()
                logger.debug("StateManager: persisted to %s", self._state_file)
            except Exception as exc:
                logger.error("StateManager: persist failed: %s", exc)

    def load(self) -> bool:
        """Load kernel state from disk.

        Returns True if state was loaded successfully.
        """
        try:
            if not self._state_file.exists():
                logger.debug("StateManager: no state file at %s", self._state_file)
                return False

            with open(self._state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            with self._lock:
                self._state = data.get("state", {})
                self._dirty = False

            logger.info(
                "StateManager: loaded state from %s (%d keys)",
                self._state_file, len(self._state),
            )
            return True
        except Exception as exc:
            logger.warning("StateManager: load failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Snapshots (for crash recovery)
    # ------------------------------------------------------------------

    def create_snapshot(self, kind: str = "auto",
                        metadata: Dict[str, Any] = None) -> StateSnapshot:
        """Create a point-in-time snapshot of kernel state.

        Snapshots are stored in snapshots/ subdirectory and can be
        used for crash recovery.

        Args:
            kind: Snapshot kind (auto, manual, recovery)
            metadata: Additional metadata

        Returns:
            StateSnapshot
        """
        import uuid as _uuid
        snapshot_id = _uuid.uuid4().hex[:12]
        now = time.time()

        with self._lock:
            data = dict(self._state)

        snapshot = StateSnapshot(
            id=snapshot_id,
            timestamp=now,
            kind=kind,
            data=data,
            metadata=metadata or {},
        )

        # Save to disk
        snapshot_file = self._snapshot_dir / f"{snapshot_id}.json"
        try:
            with open(snapshot_file, "w", encoding="utf-8") as f:
                json.dump({
                    "id": snapshot_id,
                    "timestamp": now,
                    "kind": kind,
                    "data": data,
                    "metadata": metadata or {},
                }, f, indent=2, default=str)
            logger.debug("StateManager: created snapshot %s", snapshot_id)
        except Exception as exc:
            logger.error("StateManager: snapshot creation failed: %s", exc)

        # Auto-clean old snapshots (keep last 50)
        self._prune_snapshots(keep=50)

        return snapshot

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List available recovery snapshots."""
        snapshots = []
        try:
            for f in sorted(self._snapshot_dir.glob("*.json"),
                          key=os.path.getmtime, reverse=True):
                try:
                    with open(f, "r", encoding="utf-8") as sf:
                        data = json.load(sf)
                    snapshots.append({
                        "id": data.get("id"),
                        "timestamp": data.get("timestamp"),
                        "kind": data.get("kind"),
                        "metadata": data.get("metadata"),
                    })
                except Exception:
                    continue
        except Exception:
            pass
        return snapshots

    def recover_from_snapshot(self, snapshot_id: str) -> bool:
        """Restore kernel state from a specific snapshot.

        Returns True if recovery succeeded.
        """
        snapshot_file = self._snapshot_dir / f"{snapshot_id}.json"
        if not snapshot_file.exists():
            logger.warning("StateManager: snapshot %s not found", snapshot_id)
            return False

        try:
            with open(snapshot_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            with self._lock:
                self._state = data.get("data", {})
                self._dirty = True

            # Persist the restored state
            self.persist(force=True)

            logger.info(
                "StateManager: recovered from snapshot %s (%d keys)",
                snapshot_id, len(self._state),
            )
            return True
        except Exception as exc:
            logger.error("StateManager: recovery from snapshot %s failed: %s",
                        snapshot_id, exc)
            return False

    def recover_latest(self) -> bool:
        """Recover by loading the last persisted state.

        Returns True if recovery succeeded.
        """
        return self.load()

    # ------------------------------------------------------------------
    # Integration with existing systems
    # ------------------------------------------------------------------

    def integrate_session_db(self) -> bool:
        """Connect to the existing SessionDB for session state querying.

        Returns True if the SessionDB is available.
        """
        try:
            from aetheros_state import SessionDB
            self._session_db = SessionDB()
            logger.info("StateManager: connected to SessionDB")
            return True
        except Exception as exc:
            logger.warning("StateManager: SessionDB integration failed: %s", exc)
            self._session_db = None
            return False

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Query the existing SessionDB for active sessions."""
        if not hasattr(self, "_session_db") or self._session_db is None:
            return []
        try:
            return self._session_db.list_sessions(limit=50) or []
        except Exception as exc:
            logger.debug("StateManager: get_active_sessions failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _prune_snapshots(self, keep: int = 50) -> None:
        """Remove old snapshots beyond the keep limit."""
        snapshots = sorted(
            self._snapshot_dir.glob("*.json"),
            key=os.path.getmtime,
            reverse=True,
        )
        for old in snapshots[keep:]:
            try:
                old.unlink()
                logger.debug("StateManager: pruned old snapshot %s", old.name)
            except Exception:
                pass

    def shutdown(self) -> None:
        """Persist state and clean up on shutdown."""
        self.persist(force=True)
        logger.info("StateManager: shut down")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _nested_get(data: dict, key: str, default: Any = None) -> Any:
        """Dot-notation key lookup."""
        parts = key.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return default
            else:
                return default
        return current

    @staticmethod
    def _nested_set(data: dict, key: str, value: Any) -> None:
        """Dot-notation key setting (creates intermediate dicts)."""
        parts = key.split(".")
        current = data
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
