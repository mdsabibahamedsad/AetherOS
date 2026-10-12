"""Jarvis Mode — long-term memory.

Stores preferences, facts, and mission outcomes so Jarvis remembers context
across sessions. The store is simple, explicit, and profile-aware. It is NOT
a replacement for the full memory system — it holds Jarvis-specific state.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from aetheros_constants import get_aetheros_home
except Exception:  # pragma: no cover
    import os

    def get_aetheros_home() -> Path:
        return Path(os.environ.get("AETHEROS_HOME", str(Path.home() / ".aetheros")))


class JarvisMemory:
    """Key-value long-term memory for Jarvis.

    Entry shape: ``{key, value, category, timestamp, source}``. Values are
    serialized to JSON. Retrieval supports exact key lookup and category
    listing.
    """

    def __init__(self, home: Optional[Path] = None) -> None:
        self._home = Path(home) if home else get_aetheros_home()
        self._path = self._home / "jarvis" / "memory.json"
        self._lock = threading.RLock()
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._load()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def remember(self, key: str, value: Any, *, category: str = "preference", source: str = "jarvis") -> bool:
        with self._lock:
            self._entries[key] = {
                "key": key,
                "value": value,
                "category": category,
                "timestamp": time.time(),
                "source": source,
            }
            self._save()
            return True

    def recall(self, key: str, default: Any = None) -> Any:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return default
            return entry.get("value", default)

    def recall_entry(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._entries.get(key)
            return dict(entry) if entry else None

    def forget(self, key: str) -> bool:
        with self._lock:
            if key not in self._entries:
                return False
            del self._entries[key]
            self._save()
            return True

    def category(self, category: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(e) for e in self._entries.values() if e.get("category") == category]

    def all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(e) for e in self._entries.values()]

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._entries.keys())

    def remember_mission(self, mission_id: str, summary: str) -> bool:
        return self.remember(f"mission:{mission_id}", {"summary": summary}, category="mission")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._entries = {k: v for k, v in data.items() if isinstance(v, dict)}
        except Exception as exc:
            logger.debug("Could not load Jarvis memory: %s", exc)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.debug("Could not save Jarvis memory: %s", exc)
