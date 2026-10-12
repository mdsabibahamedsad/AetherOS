from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ScheduleRecurrence(Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    WEEKDAYS = "weekdays"
    CUSTOM = "custom"


class ScheduledMessageStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ScheduledMessage:
    id: str
    provider: str
    account_id: str
    recipient_id: str
    recipient_name: str
    content: str
    scheduled_at: datetime
    status: ScheduledMessageStatus = ScheduledMessageStatus.SCHEDULED
    recurrence: ScheduleRecurrence = ScheduleRecurrence.NONE
    recurrence_config: dict[str, Any] = field(default_factory=dict)
    attachments: list[str] = field(default_factory=list)
    require_approval: bool = False
    approved: bool = False
    template_id: str = ""
    parent_id: str = ""
    sent_at: Optional[datetime] = None
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "user"


class MessageScheduler:
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path.home() / ".aetheros" / "automation" / "communications"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._messages: dict[str, ScheduledMessage] = {}
        self._load()

    def _path(self) -> Path:
        return self._storage_path / "scheduled_messages.json"

    def _load(self):
        if self._path().exists():
            try:
                data = json.loads(self._path().read_text())
                for item in data:
                    msg = self._deserialize(item)
                    self._messages[msg.id] = msg
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        data = [self._serialize(m) for m in self._messages.values()]
        self._path().write_text(json.dumps(data, indent=2, default=str))

    def _serialize(self, msg: ScheduledMessage) -> dict:
        return {
            "id": msg.id,
            "provider": msg.provider,
            "account_id": msg.account_id,
            "recipient_id": msg.recipient_id,
            "recipient_name": msg.recipient_name,
            "content": msg.content,
            "scheduled_at": msg.scheduled_at.isoformat(),
            "status": msg.status.value,
            "recurrence": msg.recurrence.value,
            "recurrence_config": msg.recurrence_config,
            "attachments": msg.attachments,
            "require_approval": msg.require_approval,
            "approved": msg.approved,
            "template_id": msg.template_id,
            "parent_id": msg.parent_id,
            "sent_at": msg.sent_at.isoformat() if msg.sent_at else None,
            "error_message": msg.error_message,
            "created_at": msg.created_at.isoformat(),
            "created_by": msg.created_by,
        }

    def _deserialize(self, data: dict) -> ScheduledMessage:
        return ScheduledMessage(
            id=data["id"],
            provider=data["provider"],
            account_id=data.get("account_id", ""),
            recipient_id=data["recipient_id"],
            recipient_name=data.get("recipient_name", ""),
            content=data["content"],
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]),
            status=ScheduledMessageStatus(data.get("status", "scheduled")),
            recurrence=ScheduleRecurrence(data.get("recurrence", "none")),
            recurrence_config=data.get("recurrence_config", {}),
            attachments=data.get("attachments", []),
            require_approval=data.get("require_approval", False),
            approved=data.get("approved", False),
            template_id=data.get("template_id", ""),
            parent_id=data.get("parent_id", ""),
            sent_at=datetime.fromisoformat(data["sent_at"]) if data.get("sent_at") else None,
            error_message=data.get("error_message", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            created_by=data.get("created_by", "user"),
        )

    def schedule(self, msg: ScheduledMessage):
        self._messages[msg.id] = msg
        self._save()

    def cancel(self, msg_id: str) -> bool:
        msg = self._messages.get(msg_id)
        if msg and msg.status in (ScheduledMessageStatus.PENDING, ScheduledMessageStatus.SCHEDULED):
            msg.status = ScheduledMessageStatus.CANCELLED
            self._save()
            return True
        return False

    def pause(self, msg_id: str) -> bool:
        msg = self._messages.get(msg_id)
        if msg and msg.status == ScheduledMessageStatus.SCHEDULED:
            msg.status = ScheduledMessageStatus.PAUSED
            self._save()
            return True
        return False

    def resume(self, msg_id: str) -> bool:
        msg = self._messages.get(msg_id)
        if msg and msg.status == ScheduledMessageStatus.PAUSED:
            msg.status = ScheduledMessageStatus.SCHEDULED
            self._save()
            return True
        return False

    def reschedule(self, msg_id: str, new_time: datetime) -> bool:
        msg = self._messages.get(msg_id)
        if msg:
            msg.scheduled_at = new_time
            if msg.status in (ScheduledMessageStatus.CANCELLED, ScheduledMessageStatus.PAUSED):
                msg.status = ScheduledMessageStatus.SCHEDULED
            self._save()
            return True
        return False

    def mark_sent(self, msg_id: str):
        msg = self._messages.get(msg_id)
        if msg:
            msg.status = ScheduledMessageStatus.SENT
            msg.sent_at = datetime.now()
            self._save()

    def mark_failed(self, msg_id: str, error: str):
        msg = self._messages.get(msg_id)
        if msg:
            msg.status = ScheduledMessageStatus.FAILED
            msg.error_message = error
            self._save()

    def approve(self, msg_id: str) -> bool:
        msg = self._messages.get(msg_id)
        if msg and msg.require_approval:
            msg.approved = True
            self._save()
            return True
        return False

    def get_due_messages(self) -> list[ScheduledMessage]:
        now = datetime.now()
        return [m for m in self._messages.values()
                if m.status == ScheduledMessageStatus.SCHEDULED and m.scheduled_at <= now]

    def get_upcoming(self, hours: int = 24) -> list[ScheduledMessage]:
        now = datetime.now()
        cutoff = now + timedelta(hours=hours)
        return sorted(
            [m for m in self._messages.values()
             if m.status == ScheduledMessageStatus.SCHEDULED and now <= m.scheduled_at <= cutoff],
            key=lambda m: m.scheduled_at
        )

    def list_scheduled(self) -> list[ScheduledMessage]:
        return sorted(
            [m for m in self._messages.values() if m.status in (ScheduledMessageStatus.SCHEDULED, ScheduledMessageStatus.PAUSED, ScheduledMessageStatus.PENDING)],
            key=lambda m: m.scheduled_at
        )

    def list_by_provider(self, provider: str) -> list[ScheduledMessage]:
        return [m for m in self._messages.values() if m.provider == provider]

    def list_history(self, limit: int = 50) -> list[ScheduledMessage]:
        return sorted(
            [m for m in self._messages.values() if m.status in (ScheduledMessageStatus.SENT, ScheduledMessageStatus.FAILED, ScheduledMessageStatus.CANCELLED)],
            key=lambda m: m.scheduled_at, reverse=True
        )[:limit]

    def update_content(self, msg_id: str, content: str) -> bool:
        msg = self._messages.get(msg_id)
        if msg:
            msg.content = content
            self._save()
            return True
        return False
