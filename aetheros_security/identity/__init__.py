"""
Principal Identity for AetherOS
===============================

Zero-trust principal registry. Every entity that can request an action is a
*principal* with an explicit identity, owner, trust level, and scope:

    USER        Authenticated human
    AGENT       Agent instance (never identified by display name alone)
    TOOL        Built-in or plugin tool
    MCP_SERVER  MCP server process
    PLUGIN      Loaded plugin
    SKILL       Loaded skill
    MODEL       Model provider endpoint
    SESSION     Conversation / agent session
    DEVICE      Device / terminal
    WORKSPACE   Workspace / project scope
    PROJECT     Project scope
    SERVICE     Background service

Agent identity carries the full lifecycle envelope required for zero-trust
authorization (see the master security spec, steps 3-5):

    agentId, agentType, agentVersion, owner, trustLevel, capabilities,
    permissions, workspace, sessionScope, status, createdAt, updatedAt

Nothing is trusted because it is "internal" — trust is a recorded, revocable
state on the principal record, enforced deterministically by the
authorization engine.

Usage::

    from aetheros_security.identity import IdentityRegistry, AgentIdentity

    reg = IdentityRegistry()
    reg.register_agent(AgentIdentity(agent_id="research-1", owner="alice"))
    agent = reg.get_agent("research-1")
    reg.quarantine("research-1")
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PrincipalType(Enum):
    """Types of security principals."""
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"
    MCP_SERVER = "mcp_server"
    PLUGIN = "plugin"
    SKILL = "skill"
    MODEL = "model"
    SESSION = "session"
    DEVICE = "device"
    WORKSPACE = "workspace"
    PROJECT = "project"
    SERVICE = "service"


class TrustLevel(Enum):
    """Trust levels for principals.

    Zero-trust ordering: nothing is ``PRIVILEGED`` by default. A principal
    must be explicitly elevated by a trusted operator.
    """
    UNTRUSTED = "untrusted"
    LOW = "low"
    STANDARD = "standard"
    ELEVATED = "elevated"
    PRIVILEGED = "privileged"


class PrincipalStatus(Enum):
    """Lifecycle status of a principal."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    QUARANTINED = "quarantined"
    REVOKED = "revoked"
    EXPIRED = "expired"


_TRUST_ORDER = {
    TrustLevel.UNTRUSTED: 0,
    TrustLevel.LOW: 1,
    TrustLevel.STANDARD: 2,
    TrustLevel.ELEVATED: 3,
    TrustLevel.PRIVILEGED: 4,
}


def trust_at_least(level: TrustLevel, minimum: TrustLevel) -> bool:
    """Whether ``level`` is at or above ``minimum`` in the trust ordering."""
    return _TRUST_ORDER.get(level, 0) >= _TRUST_ORDER.get(minimum, 0)


