"""AetherOS Jarvis Mode — proactive AI runtime.

The Jarvis runtime turns AetherOS into a proactive assistant: it observes
context, understands what the user is doing, plans and coordinates missions,
speaks and listens through the voice engine, and always respects permissions,
privacy, and user control.

Subsystems
==========

- :mod:`~aetheros_jarvis.runtime` — lifecycle (init/sleep/wake/pause/resume/shutdown), health, diagnostics, recovery
- :mod:`~aetheros_jarvis.wake_word` — real offline wake phrase detection
- :mod:`~aetheros_jarvis.voice` — STT/TTS/streaming/interruption facade
- :mod:`~aetheros_jarvis.conversation` — conversation modes
- :mod:`~aetheros_jarvis.dialogue` — multi-turn dialogue with clarifications/corrections
- :mod:`~aetheros_jarvis.presence` — idle/active/away/locked/sleep detection
- :mod:`~aetheros_jarvis.context` — context awareness
- :mod:`~aetheros_jarvis.proactive` — proactive observations and suggestions
- :mod:`~aetheros_jarvis.briefing` — daily briefing
- :mod:`~aetheros_jarvis.notifications` — notification intelligence
- :mod:`~aetheros_jarvis.mission` — mission mode (goal -> plan -> approval -> execute -> report)
- :mod:`~aetheros_jarvis.permissions` — approval-gated permission layer
- :mod:`~aetheros_jarvis.voice_commands` — voice command registry
- :mod:`~aetheros_jarvis.personalization` — voice profiles
- :mod:`~aetheros_jarvis.tone` — tone adaptation
- :mod:`~aetheros_jarvis.accessibility` — accessibility support
- :mod:`~aetheros_jarvis.performance` — battery-aware performance guard
- :mod:`~aetheros_jarvis.memory` — long-term memory

Quality principles
==================

- No fake wake word: detection requires a real speech-shaped acoustic event.
- No bypassed permissions: privileged actions are denied unless approved.
- No fabricated context: data sources report honestly when unavailable.
- No intrusive behavior: proactive output is gated by presence and cooldown.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _resolve_version() -> str:
    """Resolve the installed version (distribution metadata, then pyproject)."""
    try:
        from importlib.metadata import PackageNotFoundError, version as _pkg_version
        try:
            return _pkg_version("aetheros")
        except PackageNotFoundError:
            pass
    except Exception:
        pass
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if pyproject.exists():
        try:
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("version =") or line.startswith("version="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return "0.0.0"


__version__: str = _resolve_version()


class Jarvis:
    """Top-level Jarvis facade.

    Owns the runtime and lazily constructs the subsystem managers. Use
    :func:`get_jarvis` for the process-wide singleton.
    """

    def __init__(self, home: Optional[Path] = None) -> None:
        from aetheros_jarvis.config import JarvisConfigManager
        from aetheros_jarvis.runtime import JarvisRuntime

        self.config_mgr = JarvisConfigManager(home=Path(home) if home else None)
        self.config = self.config_mgr.config
        self.runtime = JarvisRuntime(self.config)

        # Lazily-constructed subsystems.
        self._permissions = None
        self._presence = None
        self._performance = None
        self._wake_word = None
        self._voice = None
        self._conversation = None
        self._dialogue = None
        self._context = None
        self._proactive = None
        self._briefing = None
        self._notifications = None
        self._mission = None
        self._commands = None
        self._personalization = None
        self._tone = None
        self._accessibility = None
        self._memory = None
        self._wire_runtime()

    # ------------------------------------------------------------------
    # Subsystem accessors (lazy)
    # ------------------------------------------------------------------

    @property
    def permissions(self):
        if self._permissions is None:
            from aetheros_jarvis.permissions import PermissionLayer
            self._permissions = PermissionLayer()
        return self._permissions

    @property
    def presence(self):
        if self._presence is None:
            from aetheros_jarvis.presence import PresenceDetector
            self._presence = PresenceDetector(
                idle_after_seconds=self.config.presence_idle_after_seconds,
                away_after_seconds=self.config.presence_away_after_seconds,
            )
        return self._presence

    @property
    def performance(self):
        if self._performance is None:
            from aetheros_jarvis.performance import PerformanceGuard
            self._performance = PerformanceGuard(self.config.resource_limits)
        return self._performance

    @property
    def wake_word(self):
        if self._wake_word is None:
            from aetheros_jarvis.wake_word import WakeWordEngine
            self._wake_word = WakeWordEngine(
                phrases=self.config.wake_phrases,
                enabled=self.config.wake_word_enabled,
            )
        return self._wake_word

    @property
    def voice(self):
        if self._voice is None:
            from aetheros_jarvis.voice import VoiceEngineWrapper
            self._voice = VoiceEngineWrapper(
                stt_provider=self.config.stt_provider,
                tts_provider=self.config.tts_provider,
                mic_device=self.config.mic_device,
                speaker_device=self.config.speaker_device,
                streaming_enabled=self.config.streaming_enabled,
                interruption_enabled=self.config.interruption_enabled,
            )
            self._voice.set_confirmation_resolver(lambda prompt: self.permissions.system_change(prompt))
        return self._voice

    @property
    def conversation(self):
        if self._conversation is None:
            from aetheros_jarvis.conversation import ConversationManager
            self._conversation = ConversationManager(self.config.conversation_mode)
        return self._conversation

    @property
    def dialogue(self):
        if self._dialogue is None:
            from aetheros_jarvis.dialogue import DialogueManager
            self._dialogue = DialogueManager()
        return self._dialogue

    @property
    def context(self):
        if self._context is None:
            from aetheros_jarvis.context import ContextAwareness
            self._context = ContextAwareness()
        return self._context

    @property
    def proactive(self):
        if self._proactive is None:
            from aetheros_jarvis.proactive import ProactiveEngine
            self._proactive = ProactiveEngine()
            self._proactive.set_presence_fn(self.presence.is_available)
            self._proactive.set_enabled(self.config.proactive_enabled)
            self._proactive.set_min_interval(self.config.proactive_min_interval_seconds)
        return self._proactive

    @property
    def briefing(self):
        if self._briefing is None:
            from aetheros_jarvis.briefing import DailyBriefingEngine
            self._briefing = DailyBriefingEngine()
        return self._briefing

    @property
    def notifications(self):
        if self._notifications is None:
            from aetheros_jarvis.notifications import NotificationIntelligence
            self._notifications = NotificationIntelligence()
        return self._notifications

    @property
    def mission(self):
        if self._mission is None:
            from aetheros_jarvis.mission import MissionManager
            self._mission = MissionManager()
        return self._mission

    @property
    def commands(self):
        if self._commands is None:
            from aetheros_jarvis.voice_commands import VoiceCommandRegistry
            self._commands = VoiceCommandRegistry(self.permissions)
        return self._commands

    @property
    def personalization(self):
        if self._personalization is None:
            from aetheros_jarvis.personalization import VoicePersonalization
            self._personalization = VoicePersonalization()
        return self._personalization

    @property
    def tone(self):
        if self._tone is None:
            from aetheros_jarvis.tone import ToneEngine
            self._tone = ToneEngine()
        return self._tone

    @property
    def accessibility(self):
        if self._accessibility is None:
            from aetheros_jarvis.accessibility import AccessibilityManager
            self._accessibility = AccessibilityManager()
        return self._accessibility

    @property
    def memory(self):
        if self._memory is None:
            from aetheros_jarvis.memory import JarvisMemory
            self._memory = JarvisMemory()
        return self._memory

    # ------------------------------------------------------------------
    # Runtime wiring
    # ------------------------------------------------------------------

    def _wire_runtime(self) -> None:
        self.runtime.register(self.wake_word, wake_source=True)
        self.runtime.register(self.voice)
        self.runtime.register(self.conversation)
        self.runtime.register(self.dialogue)
        self.runtime.register(self.presence)
        self.runtime.register(self.proactive)
        self.runtime.register(self.briefing)
        self.runtime.register(self.notifications)
        self.runtime.register(self.mission)
        self.runtime.register(self.performance)

    # ------------------------------------------------------------------
    # High-level operations
    # ------------------------------------------------------------------

    def start(self) -> bool:
        return self.runtime.initialize()

    def stop(self) -> bool:
        return self.runtime.shutdown()

    def sleep(self) -> bool:
        return self.runtime.sleep()

    def wake(self) -> bool:
        return self.runtime.wake()

    def pause(self) -> bool:
        return self.runtime.pause()

    def resume(self) -> bool:
        return self.runtime.resume()

    def handle_utterance(self, text: str, *, source: str = "text") -> str:
        """Route a user utterance through commands, then dialogue context."""
        result = self.commands.execute(text)
        if result.get("ok"):
            return str(result.get("result", "Done"))
        self.dialogue.user(text)
        topic = self.dialogue.last_topic()
        return f"Understood. Topic: {topic}"

    def observe(self) -> dict:
        """Run one proactive observation pass."""
        snapshot = self.context.capture()
        suggestions = self.proactive.observe(snapshot)
        return {
            "context": snapshot.to_dict(),
            "suggestions": [{"id": s.id, "title": s.title, "reason": s.reason} for s in suggestions],
        }

    def briefing_markdown(self) -> str:
        return self.briefing.to_markdown()

    def version(self) -> str:
        return __version__

    def status(self) -> dict:
        return {
            "version": __version__,
            "runtime": self.runtime.diagnostics(),
            "presence": self.presence.snapshot(),
            "performance": self.performance.snapshot(),
            "wake_word": self.wake_word.snapshot(),
            "voice": self.voice.snapshot(),
            "conversation": self.conversation.snapshot(),
            "mission": self.mission.snapshot(),
        }


_jarvis: Optional[Jarvis] = None
_jarvis_lock: Any = None


def get_jarvis() -> Jarvis:
    """Return the process-wide Jarvis singleton."""
    global _jarvis, _jarvis_lock
    if _jarvis_lock is None:
        import threading
        _jarvis_lock = threading.RLock()
    if _jarvis is None:
        with _jarvis_lock:
            if _jarvis is None:
                _jarvis = Jarvis()
    return _jarvis


__all__ = [
    "Jarvis",
    "get_jarvis",
    "__version__",
]
