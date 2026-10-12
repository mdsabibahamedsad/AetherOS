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
class HistoryEntry:
    id: str
    url: str
    title: str
    visit_time: str
    visit_count: int = 1


class HistoryManager:
    def __init__(self, max_entries: int = 10000):
        self._entries: list[HistoryEntry] = []
        self._max_entries = max_entries
        self._path = get_aetheros_home() / "automation" / "browser_history.json"
        self._load()

    def _load(self):
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._entries = [HistoryEntry(**e) for e in data]
        except Exception as e:
            logger.warning("Failed to load history: %s", e)
            self._entries = []

    def _save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(e) for e in self._entries[-self._max_entries :]]
            self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save history: %s", e)

    def add_visit(self, url: str, title: str) -> HistoryEntry:
        now = datetime.utcnow().isoformat()
        for entry in self._entries:
            if entry.url == url:
                entry.visit_count += 1
                entry.visit_time = now
                entry.title = title
                self._save()
                return entry
        entry = HistoryEntry(id=str(uuid.uuid4()), url=url, title=title, visit_time=now)
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]
        self._save()
        return entry

    def search(self, query: str) -> list[HistoryEntry]:
        q = query.lower()
        return [e for e in self._entries if q in e.url.lower() or q in e.title.lower()]

    def get_recent(self, limit: int = 100) -> list[HistoryEntry]:
        sorted_entries = sorted(self._entries, key=lambda e: e.visit_time, reverse=True)
        return sorted_entries[:limit]

    def get_by_date(self, date_str: str) -> list[HistoryEntry]:
        return [e for e in self._entries if e.visit_time.startswith(date_str)]

    def clear(self):
        self._entries.clear()
        self._save()

    def remove_entry(self, entry_id: str) -> bool:
        for i, e in enumerate(self._entries):
            if e.id == entry_id:
                self._entries.pop(i)
                self._save()
                return True
        return False

    def get_most_visited(self, limit: int = 20) -> list[HistoryEntry]:
        sorted_entries = sorted(self._entries, key=lambda e: e.visit_count, reverse=True)
        return sorted_entries[:limit]

    def count(self) -> int:
        return len(self._entries)
