"""
Core sync engine for AetherOS Cloud Sync with offline-first architecture.

Provides change detection, version vectors, conflict resolution, incremental
sync with delta updates, version history with restore points, background sync
with configurable intervals, retry queue with exponential backoff, and an
offline change queue that auto-syncs on reconnection.

Sync scopes (selective sync):
  settings, agents, agent_configs, workflows, automations, provider_configs,
  model_preferences, knowledge_metadata, memory, chat_history, plugins,
  mcp_configs, workspace_metadata, themes, shortcuts, notifications
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from aetheros_constants import get_aetheros_home

from .sync_crypto import SyncCrypto, encrypt_sync_payload, decrypt_sync_payload

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SYNC_STATE_VERSION = 1
_DEFAULT_SYNC_INTERVAL = 300
_MAX_RETRY_QUEUE_SIZE = 1000
_MAX_HISTORY_ENTRIES = 500
_RESTORE_POINT_PREFIX = "restore_"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SyncAction(Enum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"


class ConflictResolution(Enum):
    LATEST = "latest"
    MANUAL = "manual"
    KEEP_LOCAL = "keep_local"
    KEEP_REMOTE = "keep_remote"
    MERGE = "merge"


class ConnectionState(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class SyncStatus(Enum):
    IDLE = "idle"
    SYNCING = "syncing"
    PENDING = "pending"
    CONFLICT = "conflict"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Sync scopes
# ---------------------------------------------------------------------------

SYNC_SCOPES: Set[str] = {
    "settings",
    "agents",
    "agent_configs",
    "workflows",
    "automations",
    "provider_configs",
    "model_preferences",
    "knowledge_metadata",
    "memory",
    "chat_history",
    "plugins",
    "mcp_configs",
    "workspace_metadata",
    "themes",
    "shortcuts",
    "notifications",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ChangeRecord:
    """Records a single change to a sync scope entry."""
    scope: str
    key: str
    action: SyncAction
    timestamp: float
    device_id: str
    data_hash: str
    version: int = 0
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scope": self.scope,
            "key": self.key,
            "action": self.action.value,
            "timestamp": self.timestamp,
            "device_id": self.device_id,
            "data_hash": self.data_hash,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChangeRecord:
        return cls(
            id=data.get("id", ""),
            scope=data["scope"],
            key=data["key"],
            action=SyncAction(data["action"]),
            timestamp=data["timestamp"],
            device_id=data["device_id"],
            data_hash=data["data_hash"],
            version=data.get("version", 0),
        )


@dataclass
class SyncConflict:
    """Represents a sync conflict between local and remote data."""
    scope: str
    key: str
    local_version: int
    remote_version: int
    local_data: Optional[Dict[str, Any]] = None
    remote_data: Optional[Dict[str, Any]] = None
    resolved: bool = False
    resolution: Optional[ConflictResolution] = None
    resolved_at: float = 0.0
    resolved_by: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scope": self.scope,
            "key": self.key,
            "local_version": self.local_version,
            "remote_version": self.remote_version,
            "local_data": self.local_data,
            "remote_data": self.remote_data,
            "resolved": self.resolved,
            "resolution": self.resolution.value if self.resolution else None,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SyncConflict:
        res = data.get("resolution")
        return cls(
            id=data.get("id", ""),
            scope=data["scope"],
            key=data["key"],
            local_version=data["local_version"],
            remote_version=data["remote_version"],
            local_data=data.get("local_data"),
            remote_data=data.get("remote_data"),
            resolved=data.get("resolved", False),
            resolution=ConflictResolution(res) if res else None,
            resolved_at=data.get("resolved_at", 0.0),
            resolved_by=data.get("resolved_by", ""),
        )


@dataclass
class SyncState:
    """Tracks the sync state for a single scope entry."""
    scope: str
    key: str
    version: int
    timestamp: float
    checksum: str
    device_id: str
    conflict: bool = False
    resolved: bool = True
    data_preview: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope,
            "key": self.key,
            "version": self.version,
            "timestamp": self.timestamp,
            "checksum": self.checksum,
            "device_id": self.device_id,
            "conflict": self.conflict,
            "resolved": self.resolved,
            "data_preview": self.data_preview[:128],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SyncState:
        return cls(
            scope=data["scope"],
            key=data["key"],
            version=data["version"],
            timestamp=data["timestamp"],
            checksum=data["checksum"],
            device_id=data["device_id"],
            conflict=data.get("conflict", False),
            resolved=data.get("resolved", True),
            data_preview=data.get("data_preview", ""),
        )


@dataclass
class VersionSnapshot:
    """A point-in-time snapshot for version history and restore."""
    scope: str
    key: str
    version: int
    data: Dict[str, Any]
    timestamp: float
    device_id: str
    label: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scope": self.scope,
            "key": self.key,
            "version": self.version,
            "data": self.data,
            "timestamp": self.timestamp,
            "device_id": self.device_id,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VersionSnapshot:
        return cls(
            id=data.get("id", ""),
            scope=data["scope"],
            key=data["key"],
            version=data["version"],
            data=data["data"],
            timestamp=data["timestamp"],
            device_id=data["device_id"],
            label=data.get("label", ""),
        )


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _sync_dir() -> Path:
    return get_aetheros_home() / "sync"


def _state_path() -> Path:
    return _sync_dir() / "sync_state.json"


def _change_log_path() -> Path:
    return _sync_dir() / "change_log.json"


def _conflict_path() -> Path:
    return _sync_dir() / "conflicts.json"


def _history_path() -> Path:
    return _sync_dir() / "version_history.json"


def _queue_path() -> Path:
    return _sync_dir() / "offline_queue.json"


def _lock_path() -> Path:
    return _sync_dir() / "sync.lock"


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load %s: %s", path.name, exc)
    return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        logger.error("Failed to save %s: %s", path.name, exc)
        raise


def _checksum(data: Dict[str, Any]) -> str:
    raw = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# SyncEngine
# ---------------------------------------------------------------------------


class SyncEngine:
    """Core sync engine with offline-first architecture.

    Features:
      - Sync state tracking with version vectors
      - Incremental sync with delta updates
      - Change detection and change log
      - Conflict detection and resolution
      - Version history with restore points
      - Background sync with configurable interval
      - Retry queue with exponential backoff
      - Connection state tracking
      - Offline change queue
      - Auto-sync on reconnection
    """

    def __init__(
        self,
        device_id: str,
        crypto: Optional[SyncCrypto] = None,
        default_resolution: ConflictResolution = ConflictResolution.LATEST,
        sync_interval: int = _DEFAULT_SYNC_INTERVAL,
    ) -> None:
        self._device_id = device_id
        self._crypto = crypto or SyncCrypto()
        self._default_resolution = default_resolution

        self._sync_interval = sync_interval
        self._connection_state = ConnectionState.OFFLINE
        self._sync_status = SyncStatus.IDLE

        self._enabled_scopes: Set[str] = set(SYNC_SCOPES)
        self._provider: Optional[Any] = None

        self._state: Dict[str, Dict[str, SyncState]] = {}
        self._change_log: List[ChangeRecord] = []
        self._conflicts: Dict[str, SyncConflict] = {}
        self._offline_queue: List[ChangeRecord] = []
        self._version_history: Dict[str, List[VersionSnapshot]] = {}

        self._lock = threading.Lock()
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._sync_callbacks: List[Callable[..., None]] = []
        self._conflict_callbacks: List[Callable[["SyncConflict"], None]] = []

        self._sync_dir = _sync_dir()
        self._sync_dir.mkdir(parents=True, exist_ok=True)

        self._load_persisted_state()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def connection_state(self) -> ConnectionState:
        return self._connection_state

    @property
    def sync_status(self) -> SyncStatus:
        return self._sync_status

    @property
    def enabled_scopes(self) -> Set[str]:
        return set(self._enabled_scopes)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_persisted_state(self) -> None:
        raw_state = _load_json(_state_path(), {})
        for scope_key, entries in raw_state.items():
            if isinstance(entries, dict):
                self._state[scope_key] = {
                    k: SyncState.from_dict(v)
                    for k, v in entries.items()
                }

        raw_log = _load_json(_change_log_path(), [])
        self._change_log = [ChangeRecord.from_dict(r) for r in raw_log]

        raw_conflicts = _load_json(_conflict_path(), {})
        self._conflicts = {
            k: SyncConflict.from_dict(v)
            for k, v in raw_conflicts.items()
        }

        raw_queue = _load_json(_queue_path(), [])
        self._offline_queue = [ChangeRecord.from_dict(r) for r in raw_queue]

        raw_history = _load_json(_history_path(), {})
        self._version_history = {
            k: [VersionSnapshot.from_dict(s) for s in v]
            for k, v in raw_history.items()
        }

        logger.debug(
            "Loaded sync state: %d scopes, %d log entries, %d conflicts, %d queued",
            len(self._state), len(self._change_log),
            len(self._conflicts), len(self._offline_queue),
        )

    def _save_state(self) -> None:
        with self._lock:
            raw_state = {
                scope_key: {
                    k: v.to_dict() for k, v in entries.items()
                }
                for scope_key, entries in self._state.items()
            }
            _save_json(_state_path(), raw_state)

            raw_log = [r.to_dict() for r in self._change_log[-_MAX_HISTORY_ENTRIES:]]
            _save_json(_change_log_path(), raw_log)

            _save_json(_conflict_path(), {
                k: v.to_dict() for k, v in self._conflicts.items()
            })

            raw_queue = [r.to_dict() for r in self._offline_queue]
            _save_json(_queue_path(), raw_queue)

            raw_history = {
                k: [s.to_dict() for s in snapshots[-10:]]
                for k, snapshots in self._version_history.items()
            }
            _save_json(_history_path(), raw_history)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_sync(self, callback: Callable[..., None]) -> None:
        """Register a callback invoked after each sync cycle completes."""
        self._sync_callbacks.append(callback)

    def on_conflict(self, callback: Callable[["SyncConflict"], None]) -> None:
        """Register a callback invoked when a conflict is detected."""
        self._conflict_callbacks.append(callback)

    def _notify_sync_callbacks(self, **kwargs: Any) -> None:
        for cb in self._sync_callbacks:
            try:
                cb(**kwargs)
            except Exception as exc:
                logger.warning("Sync callback error: %s", exc)

    def _notify_conflict_callbacks(self, conflict: SyncConflict) -> None:
        for cb in self._conflict_callbacks:
            try:
                cb(conflict)
            except Exception as exc:
                logger.warning("Conflict callback error: %s", exc)

    # ------------------------------------------------------------------
    # Sync scope management
    # ------------------------------------------------------------------

    def set_sync_scope(self, scope: str, enabled: bool) -> None:
        """Enable or disable syncing for a specific scope.

        Args:
            scope: The scope name (e.g. ``"settings"``, ``"agents"``).
            enabled: True to enable syncing, False to disable.

        Raises:
            ValueError: If *scope* is not a known sync scope.
        """
        if scope not in SYNC_SCOPES:
            raise ValueError(
                f"Unknown sync scope: '{scope}'. "
                f"Valid scopes: {', '.join(sorted(SYNC_SCOPES))}"
            )
        with self._lock:
            if enabled:
                self._enabled_scopes.add(scope)
            else:
                self._enabled_scopes.discard(scope)
        logger.info("Sync scope '%s' %s", scope, "enabled" if enabled else "disabled")

    def set_sync_scopes(self, scopes: Dict[str, bool]) -> None:
        """Enable or disable multiple sync scopes at once."""
        for scope, enabled in scopes.items():
            self.set_sync_scope(scope, enabled)

    def is_scope_enabled(self, scope: str) -> bool:
        """Check whether a sync scope is currently enabled."""
        return scope in self._enabled_scopes

    # ------------------------------------------------------------------
    # Provider binding
    # ------------------------------------------------------------------

    def set_provider(self, provider: Any) -> None:
        """Set the cloud provider for this sync engine."""
        self._provider = provider

    def set_connection_state(self, state: ConnectionState) -> None:
        """Update the connection state.

        When transitioning from OFFLINE to ONLINE, triggers auto-sync
        of the offline change queue.
        """
        was_offline = self._connection_state == ConnectionState.OFFLINE
        self._connection_state = state
        if was_offline and state == ConnectionState.ONLINE:
            logger.info("Connection restored — processing offline queue")
            self.process_queue()

    # ------------------------------------------------------------------
    # Change tracking
    # ------------------------------------------------------------------

    def queue_change(
        self,
        scope: str,
        key: str,
        action: SyncAction,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a change and optionally queue it for sync.

        If the engine is online, the change is recorded in the change log
        and applied immediately. If offline, it is queued for later sync.

        Args:
            scope: The sync scope the change belongs to.
            key: The unique key within the scope.
            action: The type of change (add, update, delete).
            data: Optional data for checksum computation.
        """
        data_hash = _checksum(data or {})
        record = ChangeRecord(
            scope=scope,
            key=key,
            action=action,
            timestamp=time.time(),
            device_id=self._device_id,
            data_hash=data_hash,
        )

        with self._lock:
            self._change_log.append(record)

            if data is not None:
                self._update_sync_state(scope, key, record, data_hash)

            if self._connection_state != ConnectionState.ONLINE:
                if len(self._offline_queue) < _MAX_RETRY_QUEUE_SIZE:
                    self._offline_queue.append(record)
                    logger.debug("Queued offline change: %s/%s [%s]", scope, key, action.value)
                else:
                    logger.warning("Offline queue full — dropping change: %s/%s", scope, key)
            elif self._provider:
                self._sync_change(record)

        if self._connection_state == ConnectionState.ONLINE:
            self._save_state()

    def _update_sync_state(
        self,
        scope: str,
        key: str,
        record: ChangeRecord,
        data_hash: str,
    ) -> None:
        scope_state = self._state.setdefault(scope, {})
        existing = scope_state.get(key)
        if existing is None:
            scope_state[key] = SyncState(
                scope=scope,
                key=key,
                version=1,
                timestamp=record.timestamp,
                checksum=data_hash,
                device_id=self._device_id,
            )
        else:
            existing.version += 1
            existing.timestamp = record.timestamp
            existing.checksum = data_hash
            existing.device_id = self._device_id
            existing.conflict = False

    # ------------------------------------------------------------------
    # Change log
    # ------------------------------------------------------------------

    def get_change_log(
        self,
        scope: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> List[ChangeRecord]:
        """Return the change log, optionally filtered.

        Args:
            scope: If set, only return changes for this scope.
            since: Only return changes after this timestamp.
            limit: Maximum number of entries to return (most recent first).

        Returns:
            A list of :class:`ChangeRecord` objects.
        """
        with self._lock:
            results = list(self._change_log)
        if scope:
            results = [r for r in results if r.scope == scope]
        if since:
            results = [r for r in results if r.timestamp >= since]
        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # Conflict detection and resolution
    # ------------------------------------------------------------------

    def detect_conflict(
        self,
        scope: str,
        key: str,
        local_version: int,
        remote_version: int,
        local_data: Optional[Dict[str, Any]] = None,
        remote_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[SyncConflict]:
        """Detect and register a sync conflict.

        Returns the :class:`SyncConflict` if one was created, or None if
        the versions are consistent.
        """
        with self._lock:
            scope_state = self._state.get(scope, {})
            entry = scope_state.get(key)

            if entry and entry.version == remote_version:
                return None

            conflict = SyncConflict(
                scope=scope,
                key=key,
                local_version=local_version,
                remote_version=remote_version,
                local_data=local_data,
                remote_data=remote_data,
            )
            conflict_id = f"{scope}:{key}"
            self._conflicts[conflict_id] = conflict

            if entry:
                entry.conflict = True
                entry.resolved = False

        self._save_state()
        self._notify_conflict_callbacks(conflict)
        return conflict

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: ConflictResolution,
        resolved_by: str = "",
    ) -> bool:
        """Resolve a previously detected conflict.

        Args:
            conflict_id: The conflict identifier (``"scope:key"``).
            resolution: The resolution strategy to apply.
            resolved_by: Who or what resolved the conflict.

        Returns:
            True if the conflict was resolved.
        """
        with self._lock:
            conflict = self._conflicts.get(conflict_id)
            if conflict is None:
                logger.warning("Unknown conflict: %s", conflict_id)
                return False

            conflict.resolved = True
            conflict.resolution = resolution
            conflict.resolved_at = time.time()
            conflict.resolved_by = resolved_by

            scope_state = self._state.get(conflict.scope, {})
            entry = scope_state.get(conflict.key)
            if entry:
                entry.conflict = False
                entry.resolved = True

        self._save_state()

        if resolution == ConflictResolution.KEEP_LOCAL and conflict.local_data:
            self.queue_change(
                conflict.scope, conflict.key,
                SyncAction.UPDATE, conflict.local_data,
            )
        elif resolution == ConflictResolution.KEEP_REMOTE and conflict.remote_data:
            self.queue_change(
                conflict.scope, conflict.key,
                SyncAction.UPDATE, conflict.remote_data,
            )

        logger.info("Conflict resolved: %s via %s", conflict_id, resolution.value)
        return True

    def get_conflicts(self, unresolved_only: bool = True) -> List[SyncConflict]:
        """Return all tracked sync conflicts.

        Args:
            unresolved_only: If True, only return unresolved conflicts.

        Returns:
            A list of :class:`SyncConflict` objects.
        """
        with self._lock:
            results = list(self._conflicts.values())
        if unresolved_only:
            results = [c for c in results if not c.resolved]
        return results

    # ------------------------------------------------------------------
    # Version history
    # ------------------------------------------------------------------

    def snapshot_version(
        self,
        scope: str,
        key: str,
        data: Dict[str, Any],
        label: str = "",
    ) -> VersionSnapshot:
        """Create a version snapshot for restore/history.

        Args:
            scope: The sync scope.
            key: The entry key.
            data: The data to snapshot.
            label: Optional human-readable label.

        Returns:
            The created :class:`VersionSnapshot`.
        """
        with self._lock:
            scope_state = self._state.get(scope, {})
            entry = scope_state.get(key)
            version = entry.version if entry else 0

            snapshot = VersionSnapshot(
                scope=scope,
                key=key,
                version=version,
                data=deepcopy(data),
                timestamp=time.time(),
                device_id=self._device_id,
                label=label or f"v{version}",
            )

            history_key = f"{scope}:{key}"
            history = self._version_history.setdefault(history_key, [])
            history.append(snapshot)
            if len(history) > 20:
                self._version_history[history_key] = history[-20:]

        self._save_state()
        logger.debug("Version snapshot: %s v%d", history_key, version)
        return snapshot

    def get_version_history(
        self,
        scope: str,
        key: str,
        limit: int = 10,
    ) -> List[VersionSnapshot]:
        """Return version history for a scope entry."""
        history_key = f"{scope}:{key}"
        with self._lock:
            snapshots = list(self._version_history.get(history_key, []))
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        return snapshots[:limit]

    def restore_version(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Restore data from a version snapshot.

        Args:
            snapshot_id: The ID of the :class:`VersionSnapshot` to restore.

        Returns:
            The snapshot's data dict, or None if not found.
        """
        with self._lock:
            for snapshots in self._version_history.values():
                for snap in snapshots:
                    if snap.id == snapshot_id:
                        data = deepcopy(snap.data)
                        break
                else:
                    continue
                break
            else:
                logger.warning("Snapshot not found: %s", snapshot_id)
                return None

        self.queue_change(snap.scope, snap.key, SyncAction.UPDATE, data)
        return data

    # ------------------------------------------------------------------
    # Sync operations
    # ------------------------------------------------------------------

    def _sync_change(self, record: ChangeRecord) -> bool:
        """Attempt to sync a single change record to the provider.

        Returns True on success.
        """
        if not self._provider:
            logger.warning("No provider set — cannot sync")
            return False
        try:
            scope_state = self._state.get(record.scope, {})
            entry = scope_state.get(record.key)
            payload = {
                "scope": record.scope,
                "key": record.key,
                "action": record.action.value,
                "timestamp": record.timestamp,
                "device_id": record.device_id,
                "version": entry.version if entry else 0,
                "checksum": entry.checksum if entry else "",
            }
            data_bytes = json.dumps(payload, default=str).encode("utf-8")
            encrypted = encrypt_sync_payload(data_bytes, self._crypto.get_encryption_key())
            sync_payload = {"encrypted": encrypted.to_dict()}

            etag = self._provider.upload(
                f"sync/{record.scope}/{record.key}.json",
                json.dumps(sync_payload, default=str).encode("utf-8"),
            )
            if etag:
                logger.debug("Synced %s/%s [%s] -> %s", record.scope, record.key, record.action.value, etag)
                return True
        except Exception as exc:
            logger.warning("Sync failed for %s/%s: %s", record.scope, record.key, exc)
        return False

    def sync_now(self) -> Dict[str, Any]:
        """Run an immediate sync of all pending changes.

        Returns a summary dict with ``synced``, ``failed``, ``conflicts``,
        and ``skipped`` counts.
        """
        if self._connection_state != ConnectionState.ONLINE:
            logger.warning("Cannot sync — connection state: %s", self._connection_state.value)
            return {"synced": 0, "failed": 0, "conflicts": 0, "skipped": 0, "reason": "offline"}

        self._sync_status = SyncStatus.SYNCING
        synced = failed = conflicts = skipped = 0

        with self._lock:
            records = list(self._offline_queue)
            self._offline_queue.clear()

        for record in records:
            if not self.is_scope_enabled(record.scope):
                skipped += 1
                continue
            try:
                if self._sync_change(record):
                    synced += 1
                else:
                    failed += 1
            except Exception as exc:
                logger.error("Sync error for %s/%s: %s", record.scope, record.key, exc)
                failed += 1

        self._sync_status = SyncStatus.IDLE if failed == 0 else SyncStatus.ERROR
        self._save_state()
        self._notify_sync_callbacks(synced=synced, failed=failed, conflicts=conflicts)

        return {
            "synced": synced,
            "failed": failed,
            "conflicts": conflicts,
            "skipped": skipped,
        }

    def process_queue(self) -> int:
        """Process the offline change queue.

        Returns the number of records successfully synced.
        """
        if self._connection_state != ConnectionState.ONLINE:
            return 0
        result = self.sync_now()
        return result["synced"]

    # ------------------------------------------------------------------
    # Background sync
    # ------------------------------------------------------------------

    def start_sync(self) -> None:
        """Start the background sync loop in a daemon thread."""
        if self._sync_thread and self._sync_thread.is_alive():
            logger.debug("Background sync already running")
            return

        self._stop_event.clear()
        self._sync_thread = threading.Thread(
            target=self._background_sync_loop,
            daemon=True,
            name="sync-engine",
        )
        self._sync_thread.start()
        logger.info("Background sync started (interval: %ds)", self._sync_interval)

    def stop_sync(self) -> None:
        """Stop the background sync loop."""
        self._stop_event.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=10)
        logger.info("Background sync stopped")

    def _background_sync_loop(self) -> None:
        """Background loop that periodically syncs pending changes."""
        while not self._stop_event.is_set():
            if self._connection_state == ConnectionState.ONLINE:
                try:
                    self.sync_now()
                except Exception as exc:
                    logger.error("Background sync error: %s", exc)
            self._stop_event.wait(self._sync_interval)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status report of the sync engine."""
        with self._lock:
            total_states = sum(len(entries) for entries in self._state.values())
            unresolved = sum(
                1 for c in self._conflicts.values() if not c.resolved
            )
            return {
                "device_id": self._device_id,
                "connection_state": self._connection_state.value,
                "sync_status": self._sync_status.value,
                "enabled_scopes": len(self._enabled_scopes),
                "tracked_entries": total_states,
                "change_log_size": len(self._change_log),
                "unresolved_conflicts": unresolved,
                "offline_queue_size": len(self._offline_queue),
                "history_snapshots": sum(len(v) for v in self._version_history.values()),
                "sync_interval": self._sync_interval,
            }

    def get_history(self, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return sync history entries.

        Args:
            scope: Optional scope filter.

        Returns:
            List of history summary dicts.
        """
        with self._lock:
            results = [s.to_dict() for snapshots in self._version_history.values() for s in snapshots]
        if scope:
            results = [r for r in results if r["scope"] == scope]
        results.sort(key=lambda r: r["timestamp"], reverse=True)
        return results[:100]

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def get_sync_state(self, scope: str, key: str) -> Optional[SyncState]:
        """Return the sync state for a specific scope entry."""
        with self._lock:
            scope_state = self._state.get(scope)
            if scope_state:
                return scope_state.get(key)
            return None

    def get_all_sync_states(self, scope: Optional[str] = None) -> Dict[str, List[SyncState]]:
        """Return all tracked sync states, optionally filtered by scope."""
        with self._lock:
            if scope:
                entries = self._state.get(scope, {})
                return {scope: list(entries.values())}
            return {
                k: list(v.values()) for k, v in self._state.items()
            }
