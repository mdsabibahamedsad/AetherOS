"""Improvement proposal engine (P61-66): evidence-backed proposals,
SAFE_AUTO_FIX allowlist, mandatory rollback, human approval for anything
beyond the allowlist. Self-improvement NEVER autonomously applies
high-risk/production changes (P21-25, P62-63).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from agent.quality.models import (
    SAFE_AUTO_FIX_KINDS,
    ChangeProposal,
    ChangeRisk,
    KnownIssue,
)


class UnsafeAutoApply(Exception):
    """P62/P63 — attempt to autonomously apply a non-allowlisted change."""


@dataclass
class FailureSignal:
    kind: str                     # repeated_failure | bottleneck | test_failure | security_finding | reliability
    component: str
    count: int
    last_message: str
    evidence_refs: List[str] = field(default_factory=list)


class ProposalEngine:
    """Derives proposals from signals; applies ONLY allowlisted safe fixes."""

    def __init__(self, safe_actions: Optional[Dict[str, Callable[[ChangeProposal], str]]] = None):
        # action registry: kind -> executor; only SAFE_AUTO_FIX_KINDS allowed
        self.safe_actions: Dict[str, Callable[[ChangeProposal], str]] = {
            k: v for k, v in (safe_actions or {}).items()
            if k in SAFE_AUTO_FIX_KINDS
        }

    # -- P61 derivation ---------------------------------------------------------

    def from_signals(self, signals: List[FailureSignal]) -> List[ChangeProposal]:
        proposals: List[ChangeProposal] = []
        for s in signals:
            if s.kind == "repeated_failure" and s.count >= 3:
                proposals.append(ChangeProposal(
                    description=f"Diagnose and fix recurring failure in {s.component}",
                    reason=f"{s.count} repetitions; last: {s.last_message[:140]}",
                    components=[s.component],
                    expected_benefit="eliminate recurring failure class",
                    evidence=s.evidence_refs or [f"signal:{s.kind}:{s.component}:x{s.count}"],
                    rollback_plan="revert fix commit; re-run component regression suite",
                    author="quality-engine",
                ))
            elif s.kind == "bottleneck" and s.count >= 2:
                proposals.append(ChangeProposal(
                    description=f"Performance bottleneck in {s.component}",
                    reason=f"observed {s.count}x; {s.last_message[:140]}",
                    components=[s.component],
                    expected_benefit="latency/cost reduction",
                    evidence=s.evidence_refs or [f"signal:bottleneck:{s.component}"],
                    rollback_plan="revert optimization; baseline metrics recorded",
                    author="quality-engine",
                ))
            elif s.kind == "security_finding":
                p = ChangeProposal(
                    description=f"Security finding in {s.component}",
                    reason=s.last_message[:200],
                    components=[s.component, "security"],
                    expected_benefit="close security gap",
                    evidence=s.evidence_refs or [f"signal:security:{s.component}"],
                    rollback_plan="revert remediation patch under review supervision",
                    author="security-review",
                )
                proposals.append(p)
        return proposals

    def from_known_issue(self, issue: KnownIssue,
                         evidence: List[str]) -> ChangeProposal:
        return ChangeProposal(
            description=f"Resolve known issue: {issue.title}",
            reason=f"known issue {issue.issue_id} ({issue.severity})",
            components=["general"],
            expected_benefit="close known issue",
            evidence=evidence or [f"known-issue:{issue.issue_id}"],
            rollback_plan="revert resolution; issue re-opens in knowledge base",
            author="quality-engine",
        )

    # -- P63 safe auto-fix --------------------------------------------------------

    def auto_applicable(self, proposal: ChangeProposal) -> bool:
        return (proposal.risk is ChangeRisk.TRIVIAL
                and proposal.auto_applicable
                and proposal.description.split(":")[0].strip().lower()
                in {k.replace("_", " ") for k in SAFE_AUTO_FIX_KINDS}
                ) or (
                proposal.auto_applicable
                and proposal.description.lower().startswith(
                    tuple(k.replace("_", " ") for k in SAFE_AUTO_FIX_KINDS))
                and proposal.risk in (ChangeRisk.TRIVIAL, ChangeRisk.LOW)
            )

    def apply(self, proposal: ChangeProposal) -> str:
        """Execute ONLY allowlisted safe fixes; anything else raises."""
        kind = self._match_safe_kind(proposal)
        if kind is None or proposal.requires_human_approval:
            raise UnsafeAutoApply(
                f"refusing autonomous application: risk={proposal.risk.value} "
                f"kind={kind or 'unrecognized'}; human approval required (P62)"
            )
        action = self.safe_actions[kind]
        return action(proposal)

    def _match_safe_kind(self, proposal: ChangeProposal) -> Optional[str]:
        low = proposal.description.lower()
        for k in sorted(SAFE_AUTO_FIX_KINDS, key=len, reverse=True):
            if low.startswith(k.replace("_", " ")) or \
                    low.startswith(k) or f"{k}:" in low:
                if k in self.safe_actions:
                    return k
        return None
