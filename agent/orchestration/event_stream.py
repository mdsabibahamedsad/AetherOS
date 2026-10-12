"""Event Stream for AetherOS Orchestration Layer.

Implements Phases 33-34 of Master Prompt 38: canonical agent events with
monotonic ordering per task, deduplication of duplicate events, and safe
ignoring of stale events.

Every event contains:
- eventId: Unique event identifier
- taskId: Task the event belongs to
- timestamp: Event timestamp
- sequence: Monotonic sequence number per task
- type: Event type
- payload: Event data
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Canonical agent event types."""

    TASK_CREATED = "task.created"
    TASK_QUEUED = "task.queued"
    TASK_PLANNING = "task.planning"
    TASK_READY = "task.ready"
    TASK_STARTED = "task.started"
    PLAN_CREATED = "plan.created"
    STEP_STARTED = "step.started"
    MODEL_STARTED = "model.started"
    MODEL_COMPLETED = "model.completed"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_COMPLETED = "approval.completed"
    VERIFICATION_STARTED = "verification.started"
    VERIFICATION_COMPLETED = "verification.completed"
    RECOVERY_STARTED = "recovery.started"
    TASK_PAUSED = "task.paused"
    TASK_RESUMED = "task.resumed"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_EXPIRED = "task.expired"
    RECOVERY_COMPLETED = "recovery.completed"
    EVENT_DEDUPLICATED = "event.deduplicated"
    EVENT_STALE_IGNORED = "event.stale_ignored"


@dataclass
class AgentEvent:
    """Canonical agent event with monotonic ordering."""

    event_id: str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    task_id: str = ""
    timestamp: float = field(default_factory=time.time)
    sequence: int = 0
    event_type: EventType = EventType.TASK_CREATED
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "event_type": self.event_type.value,
            "payload": self.payload,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentEvent":
        event = cls(
            event_id=data.get("event_id", ""),
            task_id=data.get("task_id", ""),
            timestamp=data.get("timestamp", time.time()),
            sequence=data.get("sequence", 0),
            event_type=EventType(data.get("event_type", "task.created")),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
        )
        return event


class EventDedupTracker:
    """Tracks event sequences per task to deduplicate and detect stale events."""

    def __init__(self):
        # task_id -> set of seen event sequences
        self._seen: Dict[str, Set[int]] = defaultdict(set)
        # task_id -> last seen sequence
        self._last_sequence: Dict[str, int] = {}

    def is_duplicate(self, task_id: str, sequence: int) -> bool:
        """Check if an event with this sequence for this task is a duplicate."""
        return sequence in self._seen[task_id]

    def is_stale(self, task_id: str, sequence: int) -> bool:
        """Check if an event with this sequence is stale (lower than last seen)."""
        last = self._last_sequence.get(task_id, 0)
        return sequence < last

    def record(self, task_id: str, sequence: int) -> None:
        """Record that we've seen this sequence for this task."""
        self._seen[task_id].add(sequence)
        self._last_sequence[task_id] = max(self._last_sequence.get(task_id, 0), sequence)


@dataclass
class EventStream:
    """Manages a stream of canonical events for a task."""

    task_id: str
    _dedup: EventDedupTracker = field(default_factory=EventDedupTracker)
    _sequence_counter: int = 0
    _events: List[AgentEvent] = field(default_factory=list)

    def emit(
        self,
        event_type: EventType,
        payload: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
    ) -> AgentEvent:
        """Emit a new event with incremented sequence."""
        self._sequence_counter += 1
        event = AgentEvent(
            task_id=self.task_id,
            sequence=self._sequence_counter,
            event_type=event_type,
            payload=payload or {},
            metadata=metadata or {},
        )

        # Check for duplicate
        if self._dedup.is_duplicate(self.task_id, self._sequence_counter):
            self._dedup.record(self.task_id, self._sequence_counter)
            # Don't add duplicate, but log it
            logger.debug(
                f"Duplicate event detected: seq={self._sequence_counter} for task {self.task_id}"
            )
            # Create a dedup notification event
            dedup_event = AgentEvent(
                task_id=self.task_id,
                sequence=self._sequence_counter,
                event_type=EventType.EVENT_DEDUPLICATED,
                payload={"original_sequence": self._sequence_counter},
                metadata={"action": "duplicate_dropped"},
            )
            self._events.append(dedup_event)
            return dedup_event

        # Check for stale (shouldn't normally happen with monotonically increasing)
        if self._dedup.is_stale(self.task_id, self._sequence_counter):
            self._dedup.record(self.task_id, self._sequence_counter)
            logger.warning(
                f"Stale event detected: seq={self._sequence_counter} for task {self.task_id}"
            )
            stale_event = AgentEvent(
                task_id=self.task_id,
                sequence=self._sequence_counter,
                event_type=EventType.EVENT_STALE_IGNORED,
                payload={"original_sequence": self._sequence_counter},
                metadata={"action": "stale_ignored"},
            )
            self._events.append(stale_event)
            return stale_event

        # Record and store
        self._dedup.record(self.task_id, self._sequence_counter)
        self._events.append(event)
        return event

    def get_events(
        self,
        event_type: Optional[EventType] = None,
        limit: int = None,
    ) -> List[AgentEvent]:
        """Get events, optionally filtered by type."""
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if limit:
            events = events[-limit:]
        return events

    def get_latest_sequence(self) -> int:
        """Get the latest sequence number."""
        return self._sequence_counter

    def get_event_counts_by_type(self) -> Dict[str, int]:
        """Count events by type."""
        counts: Dict[str, int] = {}
        for e in self._events:
            counts[e.event_type.value] = counts.get(e.event_type.value, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "sequence_counter": self._sequence_counter,
            "event_count": len(self._events),
            "events_by_type": self.get_event_counts_by_type(),
            "events": [e.to_dict() for e in self._events],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        stream = cls(task_id=data.get("task_id", ""))
        stream._sequence_counter = data.get("sequence_counter", 0)
        stream._events = [
            AgentEvent.from_dict(e) for e in data.get("events", [])
        ]
        return stream


# Global event stream registry (per-task)
_event_streams: Dict[str, EventStream] = {}
_event_streams_lock = asyncio.Lock()


async def get_event_stream(task_id: str) -> EventStream:
    """Get or create an event stream for a task."""
    async with _event_streams_lock:
        if task_id not in _event_streams:
            _event_streams[task_id] = EventStream(task_id=task_id)
        return _event_streams[task_id]


async def clear_event_stream(task_id: str) -> None:
    """Clear an event stream."""
    async with _event_streams_lock:
        _event_streams.pop(task_id, None)


__all__ = [
    "AgentEvent",
    "EventType",
    "EventDedupTracker",
    "EventStream",
    "get_event_stream",
    "clear_event_stream",
]