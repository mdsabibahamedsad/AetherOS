"""Critic reports, consensus and disagreement flow (P25, P28-30).

Agent outputs are DATA. Consensus compares independent results without
forcing agreement; the critic generates an adversarial report; confidence is
tracked separately per layer (result / evidence / verification / conclusion).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


class ConsensusOutcome(Enum):
    AGREEMENT = "agreement"
    DISAGREEMENT = "disagreement"
    PARTIAL_AGREEMENT = "partial_agreement"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass
class CriticReport:
    """P25 — adversarial review of a completed result."""

    target_task_id: str
    reviewer: str
    could_break: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    edge_cases_missed: List[str] = field(default_factory=list)
    verdict: str = "uncertain"          # pass | concerns | reject | uncertain

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_task_id": self.target_task_id,
            "reviewer": self.reviewer,
            "could_break": list(self.could_break),
            "missing_evidence": list(self.missing_evidence),
            "assumptions": list(self.assumptions),
            "edge_cases_missed": list(self.edge_cases_missed),
            "verdict": self.verdict,
        }


def critique(
    *,
    task_id: str,
    result_summary: str,
    success_criteria: Sequence[str],
    evidence_ids: Sequence[str],
    warnings: Sequence[str] = (),
    reviewer: str = "critic",
) -> CriticReport:
    """Deterministic offline critique heuristics (marked heuristic)."""
    report = CriticReport(target_task_id=task_id, reviewer=reviewer)
    if not evidence_ids:
        report.missing_evidence.append("no artifacts/evidence attached")
        report.verdict = "concerns"
    for c in success_criteria:
        if c not in result_summary:
            report.missing_evidence.append(f"criterion not evidenced: {c}")
    if warnings:
        report.edge_cases_missed.extend(f"warning unaddressed: {w}"
                                        for w in warnings)
        report.verdict = "concerns"
    low_words = ("maybe", "probably", "should work", "untested", "assumed")
    if any(w in result_summary.lower() for w in low_words):
        report.assumptions.append("summary contains hedged/unverified language")
        report.verdict = "concerns"
    if not report.missing_evidence and not report.edge_cases_missed \
            and not report.assumptions:
        report.verdict = "pass"
    return report


@dataclass
class LayeredConfidence:
    """P30 — confidence tracked separately per layer."""

    result: float = 0.0        # producing agent's own claim
    evidence: float = 0.0      # strength of attached artifacts/citations
    verification: float = 0.0  # independent verification strength
    conclusion: float = 0.0    # final composed confidence

    def compose(self) -> float:
        """Conclusion is gated by the weakest chain link but lifted by the
        strongest; never exceeds min(result+evidence) when verification=0."""
        base = min(self.result, self.evidence) if self.evidence else \
            self.result * 0.5
        if self.verification:
            self.conclusion = round(min(1.0, (base + self.verification) / 2 * 1.2), 3)
        else:
            self.conclusion = round(base * 0.7, 3)
        return self.conclusion


@dataclass
class CandidateResult:
    agent_id: str
    answer: str
    key_facts: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class ConsensusVerdict:
    outcome: ConsensusOutcome
    agreement_ratio: float
    agreeing_agents: List[str]
    dissenting_agents: List[str]
    details: str


def compare_results(candidates: Sequence[CandidateResult],
                    *, fact_agreement_threshold: float = 0.5) -> ConsensusVerdict:
    """P28 — compare independent answers. Never forces consensus.

    Facts are matched on normalized substring containment so equivalent
    phrasings count as agreement.
    """
    if len(candidates) < 2:
        return ConsensusVerdict(
            outcome=ConsensusOutcome.INSUFFICIENT_EVIDENCE,
            agreement_ratio=0.0,
            agreeing_agents=[c.agent_id for c in candidates],
            dissenting_agents=[],
            details="fewer than two candidates",
        )

    def norm(s: str) -> str:
        return " ".join(s.lower().split())

    # pairwise fact overlap
    n = len(candidates)
    pair_scores: List[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            fi = {norm(f) for f in candidates[i].key_facts}
            fj = {norm(f) for f in candidates[j].key_facts}
            if not fi and not fj:
                overlap = 1.0
            elif not fi or not fj:
                overlap = 0.0
            else:
                contained = sum(1 for f in fi if any(f in g or g in f for g in fj))
                overlap = contained / max(len(fi), len(fj))
            pair_scores.append(overlap)

    ratio = sum(pair_scores) / len(pair_scores) if pair_scores else 0.0

    # direct answer contradiction check
    answers = {norm(c.answer) for c in candidates}
    direct_conflict = len(answers) > 1 and ratio < fact_agreement_threshold

    if direct_conflict:
        outcome = ConsensusOutcome.DISAGREEMENT
    elif ratio >= fact_agreement_threshold:
        outcome = ConsensusOutcome.AGREEMENT
    elif ratio > 0:
        outcome = ConsensusOutcome.PARTIAL_AGREEMENT
    else:
        outcome = ConsensusOutcome.DISAGREEMENT

    majority_agent = max(candidates, key=lambda c: c.confidence).agent_id
    agreeing = [c.agent_id for c in candidates
                if outcome is not ConsensusOutcome.DISAGREEMENT
                or c.agent_id == majority_agent]
    dissenting = [c.agent_id for c in candidates if c.agent_id not in agreeing]

    details = {
        "pair_overlap": [round(x, 2) for x in pair_scores],
        "distinct_answers": sorted(answers),
    }
    return ConsensusVerdict(
        outcome=outcome,
        agreement_ratio=round(ratio, 3),
        agreeing_agents=agreeing,
        dissenting_agents=dissenting,
        details=str(details),
    )


@dataclass
class DisagreementPlan:
    """P29 — next steps when agents disagree (data, not authority)."""

    collect_more_evidence: bool = False
    run_independent_verification: bool = False
    request_additional_research: bool = False
    escalate_to_user: bool = False
    notes: List[str] = field(default_factory=list)

    @classmethod
    def for_verdict(cls, verdict: ConsensusVerdict,
                    *, high_risk: bool = False) -> "DisagreementPlan":
        plan = cls()
        if verdict.outcome is ConsensusOutcome.DISAGREEMENT:
            plan.collect_more_evidence = True
            plan.run_independent_verification = True
            plan.request_additional_research = True
            plan.notes.append("compare assumptions between dissenting agents")
            if high_risk or verdict.agreement_ratio < 0.2:
                plan.escalate_to_user = True
        elif verdict.outcome is ConsensusOutcome.PARTIAL_AGREEMENT:
            plan.run_independent_verification = True
            plan.notes.append("verify the disputed subset only")
        elif verdict.outcome is ConsensusOutcome.INSUFFICIENT_EVIDENCE:
            plan.collect_more_evidence = True
            plan.notes.append("candidates too thin to compare")
        return plan
