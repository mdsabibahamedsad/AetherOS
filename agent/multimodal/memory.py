"""Multimodal Memory (Phases 54-56 of Master Prompt 10).

Stores **references** to media (never huge payloads), extracted facts with
provenance, and supports lightweight retrieval (RAG) across text/image/
document/audio-transcript/video-event entries.

Persistence is a JSON index under ``$AETHEROS_HOME/memory/multimodal/``,
profile-aware via aetheros_constants.  Entries are deduplicated by content
hash.  Embeddings are optional (stored as reference vectors) — the store works
without them.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from agent.multimodal.media_abstraction import MediaObject
from agent.multimodal.provenance import GroundedFact

logger = logging.getLogger(__name__)


@dataclass
class MultimodalMemoryEntry:
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    kind: str = ""                  # text | image | audio | video | document | screen | camera | fact
    content: str = ""               # extracted text / transcript / summary
    media_id: str = ""
    source: str = ""
    mime_type: str = ""
    hash: str = ""
    timestamp: float = field(default_factory=time.time)
    sensitivity: str = "private"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None  # optional, kept as reference only

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


class MultimodalMemoryStore:
    """Persistent reference store for multimodal memory + light RAG."""

    def __init__(self, base_dir: Optional[str] = None, max_entries: int = 2000) -> None:
        self._dir = base_dir or self._default_dir()
        os.makedirs(self._dir, exist_ok=True)
        self._index_path = os.path.join(self._dir, "index.json")
        self._lock = threading.RLock()
        self._entries: List[MultimodalMemoryEntry] = []
        self._load()

    @staticmethod
    def _default_dir() -> str:
        try:
            from aetheros_constants import get_aetheros_home

            return str(get_aetheros_home() / "memory" / "multimodal")
        except Exception:
            return os.path.join(os.path.expanduser("~"), ".aetheros", "memory", "multimodal")

    # -- persistence -------------------------------------------------------
    def _load(self) -> None:
        try:
            if os.path.exists(self._index_path):
                with open(self._index_path, encoding="utf-8") as f:
                    raw = json.load(f)
                self._entries = [MultimodalMemoryEntry(**e) for e in raw.get("entries", [])]
        except Exception as e:
            logger.warning("Could not load multimodal memory index: %s", e)
            self._entries = []

    def _save(self) -> None:
        tmp = self._index_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"entries": [e.to_dict() for e in self._entries]}, f, indent=2)
        os.replace(tmp, self._index_path)

    # -- writes ------------------------------------------------------------
    def store_media(
        self,
        media: MediaObject,
        content: str = "",
        tags: Optional[List[str]] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """Store a reference to a media object (Phase 54). Dedup by hash."""
        with self._lock:
            content_hash = media.hash or self._hash(media.source)
            for existing in self._entries:
                if existing.hash and existing.hash == content_hash and existing.kind == media.type.value:
                    return existing.entry_id  # dedup
            entry = MultimodalMemoryEntry(
                kind=media.type.value,
                content=content or media.source,
                media_id=media.media_id,
                source=media.source,
                mime_type=media.mime_type,
                hash=content_hash,
                sensitivity=media.sensitivity.value,
                tags=tags or [],
                metadata={
                    "dimensions": media.dimensions,
                    "duration": media.duration,
                    "size": media.size,
                },
                embedding=embedding,
            )
            self._entries.append(entry)
            self._prune_locked()
            self._save()
            return entry.entry_id

    def store_fact(self, fact: GroundedFact, tags: Optional[List[str]] = None) -> str:
        """Store a grounded fact with provenance (Phase 57)."""
        with self._lock:
            entry = MultimodalMemoryEntry(
                kind="fact",
                content=fact.claim,
                media_id=fact.evidence.media_id if fact.evidence else "",
                source=fact.evidence.source if fact.evidence else "",
                hash=self._hash(fact.claim),
                sensitivity="private",
                tags=tags or [],
                metadata={
                    "status": fact.status.value,
                    "fact_id": fact.fact_id,
                    "confidence": fact.evidence.confidence if fact.evidence else 1.0,
                    "evidence": fact.evidence.to_dict() if fact.evidence else None,
                },
            )
            self._entries.append(entry)
            self._prune_locked()
            self._save()
            return entry.entry_id

    def store_text(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        with self._lock:
            entry = MultimodalMemoryEntry(
                kind="text", content=content, hash=self._hash(content),
                sensitivity="private", tags=tags or [], metadata=metadata or {}, embedding=embedding,
            )
            self._entries.append(entry)
            self._prune_locked()
            self._save()
            return entry.entry_id

    # -- retrieval (Phase 56 RAG) -----------------------------------------
    def search(self, query: str, limit: int = 10, kinds: Optional[List[str]] = None) -> List[MultimodalMemoryEntry]:
        """Token-overlap scoring over stored content (no embeddings needed)."""
        q_tokens = set(self._tokenize(query))
        scored: List[tuple] = []
        for e in self._entries:
            if kinds and e.kind not in kinds:
                continue
            doc_tokens = set(self._tokenize(e.content))
            overlap = len(q_tokens & doc_tokens)
            score = overlap / max(len(q_tokens), 1)
            scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for s, e in scored[:limit] if s > 0]

    def get(self, entry_id: str) -> Optional[MultimodalMemoryEntry]:
        for e in self._entries:
            if e.entry_id == entry_id:
                return e
        return None

    def list(self, limit: int = 50, kinds: Optional[List[str]] = None) -> List[MultimodalMemoryEntry]:
        out = [e for e in self._entries if (not kinds or e.kind in kinds)]
        out.sort(key=lambda e: e.timestamp, reverse=True)
        return out[:limit]

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            before = len(self._entries)
            self._entries = [e for e in self._entries if e.entry_id != entry_id]
            if len(self._entries) != before:
                self._save()
                return True
            return False

    def count(self) -> int:
        return len(self._entries)

    # -- helpers -----------------------------------------------------------
    def _prune_locked(self) -> None:
        if len(self._entries) > self._max_entries():
            self._entries = self._entries[-self._max_entries():]

    def _max_entries(self) -> int:
        return 2000

    @staticmethod
    def _hash(text_or_path: str) -> str:
        try:
            if os.path.isfile(text_or_path):
                h = hashlib.sha256()
                with open(text_or_path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                return h.hexdigest()
        except OSError:
            pass
        return hashlib.sha256(text_or_path.encode("utf-8")).hexdigest()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        import re

        return re.findall(r"[a-z0-9]{3,}", (text or "").lower())


def default_store() -> MultimodalMemoryStore:
    """Shared process-wide store (thread-safe)."""
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = MultimodalMemoryStore()
    return _DEFAULT_STORE


_DEFAULT_STORE: Optional[MultimodalMemoryStore] = None