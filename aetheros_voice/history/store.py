from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from aetheros_voice.models.models import VoiceHistoryEntry


class VoiceHistoryStore:
    def __init__(self, storage_path: str | None = None, max_entries: int = 1000):
        if storage_path is None:
            storage_path = os.path.join(str(Path.home() / ".aetheros" / "voice"), "history.json")
        self._path = Path(storage_path)
        self._max_entries = max_entries
        self._entries: list[VoiceHistoryEntry] = []
        self._load()

    def add(self, text: str, response: str = "", mode: str = "conversation", duration: float = 0.0, source: str = "mic") -> VoiceHistoryEntry:
        entry = VoiceHistoryEntry(
            id=str(uuid.uuid4())[:8], timestamp=time.time(),
            text=text, response=response, mode=mode, duration=duration, source=source,
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        self._save()
        return entry

    def list(self, limit: int = 50, offset: int = 0) -> list[VoiceHistoryEntry]:
        return self._entries[offset:offset + limit]

    def search(self, query: str) -> list[VoiceHistoryEntry]:
        lower = query.lower()
        return [e for e in self._entries if lower in e.text.lower() or lower in e.response.lower()]

    def get(self, entry_id: str) -> VoiceHistoryEntry | None:
        for e in self._entries:
            if e.id == entry_id:
                return e
        return None

    def delete(self, entry_id: str):
        self._entries = [e for e in self._entries if e.id != entry_id]
        self._save()

    def clear_all(self):
        self._entries.clear()
        self._save()

    def count(self) -> int:
        return len(self._entries)

    def _load(self):
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
                self._entries = [VoiceHistoryEntry(**item) for item in raw]
            except Exception:
                pass

    def _save(self):
        raw = [
            {"id": e.id, "timestamp": e.timestamp, "text": e.text, "response": e.response,
             "mode": e.mode, "duration": e.duration, "source": e.source}
            for e in self._entries
        ]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(raw, indent=2))
