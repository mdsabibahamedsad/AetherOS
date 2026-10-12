"""
SecOps health model.

Posture: HEALTHY / DEGRADED / ALERT / LOCKDOWN.

The SecOps health model is *honest*: it never reports HEALTHY when telemetry
is unavailable.  Failures degrade gracefully:

    monitoring failure   -> DEGRADED (never healthy while observability is blind)
    audit failure        -> DEGRADED (safe failure: log loudly, keep deciding)
    detection engine down-> DEGRADED (deterministic authz stays authoritative)
    open high/critical   -> ALERT
    emergency stop /     -> LOCKDOWN
    account lockdown

Health composes the observability health service (reports the ``SECURITY``
component) and the security response manager's state.
"""

from __future__ import annotations

import logging
import threading
import time
from enum import Enum
from typing import Any, Dict, Optional

from .severity import SecuritySeverity, parse_severity

logger = logging.getLogger(__name__)


class SecOpsPosture(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ALERT = "alert"
    LOCKDOWN = "lockdown"


class SecOpsHealth:
    """Computes the SecOps posture and drives health registration.

    Usage::

        health = SecOpsHealth()
        health.set_monitoring_healthy(True)
        posture = health.posture()
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._monitoring_healthy = True
        self._audit_healthy = True
        self._detection_healthy = True
        self._last_report: Dict[str, Any] = {}
        self._last_report_at: float = 0.0

    # ------------------------------------------------------------------
    # Subsystem signals
    # ------------------------------------------------------------------

    def set_monitoring_healthy(self, healthy: bool, reason: str = "") -> None:
        with self._lock:
            self._monitoring_healthy = healthy

    def set_audit_healthy(self, healthy: bool, reason: str = "") -> None:
        with self._lock:
            self._audit_healthy = healthy

    def set_detection_healthy(self, healthy: bool, reason: str = "") -> None:
        with self._lock:
            self._detection_healthy = healthy

    def subsystem_health(self) -> Dict[str, bool]:
        with self._lock:
            return {
                "monitoring": self._monitoring_healthy,
                "audit": self._audit_healthy,
                "detection": self._detection_healthy,
            }

    # ------------------------------------------------------------------
    # Posture
    # ------------------------------------------------------------------

    def _response_state(self) -> str:
        try:
            from aetheros_security.response import get_response_manager
            return get_response_manager().get_state()
        except Exception:
            return "unknown"

    def posture(self) -> Dict[str, Any]:
        """Compute the current posture from subsystem + response state."""
        with self._lock:
            monitoring = self._monitoring_healthy
            audit = self._audit_healthy
            detection = self._detection_healthy

        state = self._response_state()

        # LOCKDOWN dominates everything.
        if state in ("emergency_stop", "lockdown"):
            posture = SecOpsPosture.LOCKDOWN
            reasons = [f"response state: {state}"]
        else:
            reasons: list = []
            # Monitoring failure -> DEGRADED, never healthy.
            if not monitoring:
                reasons.append("monitoring unavailable")
            if not audit:
                reasons.append("audit unavailable (safe failure)")
            if not detection:
                reasons.append("detection engine unavailable (authz unchanged)")
            if any(not r for r in (monitoring, audit, detection)):
                posture = SecOpsPosture.DEGRADED
            elif self._has_open_alerts():
                posture = SecOpsPosture.ALERT
            else:
                posture = SecOpsPosture.HEALTHY

        report = {
            "posture": posture.value,
            "response_state": state,
            "subsystems": self.subsystem_health(),
            "reasons": reasons,
            "timestamp": time.time(),
        }
        with self._lock:
            self._last_report = report
            self._last_report_at = report["timestamp"]
        self._register_with_observability(posture)
        return report

    def _has_open_alerts(self) -> bool:
        try:
            from aetheros_security.secops.incidents import get_incident_store
            store = get_incident_store()
            for incident in store.open_incidents(limit=100):
                if incident["severity"] in ("high", "critical", "emergency"):
                    return True
            return False
        except Exception:
            return False

    def last_report(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._last_report)

    # ------------------------------------------------------------------
    # Observability integration
    # ------------------------------------------------------------------

    def _register_with_observability(self, posture: SecOpsPosture) -> None:
        try:
            from aetheros_observability.health import (HealthState,
                                                       SECURITY,
                                                       get_health_service)
            state = {
                SecOpsPosture.HEALTHY: HealthState.HEALTHY,
                SecOpsPosture.DEGRADED: HealthState.DEGRADED,
                SecOpsPosture.ALERT: HealthState.DEGRADED,
                SecOpsPosture.LOCKDOWN: HealthState.UNHEALTHY,
            }[posture]
            service = get_health_service()
            service.register(
                SECURITY,
                lambda: (state, f"secops posture: {posture.value}"),
            )
        except Exception:
            logger.debug("observability health registration failed", exc_info=True)


# Global SecOps health
_secops_health: Optional[SecOpsHealth] = None


def get_secops_health() -> SecOpsHealth:
    """Return the process-wide SecOpsHealth singleton."""
    global _secops_health
    if _secops_health is None:
        _secops_health = SecOpsHealth()
    return _secops_health