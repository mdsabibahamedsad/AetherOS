"""
Universal Communication Model (Master 16 Phases 1-8).

Normalized types shared by all providers. Provider-specific behavior
remains behind adapters; this module defines the DATA CONTRACT only.
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Channels (Phase 2)
# ---------------------------------------------------------------------------

class Channel(str, enum.Enum):
    EMAIL = "email"
    CHAT = "chat"
    SMS = "sms"
    VOICE = "voice"
    VIDEO = "video"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    CALENDAR = "calendar"
    TEAM_WORKSPACE = "team_workspace"


# ---------------------------------------------------------------------------
# Sensitivity / Priority (Phases 3, 82)
# ---------------------------------------------------------------------------

class Sensitivity(enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class Priority(enum.Enum):
    CRITICAL = 4
    HIGH = 3
    NORMAL = 2
    LOW = 1
    SILENT = 0


# ---------------------------------------------------------------------------
# Message status lifecycle (Phase 33)
# ---------------------------------------------------------------------------

class SendStatus(enum.Enum):
    DRAFT = "draft"
    PENDING_CONFIRMATION = "pending_confirmation"
    QUEUED = "queued"
    SENT = "sent"
    PARTIAL = "partial"
    FAILED = "failed"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Attachment (Phases 20-22)
# ---------------------------------------------------------------------------

@dataclass
class CommunicationAttachment:
    filename: str
    mime_type: str = ""
    size_bytes: int = 0
    sha256: str = ""
    source_path: str = ""
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    scan_state: str = "unscanned"     # unscanned | clean | flagged | blocked

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.value if isinstance(v, enum.Enum) else v
                for k, v in self.__dict__.items()}


# ---------------------------------------------------------------------------
# Identity model (Phase 5)
# ---------------------------------------------------------------------------

@dataclass
class ContactPoint:
    address: str                       # email, phone, handle
    channel: Channel
    verified: bool = False
    display_name: str = ""

    def __post_init__(self):
        if isinstance(self.channel, str):
            self.channel = Channel(self.channel)


@dataclass
class Identity:
    identity_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    display_name: str = ""
    contact_points: List[ContactPoint] = field(default_factory=list)
    organization: str = ""
    confidence: float = 1.0            # identity resolution confidence
    provenance: str = ""               # how this identity was established
    created_at: float = field(default_factory=time.time)

    def addresses(self) -> List[str]:
        return [cp.address for cp in self.contact_points]


# ---------------------------------------------------------------------------
# Account (Phases 6-7)
# ---------------------------------------------------------------------------

@dataclass
class CommAccount:
    account_id: str
    provider: str                      # gmail, outlook, telegram, slack, twilio…
    channel: Channel
    display_name: str = ""
    address: str = ""                  # sending address / bot handle / number
    is_default: bool = False
    authorized: bool = True
    scopes: FrozenSet[str] = frozenset()

    def __post_init__(self):
        if isinstance(self.channel, str):
            self.channel = Channel(self.channel)


# ---------------------------------------------------------------------------
# Recipient model (Phase 8)
# ---------------------------------------------------------------------------

@dataclass
class Recipient:
    address: str
    role: str = "to"                   # to | cc | bcc | attendee
    display_name: str = ""
    identity_id: Optional[str] = None  # resolved Identity reference
    verified: bool = False             # recipient verification passed
    external: bool = False             # outside user's known org
    risk_flags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CommunicationMessage (Phase 1)
# ---------------------------------------------------------------------------

@dataclass
class CommunicationMessage:
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    conversation_id: str = ""
    provider: str = ""                 # gmail, telegram, slack, twilio…
    channel: Channel = Channel.CHAT
    sender: str = ""
    recipients: List[Recipient] = field(default_factory=list)
    cc: List[Recipient] = field(default_factory=list)
    bcc: List[Recipient] = field(default_factory=list)
    subject: str = ""
    body: str = ""
    attachments: List[CommunicationAttachment] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    reply_to: Optional[str] = None
    thread_id: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    priority: Priority = Priority.NORMAL
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    status: SendStatus = SendStatus.DRAFT
    metadata: Dict[str, Any] = field(default_factory=dict)
    authorization_context: Dict[str, Any] = field(default_factory=dict)
    draft_id: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.channel, str):
            self.channel = Channel(self.channel)
        if isinstance(self.priority, int):
            self.priority = Priority(self.priority)
        if isinstance(self.sensitivity, str):
            self.sensitivity = Sensitivity(self.sensitivity)
        if isinstance(self.status, str):
            self.status = SendStatus(self.status)

    @property
    def all_recipient_addresses(self) -> List[str]:
        return ([r.address for r in self.recipients]
                + [r.address for r in self.cc]
                + [r.address for r in self.bcc])

    @property
    def all_recipient_objects(self) -> List["Recipient"]:
        return list(self.recipients) + list(self.cc) + list(self.bcc)

    @property
    def total_recipients(self) -> int:
        return len(self.recipients) + len(self.cc) + len(self.bcc)

    def to_dict(self) -> Dict[str, Any]:
        def _ser(obj):
            if hasattr(obj, "__dict__") and not isinstance(obj, dict):
                if isinstance(obj, enum.Enum):
                    return obj.value
                return {k: _ser(v) for k, v in obj.__dict__.items()}
            if isinstance(obj, list):
                return [_ser(i) for i in obj]
            return obj
        return _ser(self.__dict__)


# ---------------------------------------------------------------------------
# Provider capability discovery (Phase 4)
# ---------------------------------------------------------------------------

class ProviderCapability(enum.Enum):
    SEND = "send"
    RECEIVE = "receive"
    LIST = "list"
    SEARCH = "search"
    REPLY = "reply"
    FORWARD = "forward"
    ARCHIVE = "archive"
    DELETE = "delete"
    LABEL = "label"
    THREAD = "thread"
    ATTACHMENT = "attachment"
    REACTION = "reaction"
    PRESENCE = "presence"
    CALENDAR = "calendar"
    MEETING = "meeting"
    DRAFT = "draft"


@dataclass
class ProviderInfo:
    name: str
    channel: Channel
    capabilities: FrozenSet[ProviderCapability]
    auth_method: str                    # oauth2 | api_key | basic | token
    rate_limit_per_minute: Optional[int] = None
    max_message_length: Optional[int] = None
    max_attachment_mb: Optional[float] = None
    api_version: str = ""

    def supports(self, cap: ProviderCapability) -> bool:
        return cap in self.capabilities


# ---------------------------------------------------------------------------
# Registry of known providers (populated from audit findings)
# ---------------------------------------------------------------------------

KNOWN_PROVIDERS: Dict[str, ProviderInfo] = {
    "gmail": ProviderInfo(
        name="gmail", channel=Channel.EMAIL,
        capabilities=frozenset({ProviderCapability.SEND, ProviderCapability.RECEIVE,
                                ProviderCapability.LIST, ProviderCapability.SEARCH,
                                ProviderCapability.REPLY, ProviderCapability.DRAFT,
                                ProviderCapability.ARCHIVE, ProviderCapability.LABEL,
                                ProviderCapability.THREAD, ProviderCapability.ATTACHMENT}),
        auth_method="oauth2", max_message_length=25000),
    "outlook": ProviderInfo(
        name="outlook", channel=Channel.EMAIL,
        capabilities=frozenset({ProviderCapability.SEND, ProviderCapability.RECEIVE,
                                ProviderCapability.LIST, ProviderCapability.SEARCH}),
        auth_method="oauth2", max_message_length=25000),
    "telegram": ProviderInfo(
        name="telegram", channel=Channel.CHAT,
        capabilities=frozenset({ProviderCapability.SEND, ProviderCapability.RECEIVE,
                                ProviderCapability.THREAD, ProviderCapability.ATTACHMENT,
                                ProviderCapability.REACTION}),
        auth_method="token", rate_limit_per_minute=30,
        max_message_length=4096, max_attachment_mb=50),
    "slack": ProviderInfo(
        name="slack", channel=Channel.CHAT,
        capabilities=frozenset({ProviderCapability.SEND, ProviderCapability.RECEIVE,
                                ProviderCapability.THREAD, ProviderCapability.ATTACHMENT,
                                ProviderCapability.REACTION, ProviderCapability.PRESENCE}),
        auth_method="token", max_message_length=39000),
    "twilio_sms": ProviderInfo(
        name="twilio_sms", channel=Channel.SMS,
        capabilities=frozenset({ProviderCapability.SEND, ProviderCapability.RECEIVE}),
        auth_method="basic", max_message_length=1600),
    "webhook": ProviderInfo(
        name="webhook", channel=Channel.WEBHOOK,
        capabilities=frozenset({ProviderCapability.SEND, ProviderCapability.RECEIVE}),
        auth_method="api_key", rate_limit_per_minute=30, max_message_length=1000000),
}


def get_provider_info(name: str) -> Optional[ProviderInfo]:
    return KNOWN_PROVIDERS.get(name.lower())


def register_provider(info: ProviderInfo) -> None:
    KNOWN_PROVIDERS[info.name.lower()] = info


__all__ = [
    "Channel", "Sensitivity", "Priority", "SendStatus",
    "CommunicationAttachment", "Identity", "ContactPoint",
    "CommAccount", "Recipient", "CommunicationMessage",
    "ProviderCapability", "ProviderInfo",
    "KNOWN_PROVIDERS", "get_provider_info", "register_provider",
]
