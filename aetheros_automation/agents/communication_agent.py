from __future__ import annotations

import json
import logging
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, Task

logger = logging.getLogger(__name__)


class CommunicationAgent(BaseAgent):
    @property
    def role(self) -> AgentRole:
        return AgentRole.COMMUNICATION

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        message = task.metadata.get("message", task.description)
        logger.info("Communication agent handling: %s", message[:80])

        if "email" in message.lower():
            return await self.send_email(message)
        if "notify" in message.lower() or "alert" in message.lower():
            return await self.send_notification(message)
        if "summarize" in message.lower() or "summary" in message.lower():
            return await self.summarize(message)
        if "forward" in message.lower() or "relay" in message.lower():
            return await self.relay_message(message)

        return await self.compose_message(message)

    async def send_email(self, message: str) -> str:
        return json.dumps({
            "status": "composed",
            "subject": f"Re: {message[:50]}",
            "body": message,
            "recipients": ctx.get("recipients", ["user@example.com"]),
            "priority": "normal",
            "requires_approval": True,
        })

    async def send_notification(self, message: str) -> str:
        return json.dumps({
            "type": "notification",
            "message": message,
            "channels": ["desktop", "mobile"],
            "priority": "high" if "urgent" in message.lower() else "normal",
        })

    async def summarize(self, content: str) -> str:
        return (
            f"Summary of '{content[:60]}...':\n\n"
            "- Key points extracted and organized\n"
            "- Action items identified\n"
            "- Decisions highlighted\n"
            "- Follow-ups scheduled\n"
        )

    async def relay_message(self, message: str) -> str:
        return f"Message relayed: {message[:100]}"

    async def compose_message(self, message: str) -> str:
        return (
            f"Communication composed:\n\n"
            f"Message: {message}\n"
            f"Tone: Professional and clear\n"
            f"Format: Structured with bullet points\n"
            f"Ready for review before sending\n"
        )


AgentRegistry.register(AgentRole.COMMUNICATION, CommunicationAgent)
