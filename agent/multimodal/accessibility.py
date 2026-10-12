"""Enhanced Multimodal Accessibility (Phase 75 of Master Prompt 10).

Extends the existing aetheros_voice.accessibility with multimodal features:
- Screen descriptions for visually impaired users
- OCR-based document reading
- Voice control for all modalities
- Speech output for visual content
- Visual assistance for hearing impaired
- High-contrast UI modes
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from agent.multimodal.media_abstraction import MediaObject, MediaType, SensitivityLevel
from agent.multimodal.perception import ocr_media, analyze_image, transcribe_audio, synthesize_speech
from agent.multimodal.local_models import process_locally, can_process_locally

logger = logging.getLogger(__name__)


class AccessibilityMode(Enum):
    """Accessibility modes for different user needs."""
    SCREEN_READER = "screen_reader"      # Full screen description
    LOW_VISION = "low_vision"            # High contrast, magnification
    VOICE_CONTROL = "voice_control"      # Voice-first interaction
    HEARING_IMPAIRED = "hearing_impaired"  # Visual alerts, captions
    MOTOR_IMPAIRED = "motor_impaired"    # Simplified input, dwell control
    COGNITIVE = "cognitive"              # Simplified language, step-by-step


class OutputModality(Enum):
    """How information is presented to the user."""
    SPEECH = "speech"
    TEXT = "text"
    BRAILLE = "braille"
    VISUAL = "visual"
    HAPTIC = "haptic"


@dataclass
class AccessibilityProfile:
    """User accessibility profile with preferences."""
    user_id: str = ""
    modes: List[AccessibilityMode] = field(default_factory=list)
    preferred_output: OutputModality = OutputModality.SPEECH
    speech_rate: float = 1.0
    speech_volume: float = 1.0
    speech_voice: str = ""
    high_contrast: bool = False
    magnification: float = 1.0
    caption_enabled: bool = True
    simplified_language: bool = False
    auto_describe_images: bool = True
    auto_read_documents: bool = True
    voice_commands_enabled: bool = True
    dwell_timeout_ms: int = 1000
    language: str = "en"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessibilityEvent:
    """Event for accessibility system."""
    event_type: str  # "describe", "read", "alert", "command", "navigate"
    content: str
    modality: OutputModality
    priority: int = 0  # 0=low, 1=normal, 2=high, 3=urgent
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScreenDescriber:
    """Generates natural language descriptions of screen content."""

    def __init__(self, profile: Optional[AccessibilityProfile] = None):
        self.profile = profile or AccessibilityProfile()
        self._cache: Dict[str, str] = {}

    def describe_screen(self, media: MediaObject) -> str:
        """Generate a screen description for accessibility."""
        cache_key = media.hash or media.source
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Use vision analysis for description
            result = analyze_image(media, "Describe this screen for a visually impaired user. "
                                         "Focus on: window titles, button labels, text content, "
                                         "layout structure, and interactive elements.")
            if result.get("success"):
                desc = result.get("analysis", "")
                self._cache[cache_key] = desc
                return desc
        except Exception as e:
            logger.warning("Screen description failed: %s", e)

        # Fallback to OCR-based description
        try:
            ocr_result = ocr_media(media)
            if ocr_result.get("success"):
                text = ocr_result.get("text", "")
                if text:
                    desc = f"Screen contains text: {text[:500]}"
                    self._cache[cache_key] = desc
                    return desc
        except Exception as e:
            logger.warning("OCR fallback failed: %s", e)

        return "Unable to describe screen content."

    def describe_image(self, media: MediaObject) -> str:
        """Describe an image for accessibility."""
        cache_key = media.hash or media.source
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            result = analyze_image(media, "Describe this image in detail for a visually impaired person. "
                                         "Include objects, people, text, colors, spatial relationships, "
                                         "and any text visible in the image.")
            if result.get("success"):
                desc = result.get("analysis", "")
                self._cache[cache_key] = desc
                return desc
        except Exception as e:
            logger.warning("Image description failed: %s", e)

        return "Unable to describe image."


class DocumentReader:
    """Reads documents aloud or converts to accessible formats."""

    def __init__(self, profile: Optional[AccessibilityProfile] = None):
        self.profile = profile or AccessibilityProfile()

    def read_document(self, media: MediaObject) -> str:
        """Extract and format document text for reading."""
        try:
            from agent.multimodal.perception import extract_document
            result = extract_document(media)
            if result.get("success"):
                text = result.get("text", "")
                if self.profile.simplified_language:
                    text = self._simplify_text(text)
                return text
        except Exception as e:
            logger.warning("Document reading failed: %s", e)

        # Fallback to OCR
        try:
            ocr_result = ocr_media(media)
            if ocr_result.get("success"):
                text = ocr_result.get("text", "")
                if self.profile.simplified_language:
                    text = self._simplify_text(text)
                return text
        except Exception as e:
            logger.warning("OCR fallback failed: %s", e)

        return "Unable to read document."

    def _simplify_text(self, text: str) -> str:
        """Simplify text for cognitive accessibility."""
        # Basic simplification: shorter sentences, common words
        import re
        sentences = re.split(r'[.!?]+', text)
        simple = []
        for s in sentences:
            s = s.strip()
            if len(s) > 20:
                # Split long sentences
                words = s.split()
                for i in range(0, len(words), 15):
                    simple.append(" ".join(words[i:i+15]) + ".")
            elif s:
                simple.append(s + ".")
        return " ".join(simple)


class VoiceCommandProcessor:
    """Processes voice commands for accessibility control."""

    def __init__(self, profile: Optional[AccessibilityProfile] = None):
        self.profile = profile or AccessibilityProfile()
        self._commands: Dict[str, Callable] = {}
        self._register_default_commands()

    def _register_default_commands(self) -> None:
        """Register default accessibility voice commands."""
        self.register("describe screen", self._cmd_describe_screen)
        self.register("describe image", self._cmd_describe_image)
        self.register("read document", self._cmd_read_document)
        self.register("read selection", self._cmd_read_selection)
        self.register("increase contrast", self._cmd_increase_contrast)
        self.register("decrease contrast", self._cmd_decrease_contrast)
        self.register("magnify", self._cmd_magnify)
        self.register("toggle captions", self._cmd_toggle_captions)
        self.register("repeat", self._cmd_repeat)
        self.register("stop", self._cmd_stop)
        self.register("help", self._cmd_help)

    def register(self, phrase: str, handler: Callable) -> None:
        """Register a voice command."""
        self._commands[phrase.lower()] = handler

    def process(self, transcript: str) -> Optional[str]:
        """Process a voice transcript and execute matching command."""
        transcript = transcript.lower().strip()
        for phrase, handler in self._commands.items():
            if phrase in transcript:
                try:
                    return handler(transcript)
                except Exception as e:
                    logger.warning("Command '%s' failed: %s", phrase, e)
                    return f"Command failed: {e}"
        return None

    # Default command handlers (to be overridden by integrating app)
    def _cmd_describe_screen(self, transcript: str) -> str:
        return "[COMMAND] describe_screen"

    def _cmd_describe_image(self, transcript: str) -> str:
        return "[COMMAND] describe_image"

    def _cmd_read_document(self, transcript: str) -> str:
        return "[COMMAND] read_document"

    def _cmd_read_selection(self, transcript: str) -> str:
        return "[COMMAND] read_selection"

    def _cmd_increase_contrast(self, transcript: str) -> str:
        self.profile.high_contrast = True
        return "High contrast mode enabled."

    def _cmd_decrease_contrast(self, transcript: str) -> str:
        self.profile.high_contrast = False
        return "High contrast mode disabled."

    def _cmd_magnify(self, transcript: str) -> str:
        import re
        match = re.search(r'magnify\s+(\d+(?:\.\d+)?)', transcript)
        if match:
            self.profile.magnification = float(match.group(1))
        else:
            self.profile.magnification = min(self.profile.magnification + 0.5, 5.0)
        return f"Magnification set to {self.profile.magnification}x"

    def _cmd_toggle_captions(self, transcript: str) -> str:
        self.profile.caption_enabled = not self.profile.caption_enabled
        return f"Captions {'enabled' if self.profile.caption_enabled else 'disabled'}."

    def _cmd_repeat(self, transcript: str) -> str:
        return "[COMMAND] repeat_last"

    def _cmd_stop(self, transcript: str) -> str:
        return "[COMMAND] stop_speech"

    def _cmd_help(self, transcript: str) -> str:
        cmds = list(self._commands.keys())
        return f"Available commands: {', '.join(cmds)}"


class CaptionManager:
    """Manages real-time captions for speech and audio."""

    def __init__(self, profile: Optional[AccessibilityProfile] = None):
        self.profile = profile or AccessibilityProfile()
        self._enabled = profile.caption_enabled
        self._current_caption: str = ""
        self._history: List[str] = []
        self._max_history = 100
        self._callbacks: List[Callable[[str], None]] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        self.profile.caption_enabled = value

    def add_caption(self, text: str, source: str = "") -> None:
        """Add a caption entry."""
        if not self._enabled:
            return
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {source}: {text}" if source else f"[{timestamp}] {text}"
        self._current_caption = entry
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        for cb in self._callbacks:
            try:
                cb(entry)
            except Exception:
                pass

    def get_current(self) -> str:
        return self._current_caption

    def get_history(self) -> List[str]:
        return list(self._history)

    def register_callback(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)

    def clear(self) -> None:
        self._current_caption = ""
        self._history.clear()


class VisualAlertSystem:
    """Visual alerts for hearing-impaired users."""

    def __init__(self):
        self._alerts: List[Dict[str, Any]] = []
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def alert(self, message: str, level: str = "info", duration: float = 5.0) -> None:
        """Trigger a visual alert."""
        alert = {
            "message": message,
            "level": level,  # info, warning, error, success
            "timestamp": time.time(),
            "duration": duration,
            "id": f"alert_{int(time.time() * 1000)}",
        }
        self._alerts.append(alert)
        for cb in self._callbacks:
            try:
                cb(alert)
            except Exception:
                pass

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        now = time.time()
        return [a for a in self._alerts if now - a["timestamp"] < a["duration"]]

    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._callbacks.append(callback)

    def dismiss(self, alert_id: str) -> None:
        self._alerts = [a for a in self._alerts if a["id"] != alert_id]


class MultimodalAccessibilityEngine:
    """Main accessibility engine coordinating all features."""

    def __init__(self, profile: Optional[AccessibilityProfile] = None):
        self.profile = profile or AccessibilityProfile()
        self.screen_describer = ScreenDescriber(self.profile)
        self.document_reader = DocumentReader(self.profile)
        self.voice_processor = VoiceCommandProcessor(self.profile)
        self.caption_manager = CaptionManager(self.profile)
        self.visual_alerts = VisualAlertSystem()
        self._speech_queue: List[str] = []
        self._speaking = False
        self._lock = threading.Lock()

    def describe_screen(self, media: MediaObject) -> str:
        """Describe screen content for accessibility."""
        if not self.profile.auto_describe_images:
            return ""
        return self.screen_describer.describe_screen(media)

    def describe_image(self, media: MediaObject) -> str:
        """Describe image for accessibility."""
        if not self.profile.auto_describe_images:
            return ""
        return self.screen_describer.describe_image(media)

    def read_document(self, media: MediaObject) -> str:
        """Read document for accessibility."""
        if not self.profile.auto_read_documents:
            return ""
        return self.document_reader.read_document(media)

    def process_voice_command(self, transcript: str) -> Optional[str]:
        """Process voice command for accessibility."""
        if not self.profile.voice_commands_enabled:
            return None
        return self.voice_processor.process(transcript)

    def speak(self, text: str, priority: int = 1) -> None:
        """Queue text for speech output."""
        with self._lock:
            self._speech_queue.append((priority, text, time.time()))
            self._speech_queue.sort(key=lambda x: (-x[0], x[2]))

    def speak_now(self, text: str) -> Dict[str, Any]:
        """Immediately speak text (bypasses queue)."""
        try:
            result = synthesize_speech(text, voice=self.profile.speech_voice)
            return result
        except Exception as e:
            logger.warning("Speech synthesis failed: %s", e)
            return {"success": False, "error": str(e)}

    def add_caption(self, text: str, source: str = "") -> None:
        self.caption_manager.add_caption(text, source)

    def visual_alert(self, message: str, level: str = "info") -> None:
        self.visual_alerts.alert(message, level)

    def set_profile(self, profile: AccessibilityProfile) -> None:
        self.profile = profile
        self.screen_describer.profile = profile
        self.document_reader.profile = profile
        self.voice_processor.profile = profile
        self.caption_manager.profile = profile

    def get_profile(self) -> AccessibilityProfile:
        return self.profile

    def enable_mode(self, mode: AccessibilityMode) -> None:
        if mode not in self.profile.modes:
            self.profile.modes.append(mode)
            if mode == AccessibilityMode.SCREEN_READER:
                self.profile.auto_describe_images = True
                self.profile.auto_read_documents = True
            elif mode == AccessibilityMode.LOW_VISION:
                self.profile.high_contrast = True
                self.profile.magnification = 2.0
            elif mode == AccessibilityMode.VOICE_CONTROL:
                self.profile.voice_commands_enabled = True
            elif mode == AccessibilityMode.HEARING_IMPAIRED:
                self.profile.caption_enabled = True
            elif mode == AccessibilityMode.MOTOR_IMPAIRED:
                self.profile.dwell_timeout_ms = 2000
            elif mode == AccessibilityMode.COGNITIVE:
                self.profile.simplified_language = True

    def disable_mode(self, mode: AccessibilityMode) -> None:
        if mode in self.profile.modes:
            self.profile.modes.remove(mode)

    def is_mode_enabled(self, mode: AccessibilityMode) -> bool:
        return mode in self.profile.modes


# --- Integration with existing aetheros_voice.accessibility ---

def create_accessibility_engine(
    user_id: str = "",
    modes: Optional[List[AccessibilityMode]] = None,
    **kwargs,
) -> MultimodalAccessibilityEngine:
    """Create an accessibility engine with the given profile."""
    profile = AccessibilityProfile(user_id=user_id, modes=modes or [], **kwargs)
    return MultimodalAccessibilityEngine(profile)


def get_default_accessibility_engine() -> MultimodalAccessibilityEngine:
    """Get the default accessibility engine (singleton)."""
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = create_accessibility_engine()
    return _DEFAULT_ENGINE


_DEFAULT_ENGINE: Optional[MultimodalAccessibilityEngine] = None


# --- Convenience functions ---

def describe_for_accessibility(media: MediaObject, profile: Optional[AccessibilityProfile] = None) -> str:
    """Get an accessibility description of media."""
    engine = MultimodalAccessibilityEngine(profile)
    if media.type == MediaType.SCREEN:
        return engine.describe_screen(media)
    elif media.type in (MediaType.IMAGE, MediaType.CAMERA):
        return engine.describe_image(media)
    elif media.type == MediaType.DOCUMENT:
        return engine.read_document(media)
    return ""


def read_aloud(text: str, voice: str = "", rate: float = 1.0) -> Dict[str, Any]:
    """Synthesize speech for accessibility."""
    return synthesize_speech(text, voice=voice)


def transcribe_for_accessibility(media: MediaObject) -> Dict[str, Any]:
    """Transcribe audio for captions/accessibility."""
    return transcribe_audio(media)


def ocr_for_accessibility(media: MediaObject, language: str = "en") -> Dict[str, Any]:
    """OCR for document reading accessibility."""
    return ocr_media(media, language=language)