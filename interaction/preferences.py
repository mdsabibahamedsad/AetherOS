"""
Interaction Preferences — User preferences for interaction channels.

Manages accessibility, notification, voice, and privacy preferences.
Preferences are stored separately from interaction history for privacy.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PermissionSetting(enum.Enum):
    """Permission state for a capability."""
    ALWAYS_ALLOW = "always_allow"
    ASK = "ask"
    DENY = "deny"
    GRANTED_SESSION = "granted_session"
    DENIED_SESSION = "denied_session"


@dataclass
class AccessibilityPrefs:
    """Accessibility preferences.

    Attributes:
        keyboard_navigation: Enable keyboard-first interaction
        screen_reader_compatible: Enable screen reader optimizations
        caption_speech: Show captions for speech output
        high_contrast: Use high contrast UI
        large_text: Use larger text sizes
        reduce_motion: Reduce animations
        announcement_volume: Volume for screen reader announcements
    """
    keyboard_navigation: bool = True
    screen_reader_compatible: bool = False
    caption_speech: bool = True
    high_contrast: bool = False
    large_text: bool = False
    reduce_motion: bool = False
    announcement_volume: float = 0.7


@dataclass
class NotificationPrefs:
    """Notification preferences.

    Attributes:
        enabled: Master toggle for notifications
        show_desktop: Show desktop notifications
        play_sound: Play notification sounds
        show_preview: Show message preview in notifications
        group_by_source: Group notifications by source
        quiet_hours_start: Quiet hours start time (HH:MM)
        quiet_hours_end: Quiet hours end time (HH:MM)
        priority_threshold: Minimum priority to show
        max_per_minute: Max notifications per minute
    """
    enabled: bool = True
    show_desktop: bool = True
    play_sound: bool = False
    show_preview: bool = True
    group_by_source: bool = True
    quiet_hours_start: str = ""
    quiet_hours_end: str = ""
    priority_threshold: str = "normal"
    max_per_minute: int = 5


@dataclass
class VoicePrefs:
    """Voice interaction preferences.

    Attributes:
        enabled: Master toggle for voice
        push_to_talk_key: Key binding for push-to-talk
        wake_word_enabled: Enable wake word
        wake_word: Wake word phrase
        speech_output_enabled: Enable speech output
        speech_output_voice: Preferred voice
        speech_output_speed: Speech speed (0.5 - 2.0)
        auto_stop_silence: Auto-stop on silence
        silence_timeout: Silence timeout seconds
        stt_provider: STT provider preference
        tts_provider: TTS provider preference
    """
    enabled: bool = False
    push_to_talk_key: str = "Ctrl+Space"
    wake_word_enabled: bool = False
    wake_word: str = "aetheros"
    speech_output_enabled: bool = True
    speech_output_voice: str = ""
    speech_output_speed: float = 1.0
    auto_stop_silence: bool = True
    silence_timeout: float = 3.0
    stt_provider: str = ""
    tts_provider: str = ""


@dataclass
class PrivacyPrefs:
    """Privacy and permission preferences.

    Attributes:
        microphone: Microphone permission
        clipboard: Clipboard access permission
        desktop_context: Desktop context permission
        notifications: Notification permission
        workspace_metadata: Workspace metadata permission
        file_selection: File selection awareness
        store_history: Store interaction history
        share_usage_stats: Share anonymous usage stats
    """
    microphone: PermissionSetting = PermissionSetting.ASK
    clipboard: PermissionSetting = PermissionSetting.DENY
    desktop_context: PermissionSetting = PermissionSetting.ASK
    notifications: PermissionSetting = PermissionSetting.ASK
    workspace_metadata: PermissionSetting = PermissionSetting.ASK
    file_selection: PermissionSetting = PermissionSetting.DENY
    store_history: bool = True
    share_usage_stats: bool = False


@dataclass
class InteractionPreferences:
    """Complete interaction preferences.

    Attributes:
        version: Preferences version (for migration)
        accessibility: Accessibility preferences
        notifications: Notification preferences
        voice: Voice interaction preferences
        privacy: Privacy and permission preferences
        custom: Custom/extensible preferences
    """
    version: int = 1
    accessibility: AccessibilityPrefs = field(default_factory=AccessibilityPrefs)
    notifications: NotificationPrefs = field(default_factory=NotificationPrefs)
    voice: VoicePrefs = field(default_factory=VoicePrefs)
    privacy: PrivacyPrefs = field(default_factory=PrivacyPrefs)
    custom: Dict[str, Any] = field(default_factory=dict)


class PreferencesManager:
    """Manages user interaction preferences with persistence.

    Stores preferences separately from interaction history for
    privacy isolation. Reads from a preferences file path.

    Usage:
        mgr = PreferencesManager("~/.aetheros/interaction_prefs.json")
        prefs = mgr.load()

        prefs.voice.push_to_talk_key = "Ctrl+Shift+V"
        mgr.save(prefs)
    """

    def __init__(self, prefs_path: Optional[str] = None):
        self._lock = threading.RLock()
        self._path = Path(prefs_path).expanduser() if prefs_path else None

    def load(self) -> InteractionPreferences:
        """Load preferences from disk or return defaults.

        Returns:
            InteractionPreferences (loaded or defaults)
        """
        if not self._path or not self._path.exists():
            return InteractionPreferences()

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return self._from_dict(data)
        except Exception as exc:
            logger.warning("PreferencesManager: load failed: %s", exc)
            return InteractionPreferences()

    def save(self, prefs: InteractionPreferences) -> bool:
        """Save preferences to disk.

        Args:
            prefs: Preferences to save

        Returns:
            True if saved
        """
        if not self._path:
            return False

        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._to_dict(prefs), indent=2),
                encoding="utf-8",
            )
            return True
        except Exception as exc:
            logger.warning("PreferencesManager: save failed: %s", exc)
            return False

    def reset(self) -> None:
        """Reset preferences to defaults."""
        if self._path and self._path.exists():
            try:
                self._path.unlink()
            except Exception as exc:
                logger.warning("PreferencesManager: reset failed: %s", exc)

    @staticmethod
    def _from_dict(data: Dict[str, Any]) -> InteractionPreferences:
        """Deserialize a dict to InteractionPreferences."""
        prefs = InteractionPreferences()
        prefs.version = data.get("version", 1)

        acc = data.get("accessibility", {})
        if isinstance(acc, dict):
            for key, value in acc.items():
                if hasattr(prefs.accessibility, key):
                    setattr(prefs.accessibility, key, value)

        notif = data.get("notifications", {})
        if isinstance(notif, dict):
            for key, value in notif.items():
                if hasattr(prefs.notifications, key):
                    setattr(prefs.notifications, key, value)

        voice = data.get("voice", {})
        if isinstance(voice, dict):
            for key, value in voice.items():
                if hasattr(prefs.voice, key):
                    setattr(prefs.voice, key, value)

        priv = data.get("privacy", {})
        if isinstance(priv, dict):
            for key, value in priv.items():
                if hasattr(prefs.privacy, key):
                    if key in ("microphone", "clipboard", "desktop_context",
                               "notifications", "workspace_metadata", "file_selection"):
                        setattr(prefs.privacy, key, PermissionSetting(value))
                    else:
                        setattr(prefs.privacy, key, value)

        prefs.custom = data.get("custom", {})
        return prefs

    @staticmethod
    def _to_dict(prefs: InteractionPreferences) -> Dict[str, Any]:
        """Serialize InteractionPreferences to a dict."""
        return {
            "version": prefs.version,
            "accessibility": {
                "keyboard_navigation": prefs.accessibility.keyboard_navigation,
                "screen_reader_compatible": prefs.accessibility.screen_reader_compatible,
                "caption_speech": prefs.accessibility.caption_speech,
                "high_contrast": prefs.accessibility.high_contrast,
                "large_text": prefs.accessibility.large_text,
                "reduce_motion": prefs.accessibility.reduce_motion,
                "announcement_volume": prefs.accessibility.announcement_volume,
            },
            "notifications": {
                "enabled": prefs.notifications.enabled,
                "show_desktop": prefs.notifications.show_desktop,
                "play_sound": prefs.notifications.play_sound,
                "show_preview": prefs.notifications.show_preview,
                "group_by_source": prefs.notifications.group_by_source,
                "quiet_hours_start": prefs.notifications.quiet_hours_start,
                "quiet_hours_end": prefs.notifications.quiet_hours_end,
                "priority_threshold": prefs.notifications.priority_threshold,
                "max_per_minute": prefs.notifications.max_per_minute,
            },
            "voice": {
                "enabled": prefs.voice.enabled,
                "push_to_talk_key": prefs.voice.push_to_talk_key,
                "wake_word_enabled": prefs.voice.wake_word_enabled,
                "wake_word": prefs.voice.wake_word,
                "speech_output_enabled": prefs.voice.speech_output_enabled,
                "speech_output_voice": prefs.voice.speech_output_voice,
                "speech_output_speed": prefs.voice.speech_output_speed,
                "auto_stop_silence": prefs.voice.auto_stop_silence,
                "silence_timeout": prefs.voice.silence_timeout,
                "stt_provider": prefs.voice.stt_provider,
                "tts_provider": prefs.voice.tts_provider,
            },
            "privacy": {
                "microphone": prefs.privacy.microphone.value,
                "clipboard": prefs.privacy.clipboard.value,
                "desktop_context": prefs.privacy.desktop_context.value,
                "notifications": prefs.privacy.notifications.value,
                "workspace_metadata": prefs.privacy.workspace_metadata.value,
                "file_selection": prefs.privacy.file_selection.value,
                "store_history": prefs.privacy.store_history,
                "share_usage_stats": prefs.privacy.share_usage_stats,
            },
            "custom": prefs.custom,
        }
