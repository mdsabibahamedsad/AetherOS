"""Jarvis Mode — models and domain types.

Shared enums and dataclasses for the Jarvis runtime, voice, conversation,
presence, proactive, mission, briefing, and accessibility subsystems.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _now() -> float:
    return time.time()


class JarvisState(Enum):
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    RUNNING = "running"
    SLEEPING = "sleeping"
    PAUSED = "paused"
    SHUTDOWN = "shutdown"
    ERROR = "error"
    RECOVERING = "recovering"


class ConversationMode(Enum):
    VOICE_ONLY = "voice_only"
    TEXT_ONLY = "text_only"
    MIXED = "mixed"
    CONTINUOUS = "continuous"
    PUSH_TO_TALK = "push_to_talk"
    HANDS_FREE = "hands_free"
    OFF = "off"


class PresenceState(Enum):
    UNKNOWN = "unknown"
    ACTIVE = "active"
    IDLE = "idle"
    AWAY = "away"
    LOCKED = "locked"
    SLEEPING = "sleeping"


class WakeWordSource(Enum):
    NONE = "none"
    VOICE = "voice"
    PUSH_TO_TALK = "push_to_talk"
    KEYBOARD = "keyboard"


class VoiceTone(Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CONCISE = "concise"
    ENCOURAGING = "encouraging"
    URGENT = "urgent"
    EMPATHETIC = "empathetic"


class MissionStatus(Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionStepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SuggestionStatus(Enum):
    PENDING = "pending"
    DISMISSED = "dismissed"
    ACCEPTED = "accepted"
    EXPIRED = "expired"


class PermissionDecision(Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    PENDING = "pending"


class JarvisMode(Enum):
    """Top-level operational modes of the Jarvis runtime."""
    INTERACTIVE = "interactive"
    MISSION = "mission"
    OBSERVE_ONLY = "observe_only"
    QUIET = "quiet"
    OFF = "off"


@dataclass
class JarvisConfig:
    """Persisted configuration for the Jarvis runtime."""
    enabled: bool = True
    mode: JarvisMode = JarvisMode.INTERACTIVE
    wake_phrases: List[str] = field(default_factory=lambda: ["aether", "jarvis"])
    conversation_mode: ConversationMode = ConversationMode.MIXED
    stt_provider: str = "local"
    tts_provider: str = "local"
    mic_device: str = ""
    speaker_device: str = ""
    wake_word_enabled: bool = True
    noise_suppression: bool = True
    echo_cancellation: bool = True
    streaming_enabled: bool = True
    interruption_enabled: bool = True
    confirm_destructive: bool = True
    auto_briefing_enabled: bool = True
    proactive_enabled: bool = True
    proactive_min_interval_seconds: float = 300.0
    presence_idle_after_seconds: float = 120.0
    presence_away_after_seconds: float = 900.0
    battery_saver_threshold: float = 20.0
    resource_limits: Dict[str, float] = field(default_factory=dict)
    voice_profile: str = "default"
    language: str = "en"
    voice_speed: float = 1.0
    voice_pitch: float = 1.0
    voice_emotion: str = "professional"
    captions_enabled: bool = False
    high_contrast: bool = False
    reduced_motion: bool = False
    screen_reader: bool = False
    keyboard_shortcuts: bool = True
    muted_notifications: List[str] = field(default_factory=list)
    schedule: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                out[key] = value.value
            elif isinstance(value, list):
                out[key] = list(value)
            elif isinstance(value, dict):
                out[key] = dict(value)
            else:
                out[key] = value
        return out

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JarvisConfig":
        config = cls()
        enums = {
            "mode": JarvisMode,
            "conversation_mode": ConversationMode,
        }
        for key, value in (data or {}).items():
            if not hasattr(config, key):
                continue
            if key in enums:
                try:
                    setattr(config, key, enums[key](value))
                except ValueError:
                    pass
            elif isinstance(getattr(config, key), list):
                setattr(config, key, list(value))
            elif isinstance(getattr(config, key), dict):
                setattr(config, key, dict(value))
            else:
                setattr(config, key, value)
        return config


@dataclass
class WakeEvent:
    timestamp: float = field(default_factory=_now)
    phrase: str = ""
    confidence: float = 0.0
    source: WakeWordSource = WakeWordSource.VOICE
    verified: bool = False
    trigger: str = "wake_phrase"


@dataclass
class Transcript:
    text: str = ""
    language: str = "en"
    confidence: float = 0.0
    is_final: bool = True
    timestamp: float = field(default_factory=_now)


@dataclass
class Utterance:
    """A full user turn, from voice or text."""
    text: str = ""
    source: str = "text"  # "voice" | "text" | "command"
    transcript: Optional[Transcript] = None
    timestamp: float = field(default_factory=_now)
    follow_up: bool = False


@dataclass
class DialogueTurn:
    id: str = field(default_factory=lambda: _new_id("turn"))
    role: str = "user"
    text: str = ""
    timestamp: float = field(default_factory=_now)
    corrected: bool = False
    clarification: bool = False


@dataclass
class Suggestion:
    id: str = field(default_factory=lambda: _new_id("sugg"))
    title: str = ""
    body: str = ""
    reason: str = ""
    action: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    status: SuggestionStatus = SuggestionStatus.PENDING
    confidence: float = 0.0
    created_at: float = field(default_factory=_now)
    expires_at: float = 0.0
    source: str = "proactive"


@dataclass
class NotificationItem:
    id: str = field(default_factory=lambda: _new_id("notif"))
    title: str = ""
    body: str = ""
    source: str = ""
    priority: NotificationPriority = NotificationPriority.MEDIUM
    group_key: str = ""
    timestamp: float = field(default_factory=_now)
    muted: bool = False
    duplicate_of: str = ""


@dataclass
class BriefingSection:
    title: str = ""
    items: List[str] = field(default_factory=list)
    empty_message: str = ""


@dataclass
class DailyBriefing:
    date: str = ""
    sections: List[BriefingSection] = field(default_factory=list)
    generated_at: float = field(default_factory=_now)

    def to_markdown(self) -> str:
        lines = [f"# Daily Briefing — {self.date}", ""]
        for section in self.sections:
            lines.append(f"## {section.title}")
            if section.items:
                for item in section.items:
                    lines.append(f"- {item}")
            else:
                lines.append(f"_{section.empty_message}_")
            lines.append("")
        return "\n".join(lines).strip()


@dataclass
class MissionPlan:
    id: str = field(default_factory=lambda: _new_id("mission"))
    goal: str = ""
    status: MissionStatus = MissionStatus.DRAFT
    created_at: float = field(default_factory=_now)
    approved_at: float = 0.0
    approval_required: bool = True
    steps: List["MissionStep"] = field(default_factory=list)
    summary: str = ""


@dataclass
class MissionStep:
    id: str = field(default_factory=lambda: _new_id("step"))
    description: str = ""
    tool: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    status: MissionStepStatus = MissionStepStatus.PENDING
    result: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    approval_required: bool = False


@dataclass
class ContextSnapshot:
    timestamp: float = field(default_factory=_now)
    app: str = ""
    project: str = ""
    file: str = ""
    selected_text: str = ""
    clipboard: str = ""
    running_agents: List[str] = field(default_factory=list)
    providers: List[str] = field(default_factory=list)
    battery_percent: Optional[float] = None
    network: str = "unknown"
    downloads_dir: str = ""
    open_files: List[str] = field(default_factory=list)
    workspace: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: (list(v) if isinstance(v, (list, tuple)) else v) for k, v in self.__dict__.items()}


@dataclass
class MissionReport:
    mission_id: str = ""
    goal: str = ""
    status: MissionStatus = MissionStatus.DRAFT
    steps: List[MissionStep] = field(default_factory=list)
    summary: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [f"# Mission Report — {self.goal}", "", f"Status: {self.status.value}", ""]
        for step in self.steps:
            icon = {
                MissionStepStatus.COMPLETED: "✓",
                MissionStepStatus.FAILED: "✗",
                MissionStepStatus.RUNNING: "…",
                MissionStepStatus.PENDING: "·",
                MissionStepStatus.BLOCKED: "!",
                MissionStepStatus.SKIPPED: "–",
            }.get(step.status, "·")
            lines.append(f"- {icon} **{step.description}** — {step.status.value}")
            if step.result:
                lines.append(f"  - {step.result[:200]}")
        if self.errors:
            lines.append("")
            lines.append("## Errors")
            for err in self.errors:
                lines.append(f"- {err}")
        return "\n".join(lines)


@dataclass
class VoiceProfileData:
    name: str = "default"
    voice: str = ""
    speed: float = 1.0
    pitch: float = 1.0
    language: str = "en"
    emotion: str = "professional"
    enabled: bool = True
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoiceProfileData":
        profile = cls()
        for key, value in (data or {}).items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        return profile


@dataclass
class PermissionContext:
    permission: str = ""
    requester: str = "jarvis"
    reason: str = ""
    risk_level: str = "low"
    action: str = ""
    target: str = ""
    decision: PermissionDecision = PermissionDecision.PENDING
    granted_at: float = 0.0
