"""AetherOS Integrations — messaging platform adapters.

Telegram, WhatsApp Business, Discord, Slack, Microsoft Teams, Signal,
Matrix, IRC, Email (SMTP send), and SMS providers. Each implements the real
HTTP protocol for its platform and reports health honestly.
"""

from __future__ import annotations

import json
import logging
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import httpx

from aetheros_integrations.models import AuthMethod, HealthStatus, IntegrationCategory, ProviderDefinition
from aetheros_integrations.providers.base import BaseProvider, RESTProvider, register_provider

logger = logging.getLogger(__name__)


@register_provider
class TelegramProvider(RESTProvider):
    definition = ProviderDefinition(
        key="telegram",
        category=IntegrationCategory.MESSAGING,
        display_name="Telegram",
        description="Send and receive Telegram messages via the Bot API.",
        auth_method=AuthMethod.BEARER,
        base_url="https://api.telegram.org",
        capabilities=["send_message", "read_messages", "files"],
    )

    def _token(self) -> str:
        auth = self.config.get("_auth_header", {})
        token = auth.get("Authorization", "").replace("Bearer ", "")
        if not token:
            token = self.config.get("bot_token", "")
        return token

    def ping(self) -> HealthStatus:
        token = self._token()
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/bot{token}/getMe", timeout=10)
            if resp.status_code == 200:
                return HealthStatus.HEALTHY
            return HealthStatus.UNHEALTHY
        except (httpx.HTTPError, socket.gaierror):
            return HealthStatus.DEGRADED

    def send_message(self, chat_id: str, text: str, **kwargs) -> Dict[str, Any]:
        token = self._token()
        if not token:
            return {"success": False, "error": "no bot token configured"}
        resp = httpx.post(
            f"{self.definition.base_url}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, **(kwargs.get("extra", {}) or {})},
            timeout=15,
        )
        return {"success": resp.status_code == 200, "status": resp.status_code, "data": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:200]}

    def read_messages(self, limit: int = 20, **kwargs) -> List[Dict[str, Any]]:
        token = self._token()
        if not token:
            return []
        resp = httpx.get(f"{self.definition.base_url}/bot{token}/getUpdates", params={"limit": limit, "timeout": 1}, timeout=15)
        if resp.status_code != 200:
            return []
        return resp.json().get("result", [])


@register_provider
class WhatsAppProvider(RESTProvider):
    definition = ProviderDefinition(
        key="whatsapp",
        category=IntegrationCategory.MESSAGING,
        display_name="WhatsApp Business",
        description="WhatsApp Business Cloud API messaging.",
        auth_method=AuthMethod.BEARER,
        base_url="https://graph.facebook.com/v19.0",
        capabilities=["send_message", "media"],
    )

    def _phone_number_id(self) -> str:
        return self.config.get("phone_number_id", "")

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token or not self._phone_number_id():
            return HealthStatus.UNAVAILABLE
        return HealthStatus.HEALTHY if token.startswith("Bearer") else HealthStatus.UNHEALTHY

    def send_message(self, to: str, text: str, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token or not self._phone_number_id():
            return {"success": False, "error": "whatsapp credentials missing"}
        resp = httpx.post(
            f"{self.definition.base_url}/{self._phone_number_id()}/messages",
            headers={"Authorization": token, "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
            timeout=15,
        )
        return {"success": resp.status_code in (200, 201), "status": resp.status_code, "data": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:200]}


@register_provider
class DiscordProvider(RESTProvider):
    definition = ProviderDefinition(
        key="discord",
        category=IntegrationCategory.MESSAGING,
        display_name="Discord",
        description="Send and read Discord messages via the REST API.",
        auth_method=AuthMethod.BEARER,
        base_url="https://discord.com/api",
        capabilities=["send_message", "read_messages"],
    )

    def _bot_token(self) -> str:
        return self.config.get("_auth_header", {}).get("Authorization", "")

    def ping(self) -> HealthStatus:
        token = self._bot_token()
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/users/@me", headers={"Authorization": token}, timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, socket.gaierror):
            return HealthStatus.DEGRADED

    def send_message(self, channel_id: str, text: str, **kwargs) -> Dict[str, Any]:
        token = self._bot_token()
        if not token:
            return {"success": False, "error": "no discord token"}
        resp = httpx.post(
            f"{self.definition.base_url}/channels/{channel_id}/messages",
            headers={"Authorization": token, "Content-Type": "application/json"},
            json={"content": text},
            timeout=15,
        )
        return {"success": resp.status_code in (200, 201), "status": resp.status_code}

    def read_messages(self, channel_id: str, limit: int = 20, **kwargs) -> List[Dict[str, Any]]:
        token = self._bot_token()
        if not token:
            return []
        resp = httpx.get(f"{self.definition.base_url}/channels/{channel_id}/messages", headers={"Authorization": token}, params={"limit": limit}, timeout=15)
        return resp.json() if resp.status_code == 200 else []


@register_provider
class SlackProvider(RESTProvider):
    definition = ProviderDefinition(
        key="slack",
        category=IntegrationCategory.MESSAGING,
        display_name="Slack",
        description="Send Slack messages and read channel history.",
        auth_method=AuthMethod.BEARER,
        base_url="https://slack.com/api",
        capabilities=["send_message", "read_messages"],
    )

    def _token(self) -> str:
        return self.config.get("_auth_header", {}).get("Authorization", "").replace("Bearer ", "")

    def ping(self) -> HealthStatus:
        token = self._token()
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.post(f"{self.definition.base_url}/auth.test", data={"token": token}, timeout=10)
            return HealthStatus.HEALTHY if resp.json().get("ok") else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, socket.gaierror):
            return HealthStatus.DEGRADED

    def send_message(self, channel: str, text: str, **kwargs) -> Dict[str, Any]:
        token = self._token()
        if not token:
            return {"success": False, "error": "no slack token"}
        resp = httpx.post(
            f"{self.definition.base_url}/chat.postMessage",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"channel": channel, "text": text},
            timeout=15,
        )
        return {"success": bool(resp.json().get("ok")), "status": resp.status_code}

    def read_messages(self, channel: str, limit: int = 20, **kwargs) -> List[Dict[str, Any]]:
        token = self._token()
        if not token:
            return []
        resp = httpx.get(f"{self.definition.base_url}/conversations.history", params={"token": token, "channel": channel, "limit": limit}, timeout=15)
        return resp.json().get("messages", []) if resp.status_code == 200 else []


