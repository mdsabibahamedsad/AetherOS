"""
Policy Engine — deterministic policy evaluation and enforcement.

Evaluates policies for intent admission, capability access, data flow,
and resource allocation.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

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


class PolicyDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    QUARANTINE = "quarantine"
    LIMIT = "limit"
    ESCALATE = "escalate"


@dataclass
class PolicyRule:
    """A policy rule."""
    rule_id: str
    name: str
    description: str
    condition: Callable[[Dict[str, Any]], bool]  # Returns True if rule matches
    action: PolicyDecision
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class PolicyEvaluationResult:
    """Result of policy evaluation."""
    decision: PolicyDecision
    matched_rules: List[str] = field(default_factory=list)
    denied_rules: List[str] = field(default_factory=list)
    required_scopes: List[str] = field(default_factory=list)
    required_approvals: List[str] = field(default_factory=list)
    risk_level: CapabilityRiskLevel = CapabilityRiskLevel.READ_ONLY
    explanation: str = ""
    policy_version: str = "1.0"
    obligations: List[str] = field(default_factory=list)
    resource_limits: Optional[ResourceBudget] = None


class PolicyEngine:
    """
    Evaluates and enforces policies for the kernel.
    
    Policies are deterministic rules that govern:
    - Intent admission
    - Capability access
    - Data flow
    - Resource allocation
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        self._rules: Dict[str, PolicyRule] = {}
        self._rule_order: List[str] = []  # Sorted by priority
        self._evaluation_cache: Dict[str, PolicyEvaluationResult] = {}
        self._cache_ttl = 5.0  # seconds
        self._cache_timestamps: Dict[str, float] = {}

        # Register default policies
        self._register_default_policies()

    def _register_default_policies(self) -> None:
        """Register default kernel policies."""
        # High-risk capabilities require approval
        self.register_rule(PolicyRule(
            rule_id="high_risk_approval",
            name="High Risk Requires Approval",
            description="Capabilities with HIGH/Critical risk require human approval",
            condition=lambda ctx: ctx.get("risk_level", "") in ("high_impact", "critical", "financial", "physical", "security_critical"),
            action=PolicyDecision.REQUIRE_APPROVAL,
            priority=100,
        ))

        # Untrusted data cannot become authority
        self.register_rule(PolicyRule(
            rule_id="untrusted_no_authority",
            name="Untrusted Data Cannot Grant Authority",
            description="External/untrusted content cannot grant capabilities or authority",
            condition=lambda ctx: ctx.get("provenance", "") in ("web_derived", "model_generated", "unverified", "simulated", "predicted")
                                  and ctx.get("requested_action") in ("grant_capability", "grant_authority", "escalate_privilege"),
            action=PolicyDecision.DENY,
            priority=200,
        ))

        # Child authority cannot exceed parent
        self.register_rule(PolicyRule(
            rule_id="child_authority_subset",
            name="Child Authority Subset of Parent",
            description="Delegated authority must be subset of parent authority",
            condition=lambda ctx: ctx.get("action") == "delegate"
                                  and not set(ctx.get("child_capabilities", [])).issubset(set(ctx.get("parent_capabilities", []))),
            action=PolicyDecision.DENY,
            priority=150,
        ))

        # Sensitive data flow control
        self.register_rule(PolicyRule(
            rule_id="sensitive_data_flow",
            name="Sensitive Data Flow Control",
            description="Secret/highly sensitive data cannot flow to untrusted destinations",
            condition=lambda ctx: ctx.get("source_classification", "") in ("secret", "highly_sensitive")
                                  and ctx.get("dest_classification", "") in ("public", "internal", "unverified"),
            action=PolicyDecision.DENY,
            priority=180,
        ))

        # Resource quotas
        self.register_rule(PolicyRule(
            rule_id="resource_quota",
            name="Resource Quota Enforcement",
            description="Agents cannot exceed allocated resource quotas",
            condition=lambda ctx: ctx.get("action") == "allocate"
                                  and ctx.get("requested", 0) > ctx.get("quota", float('inf')),
            action=PolicyDecision.DENY,
            priority=120,
        ))

        # Delegation depth limit
        self.register_rule(PolicyRule(
            rule_id="delegation_depth",
            name="Delegation Depth Limit",
            description="Delegation depth cannot exceed configured maximum",
            condition=lambda ctx: ctx.get("action") == "delegate"
                                  and ctx.get("delegation_depth", 0) > ctx.get("max_depth", 5),
            action=PolicyDecision.DENY,
            priority=130,
        ))

    def register_rule(self, rule: PolicyRule) -> None:
        """Register a policy rule."""
        with self._lock:
            self._rules[rule.rule_id] = rule
            # Re-sort by priority
            self._rule_order = sorted(
                self._rules.keys(),
                key=lambda r: self._rules[r].priority,
                reverse=True,
            )

        logger.debug("PolicyEngine: registered rule %s (priority %d)",
                     rule.rule_id, rule.priority)

    def unregister_rule(self, rule_id: str) -> bool:
        """Unregister a policy rule."""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                self._rule_order = [r for r in self._rule_order if r != rule_id]
                return True
        return False

    def evaluate_intent(self, intent: Intent) -> PolicyEvaluationResult:
        """Evaluate policies for an intent."""
        context = {
            "action": "admit_intent",
            "actor": intent.actor,
            "risk_level": intent.risk_level.value,
            "privacy_class": intent.privacy_class.value,
            "autonomy_level": intent.autonomy_level,
            "requested_capabilities": intent.requested_capabilities,
            "provenance": intent.provenance.value,
        }
        return self._evaluate(context)

    def check_capability(self, agent_id: str, capability_id: str) -> PolicyEvaluationResult:
        """Check if agent can use a capability."""
        context = {
            "action": "use_capability",
            "agent_id": agent_id,
            "capability_id": capability_id,
        }
        return self._evaluate(context)

    def check_data_flow(
        self,
        source_classification: DataClassification,
        dest_classification: DataClassification,
        agent_id: str = "",
    ) -> PolicyEvaluationResult:
        """Check if data flow is allowed."""
        context = {
            "action": "data_flow",
            "source_classification": source_classification.value,
            "dest_classification": dest_classification.value,
            "agent_id": agent_id,
        }
        return self._evaluate(context)

    def evaluate_resource_request(
        self,
        agent_id: str,
        requested: ResourceBudget,
        quota: ResourceBudget,
    ) -> PolicyEvaluationResult:
        """Evaluate resource allocation request."""
        context = {
            "action": "allocate",
            "agent_id": agent_id,
            "requested": requested.to_dict(),
            "quota": quota.to_dict(),
        }
        return self._evaluate(context)

    def evaluate_delegation(
        self,
        parent_agent_id: str,
        child_agent_id: str,
        parent_capabilities: List[str],
        child_capabilities: List[str],
        delegation_depth: int,
        max_depth: int,
    ) -> PolicyEvaluationResult:
        """Evaluate delegation request."""
        context = {
            "action": "delegate",
            "parent_agent_id": parent_agent_id,
            "child_agent_id": child_agent_id,
            "parent_capabilities": parent_capabilities,
            "child_capabilities": child_capabilities,
            "delegation_depth": delegation_depth,
            "max_depth": max_depth,
        }
        return self._evaluate(context)

    def _evaluate(self, context: Dict[str, Any]) -> PolicyEvaluationResult:
        """Evaluate all rules against context."""
        # Check cache
        cache_key = str(sorted(context.items()))
        if cache_key in self._evaluation_cache:
            if _now() - self._cache_timestamps.get(cache_key, 0) < self._cache_ttl:
                return self._evaluation_cache[cache_key]

        result = PolicyEvaluationResult(decision=PolicyDecision.ALLOW)
        
        with self._lock:
            for rule_id in self._rule_order:
                rule = self._rules[rule_id]
                if not rule.enabled:
                    continue

                try:
                    if rule.condition(context):
                        if rule.action == PolicyDecision.DENY:
                            result.decision = PolicyDecision.DENY
                            result.denied_rules.append(rule_id)
                            result.explanation = rule.description
                            break  # Deny is final
                        elif rule.action == PolicyDecision.REQUIRE_APPROVAL:
                            if result.decision != PolicyDecision.DENY:
                                result.decision = PolicyDecision.REQUIRE_APPROVAL
                            result.required_approvals.append(rule_id)
                        elif rule.action == PolicyDecision.QUARANTINE:
                            result.decision = PolicyDecision.QUARANTINE
                            result.explanation = rule.description
                            break
                        elif rule.action == PolicyDecision.LIMIT:
                            result.decision = PolicyDecision.LIMIT
                            result.resource_limits = rule.metadata.get("limits")
                        elif rule.action == PolicyDecision.ESCALATE:
                            result.decision = PolicyDecision.ESCALATE
                        
                        result.matched_rules.append(rule_id)
                except Exception as exc:
                    logger.error("Policy rule %s evaluation error: %s", rule_id, exc)
                    result.denied_rules.append(rule_id)

        # Cache result
        self._evaluation_cache[cache_key] = result
        self._cache_timestamps[cache_key] = _now()

        # Limit cache size
        if len(self._evaluation_cache) > 1000:
            oldest = min(self._cache_timestamps.items(), key=lambda x: x[1])[0]
            self._evaluation_cache.pop(oldest, None)
            self._cache_timestamps.pop(oldest, None)

        if self.event_bus:
            self.event_bus.emit("policy.evaluated", {
                "decision": result.decision.value,
                "matched_rules": result.matched_rules,
                "denied_rules": result.denied_rules,
            })

        return result

    def get_rule(self, rule_id: str) -> Optional[PolicyRule]:
        """Get a policy rule."""
        with self._lock:
            return self._rules.get(rule_id)

    def list_rules(self) -> List[PolicyRule]:
        """List all policy rules."""
        with self._lock:
            return list(self._rules.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get policy engine statistics."""
        with self._lock:
            total = len(self._rules)
            enabled = sum(1 for r in self._rules.values() if r.enabled)
            by_action: Dict[str, int] = {}
            for rule in self._rules.values():
                by_action[rule.action.value] = by_action.get(rule.action.value, 0) + 1

        return {
            "total_rules": total,
            "enabled_rules": enabled,
            "by_action": by_action,
            "cache_size": len(self._evaluation_cache),
        }

    def shutdown(self) -> None:
        """Shutdown the policy engine."""
        logger.info("PolicyEngine: shutting down")
        with self._lock:
            self._rules.clear()
            self._rule_order.clear()
            self._evaluation_cache.clear()