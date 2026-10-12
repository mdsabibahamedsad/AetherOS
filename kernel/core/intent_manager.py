"""
Intent Manager — intent admission, validation, and tracking.

Implements the Intent ABI: structured intents that survive planning,
delegation, tool calls, agent handoffs, automation, A2A communication,
recovery, checkpointing, and audit.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.core.types import (
    Intent,
    AuthorityGrant,
    CapabilityRiskLevel,
    DataClassification,
    ResourceBudget,
    ProvenanceType,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class AdmissionResult:
    """Result of intent admission."""
    allowed: bool
    reason: str = ""
    required_approval: bool = False
    risk_level: CapabilityRiskLevel = CapabilityRiskLevel.READ_ONLY
    authority_grant: Optional[AuthorityGrant] = None
    resource_allocation: Optional[Dict[str, Any]] = None


class IntentManager:
    """
    Manages intent lifecycle: creation, admission, tracking, and provenance.
    
    The Intent ABI ensures intents are first-class objects that survive
    all execution phases without relying on natural language alone.
    """

    def __init__(self, config, event_bus: EventBus, authority_manager, policy_engine):
        self.config = config
        self.event_bus = event_bus
        self.authority_manager = authority_manager
        self.policy_engine = policy_engine
        self.capability_manager = None  # bound by kernel (capability resolution)
        self._lock = threading.RLock()
        self._intents: Dict[str, Intent] = {}
        self._admission_history: List[Dict[str, Any]] = []
        self._admission_policies: List[Callable[[Intent], AdmissionResult]] = []

    def bind_capability_manager(self, capability_manager) -> None:
        """Bind the capability registry for capability resolution (§5)."""
        self.capability_manager = capability_manager

    @staticmethod
    def normalize_natural_language(
        text: str,
        actor: str = "human",
        provenance: ProvenanceType = ProvenanceType.USER_PROVIDED,
    ) -> Intent:
        """Normalize raw natural language into a structured Intent (§5).

        Honest by construction: the objective is the verbatim text and the
        ONLY capabilities extracted are explicit `cap:<id>` tokens. All
        other capability resolution happens later against the registry
        (admission), never by guessing from prose.
        """
        import re
        objective = (text or "").strip()
        caps = sorted(set(re.findall(r"cap:([A-Za-z0-9_.*-]+)", objective)))
        return Intent(
            actor=actor,
            objective=objective,
            requested_capabilities=caps,
            provenance=provenance,
            metadata={"normalized_from": "natural_language",
                      "explicit_cap_tokens": caps})

    def register_admission_policy(self, policy: Callable[[Intent], AdmissionResult]) -> None:
        """Register a custom admission policy."""
        self._admission_policies.append(policy)

    def admit(self, intent: Intent) -> AdmissionResult:
        """
        Admit an intent for execution.
        
        This is the main entry point for intent processing.
        """
        logger.info("IntentManager: admitting intent %s: %s", intent.intent_id, intent.objective[:100])

        # Validate intent structure
        validation = self._validate_intent(intent)
        if not validation.allowed:
            self._record_admission(intent, validation)
            return validation

        # Run admission policies
        for policy in self._admission_policies:
            try:
                result = policy(intent)
                if not result.allowed:
                    self._record_admission(intent, result)
                    return result
            except Exception as exc:
                logger.error("Admission policy error: %s", exc)
                result = AdmissionResult(
                    allowed=False,
                    reason=f"Admission policy error: {exc}",
                )
                self._record_admission(intent, result)
                return result

        # Check resource availability
        if self.authority_manager and hasattr(self.authority_manager, 'resource_manager'):
            resource_check = self.authority_manager.resource_manager.check_availability(intent.requested_resources)
            if not resource_check["available"]:
                result = AdmissionResult(
                    allowed=False,
                    reason=f"Insufficient resources: {resource_check['reason']}",
                )
                self._record_admission(intent, result)
                return result

        # Evaluate risk
        risk_level = self._evaluate_risk(intent)
        intent.risk_level = risk_level

        # Determine approval requirement
        required_approval = self._requires_approval(intent, risk_level)
        intent.approval_requirement = "require_approval" if required_approval else "none"

        # Create authority grant
        authority_grant = None
        if self.authority_manager:
            authority_grant = self.authority_manager.create_grant(intent)

        # Allocate resources
        resource_allocation = None
        if self.authority_manager and hasattr(self.authority_manager, 'resource_manager'):
            resource_allocation = self.authority_manager.resource_manager.reserve(intent.requested_resources)

        result = AdmissionResult(
            allowed=True,
            reason="Intent admitted",
            required_approval=required_approval,
            risk_level=risk_level,
            authority_grant=authority_grant,
            resource_allocation=resource_allocation,
        )

        # Store intent
        with self._lock:
            self._intents[intent.intent_id] = intent

        # Update intent with admission results
        intent.authority_scope = authority_grant.capabilities if authority_grant else []
        intent.updated_at = _now()

        self._record_admission(intent, result)

        # Emit event
        if self.event_bus:
            self.event_bus.emit("intent.admitted", {
                "intent_id": intent.intent_id,
                "actor": intent.actor,
                "objective": intent.objective,
                "risk_level": risk_level.value,
                "required_approval": required_approval,
            })

        return result

    def _validate_intent(self, intent: Intent) -> AdmissionResult:
        """Validate intent structure and constraints."""
        if not intent.intent_id:
            return AdmissionResult(allowed=False, reason="Missing intent_id")
        
        if not intent.actor:
            return AdmissionResult(allowed=False, reason="Missing actor")
        
        if not intent.objective:
            return AdmissionResult(allowed=False, reason="Missing objective")
        
        if intent.deadline and intent.deadline < _now():
            return AdmissionResult(allowed=False, reason="Deadline already passed")
        
        # Validate autonomy level
        if not 0.0 <= intent.autonomy_level <= 1.0:
            return AdmissionResult(allowed=False, reason="Autonomy level must be 0.0-1.0")

        # Validate requested capabilities exist (capability resolution).
        # Structurally invalid (empty/blank) entries deny admission.
        # Unknown capabilities are KEPT on the grant (backward compatible:
        # invocation still denies them) but flagged loudly: an event plus
        # a log line, so no caller mistakes the grant for a promise.
        if any(not c or not c.strip() for c in intent.requested_capabilities):
            return AdmissionResult(allowed=False, reason="Blank capability entry")
        if self.capability_manager is not None:
            known = {c.capability_id for c in
                     self.capability_manager.list_capabilities()}
            unknown = [c for c in intent.requested_capabilities if c not in known]
            if unknown:
                logger.warning("IntentManager: unknown capabilities requested (will deny at invoke): %s",
                               unknown)
                if self.event_bus:
                    try:
                        self.event_bus.emit("intent.unknown_capabilities", {
                            "intent_id": intent.intent_id,
                            "unknown": unknown,
                        })
                    except Exception:
                        pass

        return AdmissionResult(allowed=True)

    def _evaluate_risk(self, intent: Intent) -> CapabilityRiskLevel:
        """Evaluate the risk level of an intent."""
        # Start with intent's declared risk
        risk = intent.risk_level

        # Escalate based on capabilities
        high_risk_capabilities = {
            "fs.delete", "fs.write", "process.execute",
            "network.request", "browser.navigate", "computer.click",
            "computer.type", "device.control", "robot.navigate",
            "agent.spawn", "automation.create", "message.send",
        }

        for cap in intent.requested_capabilities:
            if cap in high_risk_capabilities:
                if risk.value < CapabilityRiskLevel.EXTERNAL_SIDE_EFFECT.value:
                    risk = CapabilityRiskLevel.EXTERNAL_SIDE_EFFECT

        # Escalate based on data classification
        if intent.privacy_class in (DataClassification.SECRET, DataClassification.HIGHLY_SENSITIVE):
            if risk.value < CapabilityRiskLevel.PRIVACY_SENSITIVE.value:
                risk = CapabilityRiskLevel.PRIVACY_SENSITIVE

        # Escalate based on autonomy
        if intent.autonomy_level > 0.8:
            if risk.value < CapabilityRiskLevel.IRREVERSIBLE.value:
                risk = CapabilityRiskLevel.IRREVERSIBLE

        return risk

    def _requires_approval(self, intent: Intent, risk: CapabilityRiskLevel) -> bool:
        """Determine if intent requires human approval."""
        # Always require approval for high-risk operations
        if risk in (CapabilityRiskLevel.FINANCIAL, CapabilityRiskLevel.PHYSICAL, CapabilityRiskLevel.SECURITY_CRITICAL):
            return True

        # Require approval for high autonomy
        if intent.autonomy_level > 0.7:
            return True

        # Require approval for sensitive data
        if intent.privacy_class in (DataClassification.SECRET, DataClassification.HIGHLY_SENSITIVE):
            return True

        # Check for explicit approval requirement
        if "require_approval" in intent.constraints:
            return True

        return False

    def _record_admission(self, intent: Intent, result: AdmissionResult) -> None:
        """Record admission attempt for audit."""
        record = {
            "intent_id": intent.intent_id,
            "actor": intent.actor,
            "objective": intent.objective,
            "allowed": result.allowed,
            "reason": result.reason,
            "risk_level": result.risk_level.value,
            "timestamp": _now(),
        }
        self._admission_history.append(record)

        # Keep last 1000 records
        if len(self._admission_history) > 1000:
            self._admission_history = self._admission_history[-500:]

    def get_intent(self, intent_id: str) -> Optional[Intent]:
        """Get an intent by ID."""
        with self._lock:
            return self._intents.get(intent_id)

    def list_intents(self, actor: str = "", status: str = "") -> List[Intent]:
        """List intents with optional filters."""
        with self._lock:
            intents = list(self._intents.values())
        
        if actor:
            intents = [i for i in intents if i.actor == actor]
        
        return intents

    def get_admission_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent admission history."""
        return self._admission_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get intent manager statistics."""
        with self._lock:
            total = len(self._intents)
            by_risk: Dict[str, int] = {}
            by_actor: Dict[str, int] = {}
            for intent in self._intents.values():
                by_risk[intent.risk_level.value] = by_risk.get(intent.risk_level.value, 0) + 1
                by_actor[intent.actor] = by_actor.get(intent.actor, 0) + 1

        admitted = sum(1 for r in self._admission_history if r["allowed"])
        denied = sum(1 for r in self._admission_history if not r["allowed"])

        return {
            "total_intents": total,
            "by_risk_level": by_risk,
            "by_actor": by_actor,
            "admission_history": {
                "total": len(self._admission_history),
                "admitted": admitted,
                "denied": denied,
            },
        }

    def shutdown(self) -> None:
        """Shutdown the intent manager."""
        logger.info("IntentManager: shutting down")
        with self._lock:
            self._intents.clear()
            self._admission_history.clear()