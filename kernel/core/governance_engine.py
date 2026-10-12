"""
Governance Engine — high-level governance and compliance.

Provides governance policies, compliance checking, and audit trails.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from kernel.core.types import (
    ProvenanceType,
    DataClassification,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class GovernanceDomain(Enum):
    """Governance domains."""
    SECURITY = "security"
    PRIVACY = "privacy"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    FINANCIAL = "financial"
    ETHICAL = "ethical"


@dataclass
class GovernancePolicy:
    """A governance policy."""
    policy_id: str
    domain: GovernanceDomain
    name: str
    description: str
    rules: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True
    version: str = "1.0"
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)


@dataclass
class ComplianceCheck:
    """Result of a compliance check."""
    check_id: str
    policy_id: str
    target_id: str  # agent, task, resource, etc.
    target_type: str
    passed: bool
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    checked_at: float = field(default_factory=_now)


class GovernanceEngine:
    """
    High-level governance and compliance engine.
    
    Evaluates governance policies across domains and generates compliance reports.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        self._policies: Dict[str, GovernancePolicy] = {}
        self._compliance_history: List[ComplianceCheck] = []
        self._violation_handlers: Dict[str, Callable] = {}

        # Register default governance policies
        self._register_default_policies()

    def _register_default_policies(self) -> None:
        """Register default governance policies."""
        # Security policy
        self.register_policy(GovernancePolicy(
            policy_id="sec_001",
            domain=GovernanceDomain.SECURITY,
            name="No Unauthorized Privilege Escalation",
            description="Agents must not escalate privileges without explicit authorization",
            rules=[{
                "condition": "privilege_escalation_attempt",
                "action": "deny_and_alert",
            }],
        ))

        # Privacy policy
        self.register_policy(GovernancePolicy(
            policy_id="priv_001",
            domain=GovernanceDomain.PRIVACY,
            name="Data Minimization",
            description="Agents must only access data necessary for their task",
            rules=[{
                "condition": "excessive_data_access",
                "action": "limit_and_audit",
            }],
        ))

        # Compliance policy
        self.register_policy(GovernancePolicy(
            policy_id="comp_001",
            domain=GovernanceDomain.COMPLIANCE,
            name="Audit Trail Completeness",
            description="All consequential actions must have complete audit trails",
            rules=[{
                "condition": "missing_audit_trail",
                "action": "require_documentation",
            }],
        ))

        # Operational policy
        self.register_policy(GovernancePolicy(
            policy_id="ops_001",
            domain=GovernanceDomain.OPERATIONAL,
            name="Resource Fairness",
            description="Resources must be allocated fairly among agents",
            rules=[{
                "condition": "resource_starvation",
                "action": "rebalance",
            }],
        ))

        # Financial policy
        self.register_policy(GovernancePolicy(
            policy_id="fin_001",
            domain=GovernanceDomain.FINANCIAL,
            name="Cost Control",
            description="Agent costs must stay within budget with alerts at 80%",
            rules=[{
                "condition": "budget_exceeded_80_percent",
                "action": "alert",
            }, {
                "condition": "budget_exceeded_100_percent",
                "action": "pause_agent",
            }],
        ))

    def register_policy(self, policy: GovernancePolicy) -> None:
        """Register a governance policy."""
        with self._lock:
            self._policies[policy.policy_id] = policy

        if self.event_bus:
            self.event_bus.emit("governance.policy.registered", {
                "policy_id": policy.policy_id,
                "domain": policy.domain.value,
            })

    def check_compliance(
        self,
        target_id: str,
        target_type: str,
        context: Dict[str, Any],
    ) -> List[ComplianceCheck]:
        """Check compliance for a target against all policies."""
        checks = []
        
        with self._lock:
            policies = list(self._policies.values())

        for policy in policies:
            if not policy.enabled:
                continue

            check = self._evaluate_policy(policy, target_id, target_type, context)
            checks.append(check)
            
            with self._lock:
                self._compliance_history.append(check)

            # Handle violations
            if not check.passed:
                self._handle_violation(check, context)

        return checks

    def _evaluate_policy(
        self,
        policy: GovernancePolicy,
        target_id: str,
        target_type: str,
        context: Dict[str, Any],
    ) -> ComplianceCheck:
        """Evaluate a single policy."""
        check = ComplianceCheck(
            check_id=new_id("check"),
            policy_id=policy.policy_id,
            target_id=target_id,
            target_type=target_type,
            passed=True,
        )

        for rule in policy.rules:
            condition = rule.get("condition")
            action = rule.get("action")
            
            # Evaluate condition (simplified - would use rule engine in practice)
            violated = self._evaluate_condition(condition, context)
            
            if violated:
                check.passed = False
                check.findings.append({
                    "condition": condition,
                    "action": action,
                    "context": context,
                })
                check.recommendations.append(f"Remediate: {action}")

        return check

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a governance condition."""
        # Simplified condition evaluation
        if condition == "privilege_escalation_attempt":
            return context.get("action") == "escalate_privilege"
        elif condition == "excessive_data_access":
            return context.get("data_accessed", 0) > context.get("data_required", float('inf'))
        elif condition == "missing_audit_trail":
            return not context.get("has_audit_trail", True)
        elif condition == "resource_starvation":
            return context.get("wait_time", 0) > 300  # 5 minutes
        elif condition == "budget_exceeded_80_percent":
            return context.get("cost_ratio", 0) > 0.8
        elif condition == "budget_exceeded_100_percent":
            return context.get("cost_ratio", 0) > 1.0
        return False

    def _handle_violation(self, check: ComplianceCheck, context: Dict[str, Any]) -> None:
        """Handle a policy violation."""
        handler = self._violation_handlers.get(check.policy_id)
        if handler:
            try:
                handler(check, context)
            except Exception as exc:
                logger.error("Violation handler error: %s", exc)

        if self.event_bus:
            self.event_bus.emit("governance.violation", {
                "check_id": check.check_id,
                "policy_id": check.policy_id,
                "target_id": check.target_id,
                "target_type": check.target_type,
                "findings": check.findings,
            })

    def register_violation_handler(self, policy_id: str, handler: Callable) -> None:
        """Register a violation handler."""
        self._violation_handlers[policy_id] = handler

    def get_policy(self, policy_id: str) -> Optional[GovernancePolicy]:
        """Get a governance policy."""
        with self._lock:
            return self._policies.get(policy_id)

    def list_policies(self, domain: GovernanceDomain = None) -> List[GovernancePolicy]:
        """List governance policies."""
        with self._lock:
            policies = list(self._policies.values())
        if domain:
            policies = [p for p in policies if p.domain == domain]
        return policies

    def get_compliance_history(self, target_id: str = None, limit: int = 100) -> List[ComplianceCheck]:
        """Get compliance check history."""
        with self._lock:
            checks = list(self._compliance_history)
        
        if target_id:
            checks = [c for c in checks if c.target_id == target_id]
        
        return checks[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get governance engine statistics."""
        with self._lock:
            total = len(self._policies)
            enabled = sum(1 for p in self._policies.values() if p.enabled)
            by_domain: Dict[str, int] = {}
            for p in self._policies.values():
                by_domain[p.domain.value] = by_domain.get(p.domain.value, 0) + 1
            
            total_checks = len(self._compliance_history)
            passed = sum(1 for c in self._compliance_history if c.passed)

        return {
            "total_policies": total,
            "enabled_policies": enabled,
            "by_domain": by_domain,
            "total_checks": total_checks,
            "passed_checks": passed,
            "pass_rate": passed / max(total_checks, 1),
        }

    def shutdown(self) -> None:
        """Shutdown the governance engine."""
        logger.info("GovernanceEngine: shutting down")
        with self._lock:
            self._policies.clear()
            self._compliance_history.clear()
            self._violation_handlers.clear()