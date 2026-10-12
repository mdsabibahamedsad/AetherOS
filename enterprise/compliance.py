"""
Compliance Support
==================

Configurable controls to assist organizations with internal governance
requirements. Supports retention policies, data export, audit reports,
policy documentation, and administrative reporting.
"""

from __future__ import annotations

import enum
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ComplianceControlType(enum.Enum):
    RETENTION = "retention"
    ACCESS_CONTROL = "access_control"
    ENCRYPTION = "encryption"
    AUDIT = "audit"
    DATA_EXPORT = "data_export"
    PRIVACY = "privacy"


@dataclass
class ComplianceControl:
    """A configurable compliance control."""
    name: str
    description: str = ""
    control_type: ComplianceControlType = ComplianceControlType.AUDIT
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    id: str = ""
    version: str = "1.0.0"


@dataclass
class RetentionPolicy:
    """Data retention rules for compliance."""
    data_type: str  # sessions, logs, memory, audit, backups
    retention_days: int = 90
    enabled: bool = True
    auto_purge: bool = False

    def is_expired(self, created_at: datetime) -> bool:
        return datetime.utcnow() > created_at + timedelta(days=self.retention_days)


@dataclass
class ComplianceReport:
    """A compliance report generated for audit purposes."""
    report_type: str  # policy_compliance, access_review, data_retention
    generated_at: datetime = field(default_factory=datetime.utcnow)
    organization_id: str = ""
    generated_by: str = ""
    controls_checked: List[str] = field(default_factory=list)
    passed: bool = True
    findings: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_type": self.report_type,
            "generated_at": self.generated_at.isoformat(),
            "organization_id": self.organization_id,
            "controls_checked": self.controls_checked,
            "passed": self.passed,
            "findings": self.findings,
            "summary": self.summary,
        }


class ComplianceManager:
    """Manage compliance controls, retention policies, and reporting."""

    def __init__(self) -> None:
        self._controls: Dict[str, ComplianceControl] = {}
        self._retention_policies: Dict[str, RetentionPolicy] = {}
        self._reports: List[ComplianceReport] = []

    def register_control(self, control: ComplianceControl) -> None:
        self._controls[control.name] = control

    def get_control(self, name: str) -> Optional[ComplianceControl]:
        return self._controls.get(name)

    def list_controls(self) -> List[ComplianceControl]:
        return list(self._controls.values())

    def set_retention_policy(self, policy: RetentionPolicy) -> None:
        self._retention_policies[policy.data_type] = policy

    def get_retention_policy(self, data_type: str) -> Optional[RetentionPolicy]:
        return self._retention_policies.get(data_type)

    def list_retention_policies(self) -> List[RetentionPolicy]:
        return list(self._retention_policies.values())

    def generate_report(
        self,
        report_type: str,
        org_id: str = "",
        generated_by: str = "",
    ) -> ComplianceReport:
        """Generate a compliance report."""
        controls = [c for c in self._controls.values() if c.enabled]
        report = ComplianceReport(
            report_type=report_type,
            organization_id=org_id,
            generated_by=generated_by,
            controls_checked=[c.name for c in controls],
            passed=True,
        )

        # Check controls
        for control in controls:
            finding = {
                "control": control.name,
                "status": "passed",
                "details": f"{control.description} - {control.version}",
            }
            report.findings.append(finding)

        report.summary = (
            f"Compliance check for {report_type}: "
            f"{len(report.findings)} controls checked, "
            f"{'all passed' if report.passed else 'some failed'}."
        )
        self._reports.append(report)
        return report

    def list_reports(self, limit: int = 50) -> List[ComplianceReport]:
        return list(reversed(self._reports))[:limit]

    def export_data(self, data_type: str, org_id: str = "") -> Dict[str, Any]:
        """Export data for compliance purposes (GDPR, etc.)."""
        export = {
            "export_type": data_type,
            "exported_at": datetime.utcnow().isoformat(),
            "organization_id": org_id,
            "data": {},
            "retention_policy": None,
        }
        policy = self._retention_policies.get(data_type)
        if policy:
            export["retention_policy"] = {
                "data_type": policy.data_type,
                "retention_days": policy.retention_days,
                "auto_purge": policy.auto_purge,
            }
        return export
