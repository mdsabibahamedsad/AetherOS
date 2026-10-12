"""
Authority Manager — authority grants, delegation, and capability scoping.

Implements the authority model: Kernel determines minimum authority required.
Agents cannot self-authorize. Child authority ⊆ Parent authority.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.core.types import (
    Intent,
    AuthorityGrant,
    AgentIdentity,
    ResourceBudget,
    CapabilityRiskLevel,
    DataClassification,
    AgentLifecycleState,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class DelegationRecord:
    """Record of a delegation."""
    delegation_id: str
    parent_grant_id: str
    child_agent_id: str
    child_grant_id: str
    capabilities: List[str]
    resources: ResourceBudget
    expires_at: Optional[float]
    created_at: float = field(default_factory=_now)
    revoked: bool = False


class AuthorityManager:
    """
    Manages authority grants and delegation.
    
    The Kernel is the sole authority granter. All capability access
    must be mediated through an AuthorityGrant.
    """

    def __init__(self, config, event_bus: EventBus, policy_engine, security_boundary):
        self.config = config
        self.event_bus = event_bus
        self.policy_engine = policy_engine
        self.security_boundary = security_boundary
        self._lock = threading.RLock()
        self._grants: Dict[str, AuthorityGrant] = {}
        self._delegations: Dict[str, DelegationRecord] = {}
        self._grant_index: Dict[str, Set[str]] = {}  # agent_id -> grant_ids
        self.resource_manager = None  # Set by kernel after initialization

    def set_resource_manager(self, resource_manager) -> None:
        """Set the resource manager (called by kernel)."""
        self.resource_manager = resource_manager

    def create_grant(self, intent: Intent, parent_grant_id: str = None) -> AuthorityGrant:
        """Create an authority grant for an intent."""
        # Evaluate policy to determine allowed capabilities
        policy_result = self.policy_engine.evaluate_intent(intent) if self.policy_engine else None

        if policy_result:
            allowed_capabilities = getattr(policy_result, 'matched_rules', intent.requested_capabilities)
            # For now, use requested capabilities if policy allows
            if policy_result.decision.value == "deny":
                allowed_capabilities = []
            else:
                allowed_capabilities = intent.requested_capabilities
            denied_capabilities = getattr(policy_result, 'denied_rules', [])
        else:
            allowed_capabilities = intent.requested_capabilities
            denied_capabilities = []

        if denied_capabilities:
            logger.warning("Policy denied capabilities for intent %s: %s", intent.intent_id, denied_capabilities)

        # Build resource budget (constrained by policy and availability)
        resources = intent.requested_resources
        if self.resource_manager:
            available = self.resource_manager.get_available()
            resources = self._constrain_resources(resources, available)

        # Build data scopes based on privacy class
        data_scopes = self._derive_data_scopes(intent)

        # Build network scopes
        network_scopes = self._derive_network_scopes(intent)

        # Build filesystem scopes
        filesystem_scopes = self._derive_filesystem_scopes(intent)

        # Build device scopes
        device_scopes = self._derive_device_scopes(intent)

        # Determine required credentials
        credentials = self._derive_credentials(intent, allowed_capabilities)

        grant = AuthorityGrant(
            grant_id=new_id("grant"),
            agent_id="",  # Will be set when agent is created
            intent_id=intent.intent_id,
            capabilities=allowed_capabilities,
            resources=resources,
            data_scopes=data_scopes,
            network_scopes=network_scopes,
            filesystem_scopes=filesystem_scopes,
            device_scopes=device_scopes,
            credentials=credentials,
            parent_grant_id=parent_grant_id,
            expires_at=intent.deadline,
            metadata={
                "risk_level": intent.risk_level.value,
                "autonomy_level": intent.autonomy_level,
                "privacy_class": intent.privacy_class.value,
            },
        )

        with self._lock:
            self._grants[grant.grant_id] = grant
            self._grant_index.setdefault(grant.agent_id, set()).add(grant.grant_id)

        if self.event_bus:
            self.event_bus.emit("authority.grant.created", {
                "grant_id": grant.grant_id,
                "intent_id": intent.intent_id,
                "capabilities": allowed_capabilities,
                "parent_grant_id": parent_grant_id,
            })

        return grant

    def grant_authority(
        self,
        agent_id: str,
        intent: Intent,
        parent_grant_id: str = None,
    ) -> AuthorityGrant:
        """Grant authority to a specific agent for an intent."""
        grant = self.create_grant(intent, parent_grant_id)
        grant.agent_id = agent_id

        with self._lock:
            self._grant_index.setdefault(agent_id, set()).add(grant.grant_id)

        if self.event_bus:
            self.event_bus.emit("authority.grant.assigned", {
                "grant_id": grant.grant_id,
                "agent_id": agent_id,
            })

        return grant

    def delegate_authority(
        self,
        parent_agent_id: str,
        child_agent_id: str,
        intent: Intent,
        parent_grant_id: str = None,
    ) -> AuthorityGrant:
        """
        Delegate authority from parent to child agent.
        
        Enforces: ChildAuthority ⊆ ParentAuthority
        """
        # Get parent grant
        parent_grant = self.get_grant(parent_grant_id)
        if not parent_grant:
            # Find active grant for parent agent
            grants = self.get_grants_for_agent(parent_agent_id)
            if not grants:
                raise PermissionError(f"Parent agent {parent_agent_id} has no authority grant")
            parent_grant = grants[0]  # Use most recent

        # Child capabilities must be subset of parent
        child_capabilities = [c for c in intent.requested_capabilities if c in parent_grant.capabilities]
        if len(child_capabilities) != len(intent.requested_capabilities):
            denied = set(intent.requested_capabilities) - set(parent_grant.capabilities)
            logger.warning("Delegation denied capabilities (not in parent): %s", denied)

        # Child resources must be subset of parent
        child_resources = self._constrain_resources(intent.requested_resources, parent_grant.resources)

        # Child scopes must be subset of parent
        child_data_scopes = [s for s in self._derive_data_scopes(intent) if s in parent_grant.data_scopes]
        child_network_scopes = [s for s in self._derive_network_scopes(intent) if s in parent_grant.network_scopes]
        child_filesystem_scopes = [s for s in self._derive_filesystem_scopes(intent) if s in parent_grant.filesystem_scopes]
        child_device_scopes = [s for s in self._derive_device_scopes(intent) if s in parent_grant.device_scopes]

        # Create child grant
        child_grant = AuthorityGrant(
            grant_id=new_id("grant"),
            agent_id=child_agent_id,
            intent_id=intent.intent_id,
            capabilities=child_capabilities,
            resources=child_resources,
            data_scopes=child_data_scopes,
            network_scopes=child_network_scopes,
            filesystem_scopes=child_filesystem_scopes,
            device_scopes=child_device_scopes,
            credentials=[],  # Child gets no credentials by default
            parent_grant_id=parent_grant.grant_id,
            expires_at=min(
                intent.deadline or float('inf'),
                parent_grant.expires_at or float('inf')
            ) if (intent.deadline or parent_grant.expires_at) else None,
            revocable=True,
            metadata={
                "delegated_from": parent_agent_id,
                "delegation_depth": parent_grant.metadata.get("delegation_depth", 0) + 1,
            },
        )

        # Check delegation depth limit
        depth = child_grant.metadata["delegation_depth"]
        if depth > self.config.max_agent_depth:
            raise PermissionError(f"Delegation depth {depth} exceeds limit {self.config.max_agent_depth}")

        with self._lock:
            self._grants[child_grant.grant_id] = child_grant
            self._grant_index.setdefault(child_agent_id, set()).add(child_grant.grant_id)

        # Record delegation
        delegation = DelegationRecord(
            delegation_id=new_id("deleg"),
            parent_grant_id=parent_grant.grant_id,
            child_agent_id=child_agent_id,
            child_grant_id=child_grant.grant_id,
            capabilities=child_capabilities,
            resources=child_resources,
            expires_at=child_grant.expires_at,
        )
        self._delegations[delegation.delegation_id] = delegation

        if self.event_bus:
            self.event_bus.emit("authority.delegated", {
                "parent_agent_id": parent_agent_id,
                "child_agent_id": child_agent_id,
                "parent_grant_id": parent_grant.grant_id,
                "child_grant_id": child_grant.grant_id,
                "capabilities": child_capabilities,
                "delegation_depth": depth,
            })

        return child_grant

    def revoke_grant(self, grant_id: str, reason: str = "revoked") -> bool:
        """Revoke an authority grant (fail-closed: expiry set firmly in the past)."""
        with self._lock:
            grant = self._grants.get(grant_id)
            if not grant:
                return False

            grant.revocable = False
            grant.expires_at = _now() - 1.0

            # Also revoke all delegated grants
            self._revoke_delegated(grant_id, reason)

        if self.event_bus:
            self.event_bus.emit("authority.grant.revoked", {
                "grant_id": grant_id,
                "agent_id": grant.agent_id,
                "reason": reason,
            })

        return True

    def _revoke_delegated(self, parent_grant_id: str, reason: str) -> None:
        """Recursively revoke all grants delegated from a parent."""
        for grant in list(self._grants.values()):
            if grant.parent_grant_id == parent_grant_id:
                grant.revocable = False
                grant.expires_at = _now() - 1.0
                self._revoke_delegated(grant.grant_id, reason)

    def get_grant(self, grant_id: str) -> Optional[AuthorityGrant]:
        """Get a grant by ID."""
        with self._lock:
            return self._grants.get(grant_id)

    def get_grants_for_agent(self, agent_id: str) -> List[AuthorityGrant]:
        """Get all grants for an agent."""
        with self._lock:
            grant_ids = self._grant_index.get(agent_id, set())
            return [self._grants[gid] for gid in grant_ids if gid in self._grants]

    def get_active_grant(self, agent_id: str) -> Optional[AuthorityGrant]:
        """Get the active (non-expired) grant for an agent."""
        grants = self.get_grants_for_agent(agent_id)
        now = _now()
        for grant in grants:
            if grant.is_valid():
                return grant
        return None

    def check_capability(self, agent_id: str, capability: str) -> bool:
        """Check if an agent has a capability granted."""
        grant = self.get_active_grant(agent_id)
        if not grant:
            return False
        return capability in grant.capabilities

    def check_data_scope(self, agent_id: str, scope: str) -> bool:
        """Check if an agent has a data scope granted."""
        grant = self.get_active_grant(agent_id)
        if not grant:
            return False
        return scope in grant.data_scopes

    def check_network_scope(self, agent_id: str, scope: str) -> bool:
        """Check if an agent has a network scope granted."""
        grant = self.get_active_grant(agent_id)
        if not grant:
            return False
        return scope in grant.network_scopes

    def check_filesystem_scope(self, agent_id: str, scope: str) -> bool:
        """Check if an agent has a filesystem scope granted."""
        grant = self.get_active_grant(agent_id)
        if not grant:
            return False
        return scope in grant.filesystem_scopes

    def _constrain_resources(self, requested: ResourceBudget, available: ResourceBudget) -> ResourceBudget:
        """Constrain requested resources to available."""
        return ResourceBudget(
            cpu_cores=min(requested.cpu_cores, available.cpu_cores),
            gpu_memory_mb=min(requested.gpu_memory_mb, available.gpu_memory_mb),
            ram_mb=min(requested.ram_mb, available.ram_mb),
            disk_mb=min(requested.disk_mb, available.disk_mb),
            network_mbps=min(requested.network_mbps, available.network_mbps),
            llm_tokens_per_minute=min(requested.llm_tokens_per_minute, available.llm_tokens_per_minute),
            model_concurrency=min(requested.model_concurrency, available.model_concurrency),
            tool_concurrency=min(requested.tool_concurrency, available.tool_concurrency),
            browser_sessions=min(requested.browser_sessions, available.browser_sessions),
            computer_sessions=min(requested.computer_sessions, available.computer_sessions),
            device_sessions=min(requested.device_sessions, available.device_sessions),
            research_requests_per_minute=min(requested.research_requests_per_minute, available.research_requests_per_minute),
            agent_slots=min(requested.agent_slots, available.agent_slots),
            automation_slots=min(requested.automation_slots, available.automation_slots),
        )

    def _derive_data_scopes(self, intent: Intent) -> List[str]:
        """Derive data scopes from intent."""
        scopes = []
        if intent.privacy_class == DataClassification.PUBLIC:
            scopes.append("public")
        elif intent.privacy_class == DataClassification.INTERNAL:
            scopes.extend(["public", "internal"])
        elif intent.privacy_class == DataClassification.PRIVATE:
            scopes.extend(["public", "internal", "private"])
        elif intent.privacy_class == DataClassification.CONFIDENTIAL:
            scopes.extend(["public", "internal", "private", "confidential"])
        elif intent.privacy_class == DataClassification.SECRET:
            scopes.extend(["public", "internal", "private", "confidential", "secret"])
        elif intent.privacy_class == DataClassification.HIGHLY_SENSITIVE:
            scopes.extend(["public", "internal", "private", "confidential", "secret", "highly_sensitive"])
        
        # Add explicit data scopes from intent
        scopes.extend(intent.data_scope)
        return list(set(scopes))

    def _derive_network_scopes(self, intent: Intent) -> List[str]:
        """Derive network scopes from intent."""
        scopes = ["localhost"]
        # Add explicit network scopes
        scopes.extend(intent.authority_scope)
        return list(set(scopes))

    def _derive_filesystem_scopes(self, intent: Intent) -> List[str]:
        """Derive filesystem scopes from intent."""
        scopes = ["workspace", "scratch"]
        return list(set(scopes))

    def _derive_device_scopes(self, intent: Intent) -> List[str]:
        """Derive device scopes from intent."""
        scopes = []
        if any("device" in c or "robot" in c for c in intent.requested_capabilities):
            scopes.append("sensors")
            if CapabilityRiskLevel.PHYSICAL in [CapabilityRiskLevel(c) for c in [CapabilityRiskLevel.READ_ONLY]]:
                scopes.append("actuators")
        return scopes

    def _derive_credentials(self, intent: Intent, capabilities: List[str]) -> List[str]:
        """Derive required credentials from capabilities."""
        credentials = []
        credential_map = {
            "github": "GITHUB_TOKEN",
            "gitlab": "GITLAB_TOKEN",
            "aws": "AWS_CREDENTIALS",
            "gcp": "GCP_CREDENTIALS",
            "azure": "AZURE_CREDENTIALS",
            "docker": "DOCKER_CREDENTIALS",
            "kubernetes": "KUBECONFIG",
        }
        for cap in capabilities:
            for prefix, cred in credential_map.items():
                if cap.startswith(prefix):
                    credentials.append(cred)
        return list(set(credentials))

    def get_stats(self) -> Dict[str, Any]:
        """Get authority manager statistics."""
        with self._lock:
            total_grants = len(self._grants)
            active_grants = sum(1 for g in self._grants.values() if g.is_valid())
            total_delegations = len(self._delegations)
            active_delegations = sum(1 for d in self._delegations.values() if not d.revoked)
            agents_with_grants = len(self._grant_index)

        return {
            "total_grants": total_grants,
            "active_grants": active_grants,
            "expired_grants": total_grants - active_grants,
            "total_delegations": total_delegations,
            "active_delegations": active_delegations,
            "agents_with_grants": agents_with_grants,
        }

    def shutdown(self) -> None:
        """Shutdown the authority manager."""
        logger.info("AuthorityManager: shutting down")
        with self._lock:
            self._grants.clear()
            self._delegations.clear()
            self._grant_index.clear()