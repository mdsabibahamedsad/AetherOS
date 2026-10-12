"""Communication connectors — Telegram, Discord, Slack, Teams, WhatsApp."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from connect.connectors import BaseConnector, ConnectorResult
from connect.models import (ServiceConnection, ConnectionStatus, HealthCheckResult,
                             ActivityEntry, ServiceCategory)


class TelegramBotConnector(BaseConnector):
    service_id = "telegram_bot"
    service_name = "Telegram Bot"
    category = ServiceCategory.COMMUNICATION

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Bot token required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        username = data["result"].get("username", "unknown")
                        return ConnectorResult(message=f"Connected as @{username}",
                                               data={"username": username})
                return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                       error="Invalid token")
        except Exception as e:
            return ConnectorResult(success=False, status=ConnectionStatus.ERROR,
                                   error=str(e))

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        return HealthCheckResult(service_id=self.service_id,
                                  connection_id=connection.id,
                                  status=connection.status,
                                  checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["send_messages", "receive_messages"],
                "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class DiscordConnector(BaseConnector):
    service_id = "discord"
    service_name = "Discord"
    category = ServiceCategory.COMMUNICATION

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Bot token required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://discord.com/api/v10/users/@me",
                                         headers={"Authorization": f"Bot {token}"})
                if resp.status_code == 200:
                    data = resp.json()
                    return ConnectorResult(message=f"Connected as {data.get('username', 'bot')}")
                return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                       error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ConnectorResult(success=False, status=ConnectionStatus.ERROR, error=str(e))

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        return HealthCheckResult(service_id=self.service_id,
                                  connection_id=connection.id,
                                  status=connection.status,
                                  checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["send_messages", "read_messages", "manage_channels"],
                "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class SlackConnector(BaseConnector):
    service_id = "slack"
    service_name = "Slack"
    category = ServiceCategory.COMMUNICATION

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Token required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://slack.com/api/auth.test",
                                         headers={"Authorization": f"Bearer {token}"})
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        return ConnectorResult(message=f"Connected to {data.get('team', 'Slack')}")
                return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                       error="Auth failed")
        except Exception as e:
            return ConnectorResult(success=False, status=ConnectionStatus.ERROR, error=str(e))

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        return HealthCheckResult(service_id=self.service_id,
                                  connection_id=connection.id,
                                  status=connection.status,
                                  checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["send_messages", "channels:read", "files:write"],
                "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class TeamsConnector(BaseConnector):
    service_id = "teams"
    service_name = "Microsoft Teams"
    category = ServiceCategory.COMMUNICATION

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        return ConnectorResult(status=ConnectionStatus.CONNECTED,
                               message="Teams connected (mock)")

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        return HealthCheckResult(service_id=self.service_id,
                                  connection_id=connection.id,
                                  status=connection.status,
                                  checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["send_messages", "read_channels"], "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class WhatsAppConnector(BaseConnector):
    service_id = "whatsapp"
    service_name = "WhatsApp Business"
    category = ServiceCategory.COMMUNICATION

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Token required")
        return ConnectorResult(message="WhatsApp connected")

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        return HealthCheckResult(service_id=self.service_id,
                                  connection_id=connection.id,
                                  status=connection.status,
                                  checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["send_messages", "read_messages"], "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


CONNECTOR_MAP = {
    "telegram_bot": TelegramBotConnector,
    "telegram_personal": TelegramBotConnector,
    "discord": DiscordConnector,
    "slack": SlackConnector,
    "teams": TeamsConnector,
    "whatsapp": WhatsAppConnector,
}
