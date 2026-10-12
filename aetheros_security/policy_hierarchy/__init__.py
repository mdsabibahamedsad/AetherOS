"""
Policy Priority Hierarchy for AetherOS
======================================

Deterministic ordering of layered security policies and safe, non-revealing
explanations for denied actions (master security spec steps 52-53).

Policy hierarchy (highest wins)::

    SYSTEM SECURITY
        ↓
    ORGANIZATION / WORKSPACE POLICY
        ↓
    USER POLICY
        ↓
    MISSION POLICY
        ↓
    AGENT POLICY
        ↓
    TASK POLICY
        ↓
    MODEL SUGGESTION        (never a security authority)

Lower layers can NEVER override a higher-layer decision. This module resolves
a list of per-layer decisions into a single authoritative decision.

Usage::

    from aetheros_security.policy_hierarchy import (
        PolicyLayer, resolve_layer_decisions, safe_explanation,
    )

    decision = resolve_layer_decisions([
        (PolicyLayer.SYSTEM, "DENY"),
        (PolicyLayer.AGENT, "ALLOW"),   # overridden by SYSTEM
    ])                                   # -> DENY

    message = safe_explanation("DENY", "agent lacks filesystem.write permission")
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PolicyLayer(Enum):
    """Ordered security-policy layers (highest authority first)."""
    SYSTEM = 0
    ORGANIZATION = 1
    USER = 2
    MISSION = 3
    AGENT = 4
    TASK = 5
    MODEL = 6


#: Canonical decision values understood by the hierarchy resolver.
_ALLOW_DECISIONS = {"allow", "ALLOW", True}
_DENY_DECISIONS = {"deny", "DENY", False}


class PolicyHierarchyError(Exception):
    """Raised for invalid hierarchy inputs."""


def resolve_layer_decisions(
    layered: List[Tuple[PolicyLayer, Any]],
    *,
    default: str = "deny",
) -> Dict[str, Any]:
    """Resolve a list of ``(layer, decision)`` pairs into one outcome.

    The highest-priority layer that expresses an explicit decision wins.
    Lower layers cannot override it. When no layer expresses an explicit
    decision, ``default`` (deny by default) is returned.

    Args:
        layered: Ordered decision pairs from lowest to highest authority.
        default: Fallback decision ("allow" or "deny").

    Returns:
        dict with ``decision``, ``deciding_layer``, and ``overridden`` list.
    """
    # Sort by layer ascending authority so the highest authority is first.
    resolved = sorted(layered, key=lambda pair: pair[0].value)
    decision: Optional[str] = None
    deciding_layer: Optional[PolicyLayer] = None
    overridden: List[str] = []

    for layer, value in resolved:
        explicit = None
        if value in _ALLOW_DECISIONS:
            explicit = "allow"
        elif value in _DENY_DECISIONS:
            explicit = "deny"
        if explicit is None:
            continue  # unknown values carry no authority
        if decision is None:
            # First (highest-authority) explicit decision wins.
            decision = explicit
            deciding_layer = layer
        elif explicit != decision:
            overridden.append(f"{layer.value}:{explicit}")

    if decision is None:
        decision = default
        deciding_layer = None

    return {
        "decision": decision,
        "deciding_layer": deciding_layer.value if deciding_layer else None,
        "overridden": overridden,
        "layers_considered": [l.value for l, _ in resolved],
    }


def resolve_bool(layered: List[Tuple[PolicyLayer, bool]], *,
                 default: bool = False) -> Tuple[bool, Optional[PolicyLayer]]:
    """Convenience wrapper resolving layered booleans into (result, layer)."""
    result = resolve_layer_decisions(layered, default="deny" if not default else "allow")
    deciding = result["deciding_layer"]
    # ``deciding`` may be 0 (SYSTEM), which is falsy — compare against None.
    return result["decision"] == "allow", (
        PolicyLayer(deciding) if deciding is not None else None)


# ---------------------------------------------------------------------------
# Safe explanations
# ---------------------------------------------------------------------------

#: Phrases that are safe to surface to users. Never expose policy internals.
_SAFE_REASONS = {
    "default deny": "This action is not explicitly permitted.",
    "emergency stop active": "Security controls are active; privileged actions are halted.",
    "account lockdown active": "The account is locked down; sensitive actions are blocked.",
    "principal not active": "The requester identity is not active.",
    "action outside session scope": "This action is outside the session's permitted scope.",
    "denied by rule": "A security policy denies this action.",
    "allowed by rule": "A security policy permits this action.",
    "high risk action": "This action is high-risk and requires approval.",
    "critical risk action": "This action is critical-risk and requires approval.",
    "approval rule": "This action requires explicit approval.",
    "secret data cannot leave": "Secret data is not permitted to leave the system.",
    "sensitive data to external destination": "Sensitive data is not permitted to an external destination.",
    "private data to external destination": "Private data is not permitted to an external destination.",
}


def safe_explanation(decision: str, reason: str = "", *, include_internal: bool = False) -> str:
    """Produce a safe explanation for a decision.

    Never exposes sensitive internal policy data. When ``include_internal``
    is False, only the user-safe message is returned.

    Args:
        decision: "allow" / "deny" / "approval" / "challenge".
        reason: Internal reason string (may be shown only if allowed).
        include_internal: Whether to append the raw internal reason.

    Returns:
        A safe, human-readable explanation.
    """
    reason = reason or ""
    safe = _SAFE_REASONS.get(reason) or _SAFE_REASONS.get(reason.lower())

    if decision in ("allow", "ALLOW"):
        base = "Action permitted."
    elif decision in ("approval", "REQUIRE_APPROVAL"):
        base = "Action requires explicit human approval."
    elif decision in ("challenge", "CHALLENGE"):
        base = "Additional verification is required."
    else:
        base = "Action denied."
        if safe:
            return f"DENIED because: {safe}"
        return base

    if safe:
        return f"{base} {safe}"
    return base


class PolicyHierarchyManager:
    """Evaluates layered policy decisions with safe explanations.

    Usage::

        phm = PolicyHierarchyManager()
        outcome = phm.evaluate([
            (PolicyLayer.SYSTEM, "allow"),
            (PolicyLayer.AGENT, "deny"),
        ], reason="agent lacks filesystem.write permission")
        # outcome["decision"] == "allow"  (SYSTEM wins)
    """

    def __init__(self) -> None:
        self._policies: Dict[PolicyLayer, Any] = {}

    def set_layer(self, layer: PolicyLayer, decision: Any) -> None:
        """Set an explicit decision for a policy layer."""
        self._policies[layer] = decision

    def unset_layer(self, layer: PolicyLayer) -> bool:
        if layer in self._policies:
            del self._policies[layer]
            return True
        return False

    def evaluate(self, extra: Optional[List[Tuple[PolicyLayer, Any]]] = None,
                 *, reason: str = "", default: str = "deny") -> Dict[str, Any]:
        """Evaluate configured layers (plus optional extra pairs) and explain."""
        layered = [(layer, decision) for layer, decision in self._policies.items()]
        if extra:
            layered.extend(extra)
        result = resolve_layer_decisions(layered, default=default)
        result["explanation"] = safe_explanation(result["decision"], reason)
        return result

    def allow(self, principal: str, action: str, resource: str = "",
              extra: Optional[List[Tuple[PolicyLayer, Any]]] = None) -> bool:
        """Convenience: evaluate and return whether the action is allowed."""
        outcome = self.evaluate(extra, reason=f"principal {principal} {action}")
        return outcome["decision"] == "allow"


# Global policy hierarchy manager
_policy_hierarchy_manager: PolicyHierarchyManager | None = None


def get_policy_hierarchy_manager() -> PolicyHierarchyManager:
    """Return the global PolicyHierarchyManager singleton."""
    global _policy_hierarchy_manager
    if _policy_hierarchy_manager is None:
        _policy_hierarchy_manager = PolicyHierarchyManager()
    return _policy_hierarchy_manager