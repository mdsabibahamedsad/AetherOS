"""
Security Operations orchestrator.

Ties the SecOps subsystems into one stable surface implementing the full
pipeline:

    observe -> detect -> correlate -> score -> incident -> respond -> alert
    (health, forensics, learning, inventory, copilot, kpi, chaos alongside)

The orchestrator *composes* the existing AetherOS security architecture â€” the
control plane (authz, response, kill switch, identity, mcp, manifest, tool
authz) and observability (health, incidents, recovery, service) â€” and never
duplicates it.  Deterministic authorization stays the primary control; this
layer observes and orchestrates on top of it.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .alerts import AlertManager
from .ai_guardrails import SecurityCopilot
from .baselines import BehaviorBaselines
from .chaos import SimulationResult, SimulationScenario, SimulatedIncident
from .config import SecOpsConfig, load_secops_config
from .correlation import CorrelationEngine, CorrelationMatch
from .detectors import Detection, DetectionEngine, make_detection
from .events import (SecurityEvent, SecurityEventType, SecurityEventBus,
                     get_event_bus)
from .forensics import Forensics
from .health import SecOpsHealth, SecOpsPosture
from .incidents import (ContainmentStatus, EvidenceEntry, IncidentStatus,
                        IncidentStore, SecOpsIncident)
from .inventory import ComponentInventory
from .kpi import SecurityKPIs
from .learning import LearningLoop
from .response_engine import (ContainmentAction, ContainmentResult, Runbook,
                              ResponseEngine)
from .risk import RiskScorer
from .self_protection import ProtectedControl, SelfProtectionGuard
from .severity import SecuritySeverity, parse_severity

logger = logging.getLogger(__name__)


class SecurityOperations:
    """Full Security Operations orchestrator.

    Usage::

        secops = SecurityOperations()
        secops.configure(SecOpsConfig())
        secops.start()   # wires bus -> engine, subscribes
        secops.observe(SecurityEventType.TOOL_CALL, severity="info", ...)
        report = secops.dashboard()
    """

    def __init__(self, *, bus: Optional[SecurityEventBus] = None) -> None:
        self._lock = threading.RLock()
        self._bus = bus if bus is not None else get_event_bus()
        self._config = SecOpsConfig()
        self._started = False
        self._last_pipeline_at = 0.0

        # Subsystems (fresh instances so tests never pollute the singletons).
        self._detection_engine = DetectionEngine()
        self._correlation = CorrelationEngine()
        self._risk_scorer = RiskScorer()
        self._baselines = BehaviorBaselines()
        self._incident_store = IncidentStore()
        self._response_engine = ResponseEngine()
        self._alert_manager = AlertManager()
        self._health = SecOpsHealth()
        self._forensics = Forensics()
        self._learning = LearningLoop()
        self._inventory = ComponentInventory()
        self._copilot = SecurityCopilot()
        self._kpis = SecurityKPIs()
        self._self_protection = SelfProtectionGuard()

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def configure(self, config: SecOpsConfig) -> None:
        self._config = config
        self._bus._max_events = max(1, config.max_events)
        self._alert_manager = AlertManager(
            cooldown_seconds=config.alert_cooldown_seconds,
            dedup_window_seconds=config.alert_dedup_window_seconds,
            escalate_after_seconds=config.escalate_after_seconds,
        )
        self._response_engine.set_auto_containment(
            high=config.auto_contain_high_severity,
            critical=config.auto_contain_critical_severity,
        )
        self._learning.set_auto_apply(config.learning_auto_apply)
        self._kpis.set_incident_store(self._incident_store)
        self._kpis.set_learning_loop(self._learning)

    def start(self) -> None:
        """Wire the bus to the engine, correlation, response + alert managers."""
        if self._started:
            return
        self._detection_engine.attach(self._bus)
        self._bus.subscribe(self._correlate)
        self._bus.subscribe(self._observe_baselines)
        self._response_engine.set_bus(self._bus)
        self._alert_manager.set_bus(self._bus)
        self._forensics.set_bus(self._bus)
        self._self_protection.set_bus(self._bus)
        self._register_default_runbooks()
        self._started = True

    def _register_default_runbooks(self) -> None:
        from .response_engine import RunbookStep
        self._response_engine.register_runbook(Runbook(
            name="network_egress",
            description="Contain suspected data exfiltration",
            steps=[
                RunbookStep(ContainmentAction.KILL_SWITCH,
                            target="DISABLE_EXTERNAL_NETWORK",
                            note="cut egress"),
            ],
        ))
        self._response_engine.register_runbook(Runbook(
            name="agent_compromise",
            description="Contain a compromised agent",
            steps=[
                RunbookStep(ContainmentAction.QUARANTINE_AGENT,
                            note="suspend the actor"),
            ],
        ))
        self._response_engine.register_runbook(Runbook(
            name="critical_escalation",
            description="Full stop for emergency incidents",
            steps=[
                RunbookStep(ContainmentAction.EMERGENCY_STOP,
                            note="halt agent activity"),
            ],
        ))

    def _mk_step(self, action: ContainmentAction, *, target: str = "",
                 note: str = "") -> "object":
        from .response_engine import RunbookStep
        return RunbookStep(action=action, target=target, note=note)

    # ------------------------------------------------------------------
    # Observe
    # ------------------------------------------------------------------

    def observe(self, event_type: Any, *, severity: Any = SecuritySeverity.INFO,
                source: str = "", principal: str = "",
                component: str = "", resource: str = "",
                action: str = "", outcome: str = "",
                correlation_id: str = "", message: str = "",
                payload: Optional[Dict[str, Any]] = None,
                tags: Optional[List[str]] = None,
                agent_id: str = "", mission_id: str = "",
                session_id: str = "") -> SecurityEvent:
        """Publish a security-relevant event into the pipeline."""
        event = self._bus.emit(
            event_type, severity=severity, source=source, principal=principal,
            component=component, resource=resource, action=action,
            outcome=outcome, correlation_id=correlation_id, message=message,
            payload=payload, tags=tags, agent_id=agent_id,
            mission_id=mission_id, session_id=session_id,
        )
        self._last_pipeline_at = time.time()
        return event

    def _correlate(self, event: SecurityEvent) -> None:
        """Bus subscriber: feed the correlation engine."""
        if not self._config.detection_enabled:
            return
        self._correlation.consume(event)

    def _observe_baselines(self, event: SecurityEvent) -> None:
        """Bus subscriber: feed behavior baselines for anomaly detection."""
        if event.event_type in (SecurityEventType.TOOL_CALL,
                                SecurityEventType.CODE_EXECUTED,
                                SecurityEventType.FILE_DELETE,
                                SecurityEventType.NETWORK_CONNECT,
                                SecurityEventType.MODEL_CALL):
            actor = event.agent_id or event.principal or event.source or "unknown"
            self._baselines.observe(event.event_type.value, actor=actor)

    # ------------------------------------------------------------------
    # Detect
    # ------------------------------------------------------------------

    def run_detection_pass(self, *, from_correlation: bool = True) -> List[Detection]:
        """Run the detection engine over the retained window + correlation.

        Emits each detection onto the bus so it can feed the incident engine.
        """
        detections: List[Detection] = []
        # Correlation matches -> detections.
        if from_correlation:
            for match in self._correlation.poll():
                detection = make_detection(
                    f"correlation.{match.rule}",
                    title=match.title,
                    description=match.description,
                    severity=match.severity,
                    confidence=0.85,
                    evidence={"correlation_id": match.correlation_id,
                              "event_ids": match.event_ids},
                    components=["correlation"],
                )
                self._bus.emit(
                    SecurityEventType.CORRELATION_RAISED,
                    severity=match.severity, source="correlation",
                    resource=match.rule, message=match.title,
                    payload={"correlation_id": match.correlation_id,
                             "event_ids": match.event_ids},
                )
                detections.append(detection)
        return detections

    # ------------------------------------------------------------------
    # Incident lifecycle
    # ------------------------------------------------------------------

    def open_incident(self, *, title: str, description: str = "",
                      severity: Any = "medium",
                      detection: Optional[Detection] = None,
                      event_ids: Optional[List[str]] = None,
                      affected_components: Optional[List[str]] = None,
                      affected_principals: Optional[List[str]] = None,
                      correlation_id: str = "") -> SecOpsIncident:
        """Score + open an incident, wire provenance, and auto-contain."""
        from .severity import from_incident_severity, normalize_incident_severity
        sev = normalize_incident_severity(severity)
        event_sev = from_incident_severity(sev)
        corroboration = len(event_ids or []) + (
            1 if detection is not None else 0)
        score_result = self._risk_scorer.score_incident(
            severity=sev, corroboration=corroboration,
        )
        incident = self._incident_store.create(
            title=title, description=description,
            severity=sev, risk_score=score_result["score"],
            source="secops",
            affected_components=list(affected_components or []),
            affected_principals=list(affected_principals or []),
            detection_rule=detection.rule_id if detection else "",
            correlation_id=correlation_id or (detection.evidence or {}).get(
                "correlation_id", "") if detection else "",
            event_ids=list(event_ids or []),
        )
        if detection is not None:
            incident.add_evidence(EvidenceEntry(
                kind="detection", source=detection.detector,
                data=detection.to_dict(), event_id=detection.event_id,
            ))
        incident.add_timeline("incident_opened", {
            "severity": sev, "risk_score": incident.risk_score,
        })

        self._bus.emit(
            SecurityEventType.INCIDENT_OPENED,
            severity=event_sev, source="secops",
            resource=incident.incident_id, message=title,
            payload={"risk_score": incident.risk_score,
                     "risk_tier": incident.risk_tier,
                     "detection_rule": incident.detection_rule},
        )

        # Mirror into the control-plane response manager so its notifier +
        # audit surfaces observe the incident too.
        try:
            from aetheros_security.response import get_response_manager
            get_response_manager().open_incident(
                title, severity=sev, description=description,
                source="secops", affected_principals=affected_principals,
            )
        except Exception:
            logger.debug("response-manager mirror failed", exc_info=True)

        # Auto-containment for critical/emergency (config-gated).
        if self._config.auto_contain_critical_severity or self._config.auto_contain_high_severity:
            self._response_engine.auto_contain_incident(incident)

        return incident

    def transition(self, incident_id: str, status: IncidentStatus) -> bool:
        ok = self._incident_store.transition(incident_id, status)
        if ok:
            self._bus.emit(
                SecurityEventType.INCIDENT_TRANSITION,
                severity="info", source="secops",
                resource=incident_id, outcome="ok",
                payload={"status": status.value},
            )
        return ok

    def resolve_incident(self, incident_id: str, *, resolution: str = "") -> bool:
        ok = self._incident_store.resolve(incident_id, resolution=resolution)
        if ok:
            self._bus.emit(
                SecurityEventType.INCIDENT_CLOSED,
                severity="notice", source="secops",
                resource=incident_id, message=resolution or "resolved",
            )
        return ok

    # ------------------------------------------------------------------
    # Respond
    # ------------------------------------------------------------------

    def contain(self, action: ContainmentAction, *, target: str = "",
                incident_id: str = "", reason: str = "") -> ContainmentResult:
        incident = self._incident_store.get(incident_id) if incident_id else None
        return self._response_engine.contain(action, target=target,
                                             incident=incident, reason=reason)

    def run_runbook(self, name: str, *, incident_id: str = "",
                    targets: Optional[Dict[ContainmentAction, str]] = None
                    ) -> List[ContainmentResult]:
        incident = self._incident_store.get(incident_id) if incident_id else None
        return self._response_engine.run_runbook(name, incident=incident,
                                                 targets=targets)

    # ------------------------------------------------------------------
    # Alert
    # ------------------------------------------------------------------

    def alert_user(self, *, key: str, title: str, message: str = "",
                   severity: Any = SecuritySeverity.WARNING,
                   incident_id: str = "") -> Any:
        return self._alert_manager.alert(
            key=key, title=title, message=message, severity=severity,
            incident_id=incident_id, source="secops",
        )

    def escalate(self, alert_id: str, level: Any, *, reason: str = "") -> bool:
        return self._alert_manager.escalate(alert_id, level, reason=reason)

    def promote_alerts(self) -> List[Any]:
        return self._alert_manager.promote_active()

    # ------------------------------------------------------------------
    # Health / posture
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        return self._health.posture()

    # ------------------------------------------------------------------
    # Forensics / learning / inventory
    # ------------------------------------------------------------------

    def forensics_timeline(self, incident_id: str) -> List[Dict[str, Any]]:
        incident = self._incident_store.get(incident_id)
        if incident is None:
            return []
        return self._forensics.timeline(incident)

    def forensics_root_cause(self, incident_id: str) -> Dict[str, Any]:
        incident = self._incident_store.get(incident_id)
        if incident is None:
            return {"found": False, "reason": "unknown incident"}
        return self._forensics.root_cause(incident)

    def forensics_attack_path(self, incident_id: str) -> List[Dict[str, Any]]:
        incident = self._incident_store.get(incident_id)
        if incident is None:
            return []
        return self._forensics.attack_path(incident)

    def export_incident(self, incident_id: str, output_path: str,
                        *, redacted: bool = True) -> bool:
        incident = self._incident_store.get(incident_id)
        if incident is None:
            return False
        return self._forensics.export_json(incident, output_path,
                                           redacted=redacted)

    def add_feedback(self, rule_id: str, kind: Any, *, reason: str = "",
                     source: str = "") -> Any:
        return self._learning.add_feedback(rule_id, kind, reason=reason,
                                           source=source)

    def propose_adjustment(self, rule_id: str, *, parameter: str,
                           new_value: Any, reason: str = "",
                           proposed_by: str = "system") -> Any:
        return self._learning.propose_adjustment(
            rule_id, parameter=parameter, new_value=new_value, reason=reason,
            proposed_by=proposed_by,
        )

    def approve_adjustment(self, adjustment_id: str, *, by: str = "admin") -> bool:
        return self._learning.approve(adjustment_id, approved_by=by)

    # ------------------------------------------------------------------
    # Copilot (guardrailed)
    # ------------------------------------------------------------------

    def copilot_analyze(self, incident_id: str, *, prompt: str = "",
                        claims: Optional[List[Any]] = None) -> Any:
        incident = self._incident_store.get(incident_id)
        if incident is None:
            raise ValueError(f"unknown incident: {incident_id}")
        return self._copilot.analyze(incident, prompt=prompt, claims=claims)

    # ------------------------------------------------------------------
    # Self-protection
    # ------------------------------------------------------------------

    def self_protection_check(self, control: ProtectedControl, *,
                              principal: str, action: str = "disable",
                              reason: str = "") -> None:
        """Raise SelfProtectionError when a non-elevated principal mutates a control."""
        self._self_protection.check(control, principal=principal,
                                    action=action, reason=reason)

    def self_protection_status(self) -> Dict[str, Any]:
        return self._self_protection.stats()

    # ------------------------------------------------------------------
    # Chaos / simulated incidents
    # ------------------------------------------------------------------

    def run_simulation(self, scenario: SimulationScenario) -> SimulationResult:
        simulator = SimulatedIncident(self._bus, self._detection_engine)
        return simulator.run(scenario)

    # ------------------------------------------------------------------
    # Dashboard / status
    # ------------------------------------------------------------------

    def dashboard(self) -> Dict[str, Any]:
        """Consolidated operational dashboard."""
        posture = self.health()
        return {
            "posture": posture,
            "detection": self._detection_engine.stats(),
            "correlation": self._correlation.stats(),
            "incidents": self._incident_store.stats(),
            "alerts": self._alert_manager.stats(),
            "response": self._response_engine.stats(),
            "baselines": self._baselines.snapshot(),
            "learning": self._learning.stats(),
            "inventory": self._inventory.stats(),
            "self_protection": self._self_protection.stats(),
            "kpi": self._kpis.report(),
            "config": {
                "enabled": self._config.enabled,
                "detection_enabled": self._config.detection_enabled,
                "learning_auto_apply": self._config.learning_auto_apply,
            },
            "last_pipeline_at": self._last_pipeline_at,
            "timestamp": time.time(),
        }

    # ------------------------------------------------------------------
    # Accessors (composition handles)
    # ------------------------------------------------------------------

    @property
    def bus(self) -> SecurityEventBus:
        return self._bus

    @property
    def detection_engine(self) -> DetectionEngine:
        return self._detection_engine

    @property
    def correlation(self) -> CorrelationEngine:
        return self._correlation

    @property
    def incident_store(self) -> IncidentStore:
        return self._incident_store

    @property
    def response_engine(self) -> ResponseEngine:
        return self._response_engine

    @property
    def alert_manager(self) -> AlertManager:
        return self._alert_manager

    @property
    def learning(self) -> LearningLoop:
        return self._learning

    @property
    def inventory(self) -> ComponentInventory:
        return self._inventory

    @property
    def kpis(self) -> SecurityKPIs:
        return self._kpis


@property
    def forensics(self) -> Forensics:
        return self._forensics

    @property\n    def forensics(self) -> Forensics:\n        return self._forensics\n\n    @property
    def forensics(self) -> Forensics:
        return self._forensics
    @property
    def forensics(self) -> Forensics:
        return self._forensics

# Global SecOps orchestrator
_secops: Optional[SecurityOperations] = None


def get_secops(bus: Optional[SecurityEventBus] = None) -> SecurityOperations:
    """Return the process-wide SecurityOperations singleton."""
    global _secops
    if _secops is None or bus is not None:
        _secops = SecurityOperations(bus=bus)
    return _secops

