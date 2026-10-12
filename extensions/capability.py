"""
Capability Declarations
=======================

Declares what capabilities an extension provides. Capabilities are
typed, discoverable, and can be queried at runtime.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Capability:
    """A typed capability that an extension provides.

    Format: ``<domain>:<action>``

    Examples:
        ``tool:register`` — can register tools
        ``event:publish`` — can publish events
        ``memory:store`` — can store to memory
        ``agent:hook`` — can hook into agent lifecycle
    """
    name: str

    @property
    def domain(self) -> str:
        return self.name.split(":", 1)[0] if ":" in self.name else self.name

    @property
    def action(self) -> str:
        return self.name.split(":", 1)[1] if ":" in self.name else "*"


# Standard capabilities
CAP_TOOL_REGISTER = Capability("tool:register")
CAP_EVENT_PUBLISH = Capability("event:publish")
CAP_EVENT_SUBSCRIBE = Capability("event:subscribe")
CAP_MEMORY_STORE = Capability("memory:store")
CAP_MEMORY_SEARCH = Capability("memory:search")
CAP_AGENT_HOOK = Capability("agent:hook")
CAP_AGENT_MESSAGE = Capability("agent:message")
CAP_WORKFLOW_DEFINE = Capability("workflow:define")
CAP_WORKFLOW_EXECUTE = Capability("workflow:execute")
CAP_FILE_READ = Capability("file:read")
CAP_FILE_WRITE = Capability("file:write")
CAP_NETWORK_CONNECT = Capability("network:connect")
CAP_CLUSTER_COMMUNICATE = Capability("cluster:communicate")
CAP_AUXILIARY_TASK = Capability("auxiliary:task")

ALL_CAPABILITIES: Set[Capability] = {
    CAP_TOOL_REGISTER,
    CAP_EVENT_PUBLISH,
    CAP_EVENT_SUBSCRIBE,
    CAP_MEMORY_STORE,
    CAP_MEMORY_SEARCH,
    CAP_AGENT_HOOK,
    CAP_AGENT_MESSAGE,
    CAP_WORKFLOW_DEFINE,
    CAP_WORKFLOW_EXECUTE,
    CAP_FILE_READ,
    CAP_FILE_WRITE,
    CAP_NETWORK_CONNECT,
    CAP_CLUSTER_COMMUNICATE,
    CAP_AUXILIARY_TASK,
}


class CapabilitySet:
    """A set of capabilities with fast lookup."""

    def __init__(self, capabilities: Optional[List[Capability]] = None) -> None:
        self._caps: Set[str] = {c.name for c in (capabilities or [])}

    def has(self, capability: Capability) -> bool:
        """Check if this set includes *capability*."""
        return capability.name in self._caps

    def add(self, capability: Capability) -> "CapabilitySet":
        return CapabilitySet([Capability(c) for c in self._caps | {capability.name}])

    def remove(self, capability: Capability) -> "CapabilitySet":
        return CapabilitySet([Capability(c) for c in self._caps - {capability.name}])

    def union(self, other: "CapabilitySet") -> "CapabilitySet":
        return CapabilitySet([Capability(c) for c in self._caps | other._caps])

    def intersection(self, other: "CapabilitySet") -> "CapabilitySet":
        return CapabilitySet([Capability(c) for c in self._caps & other._caps])

    def list(self) -> List[Capability]:
        return sorted([Capability(c) for c in self._caps], key=lambda x: x.name)

    def __repr__(self) -> str:
        return f"CapabilitySet({sorted(self._caps)})"
