"""
Inter-Agent Communication — shared memory, message bus, event channels, context exchange.

Provides infrastructure for agents to communicate, share state, hand off tasks,
and resolve conflicts during multi-agent execution.

Architecture:
  MessageBus     — Point-to-point and broadcast message delivery
  SharedMemory   — Namespaced key-value store for cross-agent state
  EventChannel   — Pub/sub channels for progress updates and notifications
  TaskHandoff    — Structured task transfer between agents
  ConflictResolver — Detect and resolve inter-agent conflicts
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from kernel.event_bus import EventBus, Event, EventPriority

logger = logging.getLogger(__name__)


class MessagePriority(enum.IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class MessageType(enum.Enum):
    DIRECT = "direct"
    BROADCAST = "broadcast"
    TASK_HANDOFF = "task_handoff"
    PROGRESS = "progress"
    RESULT = "result"
    ERROR = "error"
    COORDINATION = "coordination"
    QUERY = "query"
    RESPONSE = "response"


@dataclass
class AgentMessage:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    type: MessageType = MessageType.DIRECT
    sender: str = ""
    recipient: str = ""
    topic: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    ttl_seconds: Optional[float] = None
    correlation_id: str = ""
    requires_ack: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return time.time() - self.timestamp > self.ttl_seconds


@dataclass
class SharedMemoryEntry:
    key: str = ""
    value: Any = None
    namespace: str = "global"
    owner: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    ttl_seconds: Optional[float] = None
    read_permission: Set[str] = field(default_factory=lambda: {"*"})
    write_permission: Set[str] = field(default_factory=lambda: {"*"})

    @property
    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return time.time() - self.updated_at > self.ttl_seconds


@dataclass
class TaskHandoff:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    source_agent: str = ""
    target_agent: str = ""
    task_id: str = ""
    goal: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    accepted_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None


class InterAgentBus:
    """Central communication hub for inter-agent messaging.

    Agents can:
      - Send direct messages to specific agents
      - Broadcast to all agents or subscribed groups
      - Publish/subscribe to event channels
      - Share and read shared memory
      - Hand off tasks to other agents
      - Resolve conflicts
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._messages: Dict[str, AgentMessage] = {}
        self._inboxes: Dict[str, List[str]] = {}
        self._subscriptions: Dict[str, List[Tuple[str, Callable[[AgentMessage], None]]]] = {}
        self._shared_memory: Dict[str, SharedMemoryEntry] = {}
        self._handoffs: Dict[str, TaskHandoff] = {}
        self._conflicts: List[Dict[str, Any]] = []
        self._dead_letter: List[AgentMessage] = []
        self._agent_registry: Set[str] = set()
        self._shutdown_flag = False

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str) -> None:
        with self._lock:
            self._agent_registry.add(agent_id)
            self._inboxes.setdefault(agent_id, [])
        logger.debug("InterAgentBus: registered agent '%s'", agent_id)

    def unregister_agent(self, agent_id: str) -> None:
        with self._lock:
            self._agent_registry.discard(agent_id)
            self._inboxes.pop(agent_id, None)
            for subs in self._subscriptions.values():
                subs[:] = [(a, cb) for a, cb in subs if a != agent_id]
        logger.debug("InterAgentBus: unregistered agent '%s'", agent_id)

    def list_agents(self) -> List[str]:
        with self._lock:
            return sorted(self._agent_registry)

    # ------------------------------------------------------------------
    # Message sending
    # ------------------------------------------------------------------

    def send(self, message: AgentMessage) -> bool:
        if self._shutdown_flag:
            return False

        with self._lock:
            self._messages[message.id] = message

        if message.type == MessageType.BROADCAST:
            return self._broadcast(message)
        elif message.recipient:
            return self._deliver(message)
        else:
            logger.warning("InterAgentBus: message %s has no recipient", message.id)
            return False

    def _deliver(self, message: AgentMessage) -> bool:
        with self._lock:
            inbox = self._inboxes.get(message.recipient)
            if inbox is None:
                self._dead_letter.append(message)
                logger.warning(
                    "InterAgentBus: no inbox for '%s', message %s dead-lettered",
                    message.recipient, message.id,
                )
                return False
            inbox.append(message.id)

        self._notify_subscribers(message)

        if self._event_bus:
            self._event_bus.emit_async("interagent.message_delivered", {
                "message_id": message.id,
                "sender": message.sender,
                "recipient": message.recipient,
                "type": message.type.value,
            })
        return True

    def _broadcast(self, message: AgentMessage) -> bool:
        delivered = 0
        with self._lock:
            for agent_id in self._agent_registry:
                if agent_id != message.sender:
                    self._inboxes[agent_id].append(message.id)
                    delivered += 1
        self._notify_subscribers(message)

        if self._event_bus:
            self._event_bus.emit_async("interagent.broadcast", {
                "message_id": message.id,
                "sender": message.sender,
                "recipient_count": delivered,
            })
        return delivered > 0

    def reply(self, original: AgentMessage, payload: Dict[str, Any],
              sender: str) -> AgentMessage:
        reply = AgentMessage(
            type=MessageType.RESPONSE,
            sender=sender,
            recipient=original.sender,
            payload=payload,
            correlation_id=original.id,
        )
        self.send(reply)
        return reply

    # ------------------------------------------------------------------
    # Message receiving
    # ------------------------------------------------------------------

    def receive(self, agent_id: str, limit: int = 10) -> List[AgentMessage]:
        with self._lock:
            msg_ids = self._inboxes.get(agent_id, [])
            if not msg_ids:
                return []
            batch = msg_ids[:limit]
            self._inboxes[agent_id] = msg_ids[limit:]
            messages = [
                self._messages[msg_id]
                for msg_id in batch
                if msg_id in self._messages
            ]
        return messages

    def peek(self, agent_id: str, limit: int = 10) -> List[AgentMessage]:
        with self._lock:
            msg_ids = self._inboxes.get(agent_id, [])[:limit]
            return [
                self._messages[msg_id]
                for msg_id in msg_ids
                if msg_id in self._messages
            ]

    def ack(self, message_id: str) -> bool:
        with self._lock:
            msg = self._messages.get(message_id)
            if msg is None:
                return False
            msg.metadata["acked"] = True
            msg.metadata["acked_at"] = time.time()
        return True

    # ------------------------------------------------------------------
    # Pub/sub channels
    # ------------------------------------------------------------------

    def subscribe(self, channel: str, agent_id: str,
                  callback: Callable[[AgentMessage], None]) -> None:
        with self._lock:
            self._subscriptions.setdefault(channel, []).append((agent_id, callback))

    def unsubscribe(self, channel: str, agent_id: str) -> None:
        with self._lock:
            subs = self._subscriptions.get(channel, [])
            subs[:] = [(a, cb) for a, cb in subs if a != agent_id]

    def publish(self, channel: str, message: AgentMessage) -> int:
        delivered = 0
        with self._lock:
            subs = list(self._subscriptions.get(channel, []))
        for agent_id, callback in subs:
            try:
                callback(message)
                delivered += 1
            except Exception as exc:
                logger.error("InterAgentBus: channel %s callback for %s failed: %s",
                             channel, agent_id, exc)
        return delivered

    def _notify_subscribers(self, message: AgentMessage) -> None:
        for channel in (message.topic, message.type.value, "*"):
            with self._lock:
                subs = list(self._subscriptions.get(channel, []))
            for agent_id, callback in subs:
                try:
                    callback(message)
                except Exception as exc:
                    logger.error("InterAgentBus: subscriber %s failed on %s: %s",
                                 agent_id, channel, exc)

    # ------------------------------------------------------------------
    # Shared memory
    # ------------------------------------------------------------------

    def memory_set(self, key: str, value: Any, namespace: str = "global",
                   owner: str = "", ttl_seconds: Optional[float] = None,
                   read_permission: Optional[Set[str]] = None,
                   write_permission: Optional[Set[str]] = None) -> None:
        ns_key = f"{namespace}:{key}"
        with self._lock:
            entry = self._shared_memory.get(ns_key)
            if entry:
                entry.value = value
                entry.updated_at = time.time()
                entry.owner = owner or entry.owner
                if ttl_seconds is not None:
                    entry.ttl_seconds = ttl_seconds
            else:
                entry = SharedMemoryEntry(
                    key=ns_key, value=value, namespace=namespace,
                    owner=owner, ttl_seconds=ttl_seconds,
                    read_permission=read_permission or {"*"},
                    write_permission=write_permission or {"*"},
                )
                self._shared_memory[ns_key] = entry

        if self._event_bus:
            self._event_bus.emit_async("interagent.memory_updated", {
                "key": ns_key, "namespace": namespace, "owner": owner,
            })

    def memory_get(self, key: str, namespace: str = "global",
                   agent_id: str = "") -> Any:
        ns_key = f"{namespace}:{key}"
        with self._lock:
            entry = self._shared_memory.get(ns_key)
            if entry is None or entry.is_expired:
                return None
            if not self._check_permission(entry.read_permission, agent_id):
                return None
            return entry.value

    def memory_delete(self, key: str, namespace: str = "global",
                      agent_id: str = "") -> bool:
        ns_key = f"{namespace}:{key}"
        with self._lock:
            entry = self._shared_memory.get(ns_key)
            if entry is None:
                return False
            if not self._check_permission(entry.write_permission, agent_id):
                return False
            del self._shared_memory[ns_key]
        return True

    def memory_list(self, namespace: str = "", agent_id: str = "") -> List[str]:
        with self._lock:
            if namespace:
                prefix = f"{namespace}:"
                return [
                    k for k, v in self._shared_memory.items()
                    if k.startswith(prefix)
                    and self._check_permission(v.read_permission, agent_id)
                ]
            return list(self._shared_memory.keys())

    def memory_find(self, query: Dict[str, Any], namespace: str = "") -> List[SharedMemoryEntry]:
        results = []
        with self._lock:
            for key, entry in self._shared_memory.items():
                if namespace and not key.startswith(f"{namespace}:"):
                    continue
                matches = all(
                    isinstance(entry.value, dict) and entry.value.get(k) == v
                    for k, v in query.items()
                )
                if matches:
                    results.append(entry)
        return results

    @staticmethod
    def _check_permission(permissions: Set[str], agent_id: str) -> bool:
        if "*" in permissions:
            return True
        if not agent_id:
            return False
        return agent_id in permissions

    # ------------------------------------------------------------------
    # Task handoff
    # ------------------------------------------------------------------

    def handoff_task(self, source_agent: str, target_agent: str,
                     goal: str, context: Dict[str, Any] = None,
                     task_id: str = "") -> TaskHandoff:
        handoff = TaskHandoff(
            source_agent=source_agent,
            target_agent=target_agent,
            task_id=task_id or uuid.uuid4().hex[:16],
            goal=goal,
            context=context or {},
        )
        with self._lock:
            self._handoffs[handoff.id] = handoff

        msg = AgentMessage(
            type=MessageType.TASK_HANDOFF,
            sender=source_agent,
            recipient=target_agent,
            payload={
                "handoff_id": handoff.id,
                "task_id": handoff.task_id,
                "goal": goal,
                "context": context or {},
            },
            priority=MessagePriority.HIGH,
        )
        self.send(msg)

        if self._event_bus:
            self._event_bus.emit_async("interagent.handoff_created", {
                "handoff_id": handoff.id,
                "source": source_agent,
                "target": target_agent,
                "goal": goal[:80],
            })
        return handoff

    def accept_handoff(self, handoff_id: str, agent_id: str) -> bool:
        with self._lock:
            handoff = self._handoffs.get(handoff_id)
            if handoff is None or handoff.status != "pending":
                return False
            if handoff.target_agent != agent_id:
                return False
            handoff.status = "accepted"
            handoff.accepted_at = time.time()
        return True

    def complete_handoff(self, handoff_id: str, result: Any) -> bool:
        with self._lock:
            handoff = self._handoffs.get(handoff_id)
            if handoff is None:
                return False
            handoff.status = "completed"
            handoff.completed_at = time.time()
            handoff.result = result
        return True

    def fail_handoff(self, handoff_id: str, error: str) -> bool:
        with self._lock:
            handoff = self._handoffs.get(handoff_id)
            if handoff is None:
                return False
            handoff.status = "failed"
            handoff.completed_at = time.time()
            handoff.error = error
        return True

    def get_handoff(self, handoff_id: str) -> Optional[TaskHandoff]:
        with self._lock:
            return self._handoffs.get(handoff_id)

    def list_handoffs(self, agent_id: str = "") -> List[TaskHandoff]:
        with self._lock:
            if agent_id:
                return [
                    h for h in self._handoffs.values()
                    if h.source_agent == agent_id or h.target_agent == agent_id
                ]
            return list(self._handoffs.values())

    # ------------------------------------------------------------------
    # Conflict resolution
    # ------------------------------------------------------------------

    def report_conflict(self, agent_id: str, conflict_type: str,
                        description: str, agents_involved: List[str],
                        context: Dict[str, Any] = None) -> str:
        conflict_id = uuid.uuid4().hex[:12]
        conflict = {
            "id": conflict_id,
            "type": conflict_type,
            "description": description,
            "reported_by": agent_id,
            "agents_involved": agents_involved,
            "context": context or {},
            "status": "open",
            "created_at": time.time(),
            "resolved_at": None,
            "resolution": None,
        }
        with self._lock:
            self._conflicts.append(conflict)

        if self._event_bus:
            self._event_bus.emit_async("interagent.conflict_reported", conflict)
        return conflict_id

    def resolve_conflict(self, conflict_id: str, resolution: str,
                         resolved_by: str) -> bool:
        with self._lock:
            for c in self._conflicts:
                if c["id"] == conflict_id and c["status"] == "open":
                    c["status"] = "resolved"
                    c["resolution"] = resolution
                    c["resolved_at"] = time.time()
                    c["resolved_by"] = resolved_by
                    return True
        return False

    def list_conflicts(self, status: str = "") -> List[Dict[str, Any]]:
        with self._lock:
            if status:
                return [c for c in self._conflicts if c["status"] == status]
            return list(self._conflicts)

    # ------------------------------------------------------------------
    # Dead letter queue
    # ------------------------------------------------------------------

    def get_dead_letter_messages(self) -> List[AgentMessage]:
        with self._lock:
            return list(self._dead_letter)

    def replay_dead_letter(self, max_count: int = 10) -> int:
        replayed = 0
        with self._lock:
            batch = self._dead_letter[:max_count]
            self._dead_letter = self._dead_letter[max_count:]
        for msg in batch:
            if self.send(msg):
                replayed += 1
        return replayed

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        self._shutdown_flag = True
        with self._lock:
            self._inboxes.clear()
            self._subscriptions.clear()
            self._agent_registry.clear()
        logger.info("InterAgentBus: shutdown complete")

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "agents_registered": len(self._agent_registry),
                "messages_total": len(self._messages),
                "messages_in_flight": sum(len(v) for v in self._inboxes.values()),
                "dead_letter_count": len(self._dead_letter),
                "shared_memory_entries": len(self._shared_memory),
                "active_handoffs": len([h for h in self._handoffs.values() if h.status == "accepted"]),
                "open_conflicts": len([c for c in self._conflicts if c["status"] == "open"]),
                "subscriptions": sum(len(v) for v in self._subscriptions.values()),
            }