from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


class InboxFilter(Enum):
    ALL = "all"
    UNREAD = "unread"
    IMPORTANT = "important"
    MENTIONS = "mentions"
    DIRECT = "direct"
    GROUPS = "groups"
    CHANNELS = "channels"
    EMAIL = "email"
    SMS = "sms"
    SCHEDULED = "scheduled"
    ARCHIVED = "archived"


class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    VOICE = "voice"
    STICKER = "sticker"
    GIF = "gif"
    LINK = "link"
    SYSTEM = "system"
    TEMPLATE = "template"


class MessagePriority(Enum):
    URGENT = "urgent"
    IMPORTANT = "important"
    NORMAL = "normal"
    LOW = "low"
    SPAM = "spam"


@dataclass
class MessageAttachment:
    type: str
    url: str
    name: str
    size: int = 0
    mime_type: str = ""
    thumbnail_url: str = ""


@dataclass
class UnifiedMessage:
    id: str
    provider: str
    account_id: str
    conversation_id: str
    sender_id: str
    sender_name: str
    content: str
    timestamp: datetime
    direction: str
    status: str
    message_type: MessageType = MessageType.TEXT
    priority: MessagePriority = MessagePriority.NORMAL
    attachments: list[MessageAttachment] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    read: bool = False
    archived: bool = False
    important: bool = False
    mentions: list[str] = field(default_factory=list)
    in_reply_to: str = ""


@dataclass
class Conversation:
    id: str
    provider: str
    participants: list[dict] = field(default_factory=list)
    last_message: Optional[UnifiedMessage] = None
    unread_count: int = 0
    pinned: bool = False
    archived: bool = False
    muted: bool = False
    updated_at: datetime = field(default_factory=datetime.now)
    subject: str = ""


