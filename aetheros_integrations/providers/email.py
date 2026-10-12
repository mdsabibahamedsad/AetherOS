"""AetherOS Integrations — email engine adapters.

Gmail (Gmail API), Outlook/Exchange (Graph API), IMAP read, and SMTP send.
Reads, replies, drafts, attachments, search, and summaries.
"""

from __future__ import annotations

import base64
import email
import imaplib
import logging
import os
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import httpx

from aetheros_integrations.models import AuthMethod, HealthStatus, IntegrationCategory, ProviderDefinition
from aetheros_integrations.providers.base import RESTProvider, register_provider

logger = logging.getLogger(__name__)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode()


def _safe_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in "._- ").strip() or "attachment"


@register_provider
class GmailProvider(RESTProvider):
    definition = ProviderDefinition(
        key="gmail",
        category=IntegrationCategory.EMAIL,
        display_name="Gmail",
        description="Gmail API: read, send, draft, search, attachments.",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://gmail.googleapis.com/gmail/v1",
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
        capabilities=["read_messages", "send_email", "draft", "search", "attachments", "summary"],
    )

    def _user(self) -> str:
        return self.config.get("user_id", "me")

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/users/{self._user()}/profile", headers=self._headers(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def read_messages(self, query: str = "", max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        params = {"maxResults": max_results}
        if query:
            params["q"] = query
        resp = httpx.get(f"{self.definition.base_url}/users/{self._user()}/messages", headers=self._headers(), params=params, timeout=15)
        if resp.status_code != 200:
            return []
        out = []
        for msg in resp.json().get("messages", [])[:max_results]:
            detail = httpx.get(f"{self.definition.base_url}/users/{self._user()}/messages/{msg['id']}", headers=self._headers(), params={"format": "metadata"}, timeout=15)
            if detail.status_code == 200:
                payload = detail.json()
                headers = {h["name"]: h["value"] for h in payload.get("payload", {}).get("headers", [])}
                out.append({"id": payload["id"], "subject": headers.get("Subject", ""), "from": headers.get("From", ""), "snippet": payload.get("snippet", "")})
        return out

    def search(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        return self.read_messages(query=query, max_results=max_results)

    def send_email(self, to: str, subject: str, body: str, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no gmail credential"}
        sender = self.config.get("from_addr", self._user())
        mime = MIMEMultipart()
        mime["From"] = sender
        mime["To"] = to
        mime["Subject"] = subject
        mime.attach(MIMEText(body, "plain", "utf-8"))
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        resp = httpx.post(
            f"{self.definition.base_url}/users/{self._user()}/messages/send",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"raw": raw},
            timeout=20,
        )
        return {"success": resp.status_code == 200, "status": resp.status_code, "data": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}}

    def draft(self, to: str, subject: str, body: str, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no gmail credential"}
        mime = MIMEText(body, "plain", "utf-8")
        mime["From"] = self.config.get("from_addr", self._user())
        mime["To"] = to
        mime["Subject"] = subject
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        resp = httpx.post(
            f"{self.definition.base_url}/users/{self._user()}/drafts",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"message": {"raw": raw}},
            timeout=20,
        )
        return {"success": resp.status_code == 200, "status": resp.status_code}

    def attachments(self, message_id: str, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        resp = httpx.get(f"{self.definition.base_url}/users/{self._user()}/messages/{message_id}", headers=self._headers(), timeout=20)
        if resp.status_code != 200:
            return []
        parts = resp.json().get("payload", {}).get("parts", [])
        out = []
        for part in parts:
            if part.get("filename"):
                data = part.get("body", {}).get("data", "")
                out.append({"filename": part["filename"], "mime": part.get("mimeType", ""), "bytes": len(base64.urlsafe_b64decode(data.encode())) if data else 0})
        return out


@register_provider
class OutlookProvider(RESTProvider):
    definition = ProviderDefinition(
        key="outlook",
        category=IntegrationCategory.EMAIL,
        display_name="Microsoft Outlook / Exchange",
        description="Outlook mail via Graph API.",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://graph.microsoft.com/v1.0",
        scopes=["Mail.ReadWrite", "Mail.Send", "User.Read"],
        capabilities=["read_messages", "send_email", "draft", "search", "attachments"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/me", headers=self._headers(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def read_messages(self, query: str = "", max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        params = {"$top": max_results, "$select": "id,subject,from,sentDateTime,bodyPreview"}
        if query:
            params["$filter"] = f"contains(subject,'{query}')"
        resp = httpx.get(f"{self.definition.base_url}/me/messages", headers=self._headers(), params=params, timeout=15)
        if resp.status_code != 200:
            return []
        return [
            {"id": m.get("id"), "subject": m.get("subject", ""), "from": (m.get("from") or {}).get("emailAddress", {}).get("address", ""), "snippet": m.get("bodyPreview", "")}
            for m in resp.json().get("value", [])
        ]

    def send_email(self, to: str, subject: str, body: str, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no outlook credential"}
        resp = httpx.post(
            f"{self.definition.base_url}/me/sendMail",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"message": {"subject": subject, "body": {"contentType": "Text", "content": body}, "toRecipients": [{"emailAddress": {"address": to}}]}, "saveToSentItems": True},
            timeout=20,
        )
        return {"success": resp.status_code == 202, "status": resp.status_code}


@register_provider
class IMAPProvider(RESTProvider):
    definition = ProviderDefinition(
        key="imap",
        category=IntegrationCategory.EMAIL,
        display_name="IMAP (read)",
        description="Read mail from any IMAP server (stdlib imaplib).",
        auth_method=AuthMethod.BASIC,
        capabilities=["read_messages", "search", "attachments"],
    )

    def _connect(self):
        host = self.config.get("imap_host", "")
        port = int(self.config.get("imap_port", 993))
        user = self.config.get("imap_user", "")
        password = self.config.get("imap_password", "")
        if not host or not user:
            raise ValueError("IMAP configuration missing")
        conn = imaplib.IMAP4_SSL(host, port)
        conn.login(user, password)
        return conn

    def ping(self) -> HealthStatus:
        try:
            conn = self._connect()
            conn.logout()
            return HealthStatus.HEALTHY
        except (imaplib.IMAP4.error, OSError, ValueError):
            return HealthStatus.UNHEALTHY

    def read_messages(self, query: str = "ALL", max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        try:
            conn = self._connect()
        except (imaplib.IMAP4.error, OSError, ValueError) as exc:
            logger.debug("IMAP read failed: %s", exc)
            return []
        try:
            conn.select("INBOX")
            status, data = conn.search(None, query)
            if status != "OK":
                return []
            ids = data[0].split()
            out = []
            for num in ids[-max_results:]:
                _, msg_data = conn.fetch(num, "(BODY.PEEK[HEADER])")
                if msg_data and isinstance(msg_data[0], tuple):
                    raw = msg_data[0][1]
                    parsed = email.message_from_bytes(raw)
                    out.append({"id": num.decode(), "subject": parsed.get("Subject", ""), "from": parsed.get("From", ""), "date": parsed.get("Date", "")})
            return out
        finally:
            try:
                conn.logout()
            except Exception:  # noqa: BLE001
                pass


@register_provider
class ExchangeProvider(OutlookProvider):
    definition = ProviderDefinition(
        key="exchange",
        category=IntegrationCategory.EMAIL,
        display_name="Microsoft Exchange",
        description="Exchange Online via Graph API (same protocol as Outlook).",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://graph.microsoft.com/v1.0",
        scopes=["Mail.ReadWrite", "Mail.Send"],
        capabilities=["read_messages", "send_email", "search"],
    )
