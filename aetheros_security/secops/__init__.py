"""
Security Operations (SecOps) for AetherOS
==========================================

Production-grade Security Operations layer on top of the existing
AetherOS security architecture (zero-trust control plane in
``aetheros_security`` + observability in ``aetheros_observability``).

The SecOps layer *composes* the existing control-plane and observability
systems rather than replacing them:

    observe   -> SecurityEventBus (normalized, redacted, retained)
    detect    -> DetectionEngine + built-in detectors
    correlate -> CorrelationEngine (multi-signal)
    score     -> RiskScorer (deterministic, never fabricated)
    incident  -> SecOpsIncident state machine (NEW .. REOPENED)
    respond   -> IncidentResponseEngine (runbooks + containment)
    alert     -> AlertManager (dedup + escalation + user notification)
    health    -> SecOpsHealth (HEALTHY/DEGRADED/ALERT/LOCKDOWN)
    forensics -> timeline / RCA / attack path / redacted export
    learn     -> gated learning loop + false-positive management
    inventory -> component inventory + integrity + config drift
    copilot   -> guardrailed AI-assisted analysis (never authoritative)
    kpi       -> MTTD / MTTR / FP-rate computed from real data
    chaos     -> simulated incidents for pipeline testing (safe)

Deterministic authorization (``aetheros_security.authz``) remains the
primary security control.  The SecOps layer never overrides it; it
observes, correlates, and triggers the control plane's own mechanisms
(kill switches, emergency stop, quarantine, tool authz).
"""

from __future__ import annotations

import logging

from .alerts import AlertManager, EscalationLevel, UserAlert
from .ai_guardrails import (AnalysisClaim, AnalysisEnvelope, AnalysisGuard,
                            Confidence, NeverAction, SecurityCopilot)
from .baselines import BaselineStats, BehaviorBaselines
from .chaos import SimulationResult, SimulationScenario, SimulatedIncident
from .config import SecOpsConfig, load_secops_config
from .correlation import CorrelationEngine, CorrelationMatch, CorrelationRule
from .detectors import Detection, Detector, DetectionEngine
from .events import (SecurityEvent, SecurityEventBus, SecurityEventType,
                     get_event_bus)
from .forensics import Forensics
from .health import SecOpsHealth, SecOpsPosture
from .incidents import (ContainmentStatus, EvidenceEntry, IncidentStatus,
                        IncidentStore, SecOpsIncident)
from .inventory import ComponentInventory
from .kpi import SecurityKPIs
from .learning import FeedbackKind, LearningLoop
from .ops import SecurityOperations, get_secops
from .response_engine import (ContainmentAction, ContainmentResult,
                              ResponseEngine, Runbook, RunbookStep)
from .risk import RiskScorer, RiskTier
from .self_protection import (ProtectedControl, SelfProtectionError,
                              SelfProtectionGuard)
from .severity import (SecuritySeverity, from_audit_severity,
                       from_observability_severity, parse_severity)

logger = logging.getLogger(__name__)

__all__ = [
    "get_secops",
    "SecurityOperations",
    # events
    "SecurityEventBus",
    "SecurityEvent",
    "SecuritySeverity",
    "SecurityEventType",
    "get_event_bus",
    # detection / correlation
    "DetectionEngine",
    "Detection",
    "Detector",
    "CorrelationEngine",
    "CorrelationRule",
    "CorrelationMatch",
    # risk / baselines
    "RiskScorer",
    "RiskTier",
    "BehaviorBaselines",
    "BaselineStats",
    # incidents
    "SecOpsIncident",
    "IncidentStatus",
    "IncidentStore",
    "EvidenceEntry",
    "ContainmentStatus",
    # response
    "ResponseEngine",
    "ContainmentAction",
    "ContainmentResult",
    "Runbook",
    "RunbookStep",
    # alerts
    "AlertManager",
    "UserAlert",
    "EscalationLevel",
    # health / self-protection
    "SecOpsHealth",
    "SecOpsPosture",
    "SelfProtectionGuard",
    "SelfProtectionError",
    "ProtectedControl",
    # forensics / learning / inventory
    "Forensics",
    "LearningLoop",
    "FeedbackKind",
    "ComponentInventory",
    # copilot / kpi / chaos
    "SecurityCopilot",
    "AnalysisClaim",
    "AnalysisEnvelope",
    "AnalysisGuard",
    "Confidence",
    "NeverAction",
    "SecurityKPIs",
    "SimulatedIncident",
    "SimulationScenario",
    "SimulationResult",
    # config
    "SecOpsConfig",
    "load_secops_config",
    # severity helpers
    "parse_severity",
    "from_audit_severity",
    "from_observability_severity",
]