class UnifiedInbox:
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path.home() / ".aetheros" / "automation" / "communications"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._messages: list[UnifiedMessage] = []
        self._conversations: dict[str, Conversation] = {}
        self._message_handlers: list[Callable] = []
        self._load()

    def _path(self) -> Path:
        return self._storage_path / "inbox.json"

    def _load(self):
        if self._path().exists():
            try:
                data = json.loads(self._path().read_text())
                for msg_data in data.get("messages", []):
                    self._messages.append(self._deserialize_message(msg_data))
                for conv_data in data.get("conversations", []):
                    conv = self._deserialize_conversation(conv_data)
                    self._conversations[conv.id] = conv
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        data = {
            "messages": [self._serialize_message(m) for m in self._messages[-1000:]],
            "conversations": [self._serialize_conversation(c) for c in self._conversations.values()],
        }
        self._path().write_text(json.dumps(data, indent=2, default=str))

    def _serialize_message(self, msg: UnifiedMessage) -> dict:
        return {
            "id": msg.id,
            "provider": msg.provider,
            "account_id": msg.account_id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender_name,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "direction": msg.direction,
            "status": msg.status,
            "message_type": msg.message_type.value,
            "priority": msg.priority.value,
            "attachments": [a.__dict__ for a in msg.attachments],
            "labels": msg.labels,
            "read": msg.read,
            "archived": msg.archived,
            "important": msg.important,
            "mentions": msg.mentions,
            "in_reply_to": msg.in_reply_to,
        }

    def _deserialize_message(self, data: dict) -> UnifiedMessage:
        return UnifiedMessage(
            id=data["id"],
            provider=data["provider"],
            account_id=data.get("account_id", ""),
            conversation_id=data["conversation_id"],
            sender_id=data["sender_id"],
            sender_name=data["sender_name"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            direction=data["direction"],
            status=data["status"],
            message_type=MessageType(data.get("message_type", "text")),
            priority=MessagePriority(data.get("priority", "normal")),
            attachments=[MessageAttachment(**a) for a in data.get("attachments", [])],
            labels=data.get("labels", []),
            read=data.get("read", False),
            archived=data.get("archived", False),
            important=data.get("important", False),
            mentions=data.get("mentions", []),
            in_reply_to=data.get("in_reply_to", ""),
        )

    def _serialize_conversation(self, conv: Conversation) -> dict:
        return {
            "id": conv.id,
            "provider": conv.provider,
            "participants": conv.participants,
            "last_message": self._serialize_message(conv.last_message) if conv.last_message else None,
            "unread_count": conv.unread_count,
            "pinned": conv.pinned,
            "archived": conv.archived,
            "muted": conv.muted,
            "updated_at": conv.updated_at.isoformat(),
            "subject": conv.subject,
        }

    def _deserialize_conversation(self, data: dict) -> Conversation:
        lm = None
        if data.get("last_message"):
            lm = self._deserialize_message(data["last_message"])
        return Conversation(
            id=data["id"],
            provider=data["provider"],
            participants=data.get("participants", []),
            last_message=lm,
            unread_count=data.get("unread_count", 0),
            pinned=data.get("pinned", False),
            archived=data.get("archived", False),
            muted=data.get("muted", False),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            subject=data.get("subject", ""),
        )

    def add_message(self, msg: UnifiedMessage):
        self._messages.append(msg)
        self._update_conversation(msg)
        self._save()
        for handler in self._message_handlers:
            try:
                handler(msg)
            except Exception:
                pass

    def on_message(self, handler: Callable):
        self._message_handlers.append(handler)

    def _update_conversation(self, msg: UnifiedMessage):
        conv = self._conversations.get(msg.conversation_id)
        if not conv:
            conv = Conversation(
                id=msg.conversation_id,
                provider=msg.provider,
                participants=[{"id": msg.sender_id, "name": msg.sender_name}],
                subject=msg.content[:100] if len(msg.content) > 100 else msg.content,
            )
            self._conversations[msg.conversation_id] = conv
        conv.last_message = msg
        conv.updated_at = datetime.now()
        if not msg.read and msg.direction == "incoming":
            conv.unread_count += 1

    def mark_read(self, message_id: str) -> bool:
        for msg in self._messages:
            if msg.id == message_id:
                if not msg.read:
                    msg.read = True
                    conv = self._conversations.get(msg.conversation_id)
                    if conv and conv.unread_count > 0:
                        conv.unread_count -= 1
                    self._save()
                return True
        return False

    def mark_conversation_read(self, conversation_id: str) -> bool:
        conv = self._conversations.get(conversation_id)
        if not conv:
            return False
        for msg in self._messages:
            if msg.conversation_id == conversation_id and not msg.read:
                msg.read = True
        conv.unread_count = 0
        self._save()
        return True

    def toggle_important(self, message_id: str) -> bool:
        for msg in self._messages:
            if msg.id == message_id:
                msg.important = not msg.important
                self._save()
                return True
        return False

    def toggle_archive(self, message_id: str) -> bool:
        for msg in self._messages:
            if msg.id == message_id:
                msg.archived = not msg.archived
                self._save()
                return True
        return False

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self._conversations.get(conversation_id)

    def get_conversation_messages(self, conversation_id: str) -> list[UnifiedMessage]:
        return [m for m in self._messages if m.conversation_id == conversation_id]

    def list_conversations(self) -> list[Conversation]:
        return sorted(self._conversations.values(), key=lambda c: c.updated_at, reverse=True)

    def filter_messages(self, filter_type: InboxFilter = InboxFilter.ALL, provider: str = "", search: str = "", limit: int = 100) -> list[UnifiedMessage]:
        msgs = self._messages
        if provider:
            msgs = [m for m in msgs if m.provider == provider]
        if filter_type == InboxFilter.UNREAD:
            msgs = [m for m in msgs if not m.read]
        elif filter_type == InboxFilter.IMPORTANT:
            msgs = [m for m in msgs if m.important]
        elif filter_type == InboxFilter.MENTIONS:
            msgs = [m for m in msgs if m.mentions]
        elif filter_type == InboxFilter.ARCHIVED:
            msgs = [m for m in msgs if m.archived]
        elif filter_type == InboxFilter.EMAIL:
            msgs = [m for m in msgs if m.provider == "gmail" or m.provider == "outlook"]
        elif filter_type == InboxFilter.SMS:
            msgs = [m for m in msgs if m.provider == "sms"]
        else:
            msgs = [m for m in msgs if not m.archived]
        if search:
            pattern = re.compile(re.escape(search), re.IGNORECASE)
            msgs = [m for m in msgs if pattern.search(m.content) or pattern.search(m.sender_name)]
        return sorted(msgs, key=lambda m: m.timestamp, reverse=True)[:limit]

    def search_messages(self, query: str, provider: str = "") -> list[UnifiedMessage]:
        return self.filter_messages(InboxFilter.ALL, provider, query, limit=200)

    def unread_count(self) -> int:
        return sum(1 for m in self._messages if not m.read and m.direction == "incoming")

    def conversation_unread_count(self, conversation_id: str) -> int:
        conv = self._conversations.get(conversation_id)
        return conv.unread_count if conv else 0

    def get_messages_by_provider(self, provider: str) -> list[UnifiedMessage]:
        return [m for m in self._messages if m.provider == provider]

    def clear(self):
        self._messages.clear()
        self._conversations.clear()
        self._save()
