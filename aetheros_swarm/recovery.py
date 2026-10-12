"""Failure recovery (sections 40-42): typed failures -> strategies.

Strategy table keyed by FailureKind; idempotency keys
(task_id + action_id via SwarmTask.ensure_idempotency_key) prevent
duplicate side effects on retry/reassign. Recovery never replays
destructive actions blindly: reduce_scope/human_escalation win there.
"""

from __future__ import annotations

from typing import Any, Dict, List

from aetheros_swarm.models import FailureKind, SideEffectTier

STRATEGY_TABLE: Dict[FailureKind, List[str]] = {
    FailureKind.MODEL_FAILURE: ["fallback_model", "retry", "reassign"],
    FailureKind.TOOL_FAILURE: ["retry", "reassign", "reduce_scope"],
    FailureKind.NETWORK_FAILURE: ["retry", "replan", "human_escalation"],
    FailureKind.TIMEOUT: ["retry", "reduce_scope", "reassign"],
    FailureKind.CONTEXT_OVERFLOW: ["reduce_scope", "replan"],
    FailureKind.PERMISSION_DENIED: ["human_escalation", "terminate"],
    FailureKind.INVALID_OUTPUT: ["retry", "reassign", "replan"],
    FailureKind.VERIFICATION_FAILURE: ["retry", "replan", "human_escalation"],
    FailureKind.DEPENDENCY_FAILURE: ["replan", "parallel_recovery", "human_escalation"],
    FailureKind.RESOURCE_EXHAUSTED: ["reduce_scope", "terminate", "human_escalation"],
    FailureKind.SECURITY_BLOCK: ["terminate", "human_escalation"],
}


def classify_error(error: str) -> FailureKind:
    low = (error or "").lower()
    if "timeout" in low or "timed out" in low:
        return FailureKind.TIMEOUT
    if "permission" in low or "denied" in low or "unauthorized" in low:
        return FailureKind.PERMISSION_DENIED
    if "rate limit" in low or "429" in low or "quota" in low:
        return FailureKind.RESOURCE_EXHAUSTED
    if "network" in low or "connection" in low or "dns" in low:
        return FailureKind.NETWORK_FAILURE
    if "context" in low and ("length" in low or "overflow" in low or "too long" in low):
        return FailureKind.CONTEXT_OVERFLOW
    if "model" in low or "provider" in low or "api" in low:
        return FailureKind.MODEL_FAILURE
    if "verif" in low or "assertion" in low or "mismatch" in low:
        return FailureKind.VERIFICATION_FAILURE
    if "security" in low or "blocked" in low or "injection" in low:
        return FailureKind.SECURITY_BLOCK
    if "tool" in low:
        return FailureKind.TOOL_FAILURE
    return FailureKind.TOOL_FAILURE


def plan_recovery(kind: FailureKind, *, tier: SideEffectTier,
                  retry_count: int, max_retries: int) -> Dict[str, Any]:
    strategies = list(STRATEGY_TABLE.get(kind, ["retry", "human_escalation"]))
    if tier == SideEffectTier.DESTRUCTIVE:
        # Never blind-retry destructive actions.
        strategies = [s for s in strategies if s not in ("retry", "parallel_recovery")]
        if "human_escalation" not in strategies:
            strategies.append("human_escalation")
    if retry_count >= max_retries and "retry" in strategies:
        strategies.remove("retry")
        if "reassign" not in strategies:
            strategies.append("reassign")
    chosen = strategies[0] if strategies else "terminate"
    return {"strategy": chosen, "candidates": strategies,
            "idempotent_retry": chosen in ("retry", "reassign", "parallel_recovery")}
