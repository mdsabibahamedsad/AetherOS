"""Incident response (§53-55, §158): detection intake, lifecycle
states, configurable auto-containment. Destructive containment is
never irreversible without explicit policy."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from .models import Incident, new_id

STATES = ("DETECTED", "TRIAGED", "CONTAINING", "CONTAINED",
          "INVESTIGATING", "RECOVERING", "RESOLVED", "POSTMORTEM")

CONTAINMENTS = ("WARN", "RATE_LIMIT", "PAUSE_AGENT", "REVOKE_CAPABILITY",
                "ISOLATE_TOOL", "BLOCK_NETWORK", "QUARANTINE_EXTENSION",
                "STOP_SWARM", "STOP_AUTOMATION", "EMERGENCY_STOP")

# Destructive actions requiring explicit policy opt-in (§55).
DESTRUCTIVE = {"REVOKE_CAPABILITY", "BLOCK_NETWORK", "EMERGENCY_STOP"}


class IncidentController:
    def __init__(self, allow_destructive: bool = False):
        self.allow_destructive = allow_destructive
        self.incidents: Dict[str, Incident] = {}
        self._hooks: Dict[str, List[Callable[[Incident], None]]] = {}

    def on(self, action: str, fn: Callable[[Incident], None]) -> None:
        self._hooks.setdefault(action, []).append(fn)

    def open(self, kind: str, severity: str = "LOW", actor: str = "",
             resources: Optional[List[str]] = None) -> Incident:
        inc = Incident(new_id("inc"), kind, severity, "DETECTED", actor,
                       tuple(resources or []),
                       [{"state": "DETECTED", "at": str(time.time())}])
        self.incidents[inc.incident_id] = inc
        return inc

    def transition(self, incident_id: str, state: str,
                   note: str = "") -> Incident:
        inc = self.incidents[incident_id]
        if STATES.index(state) < STATES.index(inc.state) and state != "CONTAINING":
            raise ValueError(f"illegal regression {inc.state}->{state}")
        inc.state = state
        inc.timeline.append({"state": state, "at": str(time.time()),
                             "note": note})
        return inc

    def contain(self, incident_id: str, actions: List[str]) -> Incident:
        inc = self.incidents[incident_id]
        applied = []
        for a in actions:
            if a not in CONTAINMENTS:
                raise ValueError(f"unknown containment {a}")
            if a in DESTRUCTIVE and not self.allow_destructive:
                raise ValueError(
                    f"destructive containment {a} needs explicit policy")
            applied.append(a)
            for fn in self._hooks.get(a, []):
                fn(inc)
        inc.containment = tuple(applied)
        if inc.state == "DETECTED":
            self.transition(incident_id, "TRIAGED", "auto-containment")
        self.transition(incident_id, "CONTAINING", ",".join(applied))
        return inc

    def explain(self, incident_id: str) -> Dict[str, Any]:
        inc = self.incidents[incident_id]
        return {"what": f"{inc.kind} by {inc.actor} ({inc.severity})",
                "state": inc.state,
                "timeline": inc.timeline,
                "containment": list(inc.containment),
                "evidence": list(inc.evidence),
                "resources": list(inc.resources)}

    @staticmethod
    def detectors() -> List[str]:
        return ["policy violation", "credential misuse",
                "unexpected privilege escalation", "repeated denied actions",
                "tool abuse", "prompt injection", "data exfiltration attempt",
                "identity anomaly", "agent behavior anomaly",
                "network anomaly", "physical safety anomaly"]
