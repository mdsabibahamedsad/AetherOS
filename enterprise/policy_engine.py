"""
Policy Engine
=============

Declarative, auditable policy engine for enforcing organizational rules
across plugin installation, execution permissions, network/filesystem
access, workspace access, resource quotas, and automation approvals.
"""

from __future__ import annotations

import enum
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PolicyDecision(enum.Enum):
    ALLOW = "allow"
    DENY = "deny"
    PROMPT = "prompt"  # Requires manual approval


@dataclass
class PolicyRule:
    """A single policy rule — the atomic unit of policy.

    Each rule specifies:
    - A resource pattern (glob or regex)
    - An action (allow/deny/prompt)
    - Optional conditions and priority
    """
    resource: str  # Glob or regex pattern
    action: PolicyDecision = PolicyDecision.ALLOW
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    description: str = ""
    id: str = ""
    enabled: bool = True

    def matches(self, resource_name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if this rule matches a resource."""
        if not self.enabled:
            return False
        # Simple glob matching (* → .*)
        pattern = "^" + re.escape(self.resource).replace("\\*", ".*") + "$"
        if not re.match(pattern, resource_name):
            return False
        # Check conditions
        if self.conditions and context:
            for key, expected in self.conditions.items():
                actual = context.get(key)
                if actual != expected:
                    return False
        return True


@dataclass
class PolicyEvaluation:
    """The result of evaluating a policy for a given request."""
    resource: str
    action: str
    decision: PolicyDecision
    matched_rule: Optional[PolicyRule] = None
    context: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource": self.resource,
            "action": self.action,
            "decision": self.decision.value,
            "matched_rule": self.matched_rule.id if self.matched_rule else None,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass
class Policy:
    """A named, versioned collection of policy rules."""
    name: str
    description: str = ""
    rules: List[PolicyRule] = field(default_factory=list)
    version: str = "0.0.1"
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def add_rule(self, rule: PolicyRule) -> None:
        self.rules.append(rule)
        self.updated_at = datetime.utcnow()

    def remove_rule(self, rule_id: str) -> bool:
        for rule in self.rules:
            if rule.id == rule_id:
                self.rules.remove(rule)
                self.updated_at = datetime.utcnow()
                return True
        return False

    def evaluate(
        self,
        resource: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyEvaluation:
        """Evaluate this policy against a resource request.

        Rules are evaluated in priority order (lower number = higher priority).
        The first matching rule determines the decision.
        """
        sorted_rules = sorted(self.rules, key=lambda r: r.priority)
        for rule in sorted_rules:
            if rule.matches(resource, context):
                return PolicyEvaluation(
                    resource=resource,
                    action=resource.split(":")[0] if ":" in resource else resource,
                    decision=rule.action,
                    matched_rule=rule,
                    context=context or {},
                )
        # Default: deny if no rule matches
        return PolicyEvaluation(
            resource=resource,
            action=resource.split(":")[0] if ":" in resource else resource,
            decision=PolicyDecision.DENY,
            context=context or {},
        )


class PolicyEngine:
    """Central policy engine for evaluating access requests.

    Supports multiple named policies, rule priority, conditional matching,
    and complete audit trails for every evaluation.
    """

    def __init__(self) -> None:
        self._policies: Dict[str, Policy] = {}
        self._evaluation_log: List[PolicyEvaluation] = []

    def register_policy(self, policy: Policy) -> None:
        """Register a named policy."""
        self._policies[policy.name] = policy
        logger.info("Registered policy: %s v%s", policy.name, policy.version)

    def get_policy(self, name: str) -> Optional[Policy]:
        return self._policies.get(name)

    def list_policies(self) -> List[Policy]:
        return list(self._policies.values())

    def remove_policy(self, name: str) -> bool:
        if name in self._policies:
            del self._policies[name]
            return True
        return False

    def evaluate(
        self,
        policy_name: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyEvaluation:
        """Evaluate a resource request against a named policy."""
        policy = self._policies.get(policy_name)
        if not policy:
            result = PolicyEvaluation(
                resource=resource,
                action=resource.split(":")[0] if ":" in resource else resource,
                decision=PolicyDecision.DENY,
                context=context or {},
            )
        else:
            result = policy.evaluate(resource, context)

        self._evaluation_log.append(result)
        return result

    def evaluate_multi(
        self,
        resources: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, PolicyEvaluation]:
        """Evaluate multiple resources against their policies.

        Uses the resource prefix (e.g. ``plugin:`` → ``plugin``) to
        select which policy to apply.
        """
        results: Dict[str, PolicyEvaluation] = {}
        for resource in resources:
            prefix = resource.split(":")[0] if ":" in resource else resource
            # Try prefix-specific policy, fall back to default
            policy_name = prefix if prefix in self._policies else "default"
            results[resource] = self.evaluate(policy_name, resource, context)
        return results

    def get_evaluation_log(
        self,
        limit: int = 100,
        decision: Optional[PolicyDecision] = None,
    ) -> List[PolicyEvaluation]:
        """Get recent evaluations, optionally filtered by decision."""
        results = list(reversed(self._evaluation_log))
        if decision:
            results = [e for e in results if e.decision == decision]
        return results[:limit]

    def clear_log(self) -> None:
        self._evaluation_log.clear()
