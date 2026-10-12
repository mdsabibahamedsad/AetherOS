"""
Interaction History — Records and queries interaction events.

Maintains a structured history of all interactions (voice, desktop,
notifications, workspace changes) for analysis, recall, and session
continuity.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """A single interaction history entry.

    Attributes:
        id: Unique entry identifier
        timestamp: When the interaction occurred
        event_type: Type of interaction event
        channel: Interaction channel (voice, desktop, notification, etc.)
        summary: Human-readable summary
        details: Structured details
        duration_ms: Duration in milliseconds (if applicable)
        tags: Tags for filtering
        session_id: Associated session ID (if any)
    """
    id: str = ""
    timestamp: float = 0.0
    event_type: str = ""
    channel: str = ""
    summary: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    tags: List[str] = field(default_factory=list)
    session_id: str = ""


@dataclass
class HistoryQuery:
    """Query parameters for history retrieval.

    Attributes:
        event_type: Filter by event type
        channel: Filter by channel
        tags: Filter by tags (AND)
        start_time: Filter by start time
        end_time: Filter by end time
        session_id: Filter by session
        text_search: Search in summaries
        limit: Max results
        offset: Pagination offset
        sort_desc: Sort descending (newest first)
    """
    event_type: str = ""
    channel: str = ""
    tags: List[str] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    session_id: str = ""
    text_search: str = ""
    limit: int = 50
    offset: int = 0
    sort_desc: bool = True


@dataclass
class HistorySummary:
    """Summary of interaction history.

    Attributes:
        total_entries: Total entries matching query
        time_range: Time range covered (start, end)
        event_counts: Count by event type
        channel_counts: Count by channel
        most_frequent_type: Most common event type
        session_count: Number of unique sessions
    """
    total_entries: int = 0
    time_range: Optional[tuple] = None
    event_counts: Dict[str, int] = field(default_factory=dict)
    channel_counts: Dict[str, int] = field(default_factory=dict)
    most_frequent_type: str = ""
    session_count: int = 0


class InteractionHistory:
    """Records and queries interaction history.

    Maintains an in-memory buffer of interaction entries with
    optional persistence to disk. Supports filtering by event type,
    channel, tags, time range, and session.

    Usage:
        history = InteractionHistory()
        history.initialize()

        entry = history.record("voice_command", "voice",
                               summary="User said 'open terminal'")

        results = history.query(HistoryQuery(channel="voice", limit=10))
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self._lock = threading.RLock()
        self._entries: List[HistoryEntry] = []
        self._max_entries: int = 10000
        self._storage_dir = Path(storage_dir) if storage_dir else None
        self._auto_persist = storage_dir is not None

    def initialize(self) -> None:
        """Initialize the history store."""
        if self._auto_persist and self._storage_dir:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            self._load()
        logger.info("InteractionHistory: initialized (max=%d, persist=%s)",
                     self._max_entries, self._auto_persist)

    def record(
        self,
        event_type: str,
        channel: str = "",
        summary: str = "",
        details: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
        tags: Optional[List[str]] = None,
        session_id: str = "",
    ) -> HistoryEntry:
        """Record a new interaction entry.

        Args:
            event_type: Type of event
            channel: Interaction channel
            summary: Human-readable summary
            details: Structured details
            duration_ms: Duration in milliseconds
            tags: Tags for filtering
            session_id: Associated session ID

        Returns:
            The created HistoryEntry
        """
        entry = HistoryEntry(
            id=uuid.uuid4().hex[:16],
            timestamp=time.time(),
            event_type=event_type,
            channel=channel,
            summary=summary,
            details=details or {},
            duration_ms=duration_ms,
            tags=tags or [],
            session_id=session_id,
        )

        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]

        if self._auto_persist:
            self._persist()

        return entry

    def record_many(self, entries: List[HistoryEntry]) -> None:
        """Record multiple entries at once.

        Args:
            entries: History entries to record
        """
        with self._lock:
            self._entries.extend(entries)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]

        if self._auto_persist:
            self._persist()

    def query(self, query: Optional[HistoryQuery] = None) -> List[HistoryEntry]:
        """Query history entries.

        Args:
            query: Query parameters (all entries if None)

        Returns:
            Matching HistoryEntry list
        """
        with self._lock:
            results = list(self._entries)

        if query is None:
            return results[-50:]

        # Apply filters
        if query.event_type:
            results = [e for e in results if e.event_type == query.event_type]
        if query.channel:
            results = [e for e in results if e.channel == query.channel]
        if query.tags:
            results = [e for e in results if all(t in e.tags for t in query.tags)]
        if query.start_time:
            results = [e for e in results if e.timestamp >= query.start_time]
        if query.end_time:
            results = [e for e in results if e.timestamp <= query.end_time]
        if query.session_id:
            results = [e for e in results if e.session_id == query.session_id]
        if query.text_search:
            query_lower = query.text_search.lower()
            results = [e for e in results if query_lower in e.summary.lower()]

        # Sort
        results.sort(key=lambda e: e.timestamp, reverse=query.sort_desc)

        # Apply pagination
        return results[query.offset:query.offset + query.limit]

    def summarize(self, query: Optional[HistoryQuery] = None) -> HistorySummary:
        """Generate a summary of history entries.

        Args:
            query: Optional filter

        Returns:
            HistorySummary
        """
        entries = self.query(query) if query else self._entries

        if not entries:
            return HistorySummary()

        event_counts: Dict[str, int] = {}
        channel_counts: Dict[str, int] = {}
        sessions: set = set()

        for entry in entries:
            event_counts[entry.event_type] = event_counts.get(entry.event_type, 0) + 1
            channel_counts[entry.channel] = channel_counts.get(entry.channel, 0) + 1
            if entry.session_id:
                sessions.add(entry.session_id)

        most_frequent = max(event_counts, key=event_counts.get) if event_counts else ""

        return HistorySummary(
            total_entries=len(entries),
            time_range=(entries[0].timestamp, entries[-1].timestamp),
            event_counts=event_counts,
            channel_counts=channel_counts,
            most_frequent_type=most_frequent,
            session_count=len(sessions),
        )

    def get_event_types(self) -> List[str]:
        """Get all distinct event types in history.

        Returns:
            Sorted list of event type strings
        """
        with self._lock:
            return sorted(set(e.event_type for e in self._entries))

    def get_channels(self) -> List[str]:
        """Get all distinct channels in history.

        Returns:
            Sorted list of channel strings
        """
        with self._lock:
            return sorted(set(e.channel for e in self._entries))

    def clear(self) -> None:
        """Clear all history entries."""
        with self._lock:
            self._entries.clear()
        if self._auto_persist:
            self._persist()
        logger.info("InteractionHistory: cleared")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self) -> None:
        """Persist history to disk as JSONL (one JSON object per line)."""
        if not self._storage_dir:
            return
        try:
            path = self._storage_dir / "interaction_history.jsonl"
            with self._lock:
                with open(path, "w", encoding="utf-8") as f:
                    for entry in self._entries:
                        f.write(self._entry_to_json(entry) + "\n")
        except Exception as exc:
            logger.warning("InteractionHistory: persistence failed: %s", exc)

    def _load(self) -> None:
        """Load history from disk."""
        if not self._storage_dir:
            return
        path = self._storage_dir / "interaction_history.jsonl"
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        self._entries.append(HistoryEntry(**data))
                    except (json.JSONDecodeError, TypeError):
                        continue
        except Exception as exc:
            logger.warning("InteractionHistory: load failed: %s", exc)

    @staticmethod
    def _entry_to_json(entry: HistoryEntry) -> str:
        """Serialize an entry to JSON."""
        return json.dumps({
            "id": entry.id,
            "timestamp": entry.timestamp,
            "event_type": entry.event_type,
            "channel": entry.channel,
            "summary": entry.summary,
            "details": entry.details,
            "duration_ms": entry.duration_ms,
            "tags": entry.tags,
            "session_id": entry.session_id,
        }, ensure_ascii=False)

    def get_stats(self) -> Dict[str, Any]:
        """Get history statistics."""
        with self._lock:
            return {
                "total_entries": len(self._entries),
                "event_types": len(self.get_event_types()),
                "channels": len(self.get_channels()),
                "auto_persist": self._auto_persist,
            }
