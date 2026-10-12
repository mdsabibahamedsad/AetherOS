"""Research agents: role presets, decomposition, merging (P69-73).

Roles map onto the EXISTING ``delegate_task`` surface — each role is a
(goal template, toolset subset, constraints) triple a caller can hand to
``tools.delegate_tool.delegate_task(tasks=[...])``. A local runner is also
supported so teams execute without subagents (and fully offline in tests).
Merging ALWAYS goes through claim/evidence objects, never concatenation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from agent.research.models import (
    Claim,
    ClaimStatus,
    Evidence,
    ResearchSource,
)


@dataclass(frozen=True)
class ResearchRole:
    name: str
    purpose: str
    toolsets: tuple
    goal_template: str


ROLES: Dict[str, ResearchRole] = {
    "search": ResearchRole(
        "search",
        "run broad discovery queries across the open web",
        ("web",),
        "Search the web for primary sources answering: {query}. "
        "Return URLs with titles and short factual snippets only.",
    ),
    "primary_sources": ResearchRole(
        "primary_sources",
        "find official documentation and first-party announcements",
        ("web",),
        "Find OFFICIAL documentation, specifications, or first-party "
        "announcements about: {query}. Prefer docs./vendor domains.",
    ),
    "academic": ResearchRole(
        "academic",
        "locate papers, preprints, and datasets",
        ("web",),
        "Find academic papers or preprints relevant to: {query}. "
        "Record arXiv IDs, publication dates, and authors.",
    ),
    "industry": ResearchRole(
        "industry",
        "gather credible industry and press coverage",
        ("web",),
        "Find reputable industry/news coverage of: {query}. Distinguish "
        "reported vs confirmed vs alleged statements.",
    ),
    "contradiction": ResearchRole(
        "contradiction",
        "hunt counter-evidence and criticism",
        ("web",),
        "Actively search for counter-evidence, criticism, failed attempts, "
        "and contradictions regarding: {query}. Report findings even when "
        "they disagree with the majority view.",
    ),
    "verification": ResearchRole(
        "verification",
        "independently verify specific claims across new domains",
        ("web",),
        "Independently verify each of these claims against sources NOT in "
        "the provided list: {claims}",
    ),
}


@dataclass
class SubTask:
    role: str
    goal: str
    toolsets: List[str]
    context: str = ""
    result: List[Claim] = field(default_factory=list)

    def to_delegate_dict(self) -> Dict:
        """Shape accepted by tools/delegate_tool.py batch mode."""
        return {
            "goal": self.goal,
            "context": self.context,
            "toolsets": list(self.toolsets),
            "role": "leaf",
        }


def build_subtasks(query: str, role_names: List[str],
                   claims_to_verify: Optional[List[str]] = None,
                   known_context: str = "") -> List[SubTask]:
    tasks = []
    for role_name in role_names:
        role = ROLES.get(role_name)
        if role is None:
            continue
        if role_name == "verification":
            if not claims_to_verify:
                continue
            goal = role.goal_template.format(
                claims=" | ".join(claims_to_verify[:8])
            )
        else:
            goal = role.goal_template.format(query=query)
        tasks.append(SubTask(role=role_name, goal=goal,
                             toolsets=list(role.toolsets), context=known_context))
    return tasks


LocalRunner = Callable[[SubTask], List[Claim]]


def run_research_team(subtasks: List[SubTask],
                      runner: Optional[LocalRunner] = None,
                      delegate_fn: Optional[Callable] = None) -> Dict[str, List[Claim]]:
    """Execute the team. Priority: injected runner > delegate_task > none."""
    results: Dict[str, List[Claim]] = {}
    if runner is not None:
        for task in subtasks:
            results[task.role] = list(runner(task) or [])
        return results
    if delegate_fn is not None:
        payload = [t.to_delegate_dict() for t in subtasks]
        raw = delegate_fn(tasks=payload)
        # delegate_task returns a JSON string array; parsing lives with the
        # caller's schema — we accept either pre-parsed lists or JSON.
        import json

        entries = json.loads(raw) if isinstance(raw, str) else raw
        for entry, task in zip(entries or [], subtasks):
            results[task.role] = _claims_from_agent_output(entry, task.role)
        return results
    raise ValueError("no runner or delegate_fn available for research team")


def _claims_from_agent_output(entry, role: str) -> List[Claim]:
    """Normalize an agent's textual answer into UNVERIFIED source claims.

    Agent output is external data: nothing here may arrive pre-marked as
    CONFIRMED — verification happens through evidence linkage later.
    """
    text = ""
    if isinstance(entry, dict):
        text = str(entry.get("summary") or entry.get("result") or "")
    else:
        text = str(entry or "")
    claims: List[Claim] = []
    for sentence in [s.strip() for s in text.split(". ") if 40 <= len(s.strip()) <= 400][:6]:
        claims.append(
            Claim(
                text=sentence.rstrip("."),
                status=ClaimStatus.UNVERIFIED,
                confidence=0.2,
            )
        )
    return claims


def merge_through_evidence(groups_of_claims: List[List[Claim]],
                           sources: Dict[str, ResearchSource]) -> List[Claim]:
    """P72: merge agent outputs via assertion identity + evidence union."""
    from agent.research.engine import _same_assertion

    merged: List[Claim] = []
    for claims in groups_of_claims:
        for claim in claims:
            twin = next(
                (m for m in merged if _same_assertion(m.text, claim.text)), None
            )
            if twin is None:
                merged.append(claim)
                continue
            twin.source_ids = list(dict.fromkeys(twin.source_ids + claim.source_ids))
            for ev in claim.evidence:
                ev.claim_id = twin.claim_id
                twin.evidence.append(ev)
            twin.updated_at = time.time()
    return merged


def independently_verified(claim: Claim, sources: Dict[str, ResearchSource],
                           min_domains: int = 2) -> bool:
    """P73: an important conclusion needs distinct registrable domains."""
    from agent.research.urlnorm import registrable_domain

    domains = {
        registrable_domain(sources[sid].url)
        for sid in claim.source_ids
        if sid in sources
    }
    return len(domains) >= min_domains
