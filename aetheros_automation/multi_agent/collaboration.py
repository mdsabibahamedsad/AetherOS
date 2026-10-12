from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from aetheros_automation.models.models import AgentRole

logger = logging.getLogger(__name__)


class AgentCollaborationManager:
    def __init__(self):
        self._conversations: dict[str, dict[str, Any]] = {}
        self._shared_results: dict[str, dict[str, Any]] = {}
        self._active_collaborations: dict[str, list[str]] = {}

    async def start_collaboration(
        self,
        agent_ids: list[str],
        goal: str,
        coordinator_id: str | None = None,
    ) -> str:
        collab_id = uuid.uuid4().hex[:12]
        self._conversations[collab_id] = {
            "id": collab_id,
            "goal": goal,
            "participants": agent_ids,
            "coordinator": coordinator_id or agent_ids[0] if agent_ids else "",
            "messages": [],
            "status": "active",
            "created_at": time.time(),
        }
        for aid in agent_ids:
            self._active_collaborations.setdefault(aid, []).append(collab_id)
        logger.info(
            "Collaboration %s started with %d agents",
            collab_id, len(agent_ids),
        )
        return collab_id

    async def send_message(
        self,
        collab_id: str,
        sender_id: str,
        content: str,
        msg_type: str = "text",
        data: Any = None,
    ) -> dict[str, Any]:
        conv = self._conversations.get(collab_id)
        if not conv:
            raise ValueError(f"Collaboration {collab_id} not found")

        message = {
            "id": uuid.uuid4().hex[:12],
            "collaboration_id": collab_id,
            "sender_id": sender_id,
            "content": content,
            "type": msg_type,
            "data": data,
            "timestamp": time.time(),
        }
        conv["messages"].append(message)
        return message

    async def broadcast(
        self,
        collab_id: str,
        sender_id: str,
        content: str,
        msg_type: str = "broadcast",
    ) -> list[dict[str, Any]]:
        conv = self._conversations.get(collab_id)
        if not conv:
            raise ValueError(f"Collaboration {collab_id} not found")

        messages: list[dict[str, Any]] = []
        for participant_id in conv["participants"]:
            if participant_id != sender_id:
                msg = await self.send_message(
                    collab_id, sender_id, content, msg_type
                )
                messages.append(msg)
        return messages

    async def share_result(
        self,
        collab_id: str,
        agent_id: str,
        result_key: str,
        result_value: Any,
    ):
        if collab_id not in self._shared_results:
            self._shared_results[collab_id] = {}
        self._shared_results[collab_id][result_key] = {
            "agent_id": agent_id,
            "value": result_value,
            "timestamp": time.time(),
        }

    def get_shared_result(self, collab_id: str, result_key: str) -> Any | None:
        collab_results = self._shared_results.get(collab_id)
        if collab_results:
            entry = collab_results.get(result_key)
            return entry["value"] if entry else None
        return None

    def get_all_shared_results(self, collab_id: str) -> dict[str, Any]:
        return {
            k: v["value"]
            for k, v in self._shared_results.get(collab_id, {}).items()
        }

    def get_conversation(self, collab_id: str) -> dict[str, Any] | None:
        return self._conversations.get(collab_id)

    def get_conversation_messages(
        self, collab_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        conv = self._conversations.get(collab_id)
        if not conv:
            return []
        return conv["messages"][-limit:]

    async def end_collaboration(self, collab_id: str):
        conv = self._conversations.pop(collab_id, None)
        if conv:
            conv["status"] = "completed"
            for aid in conv["participants"]:
                if aid in self._active_collaborations:
                    try:
                        self._active_collaborations[aid].remove(collab_id)
                    except ValueError:
                        pass
            logger.info("Collaboration %s ended", collab_id)

    def get_active_collaborations(self, agent_id: str) -> list[str]:
        return list(self._active_collaborations.get(agent_id, []))

    def list_active_collaborations(self) -> list[dict[str, Any]]:
        return [
            c for c in self._conversations.values()
            if c["status"] == "active"
        ]
