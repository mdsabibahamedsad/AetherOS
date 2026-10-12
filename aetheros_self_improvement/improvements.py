"""Proposals + candidates (Phase G/H, §44-45, §70, §72-80, §107, §119):
ImprovementPlanner turns failures/lessons into proposals; candidates
are versioned artifacts. NOTHING here mutates production (§0.2) —
deployment happens only in deploy.py after gates. Candidates declare
permissions/data/policies/risk/rollback (§44).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from .models import FailureRecord, ImprovementProposal, Lesson


class CandidateRegistry:
    """Versioned candidate changes (prompt/tool/workflow/router/memory)."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def register(self, kind: str, name: str,
                 change: Dict[str, Any]) -> Dict[str, Any]:
        blob = json.dumps({"kind": kind, "name": name, "change": change},
                          sort_keys=True, default=str)
        version = f"v{hashlib.sha256(blob.encode()).hexdigest()[:8]}"
        rec = {"kind": kind, "name": name, "version": version,
               "change": change, "state": "Proposed"}
        self._store[f"{kind}:{name}:{version}"] = rec
        return rec

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self._store.get(key)

    def set_state(self, key: str, state: str) -> None:
        if key in self._store:
            self._store[key]["state"] = state


class ImprovementPlanner:
    SUGGESTIONS = ("Improve planner", "Change model", "Change tool",
                   "Improve retrieval", "Add verification",
                   "Change workflow", "Add guardrail", "Improve memory",
                   "Reduce context")

    def __init__(self, candidates: Optional[CandidateRegistry] = None):
        self.candidates = candidates or CandidateRegistry()
        self.proposals: Dict[str, ImprovementProposal] = {}

    def from_failure(self, failure: FailureRecord,
                     cause_summary: str,
                     lesson: Optional[Lesson] = None,
                     author: str = "fabric") -> ImprovementProposal:
        suggestion = self._suggest(failure.failure_class)
        prop = ImprovementProposal(
            title=f"{suggestion} for {failure.failure_class}",
            problem=failure.what_happened[:500],
            evidence=[failure.id, failure.trace_id],
            root_cause=cause_summary[:500],
            hypothesis=f"{suggestion} reduces {failure.failure_class}",
            candidate_change={"suggestion": suggestion,
                              "lesson_id": lesson.id if lesson else ""},
            expected_benefit="fewer F3+ failures of this class",
            expected_risk="low: offline evaluation first",
            affected_systems=[failure.failure_class],
            evaluation_plan={"dataset": "regression",
                             "trials": 3, "gates": ["hard", "regression"]},
            rollback_plan="no production change; discard candidate",
            author=author, tenant=failure.tenant)
        if lesson:
            prop.evidence.append(lesson.id)
        self.proposals[prop.id] = prop
        return prop

    @staticmethod
    def _suggest(failure_class: str) -> str:
        table = {"planning": "Improve planner", "model": "Change model",
                 "routing": "Change model",
                 "tool_selection": "Change tool",
                 "tool_execution": "Change tool",
                 "retrieval": "Improve retrieval",
                 "memory": "Improve memory",
                 "verification": "Add verification",
                 "grounding": "Reduce context"}
        return table.get(failure_class, "Add guardrail")

    def to_experiment(self, prop: ImprovementProposal) -> None:
        prop.status = "experiment"

    def evaluated(self, prop: ImprovementProposal,
                  passed: bool) -> None:
        prop.status = "evaluated" if passed else "rejected"
        if passed:
            prop.status = "review_required"
