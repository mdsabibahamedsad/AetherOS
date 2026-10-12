"""Memory taxonomy for the intelligence fabric.

Defines the 11 memory types, the boundary scopes (who can see / write what),
origin sources, lifecycle states, trust levels and verification levels used
throughout the fabric.
"""

from __future__ import annotations

import enum


class MemoryType(str, enum.Enum):
    """The 11 memory classes required by the master prompt."""

    EPISODIC = "episodic"          # specific past events/turns
    SEMANTIC = "semantic"          # facts, concepts, world knowledge
    PROCEDURAL = "procedural"      # how-to, skills, workflows
    PREFERENCE = "preference"      # user preferences & style
    WORKSPACE = "workspace"        # current workspace state / context
    MISSION = "mission"            # active mission / goal state
    AGENT = "agent"                # agent self-observations & state
    SESSION = "session"            # current-session transient context
    DOCUMENT = "document"          # document/file knowledge
    SYSTEM = "system"              # system / platform state
    TEMPORARY = "temporary"        # short-lived scratch

    @property
    def is_transient(self) -> bool:
        return self in (MemoryType.SESSION, MemoryType.TEMPORARY)

    @property
    def is_high_privilege(self) -> bool:
        return self in (MemoryType.SYSTEM, MemoryType.MISSION, MemoryType.AGENT)


class MemoryBoundary(str, enum.Enum):
    """Isolation scope for a memory entry or query.

    Strictest to loosest: user < workspace < session < agent < system.
    A write/read is authorized only when the *actor's* scope is at least as
    privileged as the entry's boundary.
    """

    USER = "user"              # only the owning user
    WORKSPACE = "workspace"    # any user in the owning workspace
    SESSION = "session"        # any participant of the owning session
    AGENT = "agent"            # agent-internal (subagent / orchestration)
    SYSTEM = "system"          # platform-internal

    def allows(self, other: "MemoryBoundary") -> bool:
        """True if this boundary can access entries at ``other`` or looser."""
        order = [MemoryBoundary.USER, MemoryBoundary.WORKSPACE,
                 MemoryBoundary.SESSION, MemoryBoundary.AGENT, MemoryBoundary.SYSTEM]
        return order.index(self) >= order.index(other)


class MemoryOrigin(str, enum.Enum):
    """Where a memory entry came from."""

    USER = "user"                  # explicitly stated by the user
    CONVERSATION = "conversation"  # inferred from a conversation turn
    TOOL = "tool"                  # observed tool output / state
    WEB = "web"                    # web content / search results
    EMAIL = "email"                # email content
    FILE = "file"                  # file / document content
    AGENT = "agent"                # agent self-generated (plans, notes)
    SYSTEM = "system"              # platform/system generated
    UNKNOWN = "unknown"

    @property
    def default_trust(self) -> float:
        """Baseline trust in [0,1] for a freshly written entry."""
        return {
            MemoryOrigin.USER: 0.9,
            MemoryOrigin.SYSTEM: 0.9,
            MemoryOrigin.AGENT: 0.7,
            MemoryOrigin.CONVERSATION: 0.6,
            MemoryOrigin.TOOL: 0.6,
            MemoryOrigin.FILE: 0.5,
            MemoryOrigin.EMAIL: 0.4,
            MemoryOrigin.WEB: 0.3,
            MemoryOrigin.UNKNOWN: 0.2,
        }[self]


class MemoryState(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    FORGOTTEN = "forgotten"
    QUARANTINED = "quarantined"


class TrustLevel(str, enum.Enum):
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class VerificationLevel(str, enum.Enum):
    UNVERIFIED = "unverified"
    SINGLE_SOURCE = "single_source"
    CORROBORATED = "corroborated"
    CONTRADICTED = "contradicted"