from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    AgentMessage, CollaborationSession, AgentInstance,
)

logger = logging.getLogger(__name__)


class CollaborationManager:
    def __init__(self):
        self._sessions: dict[str, CollaborationSession] = {}
        self._message_queues: dict[str, asyncio.Queue] = {}

    async def create_session(
        self,
        plan_id: str,
        agent_ids: list[str],
    ) -> CollaborationSession:
        session = CollaborationSession(
            id=f"collab_{uuid.uuid4().hex[:12]}",
            plan_id=plan_id,
            agents=agent_ids,
            status="active",
        )
        self._sessions[session.id] = session
        for agent_id in agent_ids:
            self._message_queues[f"{session.id}:{agent_id}"] = asyncio.Queue()
        logger.info(
            "Collaboration session %s created with %d agents",
            session.id, len(agent_ids),
        )
        return session

    async def send_message(self, message: AgentMessage) -> bool:
        session = self._sessions.get(message.correlation_id) if message.correlation_id else None
        if session:
            session.messages.append(message)
        queue_key = f"{message.correlation_id}:{message.recipient_id}" if message.correlation_id else ""
        queue = self._message_queues.get(queue_key)
        if queue:
            await queue.put(message)
            return True
        if session:
            for agent_id in session.agents:
                if agent_id != message.sender_id:
                    q = self._message_queues.get(f"{session.id}:{agent_id}")
                    if q:
                        await q.put(message)
            return True
        return False

    async def broadcast(self, session_id: str, message: AgentMessage):
        session = self._sessions.get(session_id)
        if not session:
            return
        for agent_id in session.agents:
            msg = AgentMessage(
                sender_id=message.sender_id,
                recipient_id=agent_id,
                message_type=message.message_type,
                content=message.content,
                data=message.data,
                task_id=message.task_id,
                correlation_id=session_id,
            )
            session.messages.append(msg)
            queue = self._message_queues.get(f"{session_id}:{agent_id}")
            if queue:
                await queue.put(msg)

    async def receive_message(
        self, session_id: str, agent_id: str, timeout: float = 30.0
    ) -> Optional[AgentMessage]:
        queue_key = f"{session_id}:{agent_id}"
        queue = self._message_queues.get(queue_key)
        if not queue:
            return None
        try:
            message = await asyncio.wait_for(queue.get(), timeout=timeout)
            return message
        except asyncio.TimeoutError:
            return None

    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        return self._sessions.get(session_id)

    def get_session_messages(
        self, session_id: str, limit: int = 100
    ) -> list[AgentMessage]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        return session.messages[-limit:]

    async def close_session(self, session_id: str):
        session = self._sessions.get(session_id)
        if session:
            session.status = "completed"
            session.completed_at = time.time()
            for agent_id in session.agents:
                key = f"{session_id}:{agent_id}"
                self._message_queues.pop(key, None)
            logger.info("Collaboration session %s closed", session_id)

    def get_active_sessions(self) -> list[CollaborationSession]:
        return [
            s for s in self._sessions.values() if s.status == "active"
        ]

    async def transfer_result(
        self,
        from_agent_id: str,
        to_agent_id: str,
        data: dict,
        session_id: str = "",
    ) -> bool:
        message = AgentMessage(
            sender_id=from_agent_id,
            recipient_id=to_agent_id,
            message_type="result",
            content="Task result transfer",
            data=data,
            correlation_id=session_id or "",
        )
        return await self.send_message(message)

    def get_stats(self) -> dict:
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len(self.get_active_sessions()),
            "total_messages": sum(
                len(s.messages) for s in self._sessions.values()
            ),
        }
