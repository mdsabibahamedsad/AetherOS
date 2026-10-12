"""
Agent Capability Registry — defines and manages agent capabilities.

Capabilities describe what an agent type can do. They are used by
the task allocator to match tasks to agents and by the dispatcher
to route work to appropriate agents.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# Standard capability identifiers
CAPABILITY_CODING = "coding"
CAPABILITY_RESEARCH = "research"
CAPABILITY_PLANNING = "planning"
CAPABILITY_REVIEW = "review"
CAPABILITY_DEBUG = "debug"
CAPABILITY_BROWSER = "browser"
CAPABILITY_FILESYSTEM = "filesystem"
CAPABILITY_TERMINAL = "terminal"
CAPABILITY_TESTING = "testing"
CAPABILITY_DOCUMENTATION = "documentation"
CAPABILITY_MEMORY = "memory"
CAPABILITY_MCP = "mcp"
CAPABILITY_ANALYSIS = "analysis"
CAPABILITY_DECOMPOSITION = "decomposition"
CAPABILITY_WRITING = "writing"
CAPABILITY_REFACTORING = "refactoring"
CAPABILITY_CODE_REVIEW = "code_review"
CAPABILITY_AUDIT = "audit"
CAPABILITY_QUALITY = "quality"
CAPABILITY_WEB_SEARCH = "web_search"
CAPABILITY_WEB_INTERACTION = "web_interaction"
CAPABILITY_FILE_OPS = "file_ops"
CAPABILITY_EXECUTION = "execution"
CAPABILITY_BUILD = "build"
CAPABILITY_TROUBLESHOOTING = "troubleshooting"
CAPABILITY_RECALL = "recall"
CAPABILITY_STORAGE = "storage"
CAPABILITY_CUSTOM = "custom"
CAPABILITY_EXTERNAL = "external"
CAPABILITY_VALIDATION = "validation"


@dataclass
class AgentCapability:
    """A capability that an agent type can provide.

    Attributes:
        id: Unique capability identifier
        name: Human-readable name
        description: Detailed description of what this capability provides
        required_tools: Tools required to exercise this capability
        depends_on: Other capabilities this depends on
        metadata: Additional metadata
    """
    id: str
    name: str = ""
    description: str = ""
    required_tools: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AgentCapability):
            return NotImplemented
        return self.id == other.id


# Built-in capability definitions
BUILTIN_CAPABILITIES: Dict[str, AgentCapability] = {
    CAPABILITY_CODING: AgentCapability(
        id=CAPABILITY_CODING,
        name="Coding",
        description="Write, edit, and refactor source code",
        required_tools=["read_file", "write_file", "patch"],
    ),
    CAPABILITY_RESEARCH: AgentCapability(
        id=CAPABILITY_RESEARCH,
        name="Research",
        description="Search the web and gather information",
        required_tools=["web_search", "read_url", "web_extract"],
    ),
    CAPABILITY_PLANNING: AgentCapability(
        id=CAPABILITY_PLANNING,
        name="Planning",
        description="Analyze goals and create structured execution plans",
    ),
    CAPABILITY_REVIEW: AgentCapability(
        id=CAPABILITY_REVIEW,
        name="Review",
        description="Review code, plans, and output for quality",
        required_tools=["read_file"],
        depends_on=[CAPABILITY_CODING],
    ),
    CAPABILITY_DEBUG: AgentCapability(
        id=CAPABILITY_DEBUG,
        name="Debug",
        description="Diagnose and fix bugs",
        required_tools=["terminal", "read_file"],
        depends_on=[CAPABILITY_CODING],
    ),
    CAPABILITY_BROWSER: AgentCapability(
        id=CAPABILITY_BROWSER,
        name="Browser",
        description="Interact with web pages through a browser",
        required_tools=["browser_navigate", "browser_click", "browser_type"],
    ),
    CAPABILITY_FILESYSTEM: AgentCapability(
        id=CAPABILITY_FILESYSTEM,
        name="Filesystem",
        description="Manage files and directories",
        required_tools=["read_file", "write_file", "search_files"],
    ),
    CAPABILITY_TERMINAL: AgentCapability(
        id=CAPABILITY_TERMINAL,
        name="Terminal",
        description="Execute shell commands",
        required_tools=["terminal"],
    ),
    CAPABILITY_TESTING: AgentCapability(
        id=CAPABILITY_TESTING,
        name="Testing",
        description="Write and run tests",
        required_tools=["terminal", "read_file"],
        depends_on=[CAPABILITY_CODING],
    ),
    CAPABILITY_DOCUMENTATION: AgentCapability(
        id=CAPABILITY_DOCUMENTATION,
        name="Documentation",
        description="Generate and format documentation",
        required_tools=["read_file", "write_file"],
    ),
    CAPABILITY_MEMORY: AgentCapability(
        id=CAPABILITY_MEMORY,
        name="Memory",
        description="Store and retrieve information",
    ),
    CAPABILITY_MCP: AgentCapability(
        id=CAPABILITY_MCP,
        name="MCP",
        description="Communicate via Model Context Protocol",
    ),
    CAPABILITY_ANALYSIS: AgentCapability(
        id=CAPABILITY_ANALYSIS,
        name="Analysis",
        description="Analyze information and draw conclusions",
    ),
    CAPABILITY_DECOMPOSITION: AgentCapability(
        id=CAPABILITY_DECOMPOSITION,
        name="Decomposition",
        description="Break complex goals into smaller tasks",
    ),
    CAPABILITY_WRITING: AgentCapability(
        id=CAPABILITY_WRITING,
        name="Writing",
        description="Generate written content",
    ),
    CAPABILITY_REFACTORING: AgentCapability(
        id=CAPABILITY_REFACTORING,
        name="Refactoring",
        description="Restructure code without changing behavior",
        required_tools=["read_file", "write_file"],
    ),
}


class CapabilityRegistry:
    """Registry of capability definitions.

    Usage:
        cap_reg = CapabilityRegistry()
        cap_reg.register(BUILTIN_CAPABILITIES["coding"])
        coding_cap = cap_reg.get("coding")
    """

    def __init__(self, load_builtins: bool = True):
        self._lock = threading.RLock()
        self._capabilities: Dict[str, AgentCapability] = {}

        if load_builtins:
            for cap_id, cap in BUILTIN_CAPABILITIES.items():
                self.register(cap)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, capability: AgentCapability) -> AgentCapability:
        """Register a capability definition."""
        with self._lock:
            self._capabilities[capability.id] = capability
        logger.debug("CapabilityRegistry: registered '%s'", capability.id)
        return capability

    def deregister(self, cap_id: str) -> bool:
        """Remove a capability definition."""
        with self._lock:
            return self._capabilities.pop(cap_id, None) is not None

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, cap_id: str) -> Optional[AgentCapability]:
        """Get a capability by ID."""
        with self._lock:
            return self._capabilities.get(cap_id)

    def list_capabilities(self) -> List[AgentCapability]:
        """List all registered capabilities."""
        with self._lock:
            return list(self._capabilities.values())

    def get_required_tools(self, capability_ids: Set[str]) -> Set[str]:
        """Get the union of tools required for a set of capabilities."""
        tools: Set[str] = set()
        with self._lock:
            for cap_id in capability_ids:
                cap = self._capabilities.get(cap_id)
                if cap:
                    tools.update(cap.required_tools)
        return tools

    def get_dependency_chain(self, cap_id: str) -> List[str]:
        """Get the full dependency chain for a capability."""
        chain: List[str] = []
        visited: Set[str] = set()

        def _resolve(cid: str) -> None:
            if cid in visited:
                return
            visited.add(cid)
            cap = self._capabilities.get(cid)
            if cap:
                if cap not in chain:
                    chain.append(cid)
                for dep in cap.depends_on:
                    _resolve(dep)

        _resolve(cap_id)
        return chain

    def snapshot(self) -> Dict[str, Any]:
        """Return a serializable snapshot."""
        caps = self.list_capabilities()
        return {
            "total_capabilities": len(caps),
            "capabilities": [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "tool_count": len(c.required_tools),
                }
                for c in caps
            ],
        }
