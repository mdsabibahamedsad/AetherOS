from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class SyncStatus(str, Enum):
    SYNCED = "synced"
    PENDING = "pending"
    SYNCING = "syncing"
    CONFLICT = "conflict"
    ERROR = "error"
    PAUSED = "paused"


class SyncDirection(str, Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"
    BIDIRECTIONAL = "bidirectional"


class ConflictResolution(str, Enum):
    LOCAL_WINS = "local_wins"
    REMOTE_WINS = "remote_wins"
    MANUAL = "manual"
    NEWEST_WINS = "newest_wins"
    MERGE = "merge"


@dataclass
class SyncItem:
    id: str
    entity_type: str
    entity_id: str
    checksum: str
    last_modified: str
    status: SyncStatus = SyncStatus.PENDING
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    conflict_data: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    synced_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "checksum": self.checksum,
            "last_modified": self.last_modified,
            "status": self.status.value,
            "direction": self.direction.value,
            "conflict_data": self.conflict_data,
            "error_message": self.error_message,
            "synced_at": self.synced_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SyncItem:
        return cls(
            id=data["id"],
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            checksum=data.get("checksum", ""),
            last_modified=data.get("last_modified", ""),
            status=SyncStatus(data.get("status", "pending")),
            direction=SyncDirection(data.get("direction", "bidirectional")),
            conflict_data=data.get("conflict_data", {}),
            error_message=data.get("error_message", ""),
            synced_at=data.get("synced_at", ""),
        )


class KnowledgeSyncManager:
    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = Path(storage_path) if storage_path else Path.cwd() / "sync_data"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._sync_items: dict[str, SyncItem] = {}
        self._conflict_resolution = ConflictResolution.NEWEST_WINS
        self._enabled = True
        self._last_sync: str = ""
        self._load()

    def _path(self) -> Path:
        return self._storage_path / "sync_items.json"

    def _config_path(self) -> Path:
        return self._storage_path / "sync_config.json"

    def _load(self):
        p = self._path()
        if p.exists():
            try:
                data = json.loads(p.read_text("utf-8"))
                for item in data:
                    si = SyncItem.from_dict(item)
                    self._sync_items[si.id] = si
            except (json.JSONDecodeError, KeyError):
                pass
        cp = self._config_path()
        if cp.exists():
            try:
                config = json.loads(cp.read_text("utf-8"))
                self._conflict_resolution = ConflictResolution(config.get("conflict_resolution", "newest_wins"))
                self._enabled = config.get("enabled", True)
                self._last_sync = config.get("last_sync", "")
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        self._path().write_text(
            json.dumps([s.to_dict() for s in self._sync_items.values()], indent=2, default=str), "utf-8")
        self._config_path().write_text(json.dumps({
            "conflict_resolution": self._conflict_resolution.value,
            "enabled": self._enabled,
            "last_sync": self._last_sync,
        }, indent=2), "utf-8")

    def _generate_id(self) -> str:
        import uuid
        return f"sync_{uuid.uuid4().hex[:12]}"

    def _compute_checksum(self, data: str) -> str:
        import hashlib
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self._save()

    @property
    def conflict_resolution(self) -> ConflictResolution:
        return self._conflict_resolution

    def set_conflict_resolution(self, resolution: ConflictResolution):
        self._conflict_resolution = resolution
        self._save()

    def mark_for_sync(self, entity_type: str, entity_id: str, data: str,
                      direction: SyncDirection = SyncDirection.BIDIRECTIONAL) -> SyncItem:
        existing = next((s for s in self._sync_items.values()
                         if s.entity_type == entity_type and s.entity_id == entity_id), None)
        checksum = self._compute_checksum(data)
        now = datetime.now().isoformat()
        if existing:
            existing.checksum = checksum
            existing.last_modified = now
            existing.status = SyncStatus.PENDING
            existing.direction = direction
            existing.error_message = ""
            self._save()
            return existing
        item = SyncItem(
            id=self._generate_id(),
            entity_type=entity_type,
            entity_id=entity_id,
            checksum=checksum,
            last_modified=now,
            status=SyncStatus.PENDING,
            direction=direction,
        )
        self._sync_items[item.id] = item
        self._save()
        return item

    def mark_synced(self, entity_type: str, entity_id: str):
        existing = next((s for s in self._sync_items.values()
                         if s.entity_type == entity_type and s.entity_id == entity_id), None)
        if existing:
            existing.status = SyncStatus.SYNCED
            existing.synced_at = datetime.now().isoformat()
            existing.error_message = ""
            self._save()

    def mark_error(self, entity_type: str, entity_id: str, error: str):
        existing = next((s for s in self._sync_items.values()
                         if s.entity_type == entity_type and s.entity_id == entity_id), None)
        if existing:
            existing.status = SyncStatus.ERROR
            existing.error_message = error
            self._save()

    def resolve_conflict(self, entity_type: str, entity_id: str,
                         resolution: ConflictResolution, local_data: str = "",
                         remote_data: str = "") -> Optional[SyncItem]:
        existing = next((s for s in self._sync_items.values()
                         if s.entity_type == entity_type and s.entity_id == entity_id), None)
        if not existing or existing.status != SyncStatus.CONFLICT:
            return None
        if resolution == ConflictResolution.LOCAL_WINS:
            existing.status = SyncStatus.SYNCED
        elif resolution == ConflictResolution.REMOTE_WINS:
            existing.status = SyncStatus.SYNCED
        elif resolution == ConflictResolution.NEWEST_WINS:
            existing.status = SyncStatus.SYNCED
        elif resolution == ConflictResolution.MERGE:
            existing.status = SyncStatus.SYNCED
        existing.synced_at = datetime.now().isoformat()
        existing.conflict_data = {}
        self._save()
        return existing

    def get_pending_items(self) -> list[SyncItem]:
        return [s for s in self._sync_items.values() if s.status == SyncStatus.PENDING]

    def get_conflicts(self) -> list[SyncItem]:
        return [s for s in self._sync_items.values() if s.status == SyncStatus.CONFLICT]

    def get_errors(self) -> list[SyncItem]:
        return [s for s in self._sync_items.values() if s.status == SyncStatus.ERROR]

    def get_all_items(self) -> list[SyncItem]:
        return list(self._sync_items.values())

    def get_stats(self) -> dict:
        counts = {status.value: 0 for status in SyncStatus}
        for item in self._sync_items.values():
            counts[item.status.value] = counts.get(item.status.value, 0) + 1
        return {
            "total_items": len(self._sync_items),
            "status_counts": counts,
            "conflict_resolution": self._conflict_resolution.value,
            "enabled": self._enabled,
            "last_sync": self._last_sync,
        }

    def clear_history(self):
        self._sync_items.clear()
        self._save()
