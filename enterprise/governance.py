"""
Governance Framework
====================

Organizational governance framework with compliance requirements,
governance policies, and audit tracking.
"""

from __future__ import annotations

import enum
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ComplianceStatus(enum.Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_CHECKED = "not_checked"
    IN_PROGRESS = "in_progress"


@dataclass
class ComplianceRequirement:
    """A specific compliance requirement to be tracked."""
    name: str
    description: str = ""
    framework: str = ""  # SOC2, HIPAA, GDPR, etc.
    status: ComplianceStatus = ComplianceStatus.NOT_CHECKED
    last_checked: Optional[datetime] = None
    evidence: str = ""
    owner: str = ""
    controls: List[str] = field(default_factory=list)
    notes: str = ""

    def check_compliance(self) -> ComplianceStatus:
        self.last_checked = datetime.utcnow()
        # In production, this would run actual compliance checks
        self.status = ComplianceStatus.COMPLIANT
        return self.status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "framework": self.framework,
            "status": self.status.value,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "owner": self.owner,
            "controls": self.controls,
        }


@dataclass
class GovernancePolicy:
    """A governance policy that defines organizational rules."""
    name: str
    description: str = ""
    version: str = "1.0.0"
    enabled: bool = True
    scope: str = "organization"
    rules: List[Dict[str, Any]] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class GovernanceFramework:
    """Manage governance policies and compliance requirements."""

    def __init__(self) -> None:
        self._policies: Dict[str, GovernancePolicy] = {}
        self._requirements: Dict[str, ComplianceRequirement] = {}
        self._audit_trail: List[Dict[str, Any]] = []

    def register_policy(self, policy: GovernancePolicy) -> None:
        self._policies[policy.name] = policy
        logger.info("Governance policy registered: %s v%s", policy.name, policy.version)

    def get_policy(self, name: str) -> Optional[GovernancePolicy]:
        return self._policies.get(name)

    def list_policies(self) -> List[GovernancePolicy]:
        return list(self._policies.values())

    def add_requirement(self, requirement: ComplianceRequirement) -> None:
        self._requirements[requirement.name] = requirement

    def get_requirement(self, name: str) -> Optional[ComplianceRequirement]:
        return self._requirements.get(name)

    def list_requirements(self, framework: Optional[str] = None) -> List[ComplianceRequirement]:
        if framework:
            return [r for r in self._requirements.values() if r.framework == framework]
        return list(self._requirements.values())

    def run_compliance_check(self) -> Dict[str, Any]:
        """Run compliance checks on all registered requirements."""
        results = []
        for req in self._requirements.values():
            status = req.check_compliance()
            results.append({
                "requirement": req.name,
                "status": status.value,
                "framework": req.framework,
            })
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total": len(results),
            "compliant": sum(1 for r in results if r["status"] == "compliant"),
            "non_compliant": sum(1 for r in results if r["status"] == "non_compliant"),
            "results": results,
        }

    def get_compliance_score(self) -> float:
        """Calculate overall compliance score (0.0 - 1.0)."""
        if not self._requirements:
            return 1.0
        compliant = sum(1 for r in self._requirements.values() if r.status == ComplianceStatus.COMPLIANT)
        return compliant / len(self._requirements)

    def log_action(self, action: str, actor: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log a governance action for audit purposes."""
        entry = {
            "action": action,
            "actor": actor,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._audit_trail.append(entry)
        logger.info("Governance action: %s by %s", action, actor)

    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        return list(reversed(self._audit_trail))[:limit]
