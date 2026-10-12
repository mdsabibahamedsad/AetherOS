"""Dry-run / action preview (Steps 58, 60).

Produces a human-readable and machine-checkable preview of what a plan
*would* do without executing anything. Every preview path is pure — it reads
only the plan/action records and the deterministic classifiers
(reversibility, risk, blast radius) — so it is safe to call on any input,
including untrusted model output.

The manager wires this behind ``dry_run=True`` on :meth:`run_plan`; nothing
changes for callers that never pass it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_actions.blast_radius import BlastRadiusEstimate, estimate_blast_radius
from aetheros_actions.model import Action, RiskLevel
from aetheros_actions.reversibility import classify_reversibility


@dataclass
class DryRunImpact:
    """Preview of a single action's effects (no execution)."""

    action_type: str
    target: str
    risk_level: str
    reversibility: str
    permission: str = ""
    blast_radius: BlastRadiusEstimate = field(default_factory=BlastRadiusEstimate)

    @property
    def irreversible(self) -> bool:
        from aetheros_actions.model import Reversibility
        return self.reversibility == Reversibility.IRREVERSIBLE.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actionType": self.action_type,
            "target": self.target,
            "riskLevel": self.risk_level,
            "reversibility": self.reversibility,
            "permission": self.permission,
            "blastRadius": self.blast_radius.to_dict(),
        }


@dataclass
class PlanPreview:
    """Preview of a whole plan (Step 60)."""

    goal: str
    impacts: List[DryRunImpact] = field(default_factory=list)
    destructive_count: int = 0
    irreversible_count: int = 0
    high_risk_count: int = 0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "impact": [i.to_dict() for i in self.impacts],
            "destructive_count": self.destructive_count,
            "irreversible_count": self.irreversible_count,
            "high_risk_count": self.high_risk_count,
            "message": self.message,
        }


def action_dry_run(action: Action) -> DryRunImpact:
    """Preview one action without executing it."""
    reversibility = classify_reversibility(action)
    return DryRunImpact(
        action_type=action.action_type.value,
        target=action.target,
        risk_level=action.risk_level.value,
        reversibility=reversibility.value,
        permission=action.permission,
        blast_radius=estimate_blast_radius(action),
    )


def plan_dry_run(goal: str, actions: List[Action]) -> PlanPreview:
    """Preview a full plan (list of :class:`Action`) without executing it."""
    impacts = [action_dry_run(a) for a in actions]
    destructive = [i for i in impacts if i.risk_level not in (RiskLevel.LOW.value,)]
    preview = PlanPreview(
        goal=goal,
        impacts=impacts,
        destructive_count=sum(1 for i in impacts if i.risk_level != RiskLevel.LOW.value),
        irreversible_count=sum(1 for i in impacts if i.irreversible),
        high_risk_count=sum(
            1 for i in impacts if i.risk_level in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value)
        ),
    )
    preview.message = _summarize_preview(preview)
    return preview


def _summarize_preview(preview: PlanPreview) -> str:
    parts: List[str] = []
    if not preview.impacts:
        return "dry-run preview: plan is empty — nothing would be executed"
    parts.append(
        f"dry-run preview: {len(preview.impacts)} step(s) would run"
    )
    if preview.irreversible_count:
        parts.append(f"{preview.irreversible_count} irreversible")
    if preview.high_risk_count:
        parts.append(f"{preview.high_risk_count} high/CRITICAL risk")
    if preview.destructive_count:
        parts.append(f"{preview.destructive_count} mutating")
    return ", ".join(parts) + " (no changes made)"