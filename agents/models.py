"""Agent data models — pure dataclasses with no runtime dependencies."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class AgentRole(Enum):
    SOFTWARE_ENGINEER = "software_engineer"
    RESEARCHER = "researcher"
    DEVOPS = "devops"
    CYBER_SECURITY = "cyber_security"
    TEACHER = "teacher"
    WRITER = "writer"
    BUSINESS = "business"
    MARKETING = "marketing"
    GENERAL_ASSISTANT = "general_assistant"
    CUSTOM = "custom"


AGENT_ROLE_LABELS = {
    AgentRole.SOFTWARE_ENGINEER: "Software Engineer",
    AgentRole.RESEARCHER: "Researcher",
    AgentRole.DEVOPS: "DevOps",
    AgentRole.CYBER_SECURITY: "Cyber Security",
    AgentRole.TEACHER: "Teacher",
    AgentRole.WRITER: "Writer",
    AgentRole.BUSINESS: "Business",
    AgentRole.MARKETING: "Marketing",
    AgentRole.GENERAL_ASSISTANT: "General Assistant",
    AgentRole.CUSTOM: "Custom",
}


class Personality(Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    MINIMAL = "minimal"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    RESEARCH = "research"
    FUNNY = "funny"
    CUSTOM = "custom"


PERSONALITY_LABELS = {
    Personality.PROFESSIONAL: "Professional",
    Personality.FRIENDLY: "Friendly",
    Personality.MINIMAL: "Minimal",
    Personality.TECHNICAL: "Technical",
    Personality.CREATIVE: "Creative",
    Personality.RESEARCH: "Research",
    Personality.FUNNY: "Funny",
    Personality.CUSTOM: "Custom",
}


class ReasoningLevel(Enum):
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"


REASONING_LABELS = {
    ReasoningLevel.FAST: "Fast",
    ReasoningLevel.BALANCED: "Balanced",
    ReasoningLevel.DEEP: "Deep",
}


class MemoryScope(Enum):
    PERSONAL = "personal"
    WORKSPACE = "workspace"
    PROJECT = "project"
    LONG_TERM = "long_term"
    DISABLE = "disable"


MEMORY_LABELS = {
    MemoryScope.PERSONAL: "Personal",
    MemoryScope.WORKSPACE: "Workspace",
    MemoryScope.PROJECT: "Project",
    MemoryScope.LONG_TERM: "Long-Term",
    MemoryScope.DISABLE: "Disabled",
}


AVAILABLE_TOOLS = [
    "filesystem", "browser", "python", "docker", "git", "github",
    "terminal", "web_search", "ocr", "vision", "voice",
    "email", "calendar", "mcp", "computer_use",
]

AVAILABLE_PERMISSIONS = [
    "read_files", "write_files", "execute_terminal", "internet_access",
    "install_packages", "git_push", "docker", "system_commands",
    "ask_before_dangerous",
]


@dataclass
class KnowledgeSource:
    type: str  # folder, markdown, pdf, git, website, database
    path: str
    label: str = ""
    enabled: bool = True

    def to_dict(self) -> dict:
        return {"type": self.type, "path": self.path, "label": self.label, "enabled": self.enabled}

    @classmethod
    def from_dict(cls, d: dict) -> KnowledgeSource:
        return cls(type=d.get("type", ""), path=d.get("path", ""), label=d.get("label", ""), enabled=d.get("enabled", True))


@dataclass
class ProviderConfig:
    provider: str
    model: str = ""
    base_url: str = ""
    api_key: str = ""

    def to_dict(self) -> dict:
        return {"provider": self.provider, "model": self.model,
                "base_url": self.base_url, "api_key": self.api_key if self.api_key else ""}

    @classmethod
    def from_dict(cls, d: dict) -> ProviderConfig:
        return cls(provider=d.get("provider", ""), model=d.get("model", ""),
                   base_url=d.get("base_url", ""), api_key=d.get("api_key", ""))


@dataclass
class AgentAvatar:
    icon: str = "🤖"
    color: str = "#58a6ff"

    def to_dict(self) -> dict:
        return {"icon": self.icon, "color": self.color}

    @classmethod
    def from_dict(cls, d: dict) -> AgentAvatar:
        return cls(icon=d.get("icon", "🤖"), color=d.get("color", "#58a6ff"))


@dataclass
class AgentMetrics:
    sessions_run: int = 0
    total_tokens: int = 0
    total_messages: int = 0
    last_run: str = ""
    avg_response_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {"sessions_run": self.sessions_run, "total_tokens": self.total_tokens,
                "total_messages": self.total_messages, "last_run": self.last_run,
                "avg_response_time_ms": self.avg_response_time_ms}

    @classmethod
    def from_dict(cls, d: dict) -> AgentMetrics:
        return cls(sessions_run=d.get("sessions_run", 0), total_tokens=d.get("total_tokens", 0),
                   total_messages=d.get("total_messages", 0), last_run=d.get("last_run", ""),
                   avg_response_time_ms=d.get("avg_response_time_ms", 0.0))


@dataclass
class AgentConfig:
    id: str = ""
    name: str = "Assistant"
    description: str = ""
    avatar: AgentAvatar = field(default_factory=AgentAvatar)
    role: str = AgentRole.GENERAL_ASSISTANT.value
    role_custom: str = ""
    personality: str = Personality.PROFESSIONAL.value
    personality_custom: str = ""
    reasoning: str = ReasoningLevel.BALANCED.value
    provider: str = ""
    fallback_providers: list[ProviderConfig] = field(default_factory=list)
    models: dict[str, str] = field(default_factory=dict)
    memory_scope: str = MemoryScope.PERSONAL.value
    knowledge_sources: list[KnowledgeSource] = field(default_factory=list)
    tools: list[str] = field(default_factory=lambda: ["filesystem", "terminal", "web_search"])
    permissions: list[str] = field(default_factory=lambda: ["read_files", "internet_access"])
    prompt: str = ""
    skills: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    workflows: list[str] = field(default_factory=list)
    temperature: float = 0.7
    max_iterations: int = 90
    enabled: bool = True
    status: str = AgentStatus.IDLE.value
    created_at: str = ""
    updated_at: str = ""
    version: int = 1
    metrics: AgentMetrics = field(default_factory=AgentMetrics)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def validate(self) -> AgentConfig:
        if not self.name.strip():
            self.name = "Assistant"
        if self.role not in [r.value for r in AgentRole]:
            self.role = AgentRole.GENERAL_ASSISTANT.value
        if self.personality not in [p.value for p in Personality]:
            self.personality = Personality.PROFESSIONAL.value
        if self.reasoning not in [r.value for r in ReasoningLevel]:
            self.reasoning = ReasoningLevel.BALANCED.value
        if self.memory_scope not in [m.value for m in MemoryScope]:
            self.memory_scope = MemoryScope.PERSONAL.value
        self.tools = [t for t in self.tools if t in AVAILABLE_TOOLS]
        self.permissions = [p for p in self.permissions if p in AVAILABLE_PERMISSIONS]
        if not self.tools:
            self.tools = ["filesystem", "terminal", "web_search"]
        if not self.permissions:
            self.permissions = ["read_files", "internet_access"]
        self.temperature = max(0.0, min(2.0, self.temperature))
        self.max_iterations = max(1, min(500, self.max_iterations))
        return self

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "avatar": self.avatar.to_dict(),
            "role": self.role, "role_custom": self.role_custom,
            "personality": self.personality, "personality_custom": self.personality_custom,
            "reasoning": self.reasoning,
            "provider": self.provider,
            "fallback_providers": [p.to_dict() for p in self.fallback_providers],
            "models": self.models,
            "memory_scope": self.memory_scope,
            "knowledge_sources": [k.to_dict() for k in self.knowledge_sources],
            "tools": self.tools, "permissions": self.permissions,
            "prompt": self.prompt,
            "skills": self.skills, "mcp_servers": self.mcp_servers,
            "workflows": self.workflows,
            "temperature": self.temperature, "max_iterations": self.max_iterations,
            "enabled": self.enabled, "status": self.status,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "version": self.version,
            "metrics": self.metrics.to_dict(),
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AgentConfig:
        avatar = AgentAvatar.from_dict(d.get("avatar", {}))
        fallbacks = [ProviderConfig.from_dict(p) for p in d.get("fallback_providers", [])]
        knowledge = [KnowledgeSource.from_dict(k) for k in d.get("knowledge_sources", [])]
        metrics = AgentMetrics.from_dict(d.get("metrics", {}))
        return cls(
            id=d.get("id", ""), name=d.get("name", "Assistant"),
            description=d.get("description", ""), avatar=avatar,
            role=d.get("role", AgentRole.GENERAL_ASSISTANT.value),
            role_custom=d.get("role_custom", ""),
            personality=d.get("personality", Personality.PROFESSIONAL.value),
            personality_custom=d.get("personality_custom", ""),
            reasoning=d.get("reasoning", ReasoningLevel.BALANCED.value),
            provider=d.get("provider", ""), fallback_providers=fallbacks,
            models=d.get("models", {}), memory_scope=d.get("memory_scope", MemoryScope.PERSONAL.value),
            knowledge_sources=knowledge, tools=d.get("tools", ["filesystem", "terminal", "web_search"]),
            permissions=d.get("permissions", ["read_files", "internet_access"]),
            prompt=d.get("prompt", ""), skills=d.get("skills", []),
            mcp_servers=d.get("mcp_servers", []), workflows=d.get("workflows", []),
            temperature=d.get("temperature", 0.7), max_iterations=d.get("max_iterations", 90),
            enabled=d.get("enabled", True), status=d.get("status", AgentStatus.IDLE.value),
            created_at=d.get("created_at", ""), updated_at=d.get("updated_at", ""),
            version=d.get("version", 1), metrics=metrics, tags=d.get("tags", []),
        )
