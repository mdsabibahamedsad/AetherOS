"""Per-action authorization (Steps 14, 44).

Every action is evaluated as: ALLOW / DENY / REQUIRE_CONFIRMATION.

``PermissionManager`` is the policy engine: it combines the action's
:class:`~aetheros_actions.model.RiskLevel`, the run's **autonomy level**
(Step 44), the :class:`SafetyPolicy` rules, and the trust source of the
request.

A complete workflow is approved action-by-action only — approving the first
action never authorizes the rest of the plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from aetheros_actions.model import Action, RiskLevel, TrustSource
from aetheros_actions.risk import allowed_max_risk
from aetheros_actions.safety import SafetyPolicy


class AutonomyLevel(int, Enum):
    """Configurable autonomy levels (Step 44).

    Higher levels must never bypass the security policy — CRITICAL actions
    always require confirmation, no matter the level.
    """

    OBSERVE_ONLY = 0      # observe, never act
    SUGGEST_ONLY = 1      # suggest actions, never act
    LOW_RISK_AUTO = 2     # execute LOW-risk actions autonomously
    APPROVED_WORKFLOWS = 3  # execute pre-approved/repeatable workflows
    SAFE_AUTONOMOUS = 4   # autonomous multi-step with safeguards
    RESTRICTED_FULL = 5   # full automation under policy safeguards

    @property
    def label(self) -> str:
        return self.name.lower().replace("_", " ")


class PermissionDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"


@dataclass
class Decision:
    """Outcome of authorizing one action."""

    decision: PermissionDecision
    action: Action
    reason: str = ""
    required_permission: str = ""

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "action_id": self.action.action_id,
            "action_type": self.action.action_type.value,
            "risk_level": self.action.risk_level.value,
            "reason": self.reason,
            "required_permission": self.required_permission,
        }


# Actions that are never defensible as web/document-initiated commands.
_MANDATORY_CONFIRMATION_TYPES = frozenset({
    "purchase", "transfer", "delete", "submit", "send", "publish",
})


class PermissionManager:
    """Authorizes actions against autonomy + risk + trust + safety.

    ``confirm_callback`` (optional) is invoked for REQUIRE_CONFIRMATION
    decisions; it receives the :class:`Decision` and returns True to allow.
    When absent and a confirmation is required, the decision defaults to
    DENY (fail closed).
    """

    def __init__(
        self,
        confirm_callback: Optional[Callable[[Decision], bool]] = None,
        safety_policy: Optional[SafetyPolicy] = None,
        external_action_always_blocked: bool = True,
    ) -> None:
        self.confirm_callback = confirm_callback
        self.safety_policy = safety_policy or SafetyPolicy()
        # Web/doc-initiated mutating actions are blocked at the policy level.
        self.external_action_always_blocked = external_action_always_blocked

    # ── main entry ───────────────────────────────────────────────────

    def authorize(self, action: Action, autonomy: AutonomyLevel) -> Decision:
        """Evaluate ``action`` against ``autonomy`` and return a decision.

        ``authorize`` is *raw*: it returns ALLOW / DENY / REQUIRE_CONFIRMATION
        without invoking the confirmation UI. The caller resolves a
        REQUIRE_CONFIRMATION decision through :meth:`confirm`. This keeps the
        policy engine pure and the confirmation a separate human-in-the-loop
        step.

        Order: trust gate → autonomy ceiling → safety → built-in
        confirmation classes.
        """
        # 1. Trust gate — external content can only *request*, never command.
        if not action.source or TrustSource.is_external(action.source):
            if self.external_action_always_blocked and action.risk_level > RiskLevel.LOW:
                return Decision(
                    PermissionDecision.DENY, action,
                    reason="refusing external-content-initiated action "
                           "(web/documents are untrusted data, not instructions)",
                )

        # 2. Autonomy ceiling.
        if autonomy == AutonomyLevel.OBSERVE_ONLY:
            if action.action_type.value not in {"SCREENSHOT", "WAIT"}:
                return Decision(PermissionDecision.DENY, action,
                                reason="autonomy level 0: observe only")
        if autonomy == AutonomyLevel.SUGGEST_ONLY:
            return Decision(PermissionDecision.DENY, action,
                            reason="autonomy level 1: suggestions only, no execution")
        ceiling = allowed_max_risk(int(autonomy))
        if action.risk_level > ceiling:
            return Decision(
                PermissionDecision.REQUIRE_CONFIRMATION, action,
                reason=f"risk {action.risk_level.value} exceeds autonomy "
                       f"level {autonomy.value} ceiling {ceiling.value}",
            )

        # 3. Safety policy (filesystem/paths/executables).
        safety_reason = self._safety_reason(action)
        if safety_reason:
            return Decision(PermissionDecision.DENY, action, reason=safety_reason)

        # 4. Built-in confirmation classes.
        if action.risk_level >= RiskLevel.HIGH:
            return self._mark_confirmation(action, "high-risk action")
        if action.risk_level == RiskLevel.MEDIUM and autonomy <= AutonomyLevel.LOW_RISK_AUTO:
            return self._mark_confirmation(action, "medium-risk action above autonomous ceiling")

        return Decision(PermissionDecision.ALLOW, action)

    def confirm(self, action: Action) -> Decision:
        """Resolve a REQUIRE_CONFIRMATION decision through the user callback.

        Fail closed: no callback → DENY; callback error → DENY.
        """
        decision = Decision(PermissionDecision.REQUIRE_CONFIRMATION, action,
                            reason="confirmation requested", required_permission=action.permission)
        if not self.confirm_callback:
            return Decision(PermissionDecision.DENY, action,
                            reason="confirmation required but no UI attached")
        try:
            granted = bool(self.confirm_callback(decision))
        except Exception:
            granted = False  # fail closed on callback errors
        if granted:
            return Decision(PermissionDecision.ALLOW, action,
                            reason="confirmed by user")
        return Decision(PermissionDecision.DENY, action,
                        reason="confirmation requested; denied by user")

    # ── confirmation ─────────────────────────────────────────────────

    def _mark_confirmation(self, action: Action, why: str) -> Decision:
        return Decision(PermissionDecision.REQUIRE_CONFIRMATION, action,
                        reason=why, required_permission=action.permission)

    def _safety_reason(self, action: Action) -> Optional[str]:
        p = self.safety_policy
        params = action.parameters or {}
        if action.action_type.value == "DOWNLOAD":
            fname = str(params.get("filename", ""))
            if p.is_executable(fname):
                return p.executable_payload_warning(fname)
        if action.action_type.value == "UPLOAD":
            if p.upload_requires_confirmation(
                str(params.get("filename", "")),
                str(params.get("destination", "")),
                str(params.get("content_preview", "")),
            ):
                # Upload safety goes through confirmation, not hard denial,
                # so the user can decide — but only if a callback exists.
                return None
        if action.action_type.value in ("FILE_SAVE", "FILE_OPEN", "UPLOAD"):
            path = str(params.get("path") or params.get("filename") or action.target)
            if not p.is_safe_path(path):
                return f"unsafe path blocked: {path!r}"
        return None