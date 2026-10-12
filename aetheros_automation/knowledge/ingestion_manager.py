from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class IngestionStatus(str, Enum):
    IDLE = "idle"
    WATCHING = "watching"
    INDEXING = "indexing"
    PAUSED = "paused"
    ERROR = "error"


class FileTypeFilter(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"


@dataclass
class WatchFolder:
    id: str
    path: str
    enabled: bool = True
    recursive: bool = True
    file_type_filter: FileTypeFilter = FileTypeFilter.EXCLUDE
    file_types: list[str] = field(default_factory=lambda: [".tmp", ".log", ".git", ".svn", ".DS_Store"])
    exclude_folders: list[str] = field(default_factory=lambda: ["node_modules", ".git", "__pycache__", ".venv", "venv", ".next", "dist", "build", ".cache"])
    privacy_rules: list[str] = field(default_factory=list)
    space_id: str = "default"
    last_indexed_at: str = ""
    status: IngestionStatus = IngestionStatus.IDLE
    created_at: str = ""
    file_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "enabled": self.enabled,
            "recursive": self.recursive,
            "file_type_filter": self.file_type_filter.value,
            "file_types": self.file_types,
            "exclude_folders": self.exclude_folders,
            "privacy_rules": self.privacy_rules,
            "space_id": self.space_id,
            "last_indexed_at": self.last_indexed_at,
            "status": self.status.value,
            "created_at": self.created_at,
            "file_count": self.file_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> WatchFolder:
        return cls(
            id=data["id"],
            path=data["path"],
            enabled=data.get("enabled", True),
            recursive=data.get("recursive", True),
            file_type_filter=FileTypeFilter(data.get("file_type_filter", "exclude")),
            file_types=data.get("file_types", [".tmp", ".log"]),
            exclude_folders=data.get("exclude_folders", ["node_modules", ".git"]),
            privacy_rules=data.get("privacy_rules", []),
            space_id=data.get("space_id", "default"),
            last_indexed_at=data.get("last_indexed_at", ""),
            status=IngestionStatus(data.get("status", "idle")),
            created_at=data.get("created_at", ""),
            file_count=data.get("file_count", 0),
        )


class IngestionManager:
    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = Path(storage_path) if storage_path else Path.cwd() / "ingestion_data"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._folders: dict[str, WatchFolder] = {}
        self._ingestion_log: list[dict] = []
        self._indexed_files: dict[str, str] = {}  # path -> checksum
        self._load()

    def _path(self) -> Path:
        return self._storage_path / "watch_folders.json"

    def _log_path(self) -> Path:
        return self._storage_path / "ingestion_log.json"

    def _index_path(self) -> Path:
        return self._storage_path / "indexed_files.json"

    def _load(self):
        p = self._path()
        if p.exists():
            try:
                data = json.loads(p.read_text("utf-8"))
                for item in data:
                    folder = WatchFolder.from_dict(item)
                    self._folders[folder.id] = folder
            except (json.JSONDecodeError, KeyError):
                pass
        lp = self._log_path()
        if lp.exists():
            try:
                self._ingestion_log = json.loads(lp.read_text("utf-8"))
            except (json.JSONDecodeError, KeyError):
                pass
        ip = self._index_path()
        if ip.exists():
            try:
                self._indexed_files = json.loads(ip.read_text("utf-8"))
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        self._path().write_text(
            json.dumps([f.to_dict() for f in self._folders.values()], indent=2, default=str), "utf-8")
        self._log_path().write_text(
            json.dumps(self._ingestion_log[-500:], indent=2, default=str), "utf-8")
        self._index_path().write_text(json.dumps(self._indexed_files, indent=2, default=str), "utf-8")

    def _generate_id(self) -> str:
        import uuid
        return f"wf_{uuid.uuid4().hex[:12]}"

    def _compute_checksum(self, file_path: Path) -> str:
        try:
            import hashlib
            h = hashlib.sha256()
            h.update(file_path.read_bytes()[:65536])
            return h.hexdigest()[:16]
        except (IOError, OSError):
            return ""

    def add_watch_folder(self, path: str, recursive: bool = True,
                         space_id: str = "default") -> WatchFolder:
        folder = WatchFolder(
            id=self._generate_id(),
            path=path,
            enabled=True,
            recursive=recursive,
            space_id=space_id,
            created_at=datetime.now().isoformat(),
        )
        self._folders[folder.id] = folder
        self._save()
        return folder

    def remove_watch_folder(self, folder_id: str) -> bool:
        if folder_id not in self._folders:
            return False
        del self._folders[folder_id]
        self._save()
        return True

    def update_watch_folder(self, folder_id: str, **updates) -> Optional[WatchFolder]:
        folder = self._folders.get(folder_id)
        if not folder:
            return None
        for key, value in updates.items():
            if hasattr(folder, key) and key != "id":
                if key == "file_type_filter":
                    setattr(folder, key, FileTypeFilter(value) if isinstance(value, str) else value)
                elif key == "status":
                    setattr(folder, key, IngestionStatus(value) if isinstance(value, str) else value)
                else:
                    setattr(folder, key, value)
        self._save()
        return folder

    def get_watch_folders(self, space_id: str = "") -> list[WatchFolder]:
        if space_id:
            return [f for f in self._folders.values() if f.space_id == space_id]
        return list(self._folders.values())

    def scan_folder(self, folder_id: str) -> list[dict]:
        folder = self._folders.get(folder_id)
        if not folder or not folder.enabled:
            return []
        base = Path(folder.path)
        if not base.exists():
            return []
        results = []
        if folder.recursive:
            files = list(base.rglob("*"))
        else:
            files = list(base.glob("*"))
        exclude_set = set(folder.exclude_folders)
        type_filter = folder.file_type_filter
        type_set = set(folder.file_types) if folder.file_types else set()
        for f in files:
            if not f.is_file():
                continue
            if any(excl in f.parts for excl in exclude_set):
                continue
            ext = f.suffix.lower()
            if type_filter == FileTypeFilter.EXCLUDE and ext in type_set:
                continue
            if type_filter == FileTypeFilter.INCLUDE and type_set and ext not in type_set:
                continue
            checksum = self._compute_checksum(f)
            prev = self._indexed_files.get(str(f))
            if prev == checksum:
                continue
            results.append({
                "path": str(f),
                "name": f.name,
                "ext": ext,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "checksum": checksum,
            })
        folder.file_count += len(results)
        folder.last_indexed_at = datetime.now().isoformat()
        self._save()
        return results

    def mark_indexed(self, file_path: str, checksum: str):
        self._indexed_files[file_path] = checksum
        self._save()

    def log_ingestion(self, file_path: str, status: str, details: str = ""):
        self._ingestion_log.append({
            "file_path": file_path,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        })
        self._save()

    def get_ingestion_log(self, limit: int = 100) -> list[dict]:
        return sorted(self._ingestion_log, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_stats(self) -> dict:
        return {
            "total_folders": len(self._folders),
            "active_folders": sum(1 for f in self._folders.values() if f.enabled),
            "total_indexed_files": len(self._indexed_files),
            "total_log_entries": len(self._ingestion_log),
        }
