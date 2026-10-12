"""Token-budget-aware context assembly (section 45).

Priority: task constraints > explicit user instructions > project state >
decisions > recent events > validated research > stable preferences >
historical context.  Estimates tokens as chars/4 (documented heuristic).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from aetheros_memory_intelligence.hybrid import RetrievedRecord
from aetheros_memory_intelligence.record import RecordType

_PRIORITY = {
    RecordType.TASK_STATE: 0,
    RecordType.USER_PREFERENCE: 1,
    RecordType.PROJECT_FACT: 2,
    RecordType.PROJECT_DECISION: 2,
    RecordType.EPISODIC_EVENT: 3,
    RecordType.RESEARCH_FINDING: 4,
    RecordType.USER_FACT: 5,
    RecordType.ERROR_LESSON: 3,
    RecordType.PROCEDURAL_MEMORY: 4,
    RecordType.ARTIFACT_MEMORY: 4,
    RecordType.SOURCE_MEMORY: 6,
    RecordType.ENTITY_MEMORY: 6,
    RecordType.RELATIONSHIP_MEMORY: 6,
    RecordType.SYSTEM_MEMORY: 7,
}


def estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


@dataclass
class BudgetResult:
    included: List[RetrievedRecord]
    excluded: List[RetrievedRecord]
    tokens_used: int
    budget: int

    def to_dict(self) -> Dict[str, Any]:
        return {"included": [r.to_dict() for r in self.included],
                "excluded_ids": [r.record.id for r in self.excluded],
                "tokens_used": self.tokens_used, "budget": self.budget}


class MemoryBudgetManager:
    def __init__(self, budget_tokens: int = 2400) -> None:
        self.budget_tokens = budget_tokens

    def select(self, candidates: List[RetrievedRecord],
               budget: int = 0) -> BudgetResult:
        limit = budget or self.budget_tokens
        ordered = sorted(candidates,
                         key=lambda r: (_PRIORITY.get(r.record.type, 9), -r.score))
        included, excluded, used = [], [], 0
        for r in ordered:
            # Explicit user-confirmed preferences jump the queue only if they fit;
            # priority ordering above already ranks them second.
            cost = estimate_tokens(r.record.content) + 24  # framing overhead
            if used + cost <= limit:
                included.append(r)
                used += cost
            else:
                excluded.append(r)
        return BudgetResult(included=included, excluded=excluded,
                            tokens_used=used, budget=limit)
