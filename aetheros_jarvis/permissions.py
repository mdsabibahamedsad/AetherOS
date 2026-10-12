"""Jarvis Mode — permission layer.

Wraps the AetherOS security permission engine with a Jarvis-friendly approval
flow. Every sensitive action (system changes, file deletion, git push,
payments, account logins) MUST pass through this layer. By default nothing is
auto-approved: if no approval resolver is installed, the action is denied.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_jarvis.models import PermissionContext, PermissionDecision

logger = logging.getLogger(__name__)

try:
    from aetheros_security.permissions import PermissionEngine, RiskLevel
except Exception:  # pragma: no cover - degraded when security package absent
    PermissionEngine = None  # type: ignore[assignment,misc]
    RiskLevel = None  # type: ignore[assignment,misc]

APPROVAL_RESOLVER = Callable[[PermissionContext], bool]


class PermissionLayer:
    """Central gate for all privileged Jarvis actions.

    Usage::

        layer = PermissionLayer()
        layer.set_approval_resolver(resolver)
        ok = layer.require("filesystem:delete", target=path, reason="cleanup")
    """

    # Permission -> (risk level, action type)
    _RISK_MAP: Dict[str, str] = {
        "system:change": "high",
        "system:install": "high",
        "filesystem:delete": "high",
        "filesystem:write": "medium",
        "git:push": "high",
        "payment:execute": "critical",
        "account:login": "critical",
        "account:create": "high",
        "mission:execute": "high",
        "notification:send": "low",
        "context:read_clipboard": "medium",
        "context:read_screen": "high",
        "proactive:suggest": "low",
        "network:connect": "medium",
        "browser:automate": "high",
        "email:send": "high",
        "message:send": "medium",
    }

    def __init__(self, engine: Any = None) -> None:
        self._engine = engine if engine is not None else (PermissionEngine() if PermissionEngine else None)
        self._resolver: Optional[APPROVAL_RESOLVER] = None
        self._lock = threading.RLock()
        self._history: List[PermissionContext] = []
        self._max_history = 200

    # ------------------------------------------------------------------
    # Approval wiring
    # ------------------------------------------------------------------

    def set_approval_resolver(self, resolver: Optional[APPROVAL_RESOLVER]) -> None:
        """Install the callback that renders an approval prompt.

        The resolver receives a :class:`PermissionContext` and must return
        True (allow) or False (deny). With no resolver installed every
        privileged request is denied.
        """
        with self._lock:
            self._resolver = resolver

    def risk_level(self, permission: str) -> str:
        return self._RISK_MAP.get(permission, "low")

    # ------------------------------------------------------------------
    # Decision API
    # ------------------------------------------------------------------

    def require(
        self,
        permission: str,
        *,
        requester: str = "jarvis",
        reason: str = "",
        action: str = "",
        target: str = "",
    ) -> bool:
        """Request a privileged action. Returns True only if explicitly approved."""
        risk = self.risk_level(permission)
        ctx = PermissionContext(
            permission=permission,
            requester=requester,
            reason=reason,
            risk_level=risk,
            action=action,
            target=target,
        )

        # Already granted for this session/requester via the security engine.
        if self._engine is not None:
            try:
                if self._engine.check(permission, requester):
                    ctx.decision = PermissionDecision.ALLOWED
                    ctx.granted_at = time.time()
                    self._record(ctx)
                    return True
            except Exception as exc:
                logger.warning("Permission engine check failed for %s: %s", permission, exc)

        if self._resolver is None:
            logger.warning("Privileged action %s (%s) denied: no approval resolver installed", permission, target)
            ctx.decision = PermissionDecision.DENIED
            self._record(ctx)
            return False

        try:
            allowed = bool(self._resolver(ctx))
        except Exception as exc:
            logger.warning("Approval resolver failed for %s; denying: %s", permission, exc)
            allowed = False

        ctx.decision = PermissionDecision.ALLOWED if allowed else PermissionDecision.DENIED
        if allowed:
            ctx.granted_at = time.time()
            if self._engine is not None:
                try:
                    self._engine.grant(permission, requester, duration="session", reason=reason)
                except Exception as exc:
                    logger.debug("Could not persist grant for %s: %s", permission, exc)
        self._record(ctx)
        return allowed

    def check(self, permission: str, requester: str = "jarvis") -> bool:
        """Check whether a permission is currently granted without prompting."""
        if self._engine is not None:
            try:
                return bool(self._engine.check(permission, requester))
            except Exception:
                return False
        return False

    # ------------------------------------------------------------------
    # Convenience gates for the mission-critical action classes
    # ------------------------------------------------------------------

    def system_change(self, reason: str, target: str = "") -> bool:
        return self.require("system:change", reason=reason, action="system.change", target=target)

    def file_delete(self, path: str, reason: str = "") -> bool:
        return self.require("filesystem:delete", reason=reason, action="filesystem.delete", target=path)

    def git_push(self, repo: str = "", reason: str = "") -> bool:
        return self.require("git:push", reason=reason, action="git.push", target=repo)

    def payment(self, amount: str, reason: str = "") -> bool:
        return self.require("payment:execute", reason=reason, action="payment.execute", target=amount)

    def account_login(self, account: str, reason: str = "") -> bool:
        return self.require("account:login", reason=reason, action="account.login", target=account)

    def mission_execute(self, goal: str) -> bool:
        return self.require("mission:execute", reason=f"Execute mission: {goal}", action="mission.execute", target=goal)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "permission": h.permission,
                    "requester": h.requester,
                    "action": h.action,
                    "target": h.target,
                    "risk_level": h.risk_level,
                    "decision": h.decision.value,
                }
                for h in self._history[-limit:]
            ]

    def _record(self, ctx: PermissionContext) -> None:
        with self._lock:
            self._history.append(ctx)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
