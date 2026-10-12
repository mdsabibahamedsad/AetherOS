"""AetherOS Agent Ecosystem v2.0 — Multi-Agent Orchestrator with specialized agents.

Subpackages:
    models              — AgentConfig, enums, supporting dataclasses
    store               — SQLite-backed persistent agent registry
    manager             — CRUD, import/export, backup/restore
    permissions         — Tool-level access control
    runtime             — Multi-agent lifecycle (Hermes AIAgent instances)
    collaboration       — Inter-agent delegation, messaging, voting
    specialized         — Original specialized agent roles
    specialized_agents  — Enhanced 12 specialized agent types
    dashboard           — Status monitoring and Rich-based display
    marketplace         — Agent catalog, install, ratings
    wizard              — 11-step interactive agent creation
    cli                 — CLI command handlers for aetheros agent *
    web                 — JSON API for browser dashboard
"""

from __future__ import annotations

from agents.models import AgentConfig, AgentStatus
from agents.manager import AgentManager
from agents.runtime import AgentRuntime
from agents import store

from agents.specialized_agents import (
    SPECIALIZED_AGENT_DEFINITIONS,
    ResearchAgent, CodingAgent, DebugAgent,
    ReviewAgent, DocumentationAgent, PlanningAgent,
    MemoryAgent, VisionAgent, VoiceAgent,
    BrowserAgent, DesktopAgent, AutomationAgent,
    create_specialized_agent,
    list_agent_types,
    list_agent_capabilities,
)

__all__ = [
    "AgentConfig", "AgentStatus",
    "AgentManager", "AgentRuntime",
    "store",
    "SPECIALIZED_AGENT_DEFINITIONS",
    "ResearchAgent", "CodingAgent", "DebugAgent",
    "ReviewAgent", "DocumentationAgent", "PlanningAgent",
    "MemoryAgent", "VisionAgent", "VoiceAgent",
    "BrowserAgent", "DesktopAgent", "AutomationAgent",
    "create_specialized_agent",
    "list_agent_types",
    "list_agent_capabilities",
]


def init_agent_system() -> None:
    store.init_db()


def list_all_agents() -> list[AgentConfig]:
    mgr = AgentManager()
    return mgr.list(include_disabled=True)


def get_agent(agent_id: str) -> AgentConfig | None:
    mgr = AgentManager()
    return mgr.get(agent_id)


def create_agent(name: str, role: str = "general_assistant", **kwargs) -> AgentConfig:
    config = AgentConfig(name=name, role=role, **kwargs)
    mgr = AgentManager()
    return mgr.create(config)