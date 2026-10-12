"""Self-diagnostics + evidence-based RCA + change correlation (P55-60).

Composes ``aetheros_reliability.rca`` confidence discipline: root cause is
NEVER claimed without evidence, and the latest commit is never auto-blamed
(P59) — candidates are ranked by correlation evidence only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from agent.quality.models import Diagnosis


@dataclass
class FailureRecord:
    failure_id: str
    what: str
    where: str                    # component/module
    when: float
    impact: str = ""
    task_id: str = ""
    agent_id: str = ""
    tool_id: str = ""
    commit: str = ""
    release: str = ""
    environment: str = ""
    raw_error: str = ""


@dataclass
class ChangeRecord:
    commit: str
    description: str
    components: List[str]
    timestamp: float
    author: str = ""


class DiagnosticEngine:
    """Builds Diagnosis objects from failure + context records."""

    def __init__(self, changes: Optional[List[ChangeRecord]] = None):
        self.changes = list(changes or [])

    # -- P57/P58 correlation -------------------------------------------------

    def correlate(self, failure: FailureRecord) -> Dict[str, List[str]]:
        corr: Dict[str, List[str]] = {
            "task": [failure.task_id] if failure.task_id else [],
            "agent": [failure.agent_id] if failure.agent_id else [],
            "tool": [failure.tool_id] if failure.tool_id else [],
            "commit": [failure.commit] if failure.commit else [],
            "release": [failure.release] if failure.release else [],
            "environment": [failure.environment] if failure.environment else [],
        }
        return {k: v for k, v in corr.items() if v}

    # -- P59 change-regression correlation (no auto-blame) ---------------------

    def related_changes(self, failure: FailureRecord,
                        *, window_seconds: float = 7 * 86400) -> List[Tuple[ChangeRecord, str]]:
        """Changes touching the failed component inside the window, ranked
        newest-first, each labeled with an evidence caveat — the LATEST commit
        is just one candidate among many, never the automatic culprit."""
        related = []
        for c in self.changes:
            if failure.when - c.timestamp > window_seconds:
                continue
            overlap = set(c.components) & {failure.where.lower()}
            if overlap:
                related.append((c, f"touches failed component '{failure.where}'"))
        related.sort(key=lambda pair: pair[0].timestamp, reverse=True)
        return related

    # -- P55/P56/P60 ------------------------------------------------------------

    def diagnose(self, failure: FailureRecord,
                 *, evidence: Optional[List[str]] = None,
                 likely_cause: str = "",
                 confidence: str = "UNKNOWN",
                 recommended_action: str = "investigate with more evidence",
                 impact: str = "") -> Diagnosis:
        ev = list(evidence or [])
        if failure.raw_error:
            ev.insert(0, f"raw_error: {failure.raw_error}")
        related = self.related_changes(failure)
        if related and confidence == "UNKNOWN":
            # correlation raises suspicion but is never proof (P56)
            ev.append("correlated changes: " + ", ".join(
                f"{c.commit} ({why})" for c, why in related[:3]))
        return Diagnosis(
            what=failure.what,
            where=failure.where,
            when=failure.when,
            impact=impact or failure.impact,
            likely_cause=likely_cause or "undetermined — evidence insufficient",
            confidence=confidence,
            recommended_action=recommended_action,
            evidence=ev,
            correlated=self.correlate(failure),
        )

    def render_report(self, d: Diagnosis) -> str:
        """P60 — human-readable diagnostic report."""
        lines = [
            "=== AUTOMATED DIAGNOSTIC REPORT ===",
            f"WHAT:    {d.what}",
            f"WHERE:   {d.where}",
            f"WHEN:    {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(d.when))}",
            f"IMPACT:  {d.impact or '(not assessed)'}",
            f"CAUSE:   {d.likely_cause}  [confidence: {d.confidence}]",
            f"ACTION:  {d.recommended_action}",
        ]
        if d.evidence:
            lines.append("EVIDENCE:")
            lines.extend(f"  - {e}" for e in d.evidence)
        if d.correlated:
            lines.append("CORRELATION: " + json_compact(d.correlated))
        return "\n".join(lines)


def json_compact(obj: Dict[str, List[str]]) -> str:
    import json

    return json.dumps(obj, sort_keys=True)