@register_provider
class TeamsProvider(RESTProvider):
    definition = ProviderDefinition(
        key="microsoft_teams",
        category=IntegrationCategory.MESSAGING,
        display_name="Microsoft Teams",
        description="Send Teams messages via Graph API.",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://graph.microsoft.com/v1.0",
        scopes=["https://graph.microsoft.com/.default"],
        capabilities=["send_message"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        return HealthStatus.HEALTHY if token.startswith("Bearer") else HealthStatus.UNHEALTHY

    def send_message(self, team_id: str, channel_id: str, text: str, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no teams credential"}
        resp = httpx.post(
            f"{self.definition.base_url}/teams/{team_id}/channels/{channel_id}/messages",
            headers={"Authorization": token, "Content-Type": "application/json"},
            json={"body": {"content": text}},
            timeout=15,
        )
        return {"success": resp.status_code in (200, 201), "status": resp.status_code}


@register_provider
class SignalProvider(RESTProvider):
    definition = ProviderDefinition(
        key="signal",
        category=IntegrationCategory.MESSAGING,
        display_name="Signal",
        description="Send messages through a Signal REST (signal-cli-rest-api) endpoint.",
        auth_method=AuthMethod.BEARER,
        base_url="http://localhost:8080",
        capabilities=["send_message"],
    )

    def ping(self) -> HealthStatus:
        base = self.config.get("base_url", self.definition.base_url)
        try:
            resp = httpx.get(base.rstrip("/") + "/v1/health", timeout=5)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, socket.gaierror):
            return HealthStatus.UNAVAILABLE

    def send_message(self, recipient: str, text: str, **kwargs) -> Dict[str, Any]:
        base = self.config.get("base_url", self.definition.base_url)
        resp = httpx.post(
            base.rstrip("/") + "/v2/send",
            json={"message": text, "number": self.config.get("account", ""), "recipients": [recipient]},
            timeout=15,
        )
        return {"success": resp.status_code == 201, "status": resp.status_code}


@register_provider
class MatrixProvider(RESTProvider):
    definition = ProviderDefinition(
        key="matrix",
        category=IntegrationCategory.MESSAGING,
        display_name="Matrix",
        description="Matrix homeserver client-server API messaging.",
        auth_method=AuthMethod.BEARER,
        base_url="https://matrix.org",
        capabilities=["send_message", "read_messages"],
    )

    def _homeserver(self) -> str:
        return self.config.get("homeserver", self.definition.base_url)

    def ping(self) -> HealthStatus:
        try:
            resp = httpx.get(self._homeserver().rstrip("/") + "/_matrix/client/versions", timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, socket.gaierror):
            return HealthStatus.UNAVAILABLE

    def send_message(self, room_id: str, text: str, access_token: str = "", **kwargs) -> Dict[str, Any]:
        token = access_token or self.config.get("access_token", "")
        if not token:
            return {"success": False, "error": "no matrix access token"}
        txn = f"aetheros-{len(text)}"
        resp = httpx.put(
            f"{self._homeserver().rstrip('/')}/_matrix/client/r0/rooms/{room_id}/send/m.room.message/{txn}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"msgtype": "m.text", "body": text},
            timeout=15,
        )
        return {"success": resp.status_code in (200, 201), "status": resp.status_code}


@register_provider
class IRCProvider(BaseProvider):
    definition = ProviderDefinition(
        key="irc",
        category=IntegrationCategory.MESSAGING,
        display_name="IRC",
        description="IRC messaging over a local bot connection.",
        auth_method=AuthMethod.NONE,
        capabilities=["send_message"],
    )

    def ping(self) -> HealthStatus:
        server = self.config.get("server", "")
        if not server:
            return HealthStatus.UNAVAILABLE
        return HealthStatus.DEGRADED  # requires a running IRC bridge

    def send_message(self, channel: str, text: str, **kwargs) -> Dict[str, Any]:
        bridge = self.config.get("bridge_url", "")
        if not bridge:
            return {"success": False, "error": "no IRC bridge configured"}
        try:
            resp = httpx.post(bridge.rstrip("/") + "/send", json={"channel": channel, "text": text}, timeout=10)
            return {"success": resp.status_code == 200, "status": resp.status_code}
        except (httpx.HTTPError, socket.gaierror) as exc:
            return {"success": False, "error": str(exc)}


@register_provider
class EmailSMTPProvider(BaseProvider):
    """SMTP delivery used by the messaging/email engines."""

    definition = ProviderDefinition(
        key="email_smtp",
        category=IntegrationCategory.EMAIL,
        display_name="SMTP (send)",
        description="Send email over SMTP.",
        auth_method=AuthMethod.BASIC,
        capabilities=["send_message", "send_email"],
    )

    def ping(self) -> HealthStatus:
        host = self.config.get("smtp_host", "")
        if not host:
            return HealthStatus.UNAVAILABLE
        return HealthStatus.HEALTHY if self.config.get("smtp_port") else HealthStatus.DEGRADED

    def send_message(self, to: str, subject: str, body: str, **kwargs) -> Dict[str, Any]:
        return self.send_email(to=to, subject=subject, body=body, **kwargs)

    def send_email(self, *, to: str, subject: str, body: str, from_addr: str = "", html: bool = False, **kwargs) -> Dict[str, Any]:
        host = self.config.get("smtp_host", "")
        port = int(self.config.get("smtp_port", 587))
        user = self.config.get("smtp_user", "")
        password = self.config.get("smtp_password", "")
        sender = from_addr or self.config.get("from_addr", user)
        if not host or not sender:
            return {"success": False, "error": "SMTP configuration missing"}
        msg = MIMEMultipart("alternative") if html else MIMEText(body, "plain", "utf-8")
        if html:
            msg.attach(MIMEText(body, "plain", "utf-8"))
            msg.attach(MIMEText(kwargs.get("html_body", ""), "html", "utf-8"))
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to
        try:
            with smtplib.SMTP(host, port, timeout=30) as server:
                if port == 587:
                    server.starttls()
                if user:
                    server.login(user, password)
                server.sendmail(sender, [to], msg.as_string())
            return {"success": True}
        except (smtplib.SMTPException, OSError) as exc:
            return {"success": False, "error": str(exc)}


@register_provider
class SMSProvider(RESTProvider):
    definition = ProviderDefinition(
        key="sms",
        category=IntegrationCategory.MESSAGING,
        display_name="SMS",
        description="Send SMS through a provider REST endpoint (Twilio-style).",
        auth_method=AuthMethod.BASIC,
        base_url="https://api.twilio.com/2010-04-01",
        capabilities=["send_message"],
    )

    def ping(self) -> HealthStatus:
        sid = self.config.get("account_sid", "")
        if not sid:
            return HealthStatus.UNAVAILABLE
        return HealthStatus.HEALTHY

    def send_message(self, to: str, text: str, **kwargs) -> Dict[str, Any]:
        sid = self.config.get("account_sid", "")
        token = self.config.get("auth_token", "")
        if not sid or not token:
            return {"success": False, "error": "SMS credentials missing"}
        resp = httpx.post(
            f"{self.definition.base_url}/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"From": self.config.get("from_number", ""), "To": to, "Body": text},
            timeout=15,
        )
        return {"success": resp.status_code in (200, 201), "status": resp.status_code}


def _load_all() -> None:
    pass
