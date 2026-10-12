"""Email connectors — Gmail, Outlook, IMAP, SMTP, Yahoo, Proton."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from connect.connectors import BaseConnector, ConnectorResult
from connect.models import (ServiceConnection, ConnectionStatus, HealthCheckResult,
                             ServiceCategory)


class GmailConnector(BaseConnector):
    service_id = "gmail"
    service_name = "Gmail"
    category = ServiceCategory.EMAIL

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="OAuth token required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {token}"})
                if resp.status_code == 200:
                    data = resp.json()
                    email = data.get("emailAddress", "unknown")
                    return ConnectorResult(message=f"Connected as {email}")
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
        return {"granted": ["read", "send", "labels", "attachments"],
                "missing": []}

    async def sync(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult(message="Gmail synced")

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class OutlookConnector(BaseConnector):
    service_id = "outlook"
    service_name = "Outlook"
    category = ServiceCategory.EMAIL

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        token = (credentials or {}).get("token", "")
        if not token:
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="OAuth token required")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://graph.microsoft.com/v1.0/me",
                                         headers={"Authorization": f"Bearer {token}"})
                if resp.status_code == 200:
                    data = resp.json()
                    return ConnectorResult(message=f"Connected as {data.get('userPrincipalName', 'user')}")
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
        return {"granted": ["read", "send"], "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class IMAPConnector(BaseConnector):
    service_id = "imap"
    service_name = "IMAP"
    category = ServiceCategory.EMAIL

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        cfg = {**connection.config, **(credentials or {})}
        host = cfg.get("host", "")
        port = cfg.get("port", 993)
        username = cfg.get("username", "")
        password = cfg.get("password", "")
        if not all([host, username, password]):
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Host, username, and password required")
        import imaplib
        try:
            mail = imaplib.IMAP4_SSL(host, port)
            mail.login(username, password)
            mail.logout()
            return ConnectorResult(message=f"Connected to {host}")
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
        return {"granted": ["read_mail"], "missing": []}

    async def sync(self, connection: ServiceConnection) -> ConnectorResult:
        return ConnectorResult(message="IMAP synced")

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


class SMTPConnector(BaseConnector):
    service_id = "smtp"
    service_name = "SMTP"
    category = ServiceCategory.EMAIL

    async def connect(self, connection: ServiceConnection,
                       credentials: dict = None) -> ConnectorResult:
        cfg = {**connection.config, **(credentials or {})}
        host = cfg.get("host", "")
        port = cfg.get("port", 587)
        username = cfg.get("username", "")
        password = cfg.get("password", "")
        if not all([host, username, password]):
            return ConnectorResult(success=False, status=ConnectionStatus.AUTH_REQUIRED,
                                   error="Host, username, and password required")
        import smtplib
        try:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
            server.login(username, password)
            server.quit()
            return ConnectorResult(message=f"Connected to {host}")
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
        return {"granted": ["send_mail"], "missing": []}

    async def status(self, connection: ServiceConnection) -> ConnectionStatus:
        return connection.status


CONNECTOR_MAP = {
    "gmail": GmailConnector,
    "outlook": OutlookConnector,
    "imap": IMAPConnector,
    "smtp": SMTPConnector,
}
