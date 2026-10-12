"""Research Library — auto-saves research sessions, sources, documents, references, tags, collections."""

from __future__ import annotations

import enum
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_memory.memory_manager import MemoryManager, MemoryCategory

logger = logging.getLogger("aetheros_memory.research_library")


class SourceType(str, enum.Enum):
    WEB_PAGE = "web_page"
    PDF = "pdf"
    DOCUMENT = "document"
    VIDEO = "video"
    CODE_REPO = "code_repo"
    CONVERSATION = "conversation"
    IMAGE = "image"
    AUDIO = "audio"
    NOTE = "note"
    REFERENCE = "reference"


@dataclass
class ResearchSource:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: SourceType = SourceType.WEB_PAGE
    title: str = ""
    url: str = ""
    content: str = ""
    summary: str = ""
    author: str = ""
    published_date: str = ""
    retrieved_date: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "summary": self.summary,
            "author": self.author,
            "published_date": self.published_date,
            "retrieved_date": self.retrieved_date,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResearchSource:
        data = dict(data)
        data["type"] = SourceType(data.pop("type", "web_page"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ResearchSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    query: str = ""
    sources: List[ResearchSource] = field(default_factory=list)
    summary: str = ""
    collections: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "query": self.query,
            "sources": [s.to_dict() for s in self.sources],
            "summary": self.summary,
            "collections": self.collections,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "duration_seconds": self.duration_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResearchSession:
        data = dict(data)
        sources_raw = data.pop("sources", [])
        session = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        session.sources = [ResearchSource.from_dict(s) for s in sources_raw]
        return session


@dataclass
class ResearchCollection:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    session_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    is_public: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "session_ids": self.session_ids,
            "tags": self.tags,
            "created_at": self.created_at,
            "is_public": self.is_public,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResearchCollection:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ResearchLibrary:
    def __init__(
        self,
        storage_path: str = "",
        memory_manager: Optional[MemoryManager] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._memory_manager = memory_manager
        self._sessions: Dict[str, ResearchSession] = {}
        self._sources: Dict[str, ResearchSource] = {}
        self._collections: Dict[str, ResearchCollection] = {}
        self._session_source_map: Dict[str, List[str]] = {}

        if storage_path:
            self._storage_path = Path(storage_path)
        elif memory_manager and memory_manager.config.storage_dir:
            self._storage_path = Path(memory_manager.config.storage_dir) / "research_library"
        else:
            self._storage_path = Path.cwd() / "research_library"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._load()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(self, topic: str, query: str) -> ResearchSession:
        session = ResearchSession(topic=topic, query=query)
        with self._lock:
            self._sessions[session.id] = session
            self._session_source_map[session.id] = []
            self._save()
        if self._memory_manager:
            self._memory_manager.store(
                content=f"Research: {topic}\nQuery: {query}",
                category=MemoryCategory.RESEARCH,
                key=f"research_session_{session.id}",
                tags=["research", *topic.lower().split()],
                metadata={"session_id": session.id},
            )
        return session

    def get_session(self, session_id: str) -> Optional[ResearchSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def update_session(
        self,
        session_id: str,
        summary: str = "",
        tags: Optional[List[str]] = None,
    ) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            if summary:
                session.summary = summary
            if tags is not None:
                session.tags = tags
            session.updated_at = time.time()
            self._save()
            return True

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            for sid in session.sources:
                self._sources.pop(sid.id, None)
            self._sessions.pop(session_id, None)
            self._session_source_map.pop(session_id, None)
            for collection in self._collections.values():
                if session_id in collection.session_ids:
                    collection.session_ids.remove(session_id)
            self._save()
            return True

    # ------------------------------------------------------------------
    # Source management
    # ------------------------------------------------------------------

    def add_source(
        self,
        session_id: str,
        type: SourceType = SourceType.WEB_PAGE,
        title: str = "",
        url: str = "",
        content: str = "",
        summary: str = "",
        author: str = "",
        tags: Optional[List[str]] = None,
    ) -> ResearchSource:
        source = ResearchSource(
            type=type,
            title=title,
            url=url,
            content=content,
            summary=summary,
            author=author,
            tags=tags or [],
        )
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.sources.append(source)
                session.updated_at = time.time()
                if source.id not in self._session_source_map.get(session_id, []):
                    self._session_source_map.setdefault(session_id, []).append(source.id)
            self._sources[source.id] = source
            self._save()
        return source

    def get_source(self, source_id: str) -> Optional[ResearchSource]:
        with self._lock:
            return self._sources.get(source_id)

    def delete_source(self, source_id: str) -> bool:
        with self._lock:
            source = self._sources.pop(source_id, None)
            if not source:
                return False
            for session in self._sessions.values():
                session.sources = [s for s in session.sources if s.id != source_id]
            for sid_list in self._session_source_map.values():
                if source_id in sid_list:
                    sid_list.remove(source_id)
            self._save()
            return True

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_sessions(self, query: str) -> List[ResearchSession]:
        if not query:
            with self._lock:
                return list(self._sessions.values())
        q = query.lower()
        results: List[ResearchSession] = []
        with self._lock:
            for session in self._sessions.values():
                if (
                    q in session.topic.lower()
                    or q in session.query.lower()
                    or q in session.summary.lower()
                    or any(q in t.lower() for t in session.tags)
                ):
                    results.append(session)
        return results

    def search_sources(self, query: str) -> List[ResearchSource]:
        if not query:
            with self._lock:
                return list(self._sources.values())
        q = query.lower()
        results: List[ResearchSource] = []
        with self._lock:
            for source in self._sources.values():
                if (
                    q in source.title.lower()
                    or q in source.url.lower()
                    or q in source.content.lower()
                    or q in source.summary.lower()
                    or any(q in t.lower() for t in source.tags)
                ):
                    results.append(source)
        return results

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def create_collection(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> ResearchCollection:
        collection = ResearchCollection(
            name=name,
            description=description,
            tags=tags or [],
        )
        with self._lock:
            self._collections[collection.id] = collection
            self._save()
        return collection

    def add_to_collection(self, collection_id: str, session_id: str) -> bool:
        with self._lock:
            collection = self._collections.get(collection_id)
            if not collection:
                return False
            if session_id not in collection.session_ids:
                collection.session_ids.append(session_id)
                self._save()
            return True

    def get_collection(self, collection_id: str) -> Optional[ResearchCollection]:
        with self._lock:
            return self._collections.get(collection_id)

    def list_collections(self) -> List[ResearchCollection]:
        with self._lock:
            return list(self._collections.values())

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_session(self, session_id: str, format: str = "json") -> str:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return ""
            if format.lower() == "markdown":
                return self._to_markdown(session)
            return json.dumps(session.to_dict(), indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total_sessions = len(self._sessions)
            total_sources = len(self._sources)
            total_collections = len(self._collections)
            tags: set = set()
            for s in self._sessions.values():
                tags.update(s.tags)
            for c in self._collections.values():
                tags.update(c.tags)
            return {
                "total_sessions": total_sessions,
                "total_sources": total_sources,
                "total_collections": total_collections,
                "unique_tags": len(tags),
                "sessions_with_sources": sum(
                    1 for s in self._sessions.values() if s.sources
                ),
            }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        try:
            data = {
                "sessions": {sid: s.to_dict() for sid, s in self._sessions.items()},
                "sources": {sid: s.to_dict() for sid, s in self._sources.items()},
                "collections": {cid: c.to_dict() for cid, c in self._collections.items()},
                "session_source_map": self._session_source_map,
            }
            path = self._storage_path / "research_library.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except Exception as exc:
            logger.warning("Failed to save research library: %s", exc)

    def _load(self) -> None:
        path = self._storage_path / "research_library.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for sid, raw in data.get("sessions", {}).items():
                self._sessions[sid] = ResearchSession.from_dict(raw)
            for sid, raw in data.get("sources", {}).items():
                self._sources[sid] = ResearchSource.from_dict(raw)
            for cid, raw in data.get("collections", {}).items():
                self._collections[cid] = ResearchCollection.from_dict(raw)
            self._session_source_map.update(data.get("session_source_map", {}))
        except Exception as exc:
            logger.warning("Failed to load research library: %s", exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_markdown(self, session: ResearchSession) -> str:
        lines: List[str] = []
        lines.append(f"# Research Session: {session.topic}")
        lines.append("")
        lines.append(f"**Query:** {session.query}")
        lines.append(f"**Created:** {datetime.fromtimestamp(session.created_at, tz=timezone.utc).isoformat()}")
        lines.append(f"**Duration:** {session.duration_seconds:.1f}s")
        if session.tags:
            lines.append(f"**Tags:** {', '.join(session.tags)}")
        lines.append("")
        if session.summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(session.summary)
            lines.append("")
        if session.sources:
            lines.append("## Sources")
            lines.append("")
            for i, src in enumerate(session.sources, 1):
                lines.append(f"### {i}. {src.title}")
                lines.append("")
                lines.append(f"- **Type:** {src.type.value}")
                lines.append(f"- **URL:** {src.url}")
                lines.append(f"- **Author:** {src.author}")
                if src.summary:
                    lines.append("")
                    lines.append(src.summary)
                lines.append("")
        return "\n".join(lines)
