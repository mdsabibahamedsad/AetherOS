"""
Deterministic risk scoring for security events and incidents.

Risk is a 0-100 score derived from: event severity, the sensitivity of the
resource, the trust of the principal, and the number of corroborating signals.
It is entirely deterministic — no fabricated values, no model inference.  The
score maps to a risk tier (LOW/MEDIUM/HIGH/CRITICAL/EMERGENCY) that the
IncidentResponseEngine uses to pick containment actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from .events import SecurityEvent
from .severity import (SecuritySeverity, from_incident_severity,
                       normalize_incident_severity, parse_severity)


class RiskTier(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


#: Weight of each severity on the 0-100 scale.
_SEVERITY_WEIGHT = {
    SecuritySeverity.DEBUG: 0,
    SecuritySeverity.INFO: 5,
    SecuritySeverity.NOTICE: 15,
    SecuritySeverity.WARNING: 30,
    SecuritySeverity.HIGH: 55,
    SecuritySeverity.CRITICAL: 75,
    SecuritySeverity.EMERGENCY: 95,
}

#: Resource sensitivity tiers (default weight = 1.0).
_RESOURCE_SENSITIVITY = {
    "secrets": 2.0,
    "credentials": 2.0,
    "memory": 1.6,
    "knowledge": 1.5,
    "network": 1.4,
    "filesystem": 1.3,
    "terminal": 1.3,
    "config": 1.2,
    "mcp": 1.2,
    "model": 1.1,
    "tool": 1.1,
    "session": 1.2,
    "mission": 1.1,
}

#: Principal trust multipliers (lower trust -> higher risk).
_PRINCIPAL_TRUST = {
    "user": 0.9,
    "admin": 0.7,
    "system": 0.6,
    "agent": 1.0,
    "subagent": 1.1,
    "plugin": 1.2,
    "skill": 1.1,
    "mcp": 1.2,
    "untrusted": 1.5,
    "unknown": 1.3,
}

#: Corroborating-signal bonus (capped).
_CORROBORATION_BONUS = {
    0: 0,
    1: 5,
    2: 10,
    3: 15,
    4: 20,
}


def tier_for_score(score: float) -> RiskTier:
    """Map a 0-100 risk score to a tier."""
    if score >= 90:
        return RiskTier.EMERGENCY
    if score >= 75:
        return RiskTier.CRITICAL
    if score >= 55:
        return RiskTier.HIGH
    if score >= 30:
        return RiskTier.MEDIUM
    return RiskTier.LOW


class RiskScorer:
    """Deterministic risk scorer.

    Usage::

        scorer = RiskScorer()
        event = bus.emit(SecurityEventType.AUTHZ_DENY, severity="high", ...)
        score = scorer.score_event(event)
    """

    def __init__(self) -> None:
        self._resource_sensitivity = dict(_RESOURCE_SENSITIVITY)
        self._principal_trust = dict(_PRINCIPAL_TRUST)

    def register_resource_sensitivity(self, resource: str, weight: float) -> None:
        self._resource_sensitivity[resource.lower()] = max(0.5, min(3.0, weight))

    def register_principal_trust(self, principal: str, weight: float) -> None:
        self._principal_trust[principal.lower()] = max(0.5, min(2.0, weight))

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score_event(self, event: SecurityEvent,
                    corroboration: int = 0) -> float:
        """Score a single security event (0-100)."""
        severity = parse_severity(event.severity)
        base = _SEVERITY_WEIGHT[severity]

        resource = (event.resource or event.component or "").lower()
        sensitivity = self._resource_sensitivity.get(resource, 1.0)

        principal = (event.principal or "").lower()
        trust = self._principal_trust.get(principal, 1.0)

        bonus = _CORROBORATION_BONUS.get(min(4, max(0, corroboration)), 20)
        score = base * sensitivity * trust + bonus
        return round(max(0.0, min(100.0, score)), 2)

    def score_incident(self, *, severity: Any,
                       resource: str = "",
                       principal: str = "",
                       corroboration: int = 0,
                       base_score: Optional[float] = None) -> Dict[str, Any]:
        """Score an incident from its aggregated signals."""
        if base_score is None:
            sev = from_incident_severity(severity)
            base = _SEVERITY_WEIGHT[sev]
            sensitivity = self._resource_sensitivity.get(resource.lower(), 1.0)
            trust = self._principal_trust.get(principal.lower(), 1.0)
            bonus = _CORROBORATION_BONUS.get(min(4, max(0, corroboration)), 20)
            base_score = base * sensitivity * trust + bonus
        score = round(max(0.0, min(100.0, base_score)), 2)
        return {
            "score": score,
            "tier": tier_for_score(score).value,
            "severity": normalize_incident_severity(severity),
            "resource": resource,
            "principal": principal,
            "corroboration": corroboration,
        }

    def score_combined(self, scores: list) -> float:
        """Combine several signal scores into one incident score.

        Uses a deterministic (non-linear) merge so a single high signal is
        not diluted by a pile of low signals.
        """
        if not scores:
            return 0.0
        best = max(scores)
        if len(scores) == 1:
            return round(best, 2)
        avg = sum(scores) / len(scores)
        merged = 0.7 * best + 0.3 * avg
        return round(min(100.0, merged), 2)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "resource_sensitivities": len(self._resource_sensitivity),
            "principal_trusts": len(self._principal_trust),
        }


def default_risk_scorer() -> RiskScorer:
    return RiskScorer()


# Global risk scorer
_risk_scorer: Optional[RiskScorer] = None


def get_risk_scorer() -> RiskScorer:
    """Return the process-wide RiskScorer singleton."""
    global _risk_scorer
    if _risk_scorer is None:
        _risk_scorer = RiskScorer()
    return _risk_scorer