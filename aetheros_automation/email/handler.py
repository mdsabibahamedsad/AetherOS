from __future__ import annotations

import asyncio
import email
import imaplib
import logging
import os
import smtplib
import time
from email.header import decode_header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parsedate_to_datetime
from pathlib import Path
from typing import Any

from aetheros_automation.models.models import EmailSpec

logger = logging.getLogger(__name__)

try:
    import aiosmtplib

    _HAS_AIOSMTP = True
except ImportError:
    _HAS_AIOSMTP = False
    logger.warning("aiosmtplib not available; falling back to blocking smtplib")


class EmailHandler:
    """Send, read, and manage emails via SMTP/IMAP with async support."""

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int = 587
        self._user: str | None = None
        self._password: str | None = None
        self._use_tls: bool = True
        self._connected = False
        self._imap: imaplib.IMAP4_SSL | imaplib.IMAP4 | None = None
        self._smtp: smtplib.SMTP | aiosmtplib.SMTP | None = None

    async def connect(self, config: dict[str, Any] | None = None) -> None:
        self._host = (config or {}).get("host") or os.getenv("EMAIL_HOST", "")
        self._port = int((config or {}).get("port") or os.getenv("EMAIL_PORT", "587"))
        self._user = (config or {}).get("user") or os.getenv("EMAIL_USER", "")
        self._password = (config or {}).get("password") or os.getenv("EMAIL_PASS", "")
        use_tls_str = (config or {}).get("use_tls") or os.getenv("EMAIL_USE_TLS", "true")
        self._use_tls = str(use_tls_str).lower() in ("true", "1", "yes")

        if not self._host or not self._user or not self._password:
            raise ValueError(
                "Email configuration incomplete. Set EMAIL_HOST, EMAIL_USER, "
                "EMAIL_PASS (and optionally EMAIL_PORT, EMAIL_USE_TLS) env vars."
            )

        await self._connect_smtp()
        await self._connect_imap()
        self._connected = True
        logger.info("Connected to email %s@%s:%d", self._user, self._host, self._port)

    async def _connect_smtp(self) -> None:
        if _HAS_AIOSMTP:
            self._smtp = aiosmtplib.SMTP(hostname=self._host, port=self._port)
            await self._smtp.connect()
            if self._use_tls:
                await self._smtp.starttls()
            await self._smtp.login(self._user, self._password)
        else:
            loop = asyncio.get_running_loop()

            def _blocking_smtp_connect() -> smtplib.SMTP:
                server = smtplib.SMTP(self._host, self._port, timeout=30)
                if self._use_tls:
                    server.starttls()
                server.login(self._user, self._password)
                return server

            self._smtp = await loop.run_in_executor(None, _blocking_smtp_connect)

    async def _connect_imap(self) -> None:
        loop = asyncio.get_running_loop()

        def _blocking_imap_connect() -> imaplib.IMAP4_SSL | imaplib.IMAP4:
            if self._use_tls:
                imap = imaplib.IMAP4_SSL(self._host, self._port or 993)
            else:
                imap = imaplib.IMAP4(self._host, self._port or 143)
            imap.login(self._user, self._password)
            return imap

        self._imap = await loop.run_in_executor(None, _blocking_imap_connect)

    async def send(self, spec: EmailSpec) -> None:
        msg = MIMEMultipart()
        msg["From"] = formataddr(("", self._user))
        msg["To"] = ", ".join(spec.to)
        if spec.cc:
            msg["Cc"] = ", ".join(spec.cc)
        msg["Subject"] = spec.subject

        msg.attach(MIMEText(spec.body, "plain", "utf-8"))

        for attachment_path in spec.attachments:
            part = await self._build_attachment(attachment_path)
            if part:
                msg.attach(part)

        recipients = spec.to + spec.cc + spec.bcc
        if spec.bcc:
            msg["Bcc"] = ", ".join(spec.bcc)

        if _HAS_AIOSMTP and isinstance(self._smtp, aiosmtplib.SMTP):
            await self._smtp.send_message(msg)
        else:
            loop = asyncio.get_running_loop()

            def _send() -> None:
                if isinstance(self._smtp, smtplib.SMTP):
                    self._smtp.send_message(msg)

            await loop.run_in_executor(None, _send)

        logger.info("Sent email '%s' to %s", spec.subject, ", ".join(recipients))

    async def read(self, folder: str = "INBOX", limit: int = 10) -> list[dict[str, Any]]:
        if not self._imap:
            raise ConnectionError("Not connected. Call connect() first.")

        loop = asyncio.get_running_loop()

        def _fetch() -> list[dict[str, Any]]:
            imap = self._imap
            imap.select(folder)
            _, data = imap.search(None, "ALL")
            ids = data[0].split()
            recent = ids[-limit:] if len(ids) > limit else ids
            emails_list: list[dict[str, Any]] = []
            for eid in recent:
                _, msg_data = imap.fetch(eid, "(RFC822)")
                raw = msg_data[0][1]
                parsed = email.message_from_bytes(raw)
                emails_list.append(self._parse_email(eid, parsed))
            return emails_list

        return await loop.run_in_executor(None, _fetch)

    async def summarize(self, email_id: str) -> str:
        if not self._imap:
            raise ConnectionError("Not connected. Call connect() first.")

        loop = asyncio.get_running_loop()

        def _fetch_one() -> str:
            imap = self._imap
            imap.select("INBOX")
            _, msg_data = imap.fetch(email_id, "(RFC822)")
            if not msg_data or msg_data[0] is None:
                return "Email not found."
            raw = msg_data[0][1]
            parsed = email.message_from_bytes(raw)
            info = self._parse_email(email_id, parsed)
            body = info.get("body", "")[:500]
            return (
                f"From: {info.get('from')}\n"
                f"Date: {info.get('date')}\n"
                f"Subject: {info.get('subject')}\n"
                f"Preview:\n{body}"
            )

        return await loop.run_in_executor(None, _fetch_one)

    async def reply(self, email_id: str, body: str) -> None:
        if not self._imap:
            raise ConnectionError("Not connected. Call connect() first.")

        loop = asyncio.get_running_loop()

        def _reply_blocking() -> None:
            imap = self._imap
            imap.select("INBOX")
            _, msg_data = imap.fetch(email_id, "(RFC822)")
            if not msg_data or msg_data[0] is None:
                raise ValueError(f"Email {email_id} not found")
            raw = msg_data[0][1]
            parsed = email.message_from_bytes(raw)
            subject = parsed["Subject"] or ""
            if not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"
            reply_to = parsed.get("Reply-To", parsed["From"])
            msg = MIMEText(body, "plain", "utf-8")
            msg["From"] = formataddr(("", self._user))
            msg["To"] = reply_to
            msg["Subject"] = subject
            msg["In-Reply-To"] = parsed.get("Message-ID", "")
            msg["References"] = parsed.get("Message-ID", "")

            if _HAS_AIOSMTP and isinstance(self._smtp, aiosmtplib.SMTP):
                loop2 = asyncio.new_event_loop()
                loop2.run_until_complete(self._smtp.send_message(msg))
                loop2.close()
            elif isinstance(self._smtp, smtplib.SMTP):
                self._smtp.send_message(msg)

        await loop.run_in_executor(None, _reply_blocking)
        logger.info("Replied to email %s", email_id)

    async def archive(self, email_id: str) -> None:
        if not self._imap:
            raise ConnectionError("Not connected. Call connect() first.")

        loop = asyncio.get_running_loop()

        def _archive_blocking() -> None:
            imap = self._imap
            imap.select("INBOX")
            imap.copy(email_id, "[Gmail]/All Mail" if "[Gmail]" in str(imap.list()) else "Archive")
            imap.store(email_id, "+FLAGS", "\\Deleted")
            imap.expunge()

        await loop.run_in_executor(None, _archive_blocking)
        logger.info("Archived email %s", email_id)

    async def draft(self, spec: EmailSpec) -> None:
        if not self._imap:
            raise ConnectionError("Not connected. Call connect() first.")

        msg = MIMEMultipart()
        msg["From"] = formataddr(("", self._user))
        msg["To"] = ", ".join(spec.to)
        msg["Subject"] = spec.subject
        msg.attach(MIMEText(spec.body, "plain", "utf-8"))

        loop = asyncio.get_running_loop()

        def _save_draft() -> None:
            imap = self._imap
            imap.append("Drafts", "\\Draft", imaplib.Time2Internaldate(time.time()), msg.as_bytes())

        await loop.run_in_executor(None, _save_draft)
        logger.info("Saved draft '%s'", spec.subject)

    async def schedule(self, email_spec: EmailSpec, send_at: str) -> None:
        logger.info("Scheduled email '%s' for %s", email_spec.subject, send_at)
        raise NotImplementedError(
            "Scheduled sending requires a background scheduler (e.g. APScheduler). "
            "Store the spec and schedule `handler.send(spec)` at the target time."
        )

    async def search(self, query: str, folder: str = "INBOX") -> list[dict[str, Any]]:
        if not self._imap:
            raise ConnectionError("Not connected. Call connect() first.")

        loop = asyncio.get_running_loop()

        def _search_blocking() -> list[dict[str, Any]]:
            imap = self._imap
            imap.select(folder)
            _, data = imap.search(None, f'TEXT "{query}"')
            ids = data[0].split()
            results: list[dict[str, Any]] = []
            for eid in ids:
                _, msg_data = imap.fetch(eid, "(RFC822)")
                if not msg_data or msg_data[0] is None:
                    continue
                raw = msg_data[0][1]
                parsed = email.message_from_bytes(raw)
                results.append(self._parse_email(eid, parsed))
            return results

        return await loop.run_in_executor(None, _search_blocking)

    async def get_folders(self) -> list[str]:
        if not self._imap:
            raise ConnectionError("Not connected. Call connect() first.")

        loop = asyncio.get_running_loop()

        def _list_folders() -> list[str]:
            imap = self._imap
            _, data = imap.list()
            folders: list[str] = []
            for item in data:
                decoded = item.decode("utf-8", errors="replace")
                parts = decoded.split(' "/" ')
                if len(parts) == 2:
                    folders.append(parts[1].strip('"'))
                else:
                    folders.append(decoded.rsplit("/", 1)[-1].strip())
            return folders

        return await loop.run_in_executor(None, _list_folders)

    async def disconnect(self) -> None:
        loop = asyncio.get_running_loop()

        def _close() -> None:
            if self._imap:
                try:
                    self._imap.close()
                    self._imap.logout()
                except Exception:
                    pass
            if isinstance(self._smtp, smtplib.SMTP):
                try:
                    self._smtp.quit()
                except Exception:
                    pass

        await loop.run_in_executor(None, _close)
        if _HAS_AIOSMTP and isinstance(self._smtp, aiosmtplib.SMTP):
            await self._smtp.quit()
        self._connected = False
        logger.info("Disconnected from email")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_email(eid: bytes, msg: email.message.Message) -> dict[str, Any]:
        subject = EmailHandler._decode_header_str(msg["Subject"])
        sender = EmailHandler._decode_header_str(msg["From"])
        date_str = msg["Date"]
        date_val = str(parsedate_to_datetime(date_str)) if date_str else ""
        body = EmailHandler._extract_body(msg)
        return {
            "id": eid.decode() if isinstance(eid, bytes) else str(eid),
            "subject": subject,
            "from": sender,
            "date": date_val,
            "body": body[:5000],
        }

    @staticmethod
    def _decode_header_str(value: str | None) -> str:
        if not value:
            return ""
        parts = decode_header(value)
        return " ".join(
            p.decode(charset or "utf-8", errors="replace") if isinstance(p, bytes) else str(p)
            for p, charset in parts
        )

    @staticmethod
    def _extract_body(msg: email.message.Message) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode("utf-8", errors="replace")
            return ""
        payload = msg.get_payload(decode=True)
        return payload.decode("utf-8", errors="replace") if payload else ""

    @staticmethod
    async def _build_attachment(path: str) -> MIMEBase | None:
        p = Path(path).resolve()
        if not p.exists():
            logger.warning("Attachment not found: %s", p)
            return None

        loop = asyncio.get_running_loop()

        def _read() -> tuple[bytes, str]:
            return p.read_bytes(), p.name

        data, filename = await loop.run_in_executor(None, _read)
        part = MIMEBase("application", "octet-stream")
        part.set_payload(data)
        from email import encoders

        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        return part
