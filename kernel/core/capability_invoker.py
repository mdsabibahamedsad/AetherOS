"""
Capability Invoker — the syscall execution layer.

Every capability invocation passes through:
CapabilityManager → AuthorityManager → PolicyEngine → SecurityBoundary → 
ResourceManager → CapabilityInvoker → Verification → Audit
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

from kernel.core.types import (
    CapabilityInvocation,
    CapabilityDescriptor,
    CapabilityRiskLevel,
    DataClassification,
    ProvenanceType,
    AgentLifecycleState,
    AuthorityGrant,
    ResourceAllocation,
    ResourceBudget,
    new_id,
    _now,
)
from kernel.event_bus import EventBus, EventTopics

logger = logging.getLogger(__name__)


@dataclass
class InvocationContext:
    """Context for a capability invocation."""
    invocation: CapabilityInvocation
    descriptor: CapabilityDescriptor
    grant: AuthorityGrant
    process: Any  # AgentProcess
    start_time: float = field(default_factory=lambda: __import__('time').time())
    verification_results: Dict[str, Any] = field(default_factory=dict)


class CapabilityInvoker:
    """
    Executes capability invocations with full authorization and verification.
    
    The CapabilityInvoker is the kernel's syscall handler. No direct bypasses allowed.
    """

    def __init__(
        self,
        config,
        event_bus: EventBus,
        capability_manager,
        authority_manager,
        policy_engine,
        security_boundary,
        resource_manager,
    ):
        self.config = config
        self.event_bus = event_bus
        self.capability_manager = capability_manager
        self.authority_manager = authority_manager
        self.policy_engine = policy_engine
        self.security_boundary = security_boundary
        self.resource_manager = resource_manager
        self._lock = threading.RLock()
        self._verification_strategies: Dict[str, Callable] = {}
        self._invocation_history: List[Dict[str, Any]] = []

        # Register default verification strategies
        self._register_default_verifiers()

    def _register_default_verifiers(self) -> None:
        """Register default verification strategies."""
        self._verification_strategies["observe"] = self._verify_observe
        self._verification_strategies["verify"] = self._verify_execute
        self._verification_strategies["attest"] = self._verify_attest

    def register_verifier(self, strategy: str, verifier: Callable) -> None:
        """Register a custom verification strategy."""
        self._verification_strategies[strategy] = verifier

    def invoke(self, invocation: CapabilityInvocation) -> CapabilityInvocation:
        """
        Invoke a capability with full authorization pipeline.
        
        Returns the invocation with result/error populated.
        """
        logger.debug("CapabilityInvoker: invoking %s for agent %s",
                     invocation.capability_id, invocation.agent_id)

        # 1. Get capability descriptor
        descriptor = self.capability_manager.get_descriptor(invocation.capability_id)
        if not descriptor:
            invocation.status = "denied"
            invocation.error = f"Capability not found: {invocation.capability_id}"
            self._record_denial(invocation, "capability_not_found")
            return invocation

        # 2. Get authority grant
        grant = self.authority_manager.get_grant(invocation.authority_grant_id)
        if not grant:
            invocation.status = "denied"
            invocation.error = f"Authority grant not found: {invocation.authority_grant_id}"
            self._record_denial(invocation, "grant_not_found")
            return invocation

        if not grant.is_valid():
            invocation.status = "denied"
            invocation.error = "Authority grant expired or revoked"
            self._record_denial(invocation, "grant_invalid")
            return invocation

        # 3. Check capability is granted
        if invocation.capability_id not in grant.capabilities:
            invocation.status = "denied"
            invocation.error = f"Capability not granted: {invocation.capability_id}"
            self._record_denial(invocation, "capability_not_granted")
            return invocation

        # 4. Check resource availability
        if self.resource_manager:
            usage = self.resource_manager.get_usage(invocation.agent_id)
            if usage and not self._check_resource_availability(usage, descriptor.required_resources):
                invocation.status = "denied"
                invocation.error = "Insufficient resources for capability"
                self._record_denial(invocation, "insufficient_resources")
                return invocation

        # 5. Policy evaluation (PolicyEngine returns PolicyEvaluationResult)
        if self.policy_engine:
            policy_result = self.policy_engine.check_capability(invocation.agent_id, invocation.capability_id)
            allowed, reason = self._interpret_policy_result(policy_result)
            if not allowed:
                invocation.status = "denied"
                invocation.error = reason
                self._record_denial(invocation, "policy_denied")
                return invocation

        # 6. Security boundary check (returns SecurityCheckResult)
        if self.security_boundary:
            security_result = self.security_boundary.check_invocation(invocation, descriptor, grant)
            allowed, reason = self._interpret_security_result(security_result)
            if not allowed:
                invocation.status = "denied"
                invocation.error = reason
                self._record_denial(invocation, "security_denied")
                return invocation

        # 7. Information flow control
        if not self._check_information_flow(invocation, descriptor, grant):
            invocation.status = "denied"
            invocation.error = "Information flow control violation"
            self._record_denial(invocation, "ifc_violation")
            return invocation

        # 8. Create invocation context
        context = InvocationContext(
            invocation=invocation,
            descriptor=descriptor,
            grant=grant,
            process=None,  # Would be set by kernel
        )

        # 9. Emit pre-invocation event
        if self.event_bus:
            self.event_bus.emit("capability.pre_invoke", {
                "invocation_id": invocation.invocation_id,
                "agent_id": invocation.agent_id,
                "capability_id": invocation.capability_id,
                "trace_id": invocation.trace_id,
            })

        # 10. Execute capability
        invocation.status = "executing"
        invocation.started_at = _now()

        provider = self.capability_manager.get_provider(invocation.capability_id)
        if not provider:
            invocation.status = "failed"
            invocation.error = "No provider for capability"
            return invocation

        try:
            result = provider.invoke(invocation)
            invocation.result = result
            invocation.status = "completed"
        except Exception as exc:
            invocation.status = "failed"
            invocation.error = str(exc)
            logger.error("Capability invocation failed: %s", exc)

        invocation.completed_at = _now()

        # 11. Verify result
        verification = self._verify_result(context)
        invocation.verification = verification
        invocation.provenance = ProvenanceType.TOOL_RETURNED

        # 12. Record side effects
        invocation.side_effects_observed = self._detect_side_effects(invocation, descriptor)

        # 13. Emit post-invocation event
        if self.event_bus:
            self.event_bus.emit("capability.post_invoke", {
                "invocation_id": invocation.invocation_id,
                "agent_id": invocation.agent_id,
                "capability_id": invocation.capability_id,
                "status": invocation.status,
                "duration_ms": (invocation.completed_at - invocation.started_at) * 1000 if invocation.started_at else 0,
                "trace_id": invocation.trace_id,
                "verification": verification,
            })

        # 14. Record metrics
        self.capability_manager.record_invocation(invocation.capability_id, invocation.status == "completed")
        self._record_invocation(invocation)

        return invocation

    @staticmethod
    def _interpret_policy_result(result: Any) -> tuple:
        """Accept PolicyEvaluationResult or legacy dict."""
        if result is None:
            return True, ""
        if isinstance(result, dict):
            return bool(result.get("allowed", True)), result.get("reason", "Policy denied")
        decision = getattr(result, "decision", None)
        if decision is not None:
            name = getattr(decision, "value", str(decision))
            if name in ("deny", "quarantine"):
                return False, getattr(result, "explanation", None) or f"Policy {name}"
            if name == "require_approval":
                return False, getattr(result, "explanation", None) or "Policy requires approval"
            return True, ""
        if hasattr(result, "get"):
            try:
                return bool(result.get("allowed", True)), result.get("reason", "Policy denied")
            except Exception:
                pass
        return True, ""

    @staticmethod
    def _interpret_security_result(result: Any) -> tuple:
        """Accept SecurityCheckResult or legacy dict."""
        if result is None:
            return True, ""
        if isinstance(result, dict):
            return bool(result.get("allowed", True)), result.get("reason", "Security boundary denied")
        decision = getattr(result, "decision", None)
        if decision is not None:
            name = getattr(decision, "value", str(decision))
            if name in ("deny", "quarantine", "challenge"):
                return False, getattr(result, "reason", None) or f"Security {name}"
            if name == "require_approval":
                return False, getattr(result, "reason", None) or "Security requires approval"
            return True, ""
        return True, ""

    def _check_resource_availability(self, usage: ResourceAllocation, required: ResourceBudget) -> bool:
        """Check required resources against remaining allocation.

        Remaining = allocated - used (floored at zero), compared field-wise
        for every numeric budget dimension. Unknown/zero requirements pass.
        """
        if usage is None or usage.allocated is None:
            return True
        allocated = usage.allocated
        used = usage.used or ResourceBudget()
        for field_name in ResourceBudget.__dataclass_fields__:
            try:
                have = max(0.0, float(getattr(allocated, field_name, 0) or 0)
                           - float(getattr(used, field_name, 0) or 0))
                need = float(getattr(required, field_name, 0) or 0)
            except (TypeError, ValueError):
                continue
            if need > have:
                logger.debug("CapabilityInvoker: resource shortfall on %s (need %s, have %s)",
                             field_name, need, have)
                return False
        return True

    def _check_information_flow(
        self,
        invocation: CapabilityInvocation,
        descriptor: CapabilityDescriptor,
        grant: AuthorityGrant,
    ) -> bool:
        """Check information flow control policies."""
        # Check data classification flow
        data_class = descriptor.data_classification
        
        # Check if capability would leak sensitive data
        if data_class in (DataClassification.SECRET, DataClassification.HIGHLY_SENSITIVE):
            # Require explicit authorization for sensitive data access
            if "sensitive_data_access" not in grant.capabilities:
                return False

        # Check network egress for sensitive data: a capability that touches
        # the network while handling non-public data requires at least one
        # granted network scope (mirrors SecurityBoundary; URL-level checks
        # remain with NetworkManager + hypervisor egress screening).
        if descriptor.network_access and data_class != DataClassification.PUBLIC:
            if not grant.network_scopes:
                return False

        return True

    def _verify_result(self, context: InvocationContext) -> Dict[str, Any]:
        """Verify the result of a capability invocation."""
        strategy = context.descriptor.verification_strategy
        verifier = self._verification_strategies.get(strategy, self._verify_observe)
        
        try:
            return verifier(context)
        except Exception as exc:
            logger.error("Verification failed: %s", exc)
            return {"verified": False, "error": str(exc)}

    def _verify_observe(self, context: InvocationContext) -> Dict[str, Any]:
        """Basic observation verification - check result exists."""
        return {
            "verified": context.invocation.result is not None,
            "strategy": "observe",
            "result_type": type(context.invocation.result).__name__ if context.invocation.result else None,
        }

    def _verify_execute(self, context: InvocationContext) -> Dict[str, Any]:
        """Execution verification - check result matches expectations."""
        # In a real implementation, this would check against expected outputs
        return {
            "verified": context.invocation.result is not None and context.invocation.error is None,
            "strategy": "verify",
            "has_result": context.invocation.result is not None,
            "has_error": context.invocation.error is not None,
        }

    def _verify_attest(self, context: InvocationContext) -> Dict[str, Any]:
        """Attestation verification - cryptographic proof of execution.

        Honest default: without a provider-supplied attestation there is
        nothing to verify against, so the result is UNVERIFIED (fail-closed).
        Providers that support attestation must register a custom verifier
        via register_verifier().
        """
        return {
            "verified": False,
            "strategy": "attest",
            "reason": "no provider attestation available; result UNVERIFIED",
        }

    def _detect_side_effects(
        self,
        invocation: CapabilityInvocation,
        descriptor: CapabilityDescriptor,
    ) -> List[str]:
        """Detect observed side effects from invocation."""
        side_effects = []
        
        if invocation.error:
            side_effects.append("error")
            return side_effects

        result = invocation.result
        if not result:
            return side_effects

        # Detect common side effect patterns
        if isinstance(result, dict):
            if result.get("files_written"):
                side_effects.append("filesystem_write")
            if result.get("files_deleted"):
                side_effects.append("filesystem_delete")
            if result.get("network_requests"):
                side_effects.append("network_egress")
            if result.get("process_spawned"):
                side_effects.append("process_execution")
            if result.get("browser_action"):
                side_effects.append("browser_interaction")
            if result.get("device_action"):
                side_effects.append("device_interaction")

        return side_effects

    def _record_denial(self, invocation: CapabilityInvocation, reason: str) -> None:
        """Record a capability denial."""
        if self.event_bus:
            self.event_bus.emit("capability.denied", {
                "invocation_id": invocation.invocation_id,
                "agent_id": invocation.agent_id,
                "capability_id": invocation.capability_id,
                "reason": reason,
                "trace_id": invocation.trace_id,
            })

    def _record_invocation(self, invocation: CapabilityInvocation) -> None:
        """Record invocation for history and audit."""
        record = {
            "invocation_id": invocation.invocation_id,
            "agent_id": invocation.agent_id,
            "capability_id": invocation.capability_id,
            "status": invocation.status,
            "started_at": invocation.started_at,
            "completed_at": invocation.completed_at,
            "duration_ms": (invocation.completed_at - invocation.started_at) * 1000 if invocation.started_at and invocation.completed_at else 0,
            "verification": invocation.verification,
            "side_effects": invocation.side_effects_observed,
            "trace_id": invocation.trace_id,
        }
        self._invocation_history.append(record)

        # Keep last 10000 invocations
        if len(self._invocation_history) > 10000:
            self._invocation_history = self._invocation_history[-5000:]

    def get_invocation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent invocation history."""
        return self._invocation_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get invoker statistics."""
        completed = sum(1 for r in self._invocation_history if r["status"] == "completed")
        failed = sum(1 for r in self._invocation_history if r["status"] == "failed")
        denied = sum(1 for r in self._invocation_history if r["status"] == "denied")
        total_duration = sum(r["duration_ms"] for r in self._invocation_history if r["duration_ms"] > 0)

        return {
            "total_invocations": len(self._invocation_history),
            "completed": completed,
            "failed": failed,
            "denied": denied,
            "success_rate": completed / max(len(self._invocation_history), 1),
            "avg_duration_ms": total_duration / max(completed, 1) if completed else 0,
        }

    def shutdown(self) -> None:
        """Shutdown the capability invoker."""
        logger.info("CapabilityInvoker: shutting down")
        with self._lock:
            self._invocation_history.clear()
            self._verification_strategies.clear()