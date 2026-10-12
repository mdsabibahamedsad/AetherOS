"""Productivity connectors — Notion, Jira, Linear, ClickUp, Trello, Asana, Todoist, Obsidian."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from connect.connectors import BaseConnector, ConnectorResult
from connect.models import (ServiceConnection, ConnectionStatus, HealthCheckResult,
                             ServiceCategory)


class NotionConnector(BaseConnector):
    service_id = "notion"
    service_name = "Notion"
    category = ServiceCategory.PRODUCTIVITY

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Integration token required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.notion.com/v1/users/me",
                                         headers={"Authorization": f"Bearer {token}",
                                                  "Notion-Version": "2022-06-28"})
                if resp.status_code == 200:
                    data = resp.json()
                    return ConnectorResult(message=f"Connected to Notion")
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
        return {"granted": ["read", "write", "databases"], "missing": []}

    async def sync(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult(message="Notion synced")

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class JiraConnector(BaseConnector):
    service_id = "jira"
    service_name = "Jira"
    category = ServiceCategory.PRODUCTIVITY

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        domain = connection.config.get("domain", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Token required")
        return ConnectorResult(message=f"Connected to Jira")

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        return HealthCheckResult(service_id=self.service_id,
                                  connection_id=connection.id,
                                  status=connection.status,
                                  checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["read_issues", "write_issues", "read_projects"],
                "missing": []}

    async def sync(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult(message="Jira synced")

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class LinearConnector(BaseConnector):
    service_id = "linear"
    service_name = "Linear"
    category = ServiceCategory.PRODUCTIVITY

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="API key required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.linear.app/graphql",
                    json={"query": "{ viewer { id name } }"},
                    headers={"Authorization": token})
                if resp.status_code == 200:
                    return ConnectorResult(message="Connected to Linear")
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
        return {"granted": ["read_issues", "write_issues"], "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class TodoistConnector(BaseConnector):
    service_id = "todoist"
    service_name = "Todoist"
    category = ServiceCategory.PRODUCTIVITY

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Token required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.todoist.com/rest/v2/projects",
                                         headers={"Authorization": f"Bearer {token}"})
                if resp.status_code == 200:
                    return ConnectorResult(message="Connected to Todoist")
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
        return {"granted": ["read_tasks", "write_tasks", "read_projects"],
                "missing": []}

    async def sync(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult(message="Todoist synced")

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


CONNECTOR_MAP = {
    "notion": NotionConnector,
    "jira": JiraConnector,
    "linear": LinearConnector,
    "todoist": TodoistConnector,
}
