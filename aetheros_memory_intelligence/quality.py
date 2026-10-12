"""Quality checks + health + observability (sections 50-51, 70)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List

from aetheros_memory_intelligence.record import (
    MemoryRecord, PrivacyClass, RecordStatus, contains_secret,
)
from aetheros_memory_intelligence.scoring import lexical_relevance


@dataclass
class QualityReport:
    duplicates: List[List[str]] = field(default_factory=list)
    contradictions: List[List[str]] = field(default_factory=list)
    stale: List[str] = field(default_factory=list)
    unsupported: List[str] = field(default_factory=list)
    privacy_violations: List[str] = field(default_factory=list)
    secret_leaks: List[str] = field(default_factory=list)
    orphan_relations: List[str] = field(default_factory=list)
    broken_provenance: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"duplicates": self.duplicates, "contradictions": self.contradictions,
                "stale": self.stale, "unsupported": self.unsupported,
                "privacy_violations": self.privacy_violations,
                "secret_leaks": self.secret_leaks,
                "orphan_relations": self.orphan_relations,
                "broken_provenance": self.broken_provenance,
                "issue_count": (len(self.duplicates) + len(self.contradictions)
                                + len(self.stale) + len(self.unsupported)
                                + len(self.privacy_violations) + len(self.secret_leaks)
                                + len(self.orphan_relations) + len(self.broken_provenance))}


def run_quality_checks(records: List[MemoryRecord],
                       *, known_entity_ids: set = frozenset()) -> QualityReport:
    rep = QualityReport()
    live = [r for r in records if r.status not in (RecordStatus.DELETED,)]
    for i, rec in enumerate(live):
        if contains_secret(rec.content) or contains_secret(rec.summary):
            rep.secret_leaks.append(rec.id)
        if rec.privacy_class == PrivacyClass.SECRET:
            rep.privacy_violations.append(rec.id)
        if not rec.source and rec.provenance.value == "model_inferred":
            rep.broken_provenance.append(rec.id)
        if rec.confidence < 0.25 and not rec.user_confirmed:
            rep.unsupported.append(rec.id)
        if rec.status == RecordStatus.STALE:
            rep.stale.append(rec.id)
        if rec.status == RecordStatus.CONFLICTED:
            rep.contradictions.append([rec.id])
        for rid in rec.relation_ids:
            if rid not in known_entity_ids and known_entity_ids:
                rep.orphan_relations.append(rec.id)
                break
        for other in live[i + 1:]:
            if other.type == rec.type and other.scope == rec.scope \
                    and lexical_relevance(rec.content, other) >= 0.95:
                rep.duplicates.append([rec.id, other.id])
    return rep


def health_score(report: QualityReport, total: int,
                 *, last_consolidation: float = 0.0) -> Dict[str, Any]:
    """Measured health only: starts at 1.0, deducts per issue class."""
    if total <= 0:
        return {"score": 0.0, "detail": "empty-store"}
    issues = report.to_dict()["issue_count"]
    score = max(0.0, 1.0 - (issues / max(1, total)))
    detail = {"score": round(score, 3), "total": total, "issues": issues,
              "secret_leaks": len(report.secret_leaks),
              "duplicates": len(report.duplicates),
              "stale": len(report.stale),
              "last_consolidation": last_consolidation}
    return detail


class MemoryMetrics:
    """Measured counters only (section 51). No fabricated numbers."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._c: Dict[str, float] = {}

    def observe(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._c[name] = self._c.get(name, 0.0) + value

    def snapshot(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._c)

    def reset(self) -> None:
        with self._lock:
            self._c.clear()
