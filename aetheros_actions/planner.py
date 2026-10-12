"""ActionPlanner — goal → explicit executable steps (Steps 16, 36).

Converts a user goal into an ordered list of :class:`Action` records that
already carry risk classification, expected results and verification
strategies. The planner:

* detects high-impact steps and inserts an explicit confirmation boundary;
* never skips verification — every mutating plan step gets an
  ``expected_result`` and a ``verification_strategy``;
* refuses to plan when external (web/document) content is the *source* of
  the goal, treating it as untrusted data rather than instructions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_actions.model import Action, ActionType, RiskLevel, TrustSource
from aetheros_actions.risk import classify_action
from aetheros_actions.trust import TrustedInstruction, classify_text, is_instruction_source


# Planning is allowed from the trusted lineage: user instructions, security/
# system policy, and agent plans derived from them. External content
# (web/documents/model output) can never be the *source* of an actionable
# plan — it is untrusted data.
_PLANNABLE_SOURCES = {
    TrustSource.USER_INSTRUCTION,
    TrustSource.SECURITY_POLICY,
    TrustSource.SYSTEM_INSTRUCTION,
    TrustSource.AGENT_PLAN,
}


@dataclass
class PlanVerdict:
    """Outcome of building a plan."""

    ok: bool
    actions: List[Action] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confirmation_boundaries: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "action_count": len(self.actions),
            "warnings": self.warnings,
            "confirmation_boundaries": self.confirmation_boundaries,
            "steps": [a.to_dict() for a in self.actions],
        }


class ActionPlanner:
    """Validates + enriches a proposed action sequence."""

    def __init__(self, verify_every_mutation: bool = True) -> None:
        self.verify_every_mutation = verify_every_mutation

    # ── public API ───────────────────────────────────────────────────

    def plan(
        self,
        goal: str,
        steps: List[Dict[str, Any]],
        *,
        agent_id: str = "",
        session_id: str = "",
        source: TrustSource = TrustSource.USER_INSTRUCTION,
    ) -> PlanVerdict:
        """Build an executable plan from ``goal`` + structured ``steps``.

        Each step dict: ``{"action": "CLICK"|"...", "target": str,
        "parameters": {...}, "reason": str, "expected_result": {...},
        "verification_strategy": str}``.
        """
        instruction = classify_text(goal, source)
        return self.plan_instruction(instruction, steps, agent_id=agent_id,
                                     session_id=session_id)

    def plan_instruction(
        self,
        instruction: TrustedInstruction,
        steps: List[Dict[str, Any]],
        *,
        agent_id: str = "",
        session_id: str = "",
    ) -> PlanVerdict:
        if instruction.source not in _PLANNABLE_SOURCES:
            return PlanVerdict(
                ok=False,
                warnings=[
                    "refusing to plan from a non-instruction source "
                    f"({instruction.source.value})",
                    *[f.to_dict()["signal"] for f in instruction.findings],
                ],
            )
        if instruction.findings:
            return PlanVerdict(
                ok=False,
                warnings=[
                    "goal matches prompt-injection signature; not planned as a command"
                ],
            )
        actions: List[Action] = []
        boundaries: List[int] = []
        warnings: List[str] = []
        for i, raw in enumerate(steps):
            try:
                atype = ActionType(raw.get("action", "").upper())
            except ValueError:
                warnings.append(f"step {i}: unknown action "
                                f"{raw.get('action')!r}; skipped")
                continue
            action = Action(
                action_type=atype,
                target=str(raw.get("target", "")),
                parameters=dict(raw.get("parameters") or {}),
                reason=str(raw.get("reason", "")),
                agent_id=agent_id,
                session_id=session_id,
                source=instruction.source,
                expected_result=dict(raw.get("expected_result") or {}),
                verification_strategy=str(raw.get("verification_strategy", "")),
                idempotency_key=str(raw.get("idempotency_key", "")),
            )
            action.risk_level = classify_action(action)
            if not action.expected_result and self.verify_every_mutation and action.risk_level > RiskLevel.LOW:
                warnings.append(
                    f"step {i}: mutating action has no expected_result; "
                    "verification will be treated as FAIL on timeout"
                )
            if action.risk_level >= RiskLevel.HIGH:
                boundaries.append(len(actions))  # confirmation boundary index
            actions.append(action)
        return PlanVerdict(ok=True, actions=actions, warnings=warnings,
                           confirmation_boundaries=boundaries)