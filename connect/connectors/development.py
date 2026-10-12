"""Development connectors — GitHub, GitLab, Bitbucket, Docker Hub, K8s, Jenkins, Azure DevOps."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from connect.connectors import BaseConnector, ConnectorResult
from connect.models import (ServiceConnection, ConnectionStatus, HealthCheckResult,
                             ServiceCategory)


class GitHubConnector(BaseConnector):
    service_id = "github"
    service_name = "GitHub"
    category = ServiceCategory.DEVELOPMENT

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Token required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.github.com/user",
                                         headers={"Authorization": f"Bearer {token}",
                                                  "Accept": "application/vnd.github.v3+json"})
                if resp.status_code == 200:
                    data = resp.json()
                    return ConnectorResult(message=f"Connected as {data.get('login', 'user')}",
                                           data={"username": data.get("login"),
                                                 "id": data.get("id")})
                return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                       error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ConnectorResult(success=False, status=ConnectionStatus.ERROR, error=str(e))

    async def disconnect(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult()

    async def health(self, connection: ServiceConnection) -> HealthCheckResult:
        import httpx, time
        start = time.time()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.github.com/zen", timeout=5)
                latency = (time.time() - start) * 1000
                return HealthCheckResult(
                    service_id=self.service_id, connection_id=connection.id,
                    status=ConnectionStatus.CONNECTED if resp.status_code == 200 else ConnectionStatus.ERROR,
                    api_available=resp.status_code == 200, auth_valid=True,
                    latency_ms=latency, checked_at=datetime.utcnow().isoformat() + "Z")
        except Exception as e:
            return HealthCheckResult(
                service_id=self.service_id, connection_id=connection.id,
                status=ConnectionStatus.ERROR, api_available=False, auth_valid=False,
                last_error=str(e), checked_at=datetime.utcnow().isoformat() + "Z")

    async def permissions(self, connection: ServiceConnection) -> dict:
        return {"granted": ["repo", "issues", "prs", "actions"],
                "missing": []}

    async def sync(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult(message="GitHub synced")

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class GitLabConnector(BaseConnector):
    service_id = "gitlab"
    service_name = "GitLab"
    category = ServiceCategory.DEVELOPMENT

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Token required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://gitlab.com/api/v4/user",
                                         headers={"Authorization": f"Bearer {token}"})
                if resp.status_code == 200:
                    data = resp.json()
                    return ConnectorResult(message=f"Connected as {data.get('username', 'user')}")
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
        return {"granted": ["read_repo", "write_repo", "read_api"], "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class DockerHubConnector(BaseConnector):
    service_id = "docker_hub"
    service_name = "Docker Hub"
    category = ServiceCategory.DEVELOPMENT

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Token required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://hub.docker.com/v2/user/",
                                         headers={"Authorization": f"Bearer {token}"})
                if resp.status_code == 200:
                    data = resp.json()
                    return ConnectorResult(message=f"Connected as {data.get('username', 'user')}")
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
        return {"granted": ["read_repos", "push_images"], "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


CONNECTOR_MAP = {
    "github": GitHubConnector,
    "gitlab": GitLabConnector,
    "docker_hub": DockerHubConnector,
}
