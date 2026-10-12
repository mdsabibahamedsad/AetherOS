from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class NotificationChannel(Enum):
    DESKTOP = "desktop"
    SOUND = "sound"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationCategory(Enum):
    MESSAGE = "message"
    MENTION = "mention"
    URGENT = "urgent"
    SCHEDULED = "scheduled"
    AUTOMATION = "automation"
    APPROVAL = "approval"
    CALENDAR = "calendar"
    SYSTEM = "system"
    ERROR = "error"


@dataclass
class NotificationRule:
    id: str
    name: str
    category: NotificationCategory
    enabled: bool = True
    channels: list[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.DESKTOP])
    priority: NotificationPriority = NotificationPriority.NORMAL
    sound: str = "default"
    quiet_hours_start: str = ""
    quiet_hours_end: str = ""
    provider_filter: str = "all"
    min_priority: NotificationPriority = NotificationPriority.LOW


@dataclass
class Notification:
    id: str
    title: str
    body: str
    category: NotificationCategory
    priority: NotificationPriority
    provider: str = ""
    conversation_id: str = ""
    message_id: str = ""
    channel: NotificationChannel = NotificationChannel.DESKTOP
    read: bool = False
    action_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class NotificationManager:
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path.home() / ".aetheros" / "automation" / "communications"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._rules: list[NotificationRule] = self._default_rules()
        self._notifications: list[Notification] = []
        self._handlers: dict[str, list] = {}
        self._load()

    def _default_rules(self) -> list[NotificationRule]:
        return [
            NotificationRule(id="rule_msg", name="New Messages", category=NotificationCategory.MESSAGE, priority=NotificationPriority.NORMAL),
            NotificationRule(id="rule_mention", name="Mentions", category=NotificationCategory.MENTION, priority=NotificationPriority.HIGH, sound="alert"),
            NotificationRule(id="rule_urgent", name="Urgent Messages", category=NotificationCategory.URGENT, priority=NotificationPriority.URGENT, sound="critical", channels=[NotificationChannel.DESKTOP, NotificationChannel.SOUND]),
            NotificationRule(id="rule_approval", name="Approval Requests", category=NotificationCategory.APPROVAL, priority=NotificationPriority.HIGH, sound="alert"),
            NotificationRule(id="rule_automation", name="Automation Events", category=NotificationCategory.AUTOMATION, priority=NotificationPriority.NORMAL),
            NotificationRule(id="rule_scheduled", name="Scheduled Messages", category=NotificationCategory.SCHEDULED, priority=NotificationPriority.NORMAL),
            NotificationRule(id="rule_error", name="Errors & Failures", category=NotificationCategory.ERROR, priority=NotificationPriority.HIGH, sound="alert"),
            NotificationRule(id="rule_calendar", name="Calendar Events", category=NotificationCategory.CALENDAR, priority=NotificationPriority.NORMAL),
        ]

    def _rule_path(self) -> Path:
        return self._storage_path / "notification_rules.json"

    def _notif_path(self) -> Path:
        return self._storage_path / "notifications.json"

    def _load(self):
        if self._rule_path().exists():
            try:
                data = json.loads(self._rule_path().read_text())
                if data:
                    self._rules = [self._deserialize_rule(r) for r in data]
            except (json.JSONDecodeError, KeyError):
                pass
        if self._notif_path().exists():
            try:
                data = json.loads(self._notif_path().read_text())
                self._notifications = [self._deserialize_notification(n) for n in data]
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_rules(self):
        data = [self._serialize_rule(r) for r in self._rules]
        self._rule_path().write_text(json.dumps(data, indent=2, default=str))

    def _save_notifications(self):
        data = [self._serialize_notification(n) for n in self._notifications[-500:]]
        self._notif_path().write_text(json.dumps(data, indent=2, default=str))

    def _serialize_rule(self, rule: NotificationRule) -> dict:
        return {
            "id": rule.id,
            "name": rule.name,
            "category": rule.category.value,
            "enabled": rule.enabled,
            "channels": [c.value for c in rule.channels],
            "priority": rule.priority.value,
            "sound": rule.sound,
            "quiet_hours_start": rule.quiet_hours_start,
            "quiet_hours_end": rule.quiet_hours_end,
            "provider_filter": rule.provider_filter,
            "min_priority": rule.min_priority.value,
        }

    def _deserialize_rule(self, data: dict) -> NotificationRule:
        return NotificationRule(
            id=data["id"],
            name=data.get("name", ""),
            category=NotificationCategory(data["category"]),
            enabled=data.get("enabled", True),
            channels=[NotificationChannel(c) for c in data.get("channels", ["desktop"])],
            priority=NotificationPriority(data.get("priority", "normal")),
            sound=data.get("sound", "default"),
            quiet_hours_start=data.get("quiet_hours_start", ""),
            quiet_hours_end=data.get("quiet_hours_end", ""),
            provider_filter=data.get("provider_filter", "all"),
            min_priority=NotificationPriority(data.get("min_priority", "low")),
        )

    def _serialize_notification(self, notif: Notification) -> dict:
        return {
            "id": notif.id,
            "title": notif.title,
            "body": notif.body,
            "category": notif.category.value,
            "priority": notif.priority.value,
            "provider": notif.provider,
            "conversation_id": notif.conversation_id,
            "message_id": notif.message_id,
            "channel": notif.channel.value,
            "read": notif.read,
            "action_url": notif.action_url,
            "metadata": notif.metadata,
            "created_at": notif.created_at.isoformat(),
        }

    def _deserialize_notification(self, data: dict) -> Notification:
        return Notification(
            id=data["id"],
            title=data["title"],
            body=data["body"],
            category=NotificationCategory(data["category"]),
            priority=NotificationPriority(data.get("priority", "normal")),
            provider=data.get("provider", ""),
            conversation_id=data.get("conversation_id", ""),
            message_id=data.get("message_id", ""),
            channel=NotificationChannel(data.get("channel", "desktop")),
            read=data.get("read", False),
            action_url=data.get("action_url", ""),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def on(self, event: str, handler):
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def _emit(self, event: str, data: Any):
        for handler in self._handlers.get(event, []):
            try:
                handler(data)
            except Exception:
                pass

    def notify(self, title: str, body: str, category: NotificationCategory = NotificationCategory.MESSAGE, priority: NotificationPriority = NotificationPriority.NORMAL, provider: str = "", conversation_id: str = "", message_id: str = "") -> Optional[Notification]:
        if self._is_quiet_hours() and priority not in (NotificationPriority.HIGH, NotificationPriority.URGENT):
            return None
        notif = Notification(
            id=f"notif_{datetime.now().timestamp()}",
            title=title,
            body=body,
            category=category,
            priority=priority,
            provider=provider,
            conversation_id=conversation_id,
            message_id=message_id,
        )
        self._notifications.append(notif)
        self._save_notifications()
        self._emit("notification", notif)
        return notif

    def mark_read(self, notification_id: str):
        for n in self._notifications:
            if n.id == notification_id:
                n.read = True
                self._save_notifications()
                break

    def mark_all_read(self):
        for n in self._notifications:
            n.read = True
        self._save_notifications()

    def get_unread(self) -> list[Notification]:
        return [n for n in self._notifications if not n.read]

    def get_recent(self, limit: int = 50) -> list[Notification]:
        return sorted(self._notifications, key=lambda n: n.created_at, reverse=True)[:limit]

    def get_by_priority(self, priority: NotificationPriority) -> list[Notification]:
        return [n for n in self._notifications if n.priority == priority]

    def get_by_category(self, category: NotificationCategory) -> list[Notification]:
        return [n for n in self._notifications if n.category == category]

    def get_rules(self) -> list[NotificationRule]:
        return self._rules

    def update_rule(self, rule_id: str, **kwargs) -> bool:
        for rule in self._rules:
            if rule.id == rule_id:
                for key, value in kwargs.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                self._save_rules()
                return True
        return False

    def clear_all(self):
        self._notifications.clear()
        self._save_notifications()

    def clear_by_category(self, category: NotificationCategory):
        self._notifications = [n for n in self._notifications if n.category != category]
        self._save_notifications()

    def _is_quiet_hours(self) -> bool:
        for rule in self._rules:
            if not rule.enabled and rule.quiet_hours_start and rule.quiet_hours_end:
                now = datetime.now()
                start = rule.quiet_hours_start.split(":")
                end = rule.quiet_hours_end.split(":")
                try:
                    start_h, start_m = int(start[0]), int(start[1])
                    end_h, end_m = int(end[0]), int(end[1])
                    current = now.hour * 60 + now.minute
                    start_min = start_h * 60 + start_m
                    end_min = end_h * 60 + end_m
                    if start_min <= current < end_min:
                        return True
                except (ValueError, IndexError):
                    pass
        return False
