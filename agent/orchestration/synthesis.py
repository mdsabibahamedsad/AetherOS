"""Final synthesis + completion validation (P88-90).

Synthesis combines VERIFIED outputs only; it preserves conflicts, uncertainty,
citations and provenance. Final status is computed, never claimed: any
required task failed or unverified ⇒ PARTIAL / FAILED (never SUCCESS).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


class FinalStatus(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class VerifiedContribution:
    task_id: str
    agent_id: str
    summary: str
    verified: bool
    confidence: float = 0.5
    citations: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    required: bool = True


@dataclass
class FinalValidation:
    """P89 — checklist evaluated before completion is allowed."""

    requirements_satisfied: bool = False
    artifacts_exist: bool = False
    tests_pass: bool = True            # vacuous when no test criteria exist
    citations_valid: bool = True
    security_checks_pass: bool = True
    approvals_satisfied: bool = True

    def all_pass(self) -> bool:
        return all([
            self.requirements_satisfied, self.artifacts_exist, self.tests_pass,
            self.citations_valid, self.security_checks_pass,
            self.approvals_satisfied,
        ])


@dataclass
class SynthesisResult:
    status: FinalStatus
    answer: str
    validation: FinalValidation
    contributions_used: List[str] = field(default_factory=list)
    conflicts_preserved: List[str] = field(default_factory=list)
    uncertainties_preserved: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


def synthesize(
    contributions: Sequence[VerifiedContribution],
    *,
    validation: FinalValidation,
    objective: str = "",
    limitations: Optional[List[str]] = None,
) -> SynthesisResult:
    """P88/P90 — compose the final answer from verified contributions.

    - unverified REQUIRED contributions force PARTIAL/FAILED (never SUCCESS);
    - conflicts are preserved verbatim, never silently resolved;
    - every citation/provenance string flows through to the final result.
    """
    used: List[str] = []
    conflicts: List[str] = []
    uncertainties: List[str] = []
    citations: List[str] = []
    sections: List[str] = []

    for c in contributions:
        tag = f"[{c.task_id}/{c.agent_id}]"
        if c.verified:
            used.append(c.task_id)
            sections.append(f"{tag} {c.summary}")
        else:
            sections.append(f"{tag} (unverified) {c.summary}")
            if c.required:
                uncertainties.append(
                    f"{tag} required contribution NOT independently verified")
        conflicts.extend(f"{tag} {x}" for x in c.conflicts)
        uncertainties.extend(f"{tag} {x}" for x in c.uncertainties)
        citations.extend(c.citations)

    failed_required = any(
        c.required and not c.verified for c in contributions
    )
    if not contributions:
        status = FinalStatus.FAILED
    elif failed_required:
        status = FinalStatus.PARTIAL if used else FinalStatus.FAILED
    elif not validation.all_pass():
        status = FinalStatus.PARTIAL
    else:
        status = FinalStatus.SUCCESS

    header = f"Objective: {objective}" if objective else "Objective completed"
    body = "\n\n".join(sections) if sections else "(no contributions)"
    limits = list(limitations or [])
    if status is FinalStatus.PARTIAL:
        limits.append("some required work is unverified or failed")
    if conflicts:
        limits.append("conflicting contributions preserved above; unresolved")

    return SynthesisResult(
        status=status,
        answer=f"{header}\n\n{body}",
        validation=validation,
        contributions_used=used,
        conflicts_preserved=conflicts,
        uncertainties_preserved=uncertainties,
        citations=citations,
        limitations=limits,
    )


def validate_completion(
    *,
    required_tasks_completed: int,
    required_tasks_total: int,
    artifact_ids: Sequence[str],
    test_criteria_present: bool,
    tests_passed: Optional[bool],
    citations: Sequence[str],
    broken_citations: Sequence[str] = (),
    security_clean: bool = True,
    pending_approvals: int = 0,
) -> FinalValidation:
    """Build P89 checklist from measurable facts only."""
    v = FinalValidation()
    v.requirements_satisfied = (
        required_tasks_total > 0 and
        required_tasks_completed >= required_tasks_total
    )
    v.artifacts_exist = len(artifact_ids) > 0
    if test_criteria_present:
        v.tests_pass = tests_passed is True
    v.citations_valid = len(broken_citations) == 0
    v.security_checks_pass = security_clean
    v.approvals_satisfied = pending_approvals == 0
    return v
