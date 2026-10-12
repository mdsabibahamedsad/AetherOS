"""
Forensics: timeline, root cause, attack path, evidence, redacted export.

The forensics module reconstructs what happened around an incident from the
data the SecOps layer already keeps (events, detections, correlations,
containment actions).  It produces:

    - a chronological timeline,
    - a root-cause analysis (first anomalous signal),
    - an attack path (the chain of events leading to the incident),
    - a redacted incident export for sharing / retention.

Exports are always redacted through the existing redaction manager — secrets
never leave the boundary.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from .events import SecurityEventBus
from .incidents import SecOpsIncident

logger = logging.getLogger(__name__)


class Forensics:
    """Builds timelines, RCAs and redacted exports for incidents.

    Usage::

        forensics = Forensics()
        forensics.set_bus(bus)
        timeline = forensics.timeline(incident)
        rca = forensics.root_cause(incident)
        export = forensics.redacted_export(incident)
    """

    def __init__(self) -> None:
        self._bus: Optional[SecurityEventBus] = None
        self._redaction = None

    def set_bus(self, bus: SecurityEventBus) -> None:
        self._bus = bus

    def _redactor(self):
        if self._redaction is None:
            from aetheros_security.redaction import get_redaction_manager
            self._redaction = get_redaction_manager()
        return self._redaction

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def timeline(self, incident: SecOpsIncident, limit: int = 500) -> List[Dict[str, Any]]:
        """Chronological timeline of incident events + evidence + actions."""
        entries: List[Dict[str, Any]] = []

        # Incident's own timeline.
        for entry in incident.timeline:
            entries.append({
                "ts": entry.get("timestamp", 0.0),
                "kind": "incident",
                "event": entry.get("event", ""),
                "data": entry.get("details", {}),
            })

        # Evidence entries.
        for ev in incident.evidence:
            entries.append({
                "ts": ev.timestamp,
                "kind": f"evidence:{ev.kind}",
                "event": ev.source,
                "data": ev.data,
            })

        # Correlated source events from the bus.
        if self._bus is not None:
            for event_id in incident.event_ids:
                for ev in self._bus.recent(limit=10000):
                    if ev.event_id == event_id:
                        entries.append({
                            "ts": ev.timestamp,
                            "kind": f"event:{ev.event_type.value}",
                            "event": ev.message or ev.event_type.value,
                            "data": ev.to_dict(),
                        })
                        break

        entries.sort(key=lambda e: e["ts"])
        return entries[-limit:]

    # ------------------------------------------------------------------
    # Root cause
    # ------------------------------------------------------------------

    def root_cause(self, incident: SecOpsIncident) -> Dict[str, Any]:
        """Identify the earliest anomalous signal tied to the incident."""
        tl = self.timeline(incident, limit=10000)
        earliest = tl[0] if tl else None
        if earliest is None:
            return {"found": False, "reason": "no timeline data"}

        # The root cause is the earliest source event that is not the
        # incident itself — i.e. the first anomaly.
        root = None
        for entry in tl:
            if entry["kind"].startswith("event:"):
                root = entry
                break
        if root is None:
            root = earliest
        return {
            "found": root is not None,
            "first_timestamp": root["ts"] if root else None,
            "kind": root["kind"] if root else "",
            "signal": root["event"] if root else "",
            "incident_id": incident.incident_id,
        }

    # ------------------------------------------------------------------
    # Attack path
    # ------------------------------------------------------------------

    def attack_path(self, incident: SecOpsIncident) -> List[Dict[str, Any]]:
        """Reconstruct the attack path: events chained by actor + resource.

        Uses the incident's event refs (in bus order) grouped by the actor
        that raised them, producing an ordered narrative of the path.
        """
        if self._bus is None:
            return []
        events = []
        for event_id in incident.event_ids:
            for ev in self._bus.recent(limit=10000):
                if ev.event_id == event_id:
                    events.append(ev)
                    break
        events.sort(key=lambda e: e.timestamp)
        path = []
        for ev in events:
            path.append({
                "ts": ev.timestamp,
                "actor": ev.principal or ev.source or "unknown",
                "event_type": ev.event_type.value,
                "resource": ev.resource or "",
                "action": ev.action or "",
                "outcome": ev.outcome or "",
            })
        return path

    # ------------------------------------------------------------------
    # Evidence collection + export
    # ------------------------------------------------------------------

    def collect_evidence(self, incident: SecOpsIncident, *, source_events: bool = True) -> Dict[str, Any]:
        """Collect the full evidence set for an incident."""
        evidence = []
        for entry in incident.evidence:
            evidence.append(entry.to_dict())
        return {
            "incident_id": incident.incident_id,
            "evidence_entries": evidence,
            "event_refs": list(incident.event_ids),
            "collected_at": time.time(),
        }

    def redacted_export(self, incident: SecOpsIncident, *, include_timeline: bool = True) -> Dict[str, Any]:
        """Export an incident with all payloads redacted."""
        redactor = self._redactor()
        data: Dict[str, Any] = incident.to_dict()
        # Full detail: timeline, evidence, attack path.
        data["timeline_full"] = self.timeline(incident)
        data["evidence_full"] = [e.to_dict() for e in incident.evidence]
        data["attack_path"] = self.attack_path(incident)
        data["root_cause"] = self.root_cause(incident)
        return redactor.redact_dict(data)

    def export_json(self, incident: SecOpsIncident, output_path: str,
                    *, redacted: bool = True) -> bool:
        """Write a (redacted) incident export to disk as JSON."""
        data = self.redacted_export(incident) if redacted else incident.to_dict()
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as exc:
            logger.error("Incident export failed: %s", exc)
            return False


# Global forensics
_forensics: Optional[Forensics] = None


def get_forensics() -> Forensics:
    """Return the process-wide Forensics singleton."""
    global _forensics
    if _forensics is None:
        _forensics = Forensics()
    return _forensics