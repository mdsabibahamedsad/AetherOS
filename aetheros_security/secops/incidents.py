"""
SecOps incident model and store.

An incident is the core artifact of the Security Operations layer: a
correlated, scored set of evidence describing a security problem, driven
through a lifecycle state machine:

    NEW -> TRIAGED -> INVESTIGATING -> CONTAINED -> ERADICATED -> RECOVERED
        -> RESOLVED            (and REOPENED from any resolved state)

The store keeps full provenance (evidence, timeline, owner, resolution,
containment status, risk score) so the forensics module can reconstruct the
incident end to end.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .risk import RiskTier, tier_for_score


class IncidentStatus(Enum):
    """SecOps incident lifecycle states (spec: NEW .. REOPENED)."""

    NEW = "new"
    TRIAGED = "triaged"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    ERADICATED = "eradicated"
    RECOVERED = "recovered"
    RESOLVED = "resolved"
    REOPENED = "reopened"


class ContainmentStatus(Enum):
    NONE = "none"
    PARTIAL = "partial"
    CONTAINED = "contained"
    ISOLATED = "isolated"


#: Valid transitions for the incident state machine.
_TRANSITIONS: Dict[IncidentStatus, set] = {
    IncidentStatus.NEW: {IncidentStatus.TRIAGED, IncidentStatus.RESOLVED},
    IncidentStatus.TRIAGED: {IncidentStatus.INVESTIGATING, IncidentStatus.CONTAINED,
                             IncidentStatus.RESOLVED},
    IncidentStatus.INVESTIGATING: {IncidentStatus.CONTAINED, IncidentStatus.ERADICATED,
                                   IncidentStatus.RESOLVED},
    IncidentStatus.CONTAINED: {IncidentStatus.INVESTIGATING, IncidentStatus.ERADICATED,
                               IncidentStatus.RESOLVED},
    IncidentStatus.ERADICATED: {IncidentStatus.RECOVERED, IncidentStatus.RESOLVED},
    IncidentStatus.RECOVERED: {IncidentStatus.RESOLVED, IncidentStatus.REOPENED},
    IncidentStatus.RESOLVED: {IncidentStatus.REOPENED},
    IncidentStatus.REOPENED: {IncidentStatus.TRIAGED, IncidentStatus.INVESTIGATING,
                              IncidentStatus.CONTAINED, IncidentStatus.RESOLVED},
}

#: Canonical forward lifecycle path (used by ``advance()``).
_FORWARD_PATH = [
    IncidentStatus.NEW, IncidentStatus.TRIAGED, IncidentStatus.INVESTIGATING,
    IncidentStatus.CONTAINED, IncidentStatus.ERADICATED, IncidentStatus.RECOVERED,
    IncidentStatus.RESOLVED,
]


@dataclass
class EvidenceEntry:
    """A single piece of incident evidence."""

    kind: str                    # event | detection | correlation | manual | artifact
    source: str
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    event_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "source": self.source,
            "timestamp": self.timestamp,
            "data": dict(self.data),
            "event_id": self.event_id,
        }


@dataclass
class SecOpsIncident:
    """A security incident with full provenance."""

    incident_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    description: str = ""
    severity: str = "medium"
    risk_score: float = 0.0
    risk_tier: str = RiskTier.LOW.value
    status: IncidentStatus = IncidentStatus.NEW
    containment_status: ContainmentStatus = ContainmentStatus.NONE
    source: str = ""
    affected_components: List[str] = field(default_factory=list)
    affected_principals: List[str] = field(default_factory=list)
    owner: str = ""
    resolution: str = ""
    correlation_id: str = ""
    detection_rule: str = ""
    event_ids: List[str] = field(default_factory=list)
    evidence: List[EvidenceEntry] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    closed_at: float = 0.0
    reopened_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timeline:
            self.timeline.append({"timestamp": self.created_at, "event": "created"})

    # ------------------------------------------------------------------
    # Timeline / evidence
    # ------------------------------------------------------------------

    def add_timeline(self, event: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.timeline.append({"timestamp": time.time(), "event": event,
                              "details": details or {}})
        self.updated_at = time.time()

    def add_evidence(self, entry: EvidenceEntry) -> None:
        self.evidence.append(entry)
        self.add_timeline("evidence_added", {"kind": entry.kind, "source": entry.source})

    def add_event_ref(self, event_id: str) -> None:
        if event_id and event_id not in self.event_ids:
            self.event_ids.append(event_id)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def transition(self, target: IncidentStatus) -> bool:
        """Attempt a state transition; returns False on invalid transitions."""
        if target == self.status:
            return False
        if target not in _TRANSITIONS.get(self.status, set()):
            return False
        old = self.status
        self.status = target
        if target == IncidentStatus.RESOLVED:
            self.closed_at = time.time()
        if target == IncidentStatus.REOPENED:
            self.reopened_count += 1
            self.closed_at = 0.0
        self.add_timeline("status_transition", {"from": old.value, "to": target.value})
        self.updated_at = time.time()
        return True

    def advance(self) -> bool:
        """Move one step forward along the canonical lifecycle."""
        try:
            idx = _FORWARD_PATH.index(self.status)
        except ValueError:
            return False
        if idx >= len(_FORWARD_PATH) - 1:
            return False
        return self.transition(_FORWARD_PATH[idx + 1])

    def reopen(self) -> bool:
        return self.transition(IncidentStatus.REOPENED)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "risk_score": self.risk_score,
            "risk_tier": self.risk_tier,
            "status": self.status.value,
            "containment_status": self.containment_status.value,
            "source": self.source,
            "affected_components": list(self.affected_components),
            "affected_principals": list(self.affected_principals),
            "owner": self.owner,
            "resolution": self.resolution,
            "correlation_id": self.correlation_id,
            "detection_rule": self.detection_rule,
            "event_ids": list(self.event_ids),
            "evidence_count": len(self.evidence),
            "timeline_count": len(self.timeline),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "closed_at": self.closed_at,
            "reopened_count": self.reopened_count,
            "metadata": dict(self.metadata),
        }


class IncidentStore:
    """In-memory incident store with query + lifecycle helpers."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._incidents: Dict[str, SecOpsIncident] = {}
        self._max_incidents = 1000

    def create(self, *, title: str, description: str = "", severity: str = "medium",
               risk_score: float = 0.0, source: str = "",
               affected_components: Optional[List[str]] = None,
               affected_principals: Optional[List[str]] = None,
               detection_rule: str = "", correlation_id: str = "",
               event_ids: Optional[List[str]] = None) -> SecOpsIncident:
        incident = SecOpsIncident(
            title=title, description=description, severity=severity,
            risk_score=risk_score, risk_tier=tier_for_score(risk_score).value,
            source=source, affected_components=list(affected_components or []),
            affected_principals=list(affected_principals or []),
            detection_rule=detection_rule, correlation_id=correlation_id,
            event_ids=list(event_ids or []),
        )
        with self._lock:
            self._incidents[incident.incident_id] = incident
            if len(self._incidents) > self._max_incidents:
                # Drop the oldest resolved incident to bound memory.
                resolved = [i for i in self._incidents.values()
                            if i.status == IncidentStatus.RESOLVED]
                if resolved:
                    oldest = min(resolved, key=lambda i: i.created_at)
                    del self._incidents[oldest.incident_id]
        return incident

    def get(self, incident_id: str) -> Optional[SecOpsIncident]:
        with self._lock:
            return self._incidents.get(incident_id)

    def all_incidents(self) -> List[SecOpsIncident]:
        """Return raw incident objects (for KPIs/forensics needing full data)."""
        with self._lock:
            return list(self._incidents.values())

    def transition(self, incident_id: str, status: IncidentStatus) -> bool:
        incident = self.get(incident_id)
        if incident is None:
            return False
        return incident.transition(status)

    def set_owner(self, incident_id: str, owner: str) -> bool:
        incident = self.get(incident_id)
        if incident is None:
            return False
        incident.owner = owner
        incident.add_timeline("owner_assigned", {"owner": owner})
        incident.updated_at = time.time()
        return True

    def resolve(self, incident_id: str, *, resolution: str = "") -> bool:
        incident = self.get(incident_id)
        if incident is None:
            return False
        if incident.resolution and resolution:
            incident.resolution += "\n" + resolution
        elif resolution:
            incident.resolution = resolution
        ok = incident.transition(IncidentStatus.RESOLVED)
        if ok:
            incident.add_timeline("resolved", {"resolution": resolution})
        return ok

    def reopen(self, incident_id: str, *, reason: str = "") -> bool:
        incident = self.get(incident_id)
        if incident is None:
            return False
        ok = incident.reopen()
        if ok:
            incident.add_timeline("reopened", {"reason": reason})
        return ok

    def list(self, *, open_only: bool = False,
             severity: Optional[str] = None,
             status: Optional[IncidentStatus] = None,
             limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            incidents = list(self._incidents.values())
        results = []
        for incident in sorted(incidents, key=lambda i: i.created_at, reverse=True):
            if open_only and incident.status == IncidentStatus.RESOLVED:
                continue
            if severity and incident.severity != severity:
                continue
            if status and incident.status != status:
                continue
            results.append(incident.to_dict())
            if len(results) >= limit:
                break
        return results

    def open_incidents(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.list(open_only=True, limit=limit)

    def count_open(self) -> int:
        with self._lock:
            return sum(1 for i in self._incidents.values()
                       if i.status != IncidentStatus.RESOLVED)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            incidents = list(self._incidents.values())
        by_status: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for incident in incidents:
            by_status[incident.status.value] = by_status.get(incident.status.value, 0) + 1
            by_severity[incident.severity] = by_severity.get(incident.severity, 0) + 1
        return {
            "total": len(incidents),
            "open": sum(1 for i in incidents if i.status != IncidentStatus.RESOLVED),
            "by_status": by_status,
            "by_severity": by_severity,
        }

    def clear(self) -> int:
        with self._lock:
            count = len(self._incidents)
            self._incidents.clear()
            return count


# Global incident store
_incident_store: Optional[IncidentStore] = None


def get_incident_store() -> IncidentStore:
    """Return the process-wide IncidentStore singleton."""
    global _incident_store
    if _incident_store is None:
        _incident_store = IncidentStore()
    return _incident_store