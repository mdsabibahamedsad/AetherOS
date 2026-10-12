"""AetherOS Integrations — offline queue and integration memory.

A durable retry queue for actions that fail while a provider is unreachable
(no data loss), plus a local JSON-backed memory store for integration
context (notifications, summaries, references) shared with the workflow
engine.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_integrations.config import get_aetheros_dir, load_integrations_settings
from aetheros_integrations.models import OfflineQueueItem

logger = logging.getLogger(__name__)


class OfflineQueue:
    """Persistent queue: actions enqueued when a provider call fails are
    retried with exponential backoff until they succeed or hit max attempts."""

    def __init__(self, dirpath=None, settings=None, processor: Optional[Callable[[OfflineQueueItem], Any]] = None):
        self._settings = settings or load_integrations_settings()
        self._dir = dirpath or get_aetheros_dir(self._settings.data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "offline_queue.json"
        self._lock = threading.RLock()
        self._processor = processor
        self._items: Dict[str, OfflineQueueItem] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for item in data:
                self._items[item["id"]] = OfflineQueueItem(**item)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load offline queue: %s", exc)

    def _save(self) -> None:
        payload = [i.to_dict() for i in self._items.values()]
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def set_processor(self, processor: Callable[[OfflineQueueItem], Any]) -> None:
        self._processor = processor

    def enqueue(self, integration_id: str, action: str, payload: Dict[str, Any], dedup_key: str = "") -> OfflineQueueItem:
        if dedup_key and self.exists_pending(dedup_key):
            for item in self.list_pending():
                if item.dedup_key == dedup_key:
                    return item
        item = OfflineQueueItem(
            integration_id=integration_id,
            action=action,
            payload=payload,
            dedup_key=dedup_key,
            next_retry_at=time.time(),
        )
        with self._lock:
            self._items[item.id] = item
            if len(self._items) > self._settings.max_offline_queue:
                oldest = min(self._items.values(), key=lambda i: i.created_at)
                del self._items[oldest.id]
            self._save()
        return item

    def list_pending(self, limit: int = 100) -> List[OfflineQueueItem]:
        with self._lock:
            items = [i for i in self._items.values() if i.status == "queued"]
        items.sort(key=lambda i: i.next_retry_at)
        return items[:limit]

    def exists_pending(self, dedup_key: str) -> bool:
        if not dedup_key:
            return False
        with self._lock:
            return any(i.dedup_key == dedup_key and i.status == "queued" for i in self._items.values())

    def get(self, item_id: str) -> Optional[OfflineQueueItem]:
        with self._lock:
            return self._items.get(item_id)

    def flush(self, now: Optional[float] = None) -> Dict[str, Any]:
        """Retry all due queued items. Returns {'delivered': n, 'dead': n}."""
        now = now or time.time()
        delivered, dead = 0, 0
        for item in self.list_pending():
            if item.next_retry_at > now:
                continue
            if self._processor is None:
                break
            item.status = "processing"
            item.attempts += 1
            self._save()
            try:
                self._processor(item)
                item.status = "done"
                delivered += 1
            except Exception as exc:  # noqa: BLE001
                item.last_error = str(exc)
                if item.attempts >= item.max_attempts:
                    item.status = "dead"
                    dead += 1
                else:
                    item.status = "queued"
                    item.next_retry_at = now + (2 ** (item.attempts - 1)) * 5
            self._save()
        return {"delivered": delivered, "dead": dead}

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            queued = sum(1 for i in self._items.values() if i.status == "queued")
            done = sum(1 for i in self._items.values() if i.status == "done")
            dead = sum(1 for i in self._items.values() if i.status == "dead")
            processing = sum(1 for i in self._items.values() if i.status == "processing")
        return {"total": len(self._items), "queued": queued, "processing": processing, "done": done, "dead": dead}


class IntegrationMemory:
    """Local JSON store for integration context, shared with workflow memory steps."""

    def __init__(self, dirpath=None):
        from aetheros_integrations.config import load_integrations_settings

        settings = load_integrations_settings()
        self._dir = dirpath or get_aetheros_dir(settings.data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "memory.json"
        self._lock = threading.RLock()
        self._records: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            self._records = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load integration memory: %s", exc)

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._records, indent=2), encoding="utf-8")

    def store(self, key: str, content: str, source: str = "") -> Dict[str, Any]:
        record = {"content": content, "source": source, "created_at": time.time(), "updated_at": time.time()}
        with self._lock:
            self._records[key] = record
            self._save()
        return {"key": key, "stored": True}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._records.get(key)

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        q = query.lower()
        with self._lock:
            out = [{"key": k, **v} for k, v in self._records.items() if q in v.get("content", "").lower()]
        return out[:limit]
