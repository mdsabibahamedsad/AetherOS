"""Project / research / artifact / procedural memory (sections 6, 25-29).

Backed by ``MemoryRecord`` lists owned by the service; each accessor builds
live views (no cached copies, so invalidation is trivial).  Research reuse
follows: fresh -> reuse, stale volatile -> revalidate, missing -> research
again, sources gone -> uncertainty.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_memory_intelligence.record import MemoryRecord, RecordStatus, RecordType

RecordsFn = Callable[[], List[MemoryRecord]]

# Volatile topics need revalidation; stable topics can be reused longer.
VOLATILE_HINTS = ("price", "weather", "version", "api", "news", "stock",
                  "availability", "release", "changelog")
VOLATILE_TTL_S = 7 * 86400.0
STABLE_TTL_S = 180 * 86400.0


def _active(records: List[MemoryRecord]) -> List[MemoryRecord]:
    return [r for r in records if r.status == RecordStatus.ACTIVE]


@dataclass
class ProjectMemoryView:
    project_id: str
    overview: str = ""
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    active_tasks: List[Dict[str, Any]] = field(default_factory=list)
    completed_tasks: List[Dict[str, Any]] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    research: List[Dict[str, Any]] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    recent_changes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"project_id": self.project_id, "overview": self.overview,
                "goals": self.goals, "constraints": self.constraints,
                "decisions": self.decisions, "active_tasks": self.active_tasks,
                "completed_tasks": self.completed_tasks, "files": self.files,
                "research": self.research, "open_questions": self.open_questions,
                "risks": self.risks, "recent_changes": self.recent_changes}


def build_project_view(project_id: str, records: List[MemoryRecord]) -> ProjectMemoryView:
    view = ProjectMemoryView(project_id=project_id)
    mine = [r for r in _active(records) if r.project_id == project_id]
    for rec in sorted(mine, key=lambda r: r.updated_at, reverse=True):
        brief = {"id": rec.id, "summary": rec.summary or rec.content[:160],
                 "confidence": rec.confidence, "updated_at": rec.updated_at}
        if rec.type == RecordType.PROJECT_DECISION:
            meta = rec.metadata or {}
            view.decisions.append({**brief,
                                   "reason": meta.get("reason", ""),
                                   "alternatives": meta.get("alternatives", [])})
        elif rec.type == RecordType.TASK_STATE:
            (view.completed_tasks if "complet" in rec.content.lower()
             else view.active_tasks).append(brief)
        elif rec.type == RecordType.PROJECT_FACT:
            if "constraint" in rec.content.lower() or "must" in rec.content.lower():
                view.constraints.append(brief["summary"])
            elif "?" in rec.content:
                view.open_questions.append(brief["summary"])
            elif "risk" in rec.content.lower():
                view.risks.append(brief["summary"])
            else:
                view.goals.append(brief["summary"])
        elif rec.type == RecordType.ARTIFACT_MEMORY:
            for aid in rec.artifact_ids:
                if aid not in view.files:
                    view.files.append(aid)
        elif rec.type == RecordType.RESEARCH_FINDING:
            view.research.append(brief)
    view.recent_changes = [{"id": r.id, "type": r.type.value,
                            "summary": (r.summary or r.content[:120]),
                            "updated_at": r.updated_at}
                           for r in sorted(mine, key=lambda r: r.updated_at,
                                           reverse=True)[:10]]
    overviews = [r.content for r in mine if r.type == RecordType.PROJECT_FACT][:1]
    view.overview = (overviews + [""])[0][:500]
    return view


@dataclass
class ResearchReuseDecision:
    action: str  # reuse|revalidate|research_again|uncertain
    claim_id: str = ""
    reason: str = ""


def decide_research_reuse(question: str, records: List[MemoryRecord],
                          now: Optional[float] = None) -> ResearchReuseDecision:
    now = now if now is not None else time.time()
    volatile = any(h in question.lower() for h in VOLATILE_HINTS)
    ttl = VOLATILE_TTL_S if volatile else STABLE_TTL_S
    candidates = [r for r in _active(records)
                  if r.type == RecordType.RESEARCH_FINDING
                  and question.lower()[:24] in r.content.lower()
                  or (r.type == RecordType.RESEARCH_FINDING
                      and any(w in r.content.lower()
                              for w in question.lower().split()[:4]))]
    if not candidates:
        return ResearchReuseDecision(action="research_again", reason="no-prior-research")
    best = max(candidates, key=lambda r: r.confidence)
    age = now - best.updated_at
    if age > ttl:
        return ResearchReuseDecision(action="revalidate", claim_id=best.id,
                                     reason=f"stale age={age/86400:.0f}d ttl={ttl/86400:.0f}d")
    if best.status == RecordStatus.CONFLICTED:
        return ResearchReuseDecision(action="research_again", claim_id=best.id,
                                     reason="conflicted-claim")
    if not best.evidence_ids:
        return ResearchReuseDecision(action="uncertain", claim_id=best.id,
                                     reason="claim-without-evidence")
    return ResearchReuseDecision(action="reuse", claim_id=best.id,
                                 reason=f"fresh confidence={best.confidence:.2f}")
