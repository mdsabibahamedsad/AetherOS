"""
Swarm Agent Registry — catalog of agent types available in the swarm.

Maintains a runtime registry of agent type profiles. Each agent type
advertises its capabilities, cost, speed, supported tools, and priority.
This allows the dispatcher and allocator to match tasks to appropriate agents.

Designed to be extended by plugins — new agent types can be registered
without modifying the kernel.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class AgentTypeProfile:
    """Profile for a type of agent in the swarm.

    Attributes:
        name: Agent type name (e.g. "coding-agent", "research-agent")
        description: Human-readable description
        capabilities: Set of capability IDs this agent type provides
        cost_per_call: Estimated cost per agent call (arbitrary units)
        speed_rating: 1 (fastest) to 10 (slowest)
        supported_tools: Tool names this agent type can use
        priority: Default priority for tasks assigned to this type
        max_concurrent: Max concurrent instances of this agent type
        model_preference: Preferred model for this agent type
        metadata: Additional metadata
    """
    name: str
    description: str = ""
    capabilities: Set[str] = field(default_factory=set)
    cost_per_call: int = 10
    speed_rating: int = 5
    supported_tools: List[str] = field(default_factory=list)
    priority: int = 50
    max_concurrent: int = 3
    model_preference: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)


# Built-in agent type names
AGENT_TYPE_PLANNING = "planning-agent"
AGENT_TYPE_CODING = "coding-agent"
AGENT_TYPE_RESEARCH = "research-agent"
AGENT_TYPE_BROWSER = "browser-agent"
AGENT_TYPE_FILESYSTEM = "filesystem-agent"
AGENT_TYPE_TERMINAL = "terminal-agent"
AGENT_TYPE_DOCUMENTATION = "documentation-agent"
AGENT_TYPE_TESTING = "testing-agent"
AGENT_TYPE_REVIEW = "review-agent"
AGENT_TYPE_DEBUG = "debug-agent"
AGENT_TYPE_MEMORY = "memory-agent"
AGENT_TYPE_PLUGIN = "plugin-agent"
AGENT_TYPE_MCP = "mcp-agent"

# Built-in profiles
BUILTIN_AGENT_TYPE_PROFILES: Dict[str, AgentTypeProfile] = {
    AGENT_TYPE_PLANNING: AgentTypeProfile(
        name=AGENT_TYPE_PLANNING,
        description="Analyzes goals, decomposes into structured plans, identifies dependencies",
        capabilities={"planning", "analysis", "decomposition"},
        cost_per_call=15,
        speed_rating=4,
        supported_tools=["web_search", "read_file", "terminal"],
        priority=10,
        max_concurrent=2,
    ),
    AGENT_TYPE_CODING: AgentTypeProfile(
        name=AGENT_TYPE_CODING,
        description="Writes, edits, and refactors source code across languages",
        capabilities={"coding", "code_review", "refactoring"},
        cost_per_call=20,
        speed_rating=5,
        supported_tools=["read_file", "write_file", "patch", "terminal", "search_files"],
        priority=30,
        max_concurrent=3,
    ),
    AGENT_TYPE_RESEARCH: AgentTypeProfile(
        name=AGENT_TYPE_RESEARCH,
        description="Searches the web and documentation to gather information",
        capabilities={"research", "web_search", "analysis"},
        cost_per_call=10,
        speed_rating=4,
        supported_tools=["web_search", "web_extract", "read_url", "read_file"],
        priority=40,
        max_concurrent=4,
    ),
    AGENT_TYPE_BROWSER: AgentTypeProfile(
        name=AGENT_TYPE_BROWSER,
        description="Navigates web pages and interacts with browser-based interfaces",
        capabilities={"browser", "web_interaction"},
        cost_per_call=15,
        speed_rating=6,
        supported_tools=["browser_navigate", "browser_click", "browser_type", "web_extract"],
        priority=50,
        max_concurrent=2,
    ),
    AGENT_TYPE_FILESYSTEM: AgentTypeProfile(
        name=AGENT_TYPE_FILESYSTEM,
        description="Manages files, directories, and project structure",
        capabilities={"filesystem", "file_ops"},
        cost_per_call=5,
        speed_rating=2,
        supported_tools=["read_file", "write_file", "search_files", "terminal"],
        priority=60,
        max_concurrent=5,
    ),
    AGENT_TYPE_TERMINAL: AgentTypeProfile(
        name=AGENT_TYPE_TERMINAL,
        description="Executes shell commands, runs builds, manages processes",
        capabilities={"terminal", "execution", "build"},
        cost_per_call=5,
        speed_rating=2,
        supported_tools=["terminal", "execute_code"],
        priority=60,
        max_concurrent=5,
    ),
    AGENT_TYPE_DOCUMENTATION: AgentTypeProfile(
        name=AGENT_TYPE_DOCUMENTATION,
        description="Generates and formats documentation, READMEs, API docs",
        capabilities={"documentation", "writing"},
        cost_per_call=10,
        speed_rating=4,
        supported_tools=["read_file", "write_file", "web_search"],
        priority=50,
        max_concurrent=3,
    ),
    AGENT_TYPE_TESTING: AgentTypeProfile(
        name=AGENT_TYPE_TESTING,
        description="Writes and runs tests, validates code behavior",
        capabilities={"testing", "validation"},
        cost_per_call=15,
        speed_rating=5,
        supported_tools=["terminal", "read_file", "write_file", "search_files"],
        priority=40,
        max_concurrent=3,
    ),
    AGENT_TYPE_REVIEW: AgentTypeProfile(
        name=AGENT_TYPE_REVIEW,
        description="Reviews code, plans, and output for quality and correctness",
        capabilities={"review", "quality", "audit"},
        cost_per_call=15,
        speed_rating=5,
        supported_tools=["read_file", "web_search", "terminal"],
        priority=20,
        max_concurrent=2,
    ),
    AGENT_TYPE_DEBUG: AgentTypeProfile(
        name=AGENT_TYPE_DEBUG,
        description="Diagnoses and fixes bugs in code and systems",
        capabilities={"debug", "troubleshooting", "analysis"},
        cost_per_call=15,
        speed_rating=6,
        supported_tools=["terminal", "read_file", "write_file", "search_files", "web_search"],
        priority=30,
        max_concurrent=2,
    ),
    AGENT_TYPE_MEMORY: AgentTypeProfile(
        name=AGENT_TYPE_MEMORY,
        description="Manages and retrieves information from memory systems",
        capabilities={"memory", "recall", "storage"},
        cost_per_call=5,
        speed_rating=3,
        supported_tools=["memory", "search_files", "read_file"],
        priority=70,
        max_concurrent=2,
    ),
    AGENT_TYPE_PLUGIN: AgentTypeProfile(
        name=AGENT_TYPE_PLUGIN,
        description="Generic plugin-managed agent with custom capabilities",
        capabilities={"plugin", "custom"},
        cost_per_call=10,
        speed_rating=5,
        supported_tools=[],
        priority=50,
        max_concurrent=3,
    ),
    AGENT_TYPE_MCP: AgentTypeProfile(
        name=AGENT_TYPE_MCP,
        description="Agent that delegates to MCP (Model Context Protocol) servers",
        capabilities={"mcp", "external"},
        cost_per_call=10,
        speed_rating=5,
        supported_tools=[],
        priority=50,
        max_concurrent=3,
    ),
}


class SwarmAgentRegistry:
    """Runtime registry for swarm agent types.

    Maintains a catalog of agent type profiles with their capabilities,
    costs, and tools. Supports runtime registration and discovery.

    Usage:
        registry = SwarmAgentRegistry(event_bus)

        # Register a custom agent type
        registry.register(AgentTypeProfile(
            name="my-custom-agent",
            description="...",
            capabilities={"custom"},
        ))

        # Find agents by capability
        agents = registry.find_by_capability("coding")
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        load_builtins: bool = True,
    ):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._profiles: Dict[str, AgentTypeProfile] = {}
        # capability -> set of agent names
        self._capability_index: Dict[str, Set[str]] = {}

        if load_builtins:
            for name, profile in BUILTIN_AGENT_TYPE_PROFILES.items():
                self.register(profile)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, profile: AgentTypeProfile) -> AgentTypeProfile:
        """Register an agent type profile.

        Overwrites an existing profile with the same name.
        """
        with self._lock:
            self._profiles[profile.name] = profile
            for cap in profile.capabilities:
                self._capability_index.setdefault(cap, set()).add(profile.name)

        logger.info(
            "SwarmRegistry: registered '%s' (%d capabilities, %d tools)",
            profile.name, len(profile.capabilities), len(profile.supported_tools),
        )

        if self._event_bus:
            self._event_bus.emit_async("swarm.agent_type_registered", {
                "name": profile.name,
                "capabilities": list(profile.capabilities),
            })

        return profile

    def deregister(self, name: str) -> bool:
        """Remove an agent type from the registry.

        Returns True if the type was found and removed.
        """
        with self._lock:
            profile = self._profiles.pop(name, None)
            if profile is None:
                return False
            for cap in profile.capabilities:
                cap_set = self._capability_index.get(cap)
                if cap_set:
                    cap_set.discard(name)
                    if not cap_set:
                        del self._capability_index[cap]

        logger.info("SwarmRegistry: deregistered '%s'", name)
        return True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[AgentTypeProfile]:
        """Get an agent type profile by name."""
        with self._lock:
            return self._profiles.get(name)

    def list_agent_types(self) -> List[AgentTypeProfile]:
        """List all registered agent type profiles."""
        with self._lock:
            return sorted(
                self._profiles.values(),
                key=lambda p: (p.priority, p.name),
            )

    def find_by_capability(self, capability: str) -> List[AgentTypeProfile]:
        """Find agent types that provide a specific capability."""
        with self._lock:
            names = self._capability_index.get(capability, set())
            return [
                self._profiles[name]
                for name in names
                if name in self._profiles
            ]

    def find_by_capabilities(
        self, required: Set[str], min_match: Optional[int] = None
    ) -> List[AgentTypeProfile]:
        """Find agent types matching at least min_match required capabilities.

        If min_match is None, requires ALL capabilities to match.
        """
        min_match = min_match if min_match is not None else len(required)
        results = []
        with self._lock:
            for profile in self._profiles.values():
                matching = len(required & profile.capabilities)
                if matching >= min_match:
                    results.append((matching, profile))

        results.sort(key=lambda x: (-x[0], x[1].priority, x[1].cost_per_call))
        return [p for _, p in results]

    def get_all_capabilities(self) -> Set[str]:
        """Get the set of all registered capabilities."""
        with self._lock:
            return set(self._capability_index.keys())

    def snapshot(self) -> Dict[str, Any]:
        """Return a serializable snapshot of the registry."""
        profiles = self.list_agent_types()
        return {
            "total_agent_types": len(profiles),
            "total_capabilities": len(self._capability_index),
            "agent_types": [
                {
                    "name": p.name,
                    "description": p.description,
                    "capabilities": list(p.capabilities),
                    "cost_per_call": p.cost_per_call,
                    "speed_rating": p.speed_rating,
                    "tool_count": len(p.supported_tools),
                }
                for p in profiles
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Return registry statistics."""
        return {
            "agent_types": len(self._profiles),
            "capabilities": len(self._capability_index),
        }
