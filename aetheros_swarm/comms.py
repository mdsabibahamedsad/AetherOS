"""Typed agent communication: sequenced bus, blackboard, handoff, A2A layer.

- MessageBus: in-process, per-run, sequence-numbered (event ordering),
  TTL-expiry, subscribe/drain. Agent output is DATA (never authority).
- AgentBlackboard: shared facts/status/artifacts/evidence/decisions with
  mandatory provenance (source agent/task/timestamp/confidence).
- build_handoff(): structured handoff payload preserving facts, numbers,
  constraints, citations, uncertainty (no lossy summarization).
- A2A: provider-neutral discover/delegate/send/receive/handoff/subscribe/
  cancel over the bus + registry.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

from aetheros_swarm.models import AgentMessage, MsgType


class MessageBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq = 0
        self._log: List[AgentMessage] = []
        self._subs: Dict[str, List[Callable[[AgentMessage], None]]] = defaultdict(list)

    def send(self, msg: AgentMessage) -> AgentMessage:
        with self._lock:
            self._seq += 1
            msg.seq = self._seq
            if not msg.timestamp:
                msg.timestamp = time.time()
            self._log.append(msg)
            subs = list(self._subs.get(msg.recipient, [])) + list(self._subs.get("*", []))
        for fn in subs:
            try:
                fn(msg)
            except Exception:
                continue
        return msg

    def subscribe(self, recipient: str, fn: Callable[[AgentMessage], None]) -> None:
        with self._lock:
            self._subs[recipient].append(fn)

    def history(self, *, task_id: str = "", agent_id: str = "",
                limit: int = 200) -> List[AgentMessage]:
        with self._lock:
            out = [m for m in self._log
                   if (not task_id or m.task_id == task_id)
                   and (not agent_id or m.sender == agent_id or m.recipient == agent_id)]
            return out[-limit:]

    def prune_expired(self, now: Optional[float] = None) -> int:
        now = now if now is not None else time.time()
        with self._lock:
            before = len(self._log)
            self._log = [m for m in self._log if m.timestamp + m.ttl_s > now]
            return before - len(self._log)


@dataclass
class BlackboardEntry:
    key: str
    value: Any
    source_agent: str = ""
    source_task: str = ""
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)
    kind: str = "fact"  # fact|status|artifact|evidence|decision|constraint|question


class AgentBlackboard:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: Dict[str, BlackboardEntry] = {}

    def put(self, entry: BlackboardEntry) -> None:
        if not entry.source_agent:
            raise ValueError("blackboard entries require provenance (source_agent)")
        with self._lock:
            self._entries[entry.key] = entry

    def get(self, key: str) -> Optional[BlackboardEntry]:
        with self._lock:
            return self._entries.get(key)

    def list(self, *, kind: str = "") -> List[BlackboardEntry]:
        with self._lock:
            return [e for e in self._entries.values() if not kind or e.kind == kind]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {k: {"value": e.value, "source_agent": e.source_agent,
                        "source_task": e.source_task, "confidence": e.confidence,
                        "timestamp": e.timestamp, "kind": e.kind}
                    for k, e in self._entries.items()}


def build_handoff(*, task_state: Dict[str, Any], completed: List[str],
                  remaining: List[str], findings: List[str],
                  failed_attempts: List[str], artifacts: List[str],
                  evidence: List[Dict[str, Any]], risks: List[str],
                  next_action: str) -> Dict[str, Any]:
    """Structured handoff — preserves facts/numbers/citations/uncertainty."""
    return {"task_state": task_state, "completed_work": completed,
            "remaining_work": remaining, "important_findings": findings,
            "failed_attempts": failed_attempts, "artifacts": artifacts,
            "evidence": evidence, "known_risks": risks,
            "next_action": next_action, "handed_at": time.time()}


class A2ALayer:
    """Provider-neutral agent-to-agent protocol over bus + registry."""

    def __init__(self, bus: MessageBus, resolve_agent=None) -> None:
        self._bus = bus
        self._resolve = resolve_agent
        self._directory: Dict[str, Dict[str, Any]] = {}

    def advertise(self, agent_id: str, capabilities: List[str]) -> None:
        self._directory[agent_id] = {"capabilities": capabilities, "at": time.time()}

    def discover(self, capability: str = "") -> List[str]:
        if not capability:
            return sorted(self._directory)
        return sorted(aid for aid, info in self._directory.items()
                      if capability in info["capabilities"])

    def delegate(self, sender: str, recipient: str, task_id: str,
                 content: str, **kw) -> AgentMessage:
        return self._bus.send(AgentMessage(
            sender=sender, recipient=recipient, message_type=MsgType.TASK,
            task_id=task_id, content=content,
            correlation_id=kw.get("correlation_id", ""),
            artifacts=kw.get("artifacts", []), evidence=kw.get("evidence", [])))

    def send(self, sender: str, recipient: str, mtype: MsgType,
             content: str, **kw) -> AgentMessage:
        return self._bus.send(AgentMessage(
            sender=sender, recipient=recipient, message_type=mtype,
            task_id=kw.get("task_id", ""), content=content,
            correlation_id=kw.get("correlation_id", ""),
            artifacts=kw.get("artifacts", []), evidence=kw.get("evidence", [])))

    def handoff(self, sender: str, recipient: str, task_id: str,
                payload: Dict[str, Any]) -> AgentMessage:
        import json
        return self._bus.send(AgentMessage(
            sender=sender, recipient=recipient, message_type=MsgType.HANDOFF,
            task_id=task_id, content=json.dumps(payload, ensure_ascii=False)[:8000]))

    def subscribe(self, agent_id: str, fn) -> None:
        self._bus.subscribe(agent_id, fn)

    def cancel(self, sender: str, recipient: str, task_id: str,
               reason: str = "") -> AgentMessage:
        return self.send(sender, recipient, MsgType.CANCEL, reason or "cancelled",
                         task_id=task_id)
