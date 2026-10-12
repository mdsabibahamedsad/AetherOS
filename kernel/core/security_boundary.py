"""
Security Boundary — the kernel's trusted security enforcement layer.

Implements fail-closed design, prompt injection defense, and capability authorization.
"""

from __future__ import annotations

import logging
import threading
import time
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum

from kernel.core.types import (
    CapabilityInvocation,
    CapabilityDescriptor,
    CapabilityRiskLevel,
    AuthorityGrant,
    DataClassification,
    ProvenanceType,
    AgentIdentity,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class SecurityDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    QUARANTINE = "quarantine"
    REQUIRE_APPROVAL = "require_approval"
    CHALLENGE = "challenge"


@dataclass
class SecurityCheckResult:
    """Result of a security check."""
    decision: SecurityDecision
    reason: str = ""
    risk_factors: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)
    requires_human: bool = False


class SecurityBoundary:
    """
    The kernel's security boundary — all capability invocations pass through here.
    
    Implements:
    - Fail-closed design
    - Prompt injection defense
    - Capability authorization
    - Information flow control
    - Emergency stop integration
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        # Emergency stop
        self._emergency_stop_active = False
        self._emergency_stop_scope: Set[str] = set()  # agent_ids, "global"
        
        # Quarantine
        self._quarantined_agents: Set[str] = set()
        self._quarantined_capabilities: Set[str] = set()
        
        # Prompt injection patterns
        self._injection_patterns: List[re.Pattern] = []
        self._compile_injection_patterns()
        
        # Trust boundaries
        self._trusted_sources: Set[str] = {"kernel", "human", "system"}
        self._untrusted_sources: Set[str] = {
            "web", "email", "pdf", "image", "ocr", "browser",
            "tool_result", "sensor", "ambient", "external_agent", "advertisement", "qr_code"
        }
        
        # Custom security checks
        self._custom_checks: List[Callable] = []

    def _compile_injection_patterns(self) -> None:
        """Compile prompt injection detection patterns."""
        patterns = [
            # Direct instruction injection
            r"ignore\s+(previous|all|above)\s+instructions?",
            r"disregard\s+(previous|all|above)\s+instructions?",
            r"forget\s+(previous|all|above)\s+instructions?",
            r"new\s+instructions?:",
            r"system\s+prompt:",
            r"you\s+are\s+now",
            r"act\s+as\s+(if\s+you\s+are|a\s+different)",
            r"pretend\s+to\s+be",
            r"roleplay\s+as",
            # Authority escalation
            r"you\s+have\s+(full|complete|unrestricted|admin|root)\s+(access|permission|authority)",
            r"grant\s+(me|yourself)\s+(full|complete|unrestricted|admin|root)",
            r"bypass\s+(security|authorization|permission|approval)",
            r"override\s+(security|policy|restriction|limit)",
            # Data exfiltration
            r"(send|transmit|exfiltrate|leak)\s+(data|information|secrets?|keys?|tokens?)",
            r"print\s+(env|environment|secrets?|keys?|tokens?)",
            # Tool manipulation
            r"call\s+(tool|function)\s+",
            r"execute\s+(code|command|shell|script)",
            # Identity manipulation
            r"you\s+are\s+(the\s+)?(admin|root|system|kernel)",
            r"your\s+(name|identity)\s+is",
        ]
        
        for pattern in patterns:
            try:
                self._injection_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                pass

    def check_invocation(
        self,
        invocation: CapabilityInvocation,
        descriptor: CapabilityDescriptor,
        grant: AuthorityGrant,
    ) -> SecurityCheckResult:
        """
        Main security check for capability invocation.
        
        This is the central security enforcement point.
        """
        # 1. Emergency stop check
        if self._emergency_stop_active:
            if "global" in self._emergency_stop_scope or invocation.agent_id in self._emergency_stop_scope:
                return SecurityCheckResult(
                    decision=SecurityDecision.DENY,
                    reason="Emergency stop active",
                    risk_factors=["emergency_stop"],
                )

        # 2. Quarantine check
        if invocation.agent_id in self._quarantined_agents:
            return SecurityCheckResult(
                decision=SecurityDecision.QUARANTINE,
                reason="Agent quarantined",
                risk_factors=["quarantined_agent"],
            )

        if invocation.capability_id in self._quarantined_capabilities:
            return SecurityCheckResult(
                decision=SecurityDecision.QUARANTINE,
                reason="Capability quarantined",
                risk_factors=["quarantined_capability"],
            )

        # 3. Authorization check
        auth_result = self._check_authorization(invocation, descriptor, grant)
        if auth_result.decision != SecurityDecision.ALLOW:
            return auth_result

        # 4. Prompt injection check (for inputs)
        injection_result = self._check_prompt_injection(invocation.inputs)
        if injection_result.decision != SecurityDecision.ALLOW:
            return injection_result

        # 5. Information flow control
        ifc_result = self._check_information_flow(invocation, descriptor, grant)
        if ifc_result.decision != SecurityDecision.ALLOW:
            return ifc_result

        # 6. Side-effect risk check
        risk_result = self._check_side_effect_risk(invocation, descriptor)
        if risk_result.decision != SecurityDecision.ALLOW:
            return risk_result

        # 7. Custom checks
        for check in self._custom_checks:
            try:
                result = check(invocation, descriptor, grant)
                if result and result.decision != SecurityDecision.ALLOW:
                    return result
            except Exception as exc:
                logger.error("Custom security check failed: %s", exc)

        return SecurityCheckResult(decision=SecurityDecision.ALLOW)

    def _check_authorization(
        self,
        invocation: CapabilityInvocation,
        descriptor: CapabilityDescriptor,
        grant: AuthorityGrant,
    ) -> SecurityCheckResult:
        """Check capability authorization."""
        # Check capability is granted
        if invocation.capability_id not in grant.capabilities:
            return SecurityCheckResult(
                decision=SecurityDecision.DENY,
                reason=f"Capability not granted: {invocation.capability_id}",
                risk_factors=["capability_not_granted"],
            )

        # Check grant validity
        if not grant.is_valid():
            return SecurityCheckResult(
                decision=SecurityDecision.DENY,
                reason="Authority grant expired or revoked",
                risk_factors=["grant_invalid"],
            )

        # Check required credentials
        for cred in descriptor.required_credentials:
            if cred not in grant.credentials:
                return SecurityCheckResult(
                    decision=SecurityDecision.DENY,
                    reason=f"Missing required credential: {cred}",
                    risk_factors=["missing_credential"],
                )

        return SecurityCheckResult(decision=SecurityDecision.ALLOW)

    def _check_prompt_injection(self, inputs: Dict[str, Any]) -> SecurityCheckResult:
        """Check inputs for prompt injection attempts."""
        # Convert all string inputs to text for scanning
        text_parts = []
        for value in inputs.values():
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, dict):
                text_parts.extend(str(v) for v in value.values() if isinstance(v, str))
            elif isinstance(value, list):
                text_parts.extend(str(v) for v in value if isinstance(v, str))

        full_text = " ".join(text_parts)
        
        for pattern in self._injection_patterns:
            if pattern.search(full_text):
                return SecurityCheckResult(
                    decision=SecurityDecision.DENY,
                    reason="Prompt injection detected",
                    risk_factors=["prompt_injection"],
                    requires_human=True,
                )

        return SecurityCheckResult(decision=SecurityDecision.ALLOW)

    def _check_information_flow(
        self,
        invocation: CapabilityInvocation,
        descriptor: CapabilityDescriptor,
        grant: AuthorityGrant,
    ) -> SecurityCheckResult:
        """Check information flow control."""
        # Check data classification flow
        data_class = descriptor.data_classification
        
        # If capability handles sensitive data, verify authorization
        if data_class in (DataClassification.SECRET, DataClassification.HIGHLY_SENSITIVE):
            if "sensitive_data_access" not in grant.capabilities:
                return SecurityCheckResult(
                    decision=SecurityDecision.DENY,
                    reason="Sensitive data access not authorized",
                    risk_factors=["unauthorized_sensitive_access"],
                )

        # Check network egress for sensitive data
        if descriptor.network_access and data_class != DataClassification.PUBLIC:
            # Would need to verify network targets are approved
            # For now, require explicit network scope
            if not grant.network_scopes:
                return SecurityCheckResult(
                    decision=SecurityDecision.REQUIRE_APPROVAL,
                    reason="Network egress with sensitive data requires approval",
                    risk_factors=["sensitive_network_egress"],
                    requires_human=True,
                )

        return SecurityCheckResult(decision=SecurityDecision.ALLOW)

    def _check_side_effect_risk(
        self,
        invocation: CapabilityInvocation,
        descriptor: CapabilityDescriptor,
    ) -> SecurityCheckResult:
        """Check side-effect risk level."""
        risk_levels = descriptor.side_effects
        
        # High-risk side effects require additional checks
        high_risks = {
            CapabilityRiskLevel.FINANCIAL,
            CapabilityRiskLevel.PHYSICAL,
            CapabilityRiskLevel.SECURITY_CRITICAL,
        }
        
        if any(r in high_risks for r in risk_levels):
            return SecurityCheckResult(
                decision=SecurityDecision.REQUIRE_APPROVAL,
                reason=f"High-risk capability requires approval: {[r.value for r in risk_levels if r in high_risks]}",
                risk_factors=[r.value for r in risk_levels if r in high_risks],
                requires_human=True,
            )

        # Irreversible operations require confirmation
        if CapabilityRiskLevel.IRREVERSIBLE in risk_levels and not descriptor.reversibility:
            return SecurityCheckResult(
                decision=SecurityDecision.REQUIRE_APPROVAL,
                reason="Irreversible operation requires confirmation",
                risk_factors=["irreversible"],
                requires_human=True,
            )

        return SecurityCheckResult(decision=SecurityDecision.ALLOW)

    def register_custom_check(self, check: Callable) -> None:
        """Register a custom security check."""
        self._custom_checks.append(check)

    def activate_emergency_stop(self, scope: str = "global") -> None:
        """Activate emergency stop."""
        with self._lock:
            self._emergency_stop_active = True
            self._emergency_stop_scope.add(scope)

        logger.critical("SECURITY: Emergency stop activated for %s", scope)

        if self.event_bus:
            self.event_bus.emit("security.emergency_stop", {
                "scope": scope,
                "activated_at": _now(),
            })

    def deactivate_emergency_stop(self, scope: str = "global") -> None:
        """Deactivate emergency stop."""
        with self._lock:
            self._emergency_stop_scope.discard(scope)
            if not self._emergency_stop_scope:
                self._emergency_stop_active = False

        logger.info("SECURITY: Emergency stop deactivated for %s", scope)

        if self.event_bus:
            self.event_bus.emit("security.emergency_stop_cleared", {
                "scope": scope,
            })

    def quarantine_agent(self, agent_id: str, reason: str = "security") -> None:
        """Quarantine an agent."""
        with self._lock:
            self._quarantined_agents.add(agent_id)

        logger.warning("SECURITY: Agent %s quarantined: %s", agent_id, reason)

        if self.event_bus:
            self.event_bus.emit("security.agent_quarantined", {
                "agent_id": agent_id,
                "reason": reason,
            })

    def release_quarantine(self, agent_id: str) -> None:
        """Release agent from quarantine."""
        with self._lock:
            self._quarantined_agents.discard(agent_id)

        if self.event_bus:
            self.event_bus.emit("security.quarantine_released", {
                "agent_id": agent_id,
            })

    def quarantine_capability(self, capability_id: str, reason: str = "security") -> None:
        """Quarantine a capability."""
        with self._lock:
            self._quarantined_capabilities.add(capability_id)

        if self.event_bus:
            self.event_bus.emit("security.capability_quarantined", {
                "capability_id": capability_id,
                "reason": reason,
            })

    def verify_identity(self, identity: AgentIdentity) -> bool:
        """Verify agent identity."""
        if not identity.is_usable():
            return False
        
        # Check trust level
        if identity.trust_level < 2:  # Below T2_VERIFIED
            return False
        
        # Check status
        if identity.status in ("revoked", "expired", "quarantined", "suspended"):
            return False
        
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get security boundary statistics."""
        with self._lock:
            return {
                "emergency_stop_active": self._emergency_stop_active,
                "emergency_stop_scopes": list(self._emergency_stop_scope),
                "quarantined_agents": len(self._quarantined_agents),
                "quarantined_capabilities": len(self._quarantined_capabilities),
                "injection_patterns": len(self._injection_patterns),
                "custom_checks": len(self._custom_checks),
            }

    def shutdown(self) -> None:
        """Shutdown the security boundary."""
        logger.info("SecurityBoundary: shutting down")
        with self._lock:
            self._emergency_stop_active = False
            self._emergency_stop_scope.clear()
            self._quarantined_agents.clear()
            self._quarantined_capabilities.clear()
            self._custom_checks.clear()