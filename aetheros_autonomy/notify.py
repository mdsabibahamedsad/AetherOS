"""Notification center + digest engine (sections 40-42).

Channels: in-app log (always), desktop hook, email/webhook via injected
senders (never called unless authorized by policy). Intelligence:
grouping, digest/daily/weekly batching, ONLY_IMPORTANT filtering, SILENT.
External delivery requires explicit authorization per notification.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_autonomy.models import NotifyMode

SendFn = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class Notification:
    id: str = ""
    automation_id: str = ""
    run_id: str = ""
    title: str = ""
    body: str = ""
    importance: str = "normal"  # low|normal|important|critical
    channel: str = "in_app"
    mode: str = NotifyMode.IMMEDIATE.value
    created_at: float = field(default_factory=time.time)
    delivered: bool = False
    delivery_note: str = ""


class NotificationCenter:
    def __init__(self, *, email_sender: Optional[SendFn] = None,
                 webhook_sender: Optional[SendFn] = None,
                 external_allowed: Optional[Callable[[Notification], bool]] = None) -> None:
        self._lock = threading.Lock()
        self._log: List[Notification] = []
        self._email = email_sender
        self._webhook = webhook_sender
        self._allowed = external_allowed or (lambda n: False)
        self._seq = 0

    def notify(self, note: Notification) -> Notification:
        with self._lock:
            self._seq += 1
            note.id = note.id or f"n{self._seq}"
            if note.mode == NotifyMode.SILENT.value:
                note.delivered = False
                note.delivery_note = "silent"
                self._log.append(note)
                return note
            if note.channel in ("email", "webhook", "messaging"):
                if not self._allowed(note):
                    note.delivered = False
                    note.delivery_note = "external delivery not authorized"
                    self._log.append(note)
                    return note
                sender = self._email if note.channel == "email" else self._webhook
                if sender is None:
                    note.delivery_note = "no sender configured"
                    self._log.append(note)
                    return note
                try:
                    res = sender({"title": note.title, "body": note.body})
                    note.delivered = bool(res.get("delivered", True))
                    note.delivery_note = str(res.get("note", "sent"))
                except Exception as exc:
                    note.delivery_note = f"send failed: {exc}"[:200]
                self._log.append(note)
                return note
            note.delivered = True  # in_app / desktop log
            note.delivery_note = "logged"
            self._log.append(note)
            return note

    def pending_digest(self, *, mode: str, since: float) -> List[Notification]:
        with self._lock:
            return [n for n in self._log
                    if n.mode == mode and n.created_at >= since and not n.delivered]


class DigestEngine:
    def build(self, notes: List[Notification]) -> Dict[str, Any]:
        important = [n for n in notes if n.importance in ("important", "critical")]
        return {"headline": f"{len(important)} important change(s) in {len(notes)} notification(s).",
                "items": [{"title": n.title, "body": n.body[:300],
                           "automation": n.automation_id,
                           "at": n.created_at} for n in important[:20]],
                "total": len(notes)}
