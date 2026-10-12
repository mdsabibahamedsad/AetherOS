"""
Voice SDK for AetherOS
======================

SDK for building voice interactions with AetherOS.

Features:
    - Voice command registration
    - Voice skill creation
    - Wake word detection
    - Voice menu management

Usage::

    from aetheros_developer_platform.voice_sdk import VoiceManager

    manager = VoiceManager()
    manager.register_command("open settings", open_settings_handler)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class VoiceCommandType(Enum):
    """Types of voice commands."""
    COMMAND = "command"
    QUERY = "query"
    ACTION = "action"
    CONVERSATION = "conversation"


@dataclass
class VoiceCommand:
    """A voice command definition."""
    name: str
    patterns: List[str]
    handler: Optional[Callable] = None
    command_type: VoiceCommandType = VoiceCommandType.COMMAND
    description: str = ""
    examples: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class VoiceSkill:
    """A voice skill definition."""
    name: str
    description: str = ""
    commands: List[VoiceCommand] = field(default_factory=list)
    enabled: bool = True
    priority: int = 0


@dataclass
class WakeWord:
    """A wake word definition."""
    word: str
    handler: Optional[Callable] = None
    sensitivity: float = 0.5
    enabled: bool = True


class VoiceManager:
    """Manages voice interactions for AetherOS.

    Usage::

        manager = VoiceManager()

        # Register a voice command
        @manager.register_command("open settings", ["open settings", "show settings"])
        def open_settings():
            print("Opening settings...")

        # Register a voice skill
        @manager.register_skill("weather", "Get weather information")
        class WeatherSkill:
            pass

        # Register a wake word
        manager.register_wake_word("hey aether", sensitivity=0.7)
    """

    def __init__(self) -> None:
        self._commands: Dict[str, VoiceCommand] = {}
        self._skills: Dict[str, VoiceSkill] = {}
        self._wake_words: List[WakeWord] = []
        self._is_listening = False
        self._current_wake_word: Optional[str] = None

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    def register_command(
        self,
        name: str,
        patterns: List[str],
        *,
        command_type: VoiceCommandType = VoiceCommandType.COMMAND,
        description: str = "",
    ) -> Callable:
        """Register a voice command."""
        def decorator(func: Callable) -> Callable:
            cmd = VoiceCommand(
                name=name,
                patterns=patterns,
                handler=func,
                command_type=command_type,
                description=description,
            )
            self._commands[name] = cmd
            logger.info("Registered voice command: %s", name)
            return func
        return decorator

    def register_skill(
        self,
        name: str,
        description: str = "",
        *,
        priority: int = 0,
    ) -> Callable:
        """Register a voice skill."""
        def decorator(cls: type) -> type:
            skill = VoiceSkill(
                name=name,
                description=description,
                priority=priority,
            )
            self._skills[name] = skill
            logger.info("Registered voice skill: %s", name)
            return cls
        return decorator

    def register_wake_word(
        self,
        word: str,
        *,
        sensitivity: float = 0.5,
        handler: Optional[Callable] = None,
    ) -> None:
        """Register a wake word."""
        wake = WakeWord(
            word=word,
            handler=handler,
            sensitivity=sensitivity,
        )
        self._wake_words.append(wake)
        logger.info("Registered wake word: %s", word)

    def start_listening(self) -> None:
        """Start listening for voice commands."""
        self._is_listening = True
        logger.info("Started listening for voice commands")

    def stop_listening(self) -> None:
        """Stop listening for voice commands."""
        self._is_listening = False
        logger.info("Stopped listening for voice commands")

    def process_input(self, text: str) -> Optional[str]:
        """Process voice input text."""
        # Check for wake word
        for wake in self._wake_words:
            if wake.word.lower() in text.lower():
                if wake.handler:
                    wake.handler()
                return "wake_word_detected"

        # Check for commands
        for cmd in self._commands.values():
            if not cmd.enabled:
                continue
            for pattern in cmd.patterns:
                if pattern.lower() in text.lower():
                    if cmd.handler:
                        return cmd.handler()
                    return f"command:{cmd.name}"

        return None

    def get_command(self, name: str) -> Optional[VoiceCommand]:
        """Get a voice command by name."""
        return self._commands.get(name)

    def list_commands(self, enabled_only: bool = True) -> List[VoiceCommand]:
        """List all voice commands."""
        commands = list(self._commands.values())
        if enabled_only:
            commands = [c for c in commands if c.enabled]
        return commands

    def get_skill(self, name: str) -> Optional[VoiceSkill]:
        """Get a voice skill by name."""
        return self._skills.get(name)

    def list_skills(self, enabled_only: bool = True) -> List[VoiceSkill]:
        """List all voice skills."""
        skills = list(self._skills.values())
        if enabled_only:
            skills = [s for s in skills if s.enabled]
        return skills

    def list_wake_words(self, enabled_only: bool = True) -> List[WakeWord]:
        """List all wake words."""
        words = list(self._wake_words)
        if enabled_only:
            words = [w for w in words if w.enabled]
        return words

    def get_stats(self) -> Dict[str, Any]:
        """Get voice manager statistics."""
        return {
            "commands": len(self._commands),
            "skills": len(self._skills),
            "wake_words": len(self._wake_words),
            "is_listening": self._is_listening,
        }


# Global voice manager
_voice_manager: Optional[VoiceManager] = None


def get_voice_manager() -> VoiceManager:
    """Return the global VoiceManager singleton."""
    global _voice_manager
    if _voice_manager is None:
        _voice_manager = VoiceManager()
    return _voice_manager
