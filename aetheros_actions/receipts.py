"""Action receipts (Step 63).

A receipt is the durable, correlated record of one executed action: what was
requested, what decision was made, whether it ran, how verification went,
how long it took, and how it failed. Receipts are derived *after* execution
from the pipeline outputs (decision + result + verification) — they never
re-execute anything.

``run_receipts`` builds one receipt per step from a
:class:`~aetheros_actions.manager.RunReport`, giving an end-to-end audit
trail correlated by ``trace_id``.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_actions.model import Action, FailureKind
from aetheros_actions.reversibility import classify_reversibility


def _new_receipt_id() -> str:
    return uuid.uuid4().hex


@dataclass
class ActionReceipt:
    """Durable record of one action's lifecycle."""

    receipt_id: str = field(default_factory=_new_receipt_id)
    action_id: str = ""
    trace_id: str = ""
    agent_id: str = ""
    session_id: str = ""
    action_type: str = ""
    target: str = ""
    decision: str = ""
    ok: bool = False
    verification_verdict: str = ""
    failure_kind: str = FailureKind.UNKNOWN.value
    reversibility: str = ""
    started_at: float = field(default_factory=time.time)
    elapsed_ms: float = 0.0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "receiptId": self.receipt_id,
            "actionId": self.action_id,
            "traceId": self.trace_id,
            "agentId": self.agent_id,
            "sessionId": self.session_id,
            "actionType": self.action_type,
            "target": self.target,
            "decision": self.decision,
            "ok": self.ok,
            "verification": self.verification_verdict,
            "failureKind": self.failure_kind,
            "reversibility": self.reversibility,
            "startedAt": self.started_at,
            "elapsedMs": round(self.elapsed_ms, 3),
            "message": self.message,
        }


def build_receipt(
    action: Action,
    *,
    decision: str = "",
    ok: bool = False,
    verification_verdict: str = "",
    error: str = "",
    elapsed_ms: float = 0.0,
    trace_id: str = "",
    started_at: Optional[float] = None,
) -> ActionReceipt:
    """Build a receipt from an action + pipeline outcomes (no execution)."""
    from aetheros_actions.failure import classify_failure
    return ActionReceipt(
        action_id=action.action_id,
        trace_id=trace_id or action.trace_id,
        agent_id=action.agent_id,
        session_id=action.session_id,
        action_type=action.action_type.value,
        target=action.target,
        decision=decision,
        ok=bool(ok),
        verification_verdict=verification_verdict,
        failure_kind=classify_failure(error, action=action).value if not ok else FailureKind.UNKNOWN.value,
        reversibility=classify_reversibility(action).value,
        started_at=started_at if started_at is not None else time.time(),
        elapsed_ms=elapsed_ms,
        message=error or "",
    )


def run_receipts(report) -> List[ActionReceipt]:
    """Build one receipt per step from a ``RunReport``.

    ``report`` is any object with ``steps`` (each exposing ``action``,
    ``decision.decision.value``, ``result.ok``, ``verification.verdict``,
    ``result.elapsed_ms``, ``result.error``) and ``session_id`` / ``trace_id``.
    """
    receipts: List[ActionReceipt] = []
    trace_id = getattr(report, "trace_id", "") or ""
    for step in getattr(report, "steps", []) or []:
        action = step.action
        decision = getattr(step.decision, "decision", None)
        decision = getattr(decision, "value", decision) if decision is not None else ""
        result = step.result
        verification = getattr(step, "verification", None)
        verdict = getattr(verification, "verdict", None)
        verdict = getattr(verdict, "value", verdict) if verdict is not None else ""
        receipts.append(build_receipt(
            action,
            decision=str(decision),
            ok=bool(getattr(result, "ok", False)),
            verification_verdict=str(verdict),
            error=getattr(result, "error", "") or "",
            elapsed_ms=float(getattr(result, "elapsed_ms", 0.0) or 0.0),
            trace_id=trace_id,
        ))
    return receipts