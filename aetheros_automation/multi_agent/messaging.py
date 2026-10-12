from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from aetheros_automation.orchestrator.types import AgentMessage

logger = logging.getLogger(__name__)


class AgentMessaging:
    def __init__(self):
        self._messages: list[AgentMessage] = []
        self._queues: dict[str, asyncio.Queue] = {}
        self._max_messages = 10000

    async def send(
        self,
        sender_id: str,
        receiver_id: str,
        content: str = "",
        msg_type: str = "text",
        data: Any = None,
        task_id: str = "",
    ) -> AgentMessage:
        msg = AgentMessage(
            id=uuid.uuid4().hex[:12],
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=msg_type,
            content=content,
            data=data,
            task_id=task_id,
            created_at=time.time(),
        )
        self._messages.append(msg)

        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]

        if receiver_id in self._queues:
            await self._queues[receiver_id].put(msg)

        return msg

    async def receive(self, agent_id: str, timeout: float = 30.0) -> AgentMessage | None:
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue()
        try:
            return await asyncio.wait_for(
                self._queues[agent_id].get(), timeout=timeout
            )
        except asyncio.TimeoutError:
            return None

    async def send_and_wait(
        self,
        sender_id: str,
        receiver_id: str,
        content: str = "",
        msg_type: str = "text",
        data: Any = None,
        task_id: str = "",
        timeout: float = 60.0,
    ) -> AgentMessage | None:
        await self.send(sender_id, receiver_id, content, msg_type, data, task_id)
        return await self.receive(sender_id, timeout=timeout)

    def get_messages(
        self,
        agent_id: str | None = None,
        task_id: str | None = None,
        limit: int = 100,
    ) -> list[AgentMessage]:
        result = self._messages
        if agent_id:
            result = [m for m in result if m.receiver_id == agent_id or m.sender_id == agent_id]
        if task_id:
            result = [m for m in result if m.task_id == task_id]
        return result[-limit:]

    def get_conversation(
        self, agent_a: str, agent_b: str, limit: int = 100
    ) -> list[AgentMessage]:
        result = [
            m for m in self._messages
            if (m.sender_id == agent_a and m.receiver_id == agent_b)
            or (m.sender_id == agent_b and m.receiver_id == agent_a)
        ]
        return result[-limit:]

    def clear(self):
        self._messages.clear()
        self._queues.clear()

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_messages": len(self._messages),
            "active_queues": len(self._queues),
            "message_types": self._count_types(),
        }

    def _count_types(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for m in self._messages:
            counts[m.message_type] = counts.get(m.message_type, 0) + 1
        return counts
