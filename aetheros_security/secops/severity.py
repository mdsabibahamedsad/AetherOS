"""
Security event severity model (normalized).

Severity ladder: DEBUG < INFO < NOTICE < WARNING < HIGH < CRITICAL < EMERGENCY.

AetherOS observability uses ``AlertSeverity`` (INFO..SECURITY_CRITICAL) and the
audit layer uses ``AuditSeverity`` (info..critical).  The SecOps layer owns a
single normalized ladder so detectors, correlation and risk scoring agree on
ordering, and maps to/from the neighbouring systems it composes.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict


class SecuritySeverity(Enum):
    """Normalized security-event severity ladder."""

    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

    @property
    def rank(self) -> int:
        """Ordering index used for comparisons."""
        return _RANK[self]

    def __ge__(self, other: "SecuritySeverity") -> bool:
        if isinstance(other, SecuritySeverity):
            return self.rank >= other.rank
        return NotImplemented

    def __gt__(self, other: "SecuritySeverity") -> bool:
        if isinstance(other, SecuritySeverity):
            return self.rank > other.rank
        return NotImplemented

    def __le__(self, other: "SecuritySeverity") -> bool:
        if isinstance(other, SecuritySeverity):
            return self.rank <= other.rank
        return NotImplemented

    def __lt__(self, other: "SecuritySeverity") -> bool:
        if isinstance(other, SecuritySeverity):
            return self.rank < other.rank
        return NotImplemented


_RANK: Dict[SecuritySeverity, int] = {
    SecuritySeverity.DEBUG: 0,
    SecuritySeverity.INFO: 1,
    SecuritySeverity.NOTICE: 2,
    SecuritySeverity.WARNING: 3,
    SecuritySeverity.HIGH: 4,
    SecuritySeverity.CRITICAL: 5,
    SecuritySeverity.EMERGENCY: 6,
}


def parse_severity(value: Any, default: SecuritySeverity = SecuritySeverity.INFO) -> SecuritySeverity:
    """Resolve a severity from a string/enum with a safe default."""
    if value is None:
        return default
    if isinstance(value, SecuritySeverity):
        return value
    text = str(value).strip().lower()
    for sev in SecuritySeverity:
        if sev.value == text:
            return sev
    return default


def from_audit_severity(value: Any) -> SecuritySeverity:
    """Map the audit layer's severity names onto the normalized ladder."""
    text = str(value).strip().lower()
    mapping = {
        "info": SecuritySeverity.INFO,
        "warning": SecuritySeverity.WARNING,
        "error": SecuritySeverity.HIGH,
        "critical": SecuritySeverity.CRITICAL,
    }
    return mapping.get(text, SecuritySeverity.INFO)


def from_observability_severity(value: Any) -> SecuritySeverity:
    """Map observability AlertSeverity names onto the normalized ladder."""
    text = str(value).strip().upper()
    mapping = {
        "DEBUG": SecuritySeverity.DEBUG,
        "INFO": SecuritySeverity.INFO,
        "NOTICE": SecuritySeverity.NOTICE,
        "WARNING": SecuritySeverity.WARNING,
        "ERROR": SecuritySeverity.HIGH,
        "CRITICAL": SecuritySeverity.CRITICAL,
        "SECURITY_CRITICAL": SecuritySeverity.EMERGENCY,
    }
    return mapping.get(text, SecuritySeverity.INFO)


#: Incident severity scale (low..emergency) — distinct from the event ladder.
INCIDENT_SEVERITIES = ("low", "medium", "high", "critical", "emergency")


def normalize_incident_severity(value: Any) -> str:
    """Normalize an incident severity to one of low/medium/high/critical/emergency."""
    if value is None:
        return "medium"
    if isinstance(value, SecuritySeverity):
        text = value.value
    else:
        text = str(value).strip().lower()
    if text in INCIDENT_SEVERITIES:
        return text
    # Map neighbouring event-ladder values onto the incident scale.
    mapping = {
        "debug": "low",
        "info": "low",
        "notice": "low",
        "warning": "medium",
        "high": "high",
        "critical": "critical",
        "emergency": "emergency",
    }
    return mapping.get(text, "medium")


def from_incident_severity(value: Any) -> SecuritySeverity:
    """Map an incident severity onto the event ladder for weighting/ordering."""
    text = normalize_incident_severity(value)
    mapping = {
        "low": SecuritySeverity.NOTICE,
        "medium": SecuritySeverity.WARNING,
        "high": SecuritySeverity.HIGH,
        "critical": SecuritySeverity.CRITICAL,
        "emergency": SecuritySeverity.EMERGENCY,
    }
    return mapping[text]