@dataclass
class AgentIdentity:
    """Full identity envelope for an agent principal.

    An agent is never identified by its display name alone. ``agent_id`` is
    the stable identity; ``name`` is display-only.
    """
    agent_id: str = ""
    agent_type: str = "general"
    agent_version: str = "0.0.0"
    owner: str = ""                       # owning user/principal id
    trust_level: TrustLevel = TrustLevel.LOW
    capabilities: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)  # granted scopes
    workspace: str = ""
    session_scope: str = ""
    status: PrincipalStatus = PrincipalStatus.ACTIVE
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        now = time.time()
        if not self.agent_id:
            self.agent_id = uuid.uuid4().hex
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        """Serializable form (no secrets)."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "agent_version": self.agent_version,
            "owner": self.owner,
            "trust_level": self.trust_level.value,
            "capabilities": list(self.capabilities),
            "permissions": list(self.permissions),
            "workspace": self.workspace,
            "session_scope": self.session_scope,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentIdentity":
        return cls(
            agent_id=data.get("agent_id", ""),
            agent_type=data.get("agent_type", "general"),
            agent_version=data.get("agent_version", "0.0.0"),
            owner=data.get("owner", ""),
            trust_level=TrustLevel(data.get("trust_level", "low")),
            capabilities=list(data.get("capabilities", [])),
            permissions=list(data.get("permissions", [])),
            workspace=data.get("workspace", ""),
            session_scope=data.get("session_scope", ""),
            status=PrincipalStatus(data.get("status", "active")),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class Principal:
    """A generic registered principal with its identity and scope."""
    principal_id: str
    principal_type: PrincipalType
    owner: str = ""
    trust_level: TrustLevel = TrustLevel.LOW
    status: PrincipalStatus = PrincipalStatus.ACTIVE
    scopes: List[str] = field(default_factory=list)
    workspace: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        now = time.time()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "principal_type": self.principal_type.value,
            "owner": self.owner,
            "trust_level": self.trust_level.value,
            "status": self.status.value,
            "scopes": list(self.scopes),
            "workspace": self.workspace,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


class IdentityError(Exception):
    """Raised for invalid identity operations."""


class IdentityRegistry:
    """Registry of all security principals.

    Provides deterministic lookup, lifecycle transitions (suspend /
    quarantine / revoke / restore), and trust-level checks. Enforced by the
    authorization engine — the registry itself does not grant access.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, AgentIdentity] = {}
        self._principals: Dict[str, Principal] = {}

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    def register_agent(self, identity: AgentIdentity) -> AgentIdentity:
        """Register (or update) an agent identity."""
        identity.updated_at = time.time()
        self._agents[identity.agent_id] = identity
        self._emit_audit("agent_registered", identity.agent_id, identity.owner)
        logger.info("Agent registered: %s (type=%s trust=%s)",
                    identity.agent_id, identity.agent_type, identity.trust_level.value)
        return identity

    def get_agent(self, agent_id: str) -> Optional[AgentIdentity]:
        return self._agents.get(agent_id)

    def require_agent(self, agent_id: str) -> AgentIdentity:
        identity = self._agents.get(agent_id)
        if identity is None:
            raise IdentityError(f"Unknown agent: {agent_id}")
        return identity

    def list_agents(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._agents.values()]

    def update_agent_status(self, agent_id: str, status: PrincipalStatus) -> bool:
        identity = self._agents.get(agent_id)
        if identity is None:
            return False
        identity.status = status
        identity.updated_at = time.time()
        self._emit_audit("agent_status_changed", agent_id, identity.owner,
                         details={"status": status.value})
        logger.info("Agent %s status -> %s", agent_id, status.value)
        return True

    def quarantine(self, agent_id: str) -> bool:
        """Quarantine an agent: suspend it and block privileged capabilities."""
        identity = self._agents.get(agent_id)
        if identity is None:
            return False
        identity.status = PrincipalStatus.QUARANTINED
        identity.updated_at = time.time()
        # A quarantined agent is not trusted regardless of its recorded level.
        identity.trust_level = TrustLevel.UNTRUSTED
        self._emit_audit("agent_quarantined", agent_id, identity.owner,
                         severity="warning")
        logger.warning("Agent quarantined: %s", agent_id)
        return True

    def suspend(self, agent_id: str) -> bool:
        return self.update_agent_status(agent_id, PrincipalStatus.SUSPENDED)

    def revoke(self, agent_id: str) -> bool:
        return self.update_agent_status(agent_id, PrincipalStatus.REVOKED)

    def restore(self, agent_id: str, trust_level: Optional[TrustLevel] = None) -> bool:
        """Restore an agent to active with an explicit (re)assigned trust."""
        identity = self._agents.get(agent_id)
        if identity is None:
            return False
        identity.status = PrincipalStatus.ACTIVE
        if trust_level is not None:
            identity.trust_level = trust_level
        identity.updated_at = time.time()
        self._emit_audit("agent_restored", agent_id, identity.owner,
                         details={"trust_level": identity.trust_level.value})
        return True

    def is_active(self, agent_id: str) -> bool:
        identity = self._agents.get(agent_id)
        return identity is not None and identity.status == PrincipalStatus.ACTIVE

    def grant_scope(self, agent_id: str, scope: str) -> bool:
        identity = self._agents.get(agent_id)
        if identity is None:
            return False
        if scope not in identity.permissions:
            identity.permissions.append(scope)
        identity.updated_at = time.time()
        return True

    def revoke_scope(self, agent_id: str, scope: str) -> bool:
        identity = self._agents.get(agent_id)
        if identity is None:
            return False
        if scope in identity.permissions:
            identity.permissions.remove(scope)
        identity.updated_at = time.time()
        return True

    # ------------------------------------------------------------------
    # Generic principals (users, tools, plugins, skills, MCP servers, ...)
    # ------------------------------------------------------------------

    def register(self, principal: Principal) -> Principal:
        principal.updated_at = time.time()
        self._principals[principal.principal_id] = principal
        logger.info("Principal registered: %s (%s)",
                    principal.principal_id, principal.principal_type.value)
        return principal

    def register_user(self, user_id: str, *, scopes: Optional[List[str]] = None,
                      trust_level: TrustLevel = TrustLevel.STANDARD) -> Principal:
        return self.register(Principal(
            principal_id=user_id,
            principal_type=PrincipalType.USER,
            trust_level=trust_level,
            scopes=scopes or [],
        ))

    def register_tool(self, tool_id: str, *, owner: str = "", scopes: Optional[List[str]] = None,
                      trust_level: TrustLevel = TrustLevel.STANDARD) -> Principal:
        return self.register(Principal(
            principal_id=tool_id,
            principal_type=PrincipalType.TOOL,
            owner=owner,
            trust_level=trust_level,
            scopes=scopes or [],
        ))

    def get(self, principal_id: str) -> Optional[Principal]:
        return self._principals.get(principal_id)

    def get_or_agent(self, principal_id: str):
        """Resolve a principal id against generic principals, then agents."""
        principal = self._principals.get(principal_id)
        if principal is not None:
            return principal
        return self._agents.get(principal_id)

    def list_principals(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._principals.values()]

    def set_principal_status(self, principal_id: str, status: PrincipalStatus) -> bool:
        principal = self._principals.get(principal_id)
        if principal is None:
            return False
        principal.status = status
        principal.updated_at = time.time()
        if status in (PrincipalStatus.QUARANTINED, PrincipalStatus.REVOKED):
            principal.trust_level = TrustLevel.UNTRUSTED
        return True

    def quarantine_principal(self, principal_id: str) -> bool:
        return self.set_principal_status(principal_id, PrincipalStatus.QUARANTINED)

    def revoke_principal(self, principal_id: str) -> bool:
        return self.set_principal_status(principal_id, PrincipalStatus.REVOKED)

    def is_principal_active(self, principal_id: str) -> bool:
        principal = self._principals.get(principal_id)
        return principal is not None and principal.status == PrincipalStatus.ACTIVE

    def trust_level_of(self, principal_id: str) -> TrustLevel:
        """Resolve the trust level for a principal or agent id."""
        principal = self._principals.get(principal_id)
        if principal is not None:
            return principal.trust_level
        agent = self._agents.get(principal_id)
        if agent is not None:
            return agent.trust_level
        return TrustLevel.UNTRUSTED

    def active_principal_ids(self) -> List[str]:
        return [
            pid for pid, p in self._principals.items()
            if p.status == PrincipalStatus.ACTIVE
        ]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "agents": len(self._agents),
            "principals": len(self._principals),
            "quarantined": sum(
                1 for a in self._agents.values()
                if a.status == PrincipalStatus.QUARANTINED
            ),
            "active_agents": sum(
                1 for a in self._agents.values()
                if a.status == PrincipalStatus.ACTIVE
            ),
        }

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    @staticmethod
    def _emit_audit(event_type: str, principal_id: str, owner: str,
                    details: Optional[Dict[str, Any]] = None,
                    severity: Any = None) -> None:
        try:
            from aetheros_security.audit import (AuditEventType, AuditSeverity,
                                                 get_audit_logger)
            try:
                event = AuditEventType(event_type)
            except ValueError:
                event = AuditEventType.CUSTOM
            if not isinstance(severity, AuditSeverity):
                try:
                    severity = AuditSeverity(str(severity))
                except (ValueError, TypeError):
                    severity = AuditSeverity.INFO
            get_audit_logger().log(
                event,
                severity=severity,
                user=owner or principal_id,
                source="identity",
                details=details or {},
                message=f"Identity: {event_type} {principal_id}",
            )
        except Exception:
            logger.debug("Audit emit failed for %s", event_type, exc_info=True)


# Global identity registry
_identity_registry: IdentityRegistry | None = None


def get_identity_registry() -> IdentityRegistry:
    """Return the global IdentityRegistry singleton."""
    global _identity_registry
    if _identity_registry is None:
        _identity_registry = IdentityRegistry()
    return _identity_registry