"""Sync engine — offline-first, incremental, conflict-resolving."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from aetheros_cloud.models import (
    SyncItem, SyncAction, SyncStatus, SyncConflict,
    SYNCABLE_TYPES, generate_id, now,
)
from aetheros_cloud.config import CloudConfigManager

logger = logging.getLogger(__name__)


class SyncEngine:
    """Offline-first incremental sync engine.

    Features:
    - Tracks changes by entity type and checksum
    - Incremental sync (only changed items)
    - Conflict detection and resolution
    - Pluggable backend (local file → cloud API)
    """

    def __init__(
        self,
        config: Optional[CloudConfigManager] = None,
        data_dir: Optional[Path] = None,
    ):
        self._config = config or CloudConfigManager()
        if data_dir:
            self._data_dir = data_dir
        else:
            from aetheros_constants import get_aetheros_home
            self._data_dir = get_aetheros_home() / "cloud" / "sync"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._sync_queue: Dict[str, SyncItem] = {}
        self._conflicts: Dict[str, SyncConflict] = {}
        self._sync_lock = asyncio.Lock()
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False
        self._on_sync: List[Callable] = []
        self._remote_push: Optional[Callable] = None
        self._remote_pull: Optional[Callable] = None
        self._load_queue()

    # ── Public API ──────────────────────────────────────────────────

    def track_change(
        self, entity_type: str, entity_id: str,
        data: Dict[str, Any], action: SyncAction = SyncAction.UPDATE,
    ) -> SyncItem:
        if entity_type not in SYNCABLE_TYPES:
            logger.debug("Skipping unsyncable type: %s", entity_type)
            return None
        checksum = self._compute_checksum(data)
        item_id = f"{entity_type}:{entity_id}"
        item = SyncItem(
            id=item_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            status=SyncStatus.PENDING,
            data=data,
            checksum=checksum,
            created_at=now(),
            device_id=self._get_device_id(),
            workspace_id=self._config.get("workspace_id", ""),
        )
        self._sync_queue[item_id] = item
        self._save_queue()
        logger.debug("Tracked %s change for %s:%s", action.value, entity_type, entity_id)
        return item

    def get_pending(self) -> List[SyncItem]:
        return [i for i in self._sync_queue.values() if i.status == SyncStatus.PENDING]

    def get_conflicts(self) -> List[SyncConflict]:
        return list(self._conflicts.values())

    def resolve_conflict(
        self, conflict_id: str, resolution: str,
        resolved_data: Optional[Dict[str, Any]] = None,
        resolved_by: str = "",
    ) -> bool:
        conflict = self._conflicts.get(conflict_id)
        if conflict is None:
            return False
        conflict.resolved = True
        conflict.resolution = resolution
        conflict.resolved_at = now()
        conflict.resolved_by = resolved_by or self._config.get("user_id", "")
        if resolved_data:
            self.track_change(
                conflict.entity_type, conflict.entity_id,
                resolved_data, SyncAction.UPDATE,
            )
        del self._conflicts[conflict_id]
        self._save_conflicts()
        return True

    def set_remote_backend(self, push_fn: Callable, pull_fn: Callable):
        self._remote_push = push_fn
        self._remote_pull = pull_fn

    def on_sync(self, callback: Callable):
        self._on_sync.append(callback)

    # ── Sync lifecycle ──────────────────────────────────────────────

    async def start(self, interval: Optional[int] = None):
        if self._running:
            return
        self._running = True
        interval = interval or self._config.get("sync_interval", 30)
        self._sync_task = asyncio.create_task(self._sync_loop(interval))
        logger.info("SyncEngine started (interval=%ss)", interval)

    async def stop(self):
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        self._save_queue()
        logger.info("SyncEngine stopped")

    async def sync_now(self):
        async with self._sync_lock:
            await self._do_sync()

    async def _sync_loop(self, interval: int):
        while self._running:
            await asyncio.sleep(interval)
            try:
                async with self._sync_lock:
                    await self._do_sync()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Sync cycle error: %s", e)

    async def _do_sync(self):
        if not self._remote_push and not self._remote_pull:
            logger.debug("No remote backend configured; sync skipped")
            return

        pending = self.get_pending()
        if not pending:
            return

        logger.debug("Syncing %d items", len(pending))

        # Push local changes
        if self._remote_push:
            for item in pending:
                item.status = SyncStatus.SYNCING
                try:
                    result = await self._remote_push(item)
                    if result.get("conflict"):
                        self._handle_conflict(item, result)
                    else:
                        item.status = SyncStatus.SYNCED
                        item.synced_at = now()
                except Exception as e:
                    item.status = SyncStatus.FAILED
                    logger.error("Failed to push %s: %s", item.id, e)

        # Pull remote changes
        if self._remote_pull:
            try:
                remote_items = await self._remote_pull(self._config.get("workspace_id", ""))
                for remote in remote_items:
                    local = self._sync_queue.get(remote.id)
                    if local and local.checksum != remote.checksum:
                        self._handle_conflict(remote, {"local": local.data, "remote": remote.data})
                    elif local is None:
                        self._sync_queue[remote.id] = remote
                        remote.status = SyncStatus.SYNCED
                        for cb in self._on_sync:
                            cb(remote)
            except Exception as e:
                logger.error("Failed to pull remote changes: %s", e)

        self._save_queue()
        self._save_conflicts()

    # ── Conflict handling ──────────────────────────────────────────

    def _handle_conflict(self, item: SyncItem, result: Dict[str, Any]):
        strategy = self._config.get("conflict_strategy", "last_write_wins")
        conflict = SyncConflict(
            id=generate_id("conflict"),
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            local_version=item.version,
            remote_version=result.get("remote_version", 0),
            local_data=item.data,
            remote_data=result.get("remote", {}),
            created_at=now(),
        )

        if strategy == "last_write_wins":
            conflict.resolved = True
            conflict.resolution = "last_write_wins"
            conflict.resolved_at = now()
            item.status = SyncStatus.SYNCED
            logger.debug("Auto-resolved conflict for %s (last write wins)", item.id)
        elif strategy == "remote_wins":
            item.data = result.get("remote", item.data)
            item.checksum = self._compute_checksum(item.data)
            item.status = SyncStatus.SYNCED
            conflict.resolved = True
            conflict.resolution = "remote_wins"
        else:
            self._conflicts[conflict.id] = conflict
            item.status = SyncStatus.CONFLICT
            logger.warning("Conflict detected for %s: %s", item.id, conflict.id)

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _compute_checksum(data: Dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _get_device_id(self) -> str:
        import uuid
        device_file = self._data_dir / ".device_id"
        if device_file.exists():
            return device_file.read_text().strip()
        device_id = uuid.uuid4().hex[:12]
        device_file.write_text(device_id)
        return device_id

    def _save_queue(self):
        queue_file = self._data_dir / "sync_queue.json"
        conflict_file = self._data_dir / "sync_conflicts.json"
        import dataclasses
        from enum import Enum
        def ser(obj):
            if dataclasses.is_dataclass(obj):
                return {f.name: ser(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, list):
                return [ser(v) for v in obj]
            if isinstance(obj, dict):
                return {k: ser(v) for k, v in obj.items()}
            return obj
        items = [ser(i) for i in self._sync_queue.values() if i.status != SyncStatus.SYNCED]
        queue_file.write_text(json.dumps(items, indent=2, default=str))
        conflicts = [ser(c) for c in self._conflicts.values() if not c.resolved]
        conflict_file.write_text(json.dumps(conflicts, indent=2, default=str))

    def _load_queue(self):
        queue_file = self._data_dir / "sync_queue.json"
        conflict_file = self._data_dir / "sync_conflicts.json"
        if queue_file.exists():
            try:
                data = json.loads(queue_file.read_text())
                for d in data:
                    try:
                        action = SyncAction(d.get("action", "update"))
                        status = SyncStatus(d.get("status", "pending"))
                    except ValueError:
                        continue
                    item = SyncItem(
                        id=d.get("id", ""),
                        entity_type=d.get("entity_type", ""),
                        entity_id=d.get("entity_id", ""),
                        action=action,
                        status=status,
                        data=d.get("data", {}),
                        version=d.get("version", 1),
                        checksum=d.get("checksum", ""),
                        created_at=d.get("created_at", 0.0),
                        synced_at=d.get("synced_at"),
                        device_id=d.get("device_id", ""),
                        workspace_id=d.get("workspace_id", ""),
                    )
                    self._sync_queue[item.id] = item
            except Exception as e:
                logger.error("Failed to load sync queue: %s", e)
        if conflict_file.exists():
            try:
                data = json.loads(conflict_file.read_text())
                for d in data:
                    conflict = SyncConflict(
                        id=d.get("id", ""),
                        entity_type=d.get("entity_type", ""),
                        entity_id=d.get("entity_id", ""),
                        local_version=d.get("local_version", 0),
                        remote_version=d.get("remote_version", 0),
                        local_data=d.get("local_data", {}),
                        remote_data=d.get("remote_data", {}),
                        created_at=d.get("created_at", 0.0),
                    )
                    self._conflicts[conflict.id] = conflict
            except Exception as e:
                logger.error("Failed to load sync conflicts: %s", e)
