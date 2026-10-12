from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


@dataclass
class Bookmark:
    id: str
    title: str
    url: str
    folder: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class BookmarkManager:
    def __init__(self):
        self._bookmarks: list[Bookmark] = []
        self._path = get_aetheros_home() / "automation" / "bookmarks.json"
        self._load()

    def _load(self):
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._bookmarks = [Bookmark(**b) for b in data]
        except Exception as e:
            logger.warning("Failed to load bookmarks: %s", e)
            self._bookmarks = []

    def _save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(b) for b in self._bookmarks]
            self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save bookmarks: %s", e)

    def add(self, title: str, url: str, folder: str = "", tags: list[str] | None = None) -> Bookmark:
        now = datetime.utcnow().isoformat()
        bm = Bookmark(
            id=str(uuid.uuid4()),
            title=title,
            url=url,
            folder=folder,
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )
        self._bookmarks.append(bm)
        self._save()
        return bm

    def remove(self, bookmark_id: str) -> bool:
        for i, bm in enumerate(self._bookmarks):
            if bm.id == bookmark_id:
                self._bookmarks.pop(i)
                self._save()
                return True
        return False

    def update(self, bookmark_id: str, **kwargs) -> Bookmark | None:
        for bm in self._bookmarks:
            if bm.id == bookmark_id:
                for k, v in kwargs.items():
                    if hasattr(bm, k):
                        setattr(bm, k, v)
                bm.updated_at = datetime.utcnow().isoformat()
                self._save()
                return bm
        return None

    def list_all(self, folder: str = "") -> list[Bookmark]:
        if folder:
            return [b for b in self._bookmarks if b.folder == folder]
        return list(self._bookmarks)

    def search(self, query: str) -> list[Bookmark]:
        q = query.lower()
        return [
            b
            for b in self._bookmarks
            if q in b.title.lower() or q in b.url.lower() or any(q in t.lower() for t in b.tags)
        ]

    def get_folders(self) -> list[str]:
        folders = set()
        for b in self._bookmarks:
            if b.folder:
                folders.add(b.folder)
        return sorted(folders)

    def import_from_file(self, file_path: str) -> int:
        count = 0
        try:
            data = json.loads(Path(file_path).read_text(encoding="utf-8"))
            for entry in data:
                if isinstance(entry, dict) and "url" in entry:
                    self.add(entry.get("title", ""), entry["url"], entry.get("folder", ""), entry.get("tags"))
                    count += 1
        except Exception as e:
            logger.warning("Failed to import bookmarks: %s", e)
        return count

    def export_to_file(self, file_path: str):
        try:
            data = [asdict(b) for b in self._bookmarks]
            Path(file_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to export bookmarks: %s", e)

    def count(self) -> int:
        return len(self._bookmarks)
