"""
AetherOS Ambient Workspace, Voice & Desktop Integration Layer.

Provides a unified interaction layer for voice, desktop, notifications,
workspace awareness, session continuity, and human interaction.
Integrates with the AetherOS Kernel (event bus, lifecycle), Swarm,
Memory, Engineering Platform, and Event Bus.

Architecture
-----------
The interaction layer sits alongside the kernel, swarm, memory, and
engineering systems, providing a unified interface for all input/output
channels:

    ┌────────────────────────────────────────────────────────┐
    │              InteractionManager (Unified API)            │
    │                                                         │
    │  ┌────────────────┐  ┌────────────────┐               │
    │  │ Desktop        │  │ Voice          │               │
    │  │  WindowTracker │  │  SpeechInput   │               │
    │  │  Workspace     │  │  SpeechOutput  │               │
    │  │  Clipboard     │  │  WakeWord      │               │
    │  │  Notifications │  │  AudioPipeline │               │
    │  │  Shortcuts     │  │  Transcription │               │
    │  └────────────────┘  └────────────────┘               │
    │                                                         │
    │  ┌────────────────┐  ┌────────────────┐               │
    │  │ Presence       │  │ Session        │               │
    │  │  ActivityDetect│  │  SessionMgr    │               │
    │  │  IdleMonitor   │  │  History       │               │
    │  │  FocusMode     │  │  Preferences   │               │
    │  │  ContextDetect │  │  UI Events     │               │
    │  └────────────────┘  └────────────────┘               │
    └────────────────────────────────────────────────────────┘
         │
         ▼
    ┌────────────────────────────────────────────────────────┐
    │   AetherOS Kernel │ Swarm │ Memory │ Engineering        │
    │   EventBus │ Lifecycle │ Permissions │ State            │
    └────────────────────────────────────────────────────────┘

Design Principles:
- Privacy-first: all capabilities require explicit permissions
- Modular: every subsystem is optional and independently testable
- Plugin-extensible: voice providers, desktop adapters, notification channels
- Backward compatible: existing code paths remain unchanged
- Vendor-agnostic: no hardcoded vendor-specific services
"""

from interaction.interaction_manager import (
    InteractionManager,
    InteractionConfig,
    InteractionChannel,
    InteractionEvent,
    InteractionState,
    InteractionResult,
)
from interaction.session_manager import (
    SessionManager,
    SessionState,
    SessionContinuity,
    SessionSnapshot,
    SessionResumeContext,
)
from interaction.desktop.desktop_manager import (
    DesktopManager,
    DesktopConfig,
    DesktopEvent,
    DesktopPermission,
)
from interaction.desktop.window_tracker import (
    WindowTracker,
    WindowInfo,
    WindowEvent,
)
from interaction.desktop.workspace_monitor import (
    WorkspaceMonitor,
    WorkspaceInfo,
    WorkspaceChange,
)
from interaction.desktop.clipboard import (
    ClipboardMonitor,
    ClipboardEntry,
    ClipboardPermission,
)
from interaction.desktop.notifications import (
    NotificationManager,
    Notification,
    NotificationPriority,
    NotificationAction,
    NotificationChannel,
)
from interaction.desktop.shortcuts import (
    ShortcutManager,
    GlobalShortcut,
    ShortcutAction,
)
from interaction.voice.voice_manager import (
    VoiceManager,
    VoiceConfig,
    VoiceSession,
    VoiceEvent,
    VoiceState,
)
from interaction.voice.speech_input import (
    SpeechInputManager,
    SpeechInputAdapter,
    SpeechInputResult,
    SpeechInputEvent,
)
from interaction.voice.speech_output import (
    SpeechOutputManager,
    SpeechOutputAdapter,
    SpeechOutputResult,
    SpeechOutputEvent,
)
from interaction.voice.wake_word import (
    WakeWordEngine,
    WakeWordConfig,
    WakeWordEvent,
    WakeWordState,
)
from interaction.voice.audio_pipeline import (
    AudioPipeline,
    AudioConfig,
    AudioFormat,
    AudioSource,
    AudioSink,
)
from interaction.voice.transcription import (
    TranscriptionEngine,
    TranscriptionConfig,
    TranscriptionResult,
)
from interaction.presence.activity_detector import (
    ActivityDetector,
    ActivityEvent,
    ActivityType,
    ActivityState,
)
from interaction.presence.idle_monitor import (
    IdleMonitor,
    IdleEvent,
    IdleState,
)
from interaction.presence.focus_mode import (
    FocusMode,
    FocusConfig,
    FocusEvent,
    FocusState,
)
from interaction.presence.context_detector import (
    ContextDetector,
    WorkspaceContext,
    ContextEvent,
)
from interaction.interaction_history import (
    InteractionHistory,
    HistoryEntry,
    HistoryQuery,
    HistorySummary,
)
from interaction.ui_events import (
    UIEvent,
    UIEventType,
    UIEventHandler,
    EventDispatch,
)
from interaction.preferences import (
    InteractionPreferences,
    AccessibilityPrefs,
    NotificationPrefs,
    VoicePrefs,
    PrivacyPrefs,
    PermissionSetting,
)

__all__ = [
    # Interaction Manager
    "InteractionManager",
    "InteractionConfig",
    "InteractionChannel",
    "InteractionEvent",
    "InteractionState",
    "InteractionResult",
    # Session Manager
    "SessionManager",
    "SessionState",
    "SessionContinuity",
    "SessionSnapshot",
    "SessionResumeContext",
    # Desktop
    "DesktopManager",
    "DesktopConfig",
    "DesktopEvent",
    "DesktopPermission",
    "WindowTracker",
    "WindowInfo",
    "WindowEvent",
    "WorkspaceMonitor",
    "WorkspaceInfo",
    "WorkspaceChange",
    "ClipboardMonitor",
    "ClipboardEntry",
    "ClipboardPermission",
    "NotificationManager",
    "Notification",
    "NotificationPriority",
    "NotificationAction",
    "NotificationChannel",
    "ShortcutManager",
    "GlobalShortcut",
    "ShortcutAction",
    # Voice
    "VoiceManager",
    "VoiceConfig",
    "VoiceSession",
    "VoiceEvent",
    "VoiceState",
    "SpeechInputManager",
    "SpeechInputAdapter",
    "SpeechInputResult",
    "SpeechInputEvent",
    "SpeechOutputManager",
    "SpeechOutputAdapter",
    "SpeechOutputResult",
    "SpeechOutputEvent",
    "WakeWordEngine",
    "WakeWordConfig",
    "WakeWordEvent",
    "WakeWordState",
    "AudioPipeline",
    "AudioConfig",
    "AudioFormat",
    "AudioSource",
    "AudioSink",
    "TranscriptionEngine",
    "TranscriptionConfig",
    "TranscriptionResult",
    # Presence
    "ActivityDetector",
    "ActivityEvent",
    "ActivityType",
    "ActivityState",
    "IdleMonitor",
    "IdleEvent",
    "IdleState",
    "FocusMode",
    "FocusConfig",
    "FocusEvent",
    "FocusState",
    "ContextDetector",
    "WorkspaceContext",
    "ContextEvent",
    # History
    "InteractionHistory",
    "HistoryEntry",
    "HistoryQuery",
    "HistorySummary",
    # UI Events
    "UIEvent",
    "UIEventType",
    "UIEventHandler",
    "EventDispatch",
    # Preferences
    "InteractionPreferences",
    "AccessibilityPrefs",
    "NotificationPrefs",
    "VoicePrefs",
    "PrivacyPrefs",
    "PermissionSetting",
]
