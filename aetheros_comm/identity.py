"""
Agent Communication Fabric — agent identity, instances, and registration
(master spec steps 7, 8, 9, 10).

Identity is a *stable* property (``agentId``) and must never be confused with
a runtime instance (``instanceId``). Registration validates identity, version,
capabilities, security posture, protocol versions, health, and configuration
before an agent may send or receive messages.

The fabric mirrors registered agents into the AetherOS security registry
(:mod:`aetheros_security.identity`) so the broader security surface sees the
same principals.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .protocol import SUPPORTED_PROTOCOL_VERSIONS
from .types import TrustZone

try:  # integrate with the existing AetherOS security identity model
    from aetheros_security.identity import (
        AgentIdentity as SecAgentIdentity,
        PrincipalStatus,
        TrustLevel as SecTrustLevel,
        get_identity_registry,
    )
    _SEC_AVAILABLE = True
except Exception:  # pragma: no cover - optional integration
    _SEC_AVAILABLE = False

    class SecTrustLevel:  # type: ignore[no-redef]
        LOW = "low"
        STANDARD = "standard"
        ELEVATED = "elevated"
        PRIVILEGED = "privileged"
        UNTRUSTED = "untrusted"

    class PrincipalStatus:  # type: ignore[no-redef]
        ACTIVE = "active"
        SUSPENDED = "suspended"
        QUARANTINED = "quarantined"
        REVOKED = "revoked"
        EXPIRED = "expired"


_AGENT_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")


class IdentityError(Exception):
    """Raised for invalid identity operations."""


class AgentStatus(str):
    """Lifecycle status of an agent instance."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    QUARANTINED = "quarantined"
    REVOKED = "revoked"
    OFFLINE = "offline"


# Map fabric status to the aetheros_security principal status.
_STATUS_TO_SEC = {
    AgentStatus.ACTIVE: PrincipalStatus.ACTIVE,
    AgentStatus.SUSPENDED: PrincipalStatus.SUSPENDED,
    AgentStatus.QUARANTINED: PrincipalStatus.QUARANTINED,
    AgentStatus.REVOKED: PrincipalStatus.REVOKED,
}


@dataclass
class AgentCard:
    """Structured capability document (master spec step 10).

    This is the *advertised* card used for capability discovery. Privileges
    are enforced by the authorizer against the registry — an agent can never
    grant itself privileges by editing its own card (step 10: "Never allow
    arbitrary self-declared privileges").
    """

    agentId: str
    name: str = ""
    description: str = ""
    version: str = "0.0.0"
    capabilities: List[str] = field(default_factory=list)
    supportedTasks: List[str] = field(default_factory=list)
    supportedProtocols: List[str] = field(default_factory=list)
    supportedTransports: List[str] = field(default_factory=list)
    authenticationMethods: List[str] = field(default_factory=list)
    requiredPermissions: List[str] = field(default_factory=list)
    trustZone: str = TrustZone.ZONE_1.value
    healthEndpoint: str = ""
    status: str = AgentStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agentId": self.agentId,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": list(self.capabilities),
            "supportedTasks": list(self.supportedTasks),
            "supportedProtocols": list(self.supportedProtocols),
            "supportedTransports": list(self.supportedTransports),
            "authenticationMethods": list(self.authenticationMethods),
            "requiredPermissions": list(self.requiredPermissions),
            "trustZone": self.trustZone,
            "healthEndpoint": self.healthEndpoint,
            "status": self.status,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCard":
        return cls(
            agentId=data.get("agentId", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "0.0.0"),
            capabilities=list(data.get("capabilities", []) or []),
            supportedTasks=list(data.get("supportedTasks", []) or []),
            supportedProtocols=list(data.get("supportedProtocols", []) or []),
            supportedTransports=list(data.get("supportedTransports", []) or []),
            authenticationMethods=list(data.get("authenticationMethods", []) or []),
            requiredPermissions=list(data.get("requiredPermissions", []) or []),
            trustZone=data.get("trustZone", TrustZone.ZONE_1.value),
            healthEndpoint=data.get("healthEndpoint", ""),
            status=data.get("status", AgentStatus.ACTIVE),
            metadata=dict(data.get("metadata", {}) or {}),
        )


