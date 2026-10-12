"""Research planner: question -> objective -> subquestions -> strategies.

Deterministic, LLM-free decomposition so planning is reproducible and
testable offline. Each subquestion carries multiple query strategies
(exact, primary-source-oriented, contradiction-hunting, recency-scoped).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

from agent.research.models import ResearchTask

_STOPWORDS = frozenset(
    """a an and are as at be by for from has have how i in is it its of on or
    that the their there these this to was were what when where which who why
    will with vs""".split()
)


@dataclass
class SearchStrategy:
    kind: str
    query: str

    def to_dict(self) -> Dict:
        return dict(self.__dict__)


@dataclass
class SubQuestion:
    text: str
    purpose: str
    strategies: List[SearchStrategy] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "purpose": self.purpose,
            "strategies": [s.to_dict() for s in self.strategies],
        }


@dataclass
class ResearchPlan:
    objective: str
    subquestions: List[SubQuestion] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "objective": self.objective,
            "subquestions": [s.to_dict() for s in self.subquestions],
        }


def _key_terms(question: str, limit: int = 6) -> List[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", question)
    seen: List[str] = []
    for w in words:
        lw = w.lower()
        if lw in _STOPWORDS or lw in seen:
            continue
        seen.append(lw)
        if len(seen) >= limit:
            break
    return seen


def build_plan(task: ResearchTask) -> ResearchPlan:
    """Produce objective + subquestions + query strategies for a task."""
    q = " ".join(task.user_query.split())
    terms = _key_terms(q)
    term_blob = " ".join(terms[:4]) if terms else q

    subquestions: List[SubQuestion] = [
        SubQuestion(
            text=q,
            purpose="direct answer",
            strategies=_strategies_for(q, task),
        ),
        SubQuestion(
            text=f"Primary sources and official documentation about {term_blob}",
            purpose="primary sources",
            strategies=[
                SearchStrategy("primary-source", f"{term_blob} official documentation"),
                SearchStrategy("technical", f"{term_blob} specification reference"),
            ],
        ),
        SubQuestion(
            text=f"Criticisms, failures, and counter-evidence about {term_blob}",
            purpose="contradiction hunting",
            strategies=[
                SearchStrategy("contradiction", f"{term_blob} criticism problems limitations"),
                SearchStrategy("negative", f"{term_blob} failed does not work"),
            ],
        ),
        SubQuestion(
            text=f"Current status and recent developments of {term_blob}",
            purpose="recency",
            strategies=[
                SearchStrategy("date-filtered", f"{term_blob} latest status")
                if not task.time_range
                else SearchStrategy("date-filtered", f"{term_blob} {task.time_range}"),
            ],
        ),
    ]
    objective = (
        f"Determine an evidence-backed answer to: {q}. "
        f"Prefer primary sources, corroborate across independent domains, "
        f"record contradictions instead of silently resolving them."
    )
    plan = ResearchPlan(objective=objective, subquestions=subquestions)
    from agent.research.targets import bias_strategies_for_query

    for purpose in bias_strategies_for_query(q):
        if purpose == "technical":
            subquestions.append(
                SubQuestion(
                    text=f"Official technical documentation and release notes: {term_blob}",
                    purpose="technical",
                    strategies=[
                        SearchStrategy("technical", f"{term_blob} release notes changelog"),
                        SearchStrategy("primary-source", f"{term_blob} official specification"),
                    ],
                )
            )
        elif purpose == "academic":
            subquestions.append(
                SubQuestion(
                    text=f"Papers, preprints, and datasets: {term_blob}",
                    purpose="academic",
                    strategies=[
                        SearchStrategy("academic", f"arxiv {term_blob} paper"),
                        SearchStrategy("academic", f"{term_blob} benchmark dataset study"),
                    ],
                )
            )
        elif purpose == "news":
            subquestions.append(
                SubQuestion(
                    text=f"Recent developments and announcements: {term_blob}",
                    purpose="news",
                    strategies=[
                        SearchStrategy("news", f"{term_blob} announced this month"),
                        SearchStrategy("date-filtered", f"{term_blob} latest news"),
                    ],
                )
            )
    return plan


def _strategies_for(question: str, task: ResearchTask) -> List[SearchStrategy]:
    strategies = [
        SearchStrategy("exact", question),
        SearchStrategy("alternative-terminology", _synonym_broaden(question)),
    ]
    if task.sources_allowed:
        allowed = ", ".join(task.sources_allowed[:2])
        strategies.append(SearchStrategy("domain-restricted", f"{question} ({allowed})"))
    return strategies


_SYNONYM_MAP = {
    "how": "guide",
    "what": "definition",
    "why": "explanation reason",
    "best": "top recommended",
    "fast": "fastest performance",
    "vs": "versus comparison",
}


def _synonym_broaden(question: str) -> str:
    out = question
    lowered = question.lower()
    for trigger, replacement in _SYNONYM_MAP.items():
        if trigger in lowered:
            return f"{out} {replacement}"
    return f"{out} overview"
