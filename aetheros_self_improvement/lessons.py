"""Lesson engine (Phase D, §20-22, §156-167, §185): scoped lessons with
evidence counts, conflict detection (never silent overwrite), expiry,
tenant boundaries, and a strict global-promotion gate (multiple
independent examples + cross-context validation + regression +
security review).
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from .models import Lesson


class LessonEngine:
    def __init__(self, min_evidence: int = 3):
        self.lessons: Dict[str, Lesson] = {}
        self.min_evidence = min_evidence
        self.conflicts: List[Dict[str, str]] = []

    def propose(self, observation: str, generalization: str, scope: str,
                scope_id: str = "", source_traces: Optional[List[str]] = None,
                tenant: str = "default", confidence: float = 0.3,
                **scopes: str) -> Lesson:
        lesson = Lesson(
            observation=observation, generalization=generalization,
            scope=scope, scope_id=scope_id,
            source_traces=list(source_traces or []), tenant=tenant,
            confidence=confidence,
            evidence=list(source_traces or []),
            model_scope=scopes.get("model_scope", ""),
            tool_scope=scopes.get("tool_scope", ""),
            agent_scope=scopes.get("agent_scope", ""))
        self._check_conflict(lesson)
        self.lessons[lesson.id] = lesson
        return lesson

    def add_evidence(self, lesson_id: str, trace_id: str) -> Optional[Lesson]:
        lesson = self.lessons.get(lesson_id)
        if lesson is None:
            return None
        if trace_id not in lesson.evidence:
            lesson.evidence.append(trace_id)
            lesson.source_traces.append(trace_id)
        n = len(lesson.evidence)
        lesson.confidence = min(0.99, n / (n + 2))
        if n >= self.min_evidence and lesson.status == "unverified":
            lesson.status = "supported"
            lesson.knowledge_state = "Inferred"
        return lesson

    def validate(self, lesson_id: str) -> bool:
        lesson = self.lessons.get(lesson_id)
        if lesson is None or len(lesson.evidence) < self.min_evidence:
            return False
        lesson.status = "validated"
        lesson.knowledge_state = "Validated"
        return True

    def _check_conflict(self, lesson: Lesson) -> None:
        for other in self.lessons.values():
            if other.tenant != lesson.tenant:
                continue  # §162: tenants never conflict across boundary
            if (other.scope == lesson.scope
                    and other.scope_id == lesson.scope_id
                    and other.generalization
                    and lesson.generalization
                    and other.generalization != lesson.generalization):
                other.status = "contradicted"
                lesson.status = "contradicted"
                self.conflicts.append({"a": other.id, "b": lesson.id,
                                       "scope": lesson.scope})

    def expire_stale(self, max_age_days: float = 90.0) -> List[str]:
        cutoff = time.time() - max_age_days * 86400
        expired = []
        for lesson in self.lessons.values():
            if lesson.expires_at and lesson.expires_at < time.time():
                lesson.status = "stale"
                expired.append(lesson.id)
            elif lesson.at < cutoff and lesson.status == "unverified":
                lesson.status = "stale"
                expired.append(lesson.id)
        return expired

    def promote_global(self, lesson_id: str, cross_context_ok: bool = False,
                       regression_ok: bool = False,
                       security_ok: bool = False) -> bool:
        """§167 gate: all four required, else stays scoped (§160)."""
        lesson = self.lessons.get(lesson_id)
        if lesson is None or lesson.status != "validated":
            return False
        if not (len(lesson.evidence) >= max(2, self.min_evidence)
                and cross_context_ok and regression_ok and security_ok):
            return False
        lesson.scope = "global_candidate"
        return True

    def for_scope(self, scope: str, scope_id: str = "",
                  tenant: str = "default") -> List[Lesson]:
        return [l for l in self.lessons.values()
                if l.scope == scope and l.scope_id == scope_id
                and l.tenant == tenant
                and l.status in ("supported", "validated")]
