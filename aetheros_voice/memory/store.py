from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from aetheros_voice.models.models import VoiceMemoryEntry


class VoiceMemoryStore:
    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(str(Path.home() / ".aetheros" / "voice"), "memory.json")
        self._path = Path(storage_path)
        self._memory: dict[str, VoiceMemoryEntry] = {}
        self._consented_keys: set[str] = set()
        self._load()

    def remember(self, key: str, value: Any, category: str = "preference", consented: bool = True) -> VoiceMemoryEntry:
        if not self._is_consented(key) and not consented:
            return VoiceMemoryEntry(key=key, value=value, category=category, timestamp=time.time(), consented=False)
        entry = VoiceMemoryEntry(key=key, value=value, category=category, timestamp=time.time(), consented=consented)
        self._memory[key] = entry
        self._save()
        return entry

    def recall(self, key: str, default: Any = None) -> Any:
        entry = self._memory.get(key)
        return entry.value if entry else default

    def forget(self, key: str):
        self._memory.pop(key, None)
        self._save()

    def clear_all(self):
        self._memory.clear()
        self._save()

    def get_category(self, category: str) -> list[VoiceMemoryEntry]:
        return [e for e in self._memory.values() if e.category == category]

    def request_consent(self, key: str) -> bool:
        return True

    def grant_consent(self, key: str):
        self._consented_keys.add(key)

    def revoke_consent(self, key: str):
        self._consented_keys.discard(key)
        self.forget(key)

    def _is_consented(self, key: str) -> bool:
        return key in self._consented_keys

    def _load(self):
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
                for item in raw:
                    entry = VoiceMemoryEntry(**item)
                    self._memory[entry.key] = entry
                    if entry.consented:
                        self._consented_keys.add(entry.key)
            except Exception:
                pass

    def _save(self):
        raw = [{"key": e.key, "value": e.value, "category": e.category, "timestamp": e.timestamp, "consented": e.consented}
               for e in self._memory.values()]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(raw, indent=2, default=str))
