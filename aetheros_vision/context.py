"""AetherOS Vision — multimodal context, memory, and accessibility.

Bundles the vision subsystems into one runtime facade, plus a JSON-file
backed vision memory store (annotated screenshots, recognized objects,
layouts, UI history, documents) and assistive descriptions.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_vision.config import VisionSettings, get_aetheros_dir, load_vision_settings
from aetheros_vision.models import VisionMemoryKind, VisionMemoryRecord

logger = logging.getLogger(__name__)


class VisionMemory:
    """Persistent JSON-backed store for vision memory records.

    Used to keep annotated screenshots, recognized objects, workspace
    layouts, UI history, and referenced documents retrievable across
    sessions. File-based and local-only by design.
    """

    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()
        self._lock = threading.RLock()
        self._dir = get_aetheros_dir("memory/vision")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._records: Dict[str, VisionMemoryRecord] = {}
        self._load()

    def _store_path(self) -> Path:
        return self._dir / "records.json"

    def _load(self) -> None:
        path = self._store_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data:
                rec = VisionMemoryRecord(
                    id=item.get("id", ""),
                    kind=VisionMemoryKind(item.get("kind", "screenshot")),
                    content=item.get("content", ""),
                    image_path=item.get("image_path", ""),
                    caption=item.get("caption", ""),
                    tags=item.get("tags", []),
                    metadata=item.get("metadata", {}),
                    created_at=item.get("created_at", time.time()),
                )
                if rec.id:
                    self._records[rec.id] = rec
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load vision memory: %s", exc)

    def _save(self) -> None:
        path = self._store_path()
        try:
            payload = [r.to_dict() for r in self._records.values()]
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not save vision memory: %s", exc)

    def store(self, record: VisionMemoryRecord) -> VisionMemoryRecord:
        with self._lock:
            self._records[record.id] = record
            self._save()
            return record

    def store_many(self, records: List[VisionMemoryRecord]) -> List[VisionMemoryRecord]:
        with self._lock:
            for r in records:
                self._records[r.id] = r
            self._save()
            return records

    def get(self, record_id: str) -> Optional[VisionMemoryRecord]:
        with self._lock:
            return self._records.get(record_id)

    def search(self, query: str = "", kind: Optional[VisionMemoryKind] = None, limit: int = 50, tag: Optional[str] = None) -> List[VisionMemoryRecord]:
        with self._lock:
            records = list(self._records.values())
            if kind:
                records = [r for r in records if r.kind == kind]
            if tag:
                records = [r for r in records if tag in r.tags]
            if query:
                q = query.lower()
                records = [r for r in records if q in r.content.lower() or q in r.caption.lower() or q in (r.tags or [])]
            records.sort(key=lambda r: r.created_at, reverse=True)
            return records[:limit]

    def list_kinds(self) -> Dict[str, int]:
        with self._lock:
            counts: Dict[str, int] = {}
            for r in self._records.values():
                counts[r.kind.value] = counts.get(r.kind.value, 0) + 1
            return counts

    def delete(self, record_id: str) -> bool:
        with self._lock:
            removed = self._records.pop(record_id, None)
            if removed is not None:
                self._save()
                return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._records)


class AccessibilityIntelligence:
    """Assistive descriptions: image captions, object descriptions, UI narration."""

    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()

    def describe_image(self, path: str) -> str:
        from aetheros_vision.images import ImageUnderstanding
        result = ImageUnderstanding(self._settings).describe(path)
        return result.text or result.summary or "No description available."

    def narrate_ui(self, path: str) -> str:
        from aetheros_vision.desktop import DesktopVision
        result = DesktopVision(self._settings).analyze_screenshot(path)
        if not result.ocr or not result.ocr.success:
            return "Screen could not be read."
        lines = [b.text for b in result.ocr.blocks if b.text.strip()]
        return " ".join(lines[:80]) or "No readable UI text."


class MultimodalContext:
    """Unified context combining vision, memory, chat, and document signals."""

    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()
        self._memory: Optional[VisionMemory] = None
        self._chat_context: List[Dict[str, Any]] = []

    @property
    def memory(self) -> VisionMemory:
        if self._memory is None:
            self._memory = VisionMemory(self._settings)
        return self._memory

    def bind_chat(self, messages: List[Dict[str, Any]]) -> None:
        self._chat_context = list(messages)

    def add_message(self, role: str, content: str) -> None:
        self._chat_context.append({"role": role, "content": content})

    def build(self, query: str = "", include_memory: bool = True, include_chat: bool = True) -> Dict[str, Any]:
        """Assemble a unified context bundle."""
        bundle: Dict[str, Any] = {"query": query, "timestamp": time.time()}
        if include_memory:
            memory_records = self.memory.search(query=query, limit=20)
            bundle["memory"] = [r.to_dict() for r in memory_records]
        if include_chat:
            bundle["chat"] = self._chat_context[-40:]
        return bundle
