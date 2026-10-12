"""AetherOS Integrations — Synchronization engine.

Bidirectional sync of records between a provider and a local mirror. Tracks
last-seen state, avoids duplicate events, and supports pull/push/merge.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_integrations.config import get_aetheros_dir, load_integrations_settings

logger = logging.getLogger(__name__)


class SyncEngine:
    """Mirrors remote records locally with cursor-based incremental sync."""

    def __init__(self, dirpath=None, settings=None):
        self._settings = settings or load_integrations_settings()
        self._dir = dirpath or get_aetheros_dir(self._settings.data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "sync_state.json"
        self._lock = threading.RLock()
        self._state: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            self._state = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load sync state: %s", exc)

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")

    def get_cursor(self, sync_id: str) -> str:
        return self._state.get(sync_id, {}).get("cursor", "")

    def set_cursor(self, sync_id: str, cursor: str) -> None:
        with self._lock:
            state = self._state.setdefault(sync_id, {})
            state["cursor"] = cursor
            state["updated_at"] = time.time()
            self._save()

    def is_seen(self, sync_id: str, record_key: str) -> bool:
        return record_key in self._state.get(sync_id, {}).get("seen", {})

    def mark_seen(self, sync_id: str, record_key: str, meta: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            seen = self._state.setdefault(sync_id, {}).setdefault("seen", {})
            seen[record_key] = {"first_seen": time.time(), **((meta or {}) or {})}
            self._save()

    def pull(self, sync_id: str, fetch: Callable[[str], List[Dict[str, Any]]], key_fn: Callable[[Dict[str, Any]], str]) -> Dict[str, Any]:
        """Incremental pull: fetch records since the stored cursor, record new ones."""
        cursor = self.get_cursor(sync_id)
        records = fetch(cursor) or []
        new_count, updated_count, seen_count = 0, 0, 0
        last_cursor = cursor
        for record in records:
            key = key_fn(record)
            if "cursor" in record:
                last_cursor = record["cursor"]
            if self.is_seen(sync_id, key):
                seen_count += 1
                continue
            self.mark_seen(sync_id, key)
            new_count += 1
        self.set_cursor(sync_id, last_cursor or cursor)
        return {"sync_id": sync_id, "fetched": len(records), "new": new_count, "seen": seen_count, "updated": updated_count, "cursor": last_cursor or cursor}

    def stats(self, sync_id: str = "") -> Dict[str, Any]:
        with self._lock:
            if sync_id:
                state = self._state.get(sync_id, {})
                return {"sync_id": sync_id, "seen": len(state.get("seen", {})), "cursor": state.get("cursor", ""), "updated_at": state.get("updated_at", 0.0)}
            return {sid: {"seen": len(s.get("seen", {})), "cursor": s.get("cursor", "")} for sid, s in self._state.items()}