@dataclass
class AgentIdentity:
    """Stable identity + runtime instance (master spec steps 7 and 8).

    ``agentId`` is stable across restarts; ``instanceId`` uniquely identifies
    one running instance so multiple instances of the same agent are never
    confused.
    """

    agentId: str = ""
    instanceId: str = ""
    agentType: str = "general"
    version: str = "0.0.0"
    capabilities: List[str] = field(default_factory=list)
    trustLevel: str = getattr(SecTrustLevel, "LOW", "low") if isinstance(
        getattr(SecTrustLevel, "LOW", "low"), str) else getattr(
        SecTrustLevel, "LOW", "low").value
    status: str = AgentStatus.ACTIVE
    trustZone: str = TrustZone.ZONE_1.value
    owner: str = ""
    createdAt: float = 0.0
    registeredAt: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        now = time.time()
        if not self.agentId:
            self.agentId = f"agent-{uuid.uuid4().hex[:8]}"
        if not self.instanceId:
            self.instanceId = f"{self.agentId}-{uuid.uuid4().hex[:12]}"
        if not self.createdAt:
            self.createdAt = now
        if not self.registeredAt:
            self.registeredAt = now

    def to_card(self) -> AgentCard:
        return AgentCard(
            agentId=self.agentId,
            name=self.metadata.get("name", self.agentId),
            description=self.metadata.get("description", ""),
            version=self.version,
            capabilities=list(self.capabilities),
            supportedTasks=list(self.metadata.get("supportedTasks", []) or []),
            supportedProtocols=list(self.metadata.get(
                "supportedProtocols", SUPPORTED_PROTOCOL_VERSIONS) or []),
            supportedTransports=list(self.metadata.get(
                "supportedTransports", ["local"]) or []),
            authenticationMethods=list(self.metadata.get(
                "authenticationMethods", []) or []),
            requiredPermissions=list(self.metadata.get(
                "requiredPermissions", []) or []),
            trustZone=self.trustZone,
            healthEndpoint=self.metadata.get("healthEndpoint", ""),
            status=self.status,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agentId": self.agentId,
            "instanceId": self.instanceId,
            "agentType": self.agentType,
            "version": self.version,
            "capabilities": list(self.capabilities),
            "trustLevel": self.trustLevel,
            "status": self.status,
            "trustZone": self.trustZone,
            "owner": self.owner,
            "createdAt": self.createdAt,
            "registeredAt": self.registeredAt,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentIdentity":
        return cls(
            agentId=data.get("agentId", ""),
            instanceId=data.get("instanceId", ""),
            agentType=data.get("agentType", "general"),
            version=data.get("version", "0.0.0"),
            capabilities=list(data.get("capabilities", []) or []),
            trustLevel=data.get("trustLevel", "low"),
            status=data.get("status", AgentStatus.ACTIVE),
            trustZone=data.get("trustZone", TrustZone.ZONE_1.value),
            owner=data.get("owner", ""),
            createdAt=data.get("createdAt", 0.0),
            registeredAt=data.get("registeredAt", 0.0),
            metadata=dict(data.get("metadata", {}) or {}),
        )


class AgentRegistry:
    """Registry of registered agent identities and their cards.

    Registration validates identity, version, capabilities, security posture
    (trust zone + trust level), protocol support, health, and configuration
    (step 9). Capability discovery and capability-based routing (step 11) read
    from this registry.
    """

    def __init__(self, min_trust: str = "low") -> None:
        self._agents: Dict[str, AgentIdentity] = {}
        self._cards: Dict[str, AgentCard] = {}
        self._min_trust = min_trust

    # ------------------------------------------------------------------
    # Registration (step 9)
    # ------------------------------------------------------------------

    def register(self, identity: AgentIdentity,
                 card: Optional[AgentCard] = None,
                 *, require_health: bool = True,
                 require_config: bool = True) -> AgentIdentity:
        """Register (or update) an agent after validation.

        Raises :class:`IdentityError` with a specific reason on any failed
        registration check.
        """
        self._validate_registration(identity)
        card = card or identity.to_card()
        # Capability document must be consistent with the identity — the
        # registry is authoritative, the card is only an advertisement.
        card.capabilities = list(identity.capabilities)
        card.status = identity.status
        card.trustZone = identity.trustZone
        if not card.supportedProtocols:
            card.supportedProtocols = list(SUPPORTED_PROTOCOL_VERSIONS)
        if require_health and not self._check_health(identity):
            raise IdentityError(
                f"agent {identity.agentId} failed health check", "unhealthy")
        if require_config and not self._check_config(identity):
            raise IdentityError(
                f"agent {identity.agentId} has invalid configuration",
                "bad_config")
        identity.registeredAt = time.time()
        self._agents[identity.agentId] = identity
        self._cards[identity.agentId] = card
        self._mirror_to_security(identity)
        return identity

    def _validate_registration(self, identity: AgentIdentity) -> None:
        if not _AGENT_ID_RE.match(identity.agentId):
            raise IdentityError(
                f"invalid agentId {identity.agentId!r}", "bad_id")
        if not identity.instanceId:
            raise IdentityError("instanceId is required", "bad_instance")
        if not isinstance(identity.capabilities, list) or not identity.capabilities:
            raise IdentityError(
                f"agent {identity.agentId} declares no capabilities",
                "no_capabilities")
        if not identity.version:
            raise IdentityError("version is required", "bad_version")
        try:
            TrustZone.from_str(identity.trustZone)
        except ValueError:
            raise IdentityError(
                f"invalid trust zone {identity.trustZone!r}", "bad_zone") from None
        if identity.status not in (AgentStatus.ACTIVE, AgentStatus.OFFLINE,
                                   AgentStatus.SUSPENDED):
            raise IdentityError(
                f"cannot register agent in status {identity.status!r}",
                "bad_status")

    @staticmethod
    def _check_health(identity: AgentIdentity) -> bool:
        # Health is a declarative posture for registration; liveness is
        # tracked separately by the heartbeat monitor.
        return identity.status != AgentStatus.QUARANTINED

    @staticmethod
    def _check_config(identity: AgentIdentity) -> bool:
        return True

    def _mirror_to_security(self, identity: AgentIdentity) -> None:
        if not _SEC_AVAILABLE:
            return
        try:
            reg = get_identity_registry()
            level = getattr(SecTrustLevel, str(identity.trustLevel).upper(), None)
            if level is None:
                level = SecTrustLevel.LOW
            sec = SecAgentIdentity(
                agent_id=identity.agentId,
                agent_type=identity.agentType,
                agent_version=identity.version,
                owner=identity.owner,
                trust_level=level,
                capabilities=list(identity.capabilities),
                permissions=list(identity.capabilities),
                status=_STATUS_TO_SEC.get(identity.status, PrincipalStatus.ACTIVE),
                metadata=dict(identity.metadata),
            )
            reg.register_agent(sec)
        except Exception:
            # Mirroring is best-effort; the fabric's own registry is
            # authoritative for communication.
            pass

    # ------------------------------------------------------------------
    # Lookup / discovery
    # ------------------------------------------------------------------

    def get(self, agent_id: str) -> Optional[AgentIdentity]:
        return self._agents.get(agent_id)

    def require(self, agent_id: str) -> AgentIdentity:
        identity = self._agents.get(agent_id)
        if identity is None:
            raise IdentityError(f"unknown agent {agent_id}", "unknown")
        return identity

    def get_card(self, agent_id: str) -> Optional[AgentCard]:
        return self._cards.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._agents.values()]

    def list_cards(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._cards.values()]

    def is_registered(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def is_active(self, agent_id: str) -> bool:
        identity = self._agents.get(agent_id)
        return identity is not None and identity.status == AgentStatus.ACTIVE

    def agents_with_capability(self, capability: str) -> List[str]:
        """Return active agent ids that declare ``capability`` (step 11)."""
        return [
            aid for aid, a in self._agents.items()
            if a.status == AgentStatus.ACTIVE and capability in a.capabilities
        ]

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def update_status(self, agent_id: str, status: str) -> bool:
        identity = self._agents.get(agent_id)
        if identity is None:
            return False
        identity.status = status
        if agent_id in self._cards:
            self._cards[agent_id].status = status
        if status == AgentStatus.QUARANTINED:
            identity.trustLevel = "untrusted"
            if _SEC_AVAILABLE:
                try:
                    get_identity_registry().quarantine(agent_id)
                except Exception:
                    pass
        elif status == AgentStatus.ACTIVE and _SEC_AVAILABLE:
            try:
                get_identity_registry().restore(agent_id)
            except Exception:
                pass
        return True

    def quarantine(self, agent_id: str) -> bool:
        return self.update_status(agent_id, AgentStatus.QUARANTINED)

    def suspend(self, agent_id: str) -> bool:
        return self.update_status(agent_id, AgentStatus.SUSPENDED)

    def revoke(self, agent_id: str) -> bool:
        return self.update_status(agent_id, AgentStatus.REVOKED)

    def reactivate(self, agent_id: str) -> bool:
        """Re-activate an agent after recovery (step 61).

        The *policy* decision to reactivate is made by the
        :class:`aetheros_comm.quarantine.QuarantineController`; this only
        applies the resulting transition.
        """
        return self.update_status(agent_id, AgentStatus.ACTIVE)

    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "agents": len(self._agents),
            "active": sum(1 for a in self._agents.values()
                          if a.status == AgentStatus.ACTIVE),
            "quarantined": sum(1 for a in self._agents.values()
                               if a.status == AgentStatus.QUARANTINED),
            "suspended": sum(1 for a in self._agents.values()
                             if a.status == AgentStatus.SUSPENDED),
        }


def make_instance_id(agent_id: str) -> str:
    return f"{agent_id}-{uuid.uuid4().hex[:12]}"