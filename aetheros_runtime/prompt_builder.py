"""Prompt Builder — automatically builds system, developer, workspace, memory, conversation, user, and safety prompts.

Never concatenate manually. Every prompt section is structured and typed.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aetheros_runtime.prompts")


class PromptSection(enum.Enum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    WORKSPACE = "workspace"
    MEMORY = "memory"
    CONVERSATION = "conversation"
    USER = "user"
    SAFETY = "safety"
    CUSTOM = "custom"


@dataclass
class BuiltPrompt:
    sections: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_section(self, section: PromptSection) -> str:
        return self.sections.get(section.value, "")

    def set_section(self, section: PromptSection, content: str) -> None:
        self.sections[section.value] = content

    @property
    def system_prompt(self) -> str:
        return self.get_section(PromptSection.SYSTEM)

    @property
    def full_prompt(self) -> str:
        parts = []
        for section in [PromptSection.SYSTEM, PromptSection.DEVELOPER, PromptSection.WORKSPACE,
                        PromptSection.MEMORY, PromptSection.SAFETY, PromptSection.CONVERSATION]:
            content = self.get_section(section)
            if content:
                parts.append(content)
        return "\n\n".join(parts)

    @property
    def token_estimate(self) -> int:
        return len(self.full_prompt) // 4

    def to_dict(self) -> Dict[str, str]:
        return dict(self.sections)

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "BuiltPrompt":
        bp = cls()
        bp.sections = dict(data)
        return bp


SectionProvider = Callable[[], str]


class PromptBuilder:
    """Structured prompt builder with automatic section assembly.

    Each section is an independent provider. The builder merges them
    in the correct order: System → Developer → Workspace → Memory →
    Safety → Conversation → User.
    """

    SECTION_ORDER: List[PromptSection] = [
        PromptSection.SYSTEM,
        PromptSection.DEVELOPER,
        PromptSection.WORKSPACE,
        PromptSection.MEMORY,
        PromptSection.SAFETY,
        PromptSection.CONVERSATION,
        PromptSection.USER,
    ]

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._providers: Dict[str, SectionProvider] = {}
        self._static_content: Dict[str, str] = {}
        self._max_section_length: int = 10000

    # ------------------------------------------------------------------
    # Provider registration
    # ------------------------------------------------------------------

    def register_provider(self, section: PromptSection, provider: SectionProvider) -> None:
        with self._lock:
            self._providers[section.value] = provider

    def set_static(self, section: PromptSection, content: str) -> None:
        with self._lock:
            self._static_content[section.value] = content

    def set_system_prompt(self, prompt: str) -> None:
        self.set_static(PromptSection.SYSTEM, prompt)

    def set_safety_prompt(self, prompt: str) -> None:
        self.set_static(PromptSection.SAFETY, prompt)

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def build(self, user_message: str = "", sections: Optional[List[PromptSection]] = None) -> BuiltPrompt:
        prompt = BuiltPrompt()
        target_sections = sections or self.SECTION_ORDER

        for section in target_sections:
            content = self._get_section_content(section, user_message)
            if content:
                prompt.set_section(section, content)

        prompt.metadata["section_count"] = len([s for s in target_sections if prompt.get_section(s)])
        prompt.metadata["token_estimate"] = prompt.token_estimate
        return prompt

    def build_chat(
        self,
        user_message: str,
        include_sections: Optional[List[PromptSection]] = None,
    ) -> List[Dict[str, str]]:
        prompt = self.build(user_message, include_sections)
        messages = []

        system = prompt.get_section(PromptSection.SYSTEM)
        if system:
            messages.append({"role": "system", "content": system})

        user_text = prompt.get_section(PromptSection.USER) or user_message
        context_parts = []
        for section in [PromptSection.DEVELOPER, PromptSection.WORKSPACE, PromptSection.MEMORY, PromptSection.SAFETY]:
            content = prompt.get_section(section)
            if content:
                context_parts.append(content)

        if context_parts:
            combined = "\n\n".join(context_parts) + "\n\n" + user_text
            messages.append({"role": "user", "content": combined})
        else:
            messages.append({"role": "user", "content": user_text})

        return messages

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_section_content(self, section: PromptSection, user_message: str) -> str:
        key = section.value

        if section == PromptSection.USER:
            return user_message

        static = self._static_content.get(key)
        if static:
            return static[:self._max_section_length]

        provider = self._providers.get(key)
        if provider:
            try:
                content = provider()
                return content[:self._max_section_length]
            except Exception as exc:
                logger.warning("Prompt provider %s failed: %s", key, exc)

        return ""

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    @staticmethod
    def create_system_prompt(
        agent_name: str = "AetherOS",
        capabilities: Optional[List[str]] = None,
        rules: Optional[List[str]] = None,
    ) -> str:
        parts = [f"You are {agent_name}, an AI operating system."]
        if capabilities:
            parts.append("\nCapabilities:")
            for cap in capabilities:
                parts.append(f"- {cap}")
        if rules:
            parts.append("\nRules:")
            for rule in rules:
                parts.append(f"- {rule}")
        return "\n".join(parts)

    @staticmethod
    def create_developer_prompt(
        project: str = "",
        language: str = "",
        framework: str = "",
    ) -> str:
        parts = ["Developer context:"]
        if project:
            parts.append(f"Project: {project}")
        if language:
            parts.append(f"Language: {language}")
        if framework:
            parts.append(f"Framework: {framework}")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        try:
            with self._lock:
                return bool(self._providers or self._static_content)
        except Exception:
            return False

    def summary(self) -> str:
        with self._lock:
            return (
                f"Prompt Builder: {len(self._providers)} dynamic providers, "
                f"{len(self._static_content)} static sections"
            )