from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aetheros_voice.models.models import Personality


@dataclass
class PersonalityProfile:
    name: str = "Friendly"
    greeting: str = "Hello! How can I help you?"
    style: str = "conversational"
    formality: str = "casual"
    response_length: str = "balanced"
    humor_level: float = 0.3
    empathy_level: float = 0.7
    verbosity: float = 0.5
    prefix: str = ""
    suffix: str = ""


BUILTIN_PERSONALITIES: dict[Personality, PersonalityProfile] = {
    Personality.PROFESSIONAL: PersonalityProfile(
        name="Professional", greeting="Greetings. How may I assist you today?",
        style="formal", formality="formal", response_length="concise",
        humor_level=0.0, empathy_level=0.3, verbosity=0.3,
        prefix="", suffix="",
    ),
    Personality.FRIENDLY: PersonalityProfile(
        name="Friendly", greeting="Hey there! What can I do for you?",
        style="conversational", formality="casual", response_length="balanced",
        humor_level=0.4, empathy_level=0.8, verbosity=0.6,
        prefix="", suffix="",
    ),
    Personality.MINIMAL: PersonalityProfile(
        name="Minimal", greeting="Ready.",
        style="minimal", formality="neutral", response_length="concise",
        humor_level=0.0, empathy_level=0.1, verbosity=0.1,
        prefix="", suffix="",
    ),
    Personality.TECHNICAL: PersonalityProfile(
        name="Technical", greeting="System ready. Awaiting input.",
        style="technical", formality="neutral", response_length="detailed",
        humor_level=0.1, empathy_level=0.2, verbosity=0.8,
        prefix="", suffix="",
    ),
    Personality.CUSTOM: PersonalityProfile(
        name="Custom", greeting="Hello!",
        style="conversational", formality="casual", response_length="balanced",
        humor_level=0.3, empathy_level=0.5, verbosity=0.5,
    ),
}


class PersonalityEngine:
    def __init__(self):
        self._current: Personality = Personality.FRIENDLY
        self._custom: PersonalityProfile = BUILTIN_PERSONALITIES[Personality.CUSTOM]

    @property
    def current(self) -> Personality:
        return self._current

    @current.setter
    def current(self, value: Personality):
        self._current = value

    @property
    def profile(self) -> PersonalityProfile:
        if self._current == Personality.CUSTOM:
            return self._custom
        return BUILTIN_PERSONALITIES.get(self._current, BUILTIN_PERSONALITIES[Personality.FRIENDLY])

    def apply(self, response: str) -> str:
        profile = self.profile
        if profile.prefix:
            response = profile.prefix + " " + response
        if profile.suffix:
            response = response + " " + profile.suffix
        return response

    def update_custom(self, **kwargs):
        for key, val in kwargs.items():
            if hasattr(self._custom, key):
                setattr(self._custom, key, val)

    def list_personalities(self) -> list[str]:
        return [p.name for p in BUILTIN_PERSONALITIES.values()]
