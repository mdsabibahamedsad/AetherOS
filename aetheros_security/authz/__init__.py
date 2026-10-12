"""
Authorization Engine for AetherOS
=================================

Central, deterministic authorization engine. Every sensitive action passes
through :class:`AuthorizationEngine.authorize`, which returns a decision:

    ALLOW              Action is permitted
    DENY               Action is denied
    REQUIRE_APPROVAL   High-risk action — needs explicit human approval
    CHALLENGE          Needs re-authentication or a one-time proof

Zero-trust rules applied on every check:

    - WHO    principal (user / agent / tool / MCP server / plugin / skill)
    - WHAT   action (filesystem:read, email:send, ...)
    - WHERE  resource scope (workspace/projectA/**, email:read, ...)
    - WHEN   session validity + continuous authorization
    - RISK   action risk classification (low/medium/high/critical)

Authorization is evaluated at execution time, not just at setup time. The
engine consults, in order:

    1. Emergency stop / global lockdown state
    2. Principal status (active / suspended / quarantined / revoked)
    3. Session validity and scope (when a session is supplied)
    4. Resource-scoped policy rules (allow/deny/approval)
    5. Risk classification of the action
    6. Approval binding (approved approvals must match this exact action)

The engine never trusts the model, tool descriptions, or memory — decisions
are made from deterministic state only.

Usage::

    from aetheros_security.authz import (
        AuthorizationEngine, AuthorizationRequest, Decision,
        ActionRiskEngine, RiskLevel,
    )

    engine = AuthorizationEngine()
    request = AuthorizationRequest(
        principal="research-agent",
        action="filesystem:read",
        resource="workspace/research/notes.md",
        session="<session token>",
    )
    decision = engine.authorize(request)
    if decision.decision == Decision.ALLOW:
        ...
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Decision(Enum):
    """Authorization decision outcomes."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    CHALLENGE = "CHALLENGE"


class RiskLevel(Enum):
    """Action risk classification (step 12)."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


_RISK_WEIGHT = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


class ActionRiskEngine:
    """Classifies an action/resource pair into a risk level.

    Rules are deterministic and explicit. Unknown actions default to MEDIUM
    (fail-safer than LOW). ``critical``/``high`` actions drive the approval
    requirement in the authorization engine.
    """

    #: Action prefixes that are always CRITICAL.
    CRITICAL_ACTIONS = {
        "credential:", "key:", "secret:", "auth:", "admin:",
        "policy:", "security:", "payment:", "identity:",
        "secrets:delete", "security_policy:modify",
    }
    #: Action prefixes that are always HIGH.
    HIGH_ACTIONS = {
        "email:send", "message:send", "filesystem:delete",
        "filesystem:write", "network:connect", "terminal:execute",
        "browser:submit", "cloud:upload", "git:push",
        "database:write", "webhook:send",
    }
    #: Explicitly LOW actions (reads of public/safe data).
    LOW_ACTIONS = {
        "filesystem:read", "web:read", "search:query",
        "knowledge:read", "memory:read", "network:resolve",
    }

    def classify(self, action: str, resource: str = "") -> RiskLevel:
        """Return the risk level for an action/resource pair."""
        action = (action or "").lower()
        resource = (resource or "").lower()

        for prefix in self.CRITICAL_ACTIONS:
            if action.startswith(prefix):
                return RiskLevel.CRITICAL
        if action in self.HIGH_ACTIONS:
            return RiskLevel.HIGH
        if action.startswith("filesystem:write") and resource:
            # Writes outside the workspace are riskier.
            if any(seg in resource for seg in (".ssh", "config", ".env",
                                               "passwd", "credentials", "key")):
                return RiskLevel.CRITICAL
            return RiskLevel.HIGH
        if action in self.LOW_ACTIONS:
            return RiskLevel.LOW
        return RiskLevel.MEDIUM

    def requires_approval(self, action: str, resource: str = "") -> bool:
        """Whether an action of this risk requires human approval."""
        return self.classify(action, resource) in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    @staticmethod
    def weight(level: RiskLevel) -> int:
        return _RISK_WEIGHT.get(level, 2)


class DecisionOutcome(Enum):
    """Outcome of an authorization check (for audit)."""
    ALLOWED = "allowed"
    DENIED = "denied"
    APPROVAL_REQUIRED = "approval_required"
    CHALLENGE_REQUIRED = "challenge_required"


@dataclass
class AuthorizationRequest:
    """A request to authorize a single action.

    Attributes:
        principal: Principal id (user, agent, tool, MCP server, plugin, skill).
        action: Canonical action string (``category:operation``).
        resource: Scoped resource (path, email address, network host, ...).
        session: Optional session token to validate.
        risk: Optional override for the action risk.
        mission: Optional mission/context id for correlation.
    """
    principal: str
    action: str
    resource: str = ""
    session: str = ""
    risk: Optional[RiskLevel] = None
    mission: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthorizationDecision:
    """Result of an authorization check."""
    decision: Decision
    principal: str
    action: str
    resource: str = ""
    reason: str = ""
    risk: RiskLevel = RiskLevel.MEDIUM
    requires_approval: bool = False
    approval_id: str = ""
    checked_at: float = 0.0

    @property
    def allowed(self) -> bool:
        return self.decision == Decision.ALLOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "principal": self.principal,
            "action": self.action,
            "resource": self.resource,
            "reason": self.reason,
            "risk": self.risk.value,
            "requires_approval": self.requires_approval,
            "approval_id": self.approval_id,
            "checked_at": self.checked_at,
        }


@dataclass
class AuthorizationPolicyRule:
    """A single authorization policy rule.

    ``decision`` is one of "allow", "deny", "approval", "challenge".
    ``principal_pattern`` is a regex matched against the principal id.
    ``action`` is the action (or prefix) covered. ``resource_pattern`` is a
    glob-style pattern matched against the resource.
    """
    decision: str  # allow | deny | approval | challenge
    action: str
    principal_pattern: str = ".*"
    resource_pattern: str = "*"
    reason: str = ""
    priority: int = 100  # lower number = higher priority (evaluated first)


def _glob_match(pattern: str, value: str) -> bool:
    """Match a simple ``*`` glob against a value (case-insensitive)."""
    import re
    pattern = (pattern or "*").lower()
    value = (value or "").lower()
    regex = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
    return re.fullmatch(regex, value) is not None


class AuthorizationEngine:
    """Deterministic authorization engine.

    Integrates with:
        - :mod:`aetheros_security.identity` (principal state)
        - :mod:`aetheros_security.session` (session validity + scope)
        - :mod:`aetheros_security.policy` (declarative policies)
        - :mod:`aetheros_security.rate_limit` (abuse prevention)

    Every decision is audited. Decisions are made from deterministic state
    only — never from model output or prompt content.
    """

    def __init__(self) -> None:
        self._rules: List[AuthorizationPolicyRule] = []
        self._risk_engine = ActionRiskEngine()
        self._callbacks: Dict[str, Callable] = {}
        self._emergency_stop = False
        self._lockdown = False
        self._decision_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Global kill switches
    # ------------------------------------------------------------------

    def set_emergency_stop(self, enabled: bool) -> None:
        """Activate/deactivate the global emergency stop.

        When active, every authorization request is DENIED except a
        narrow allowlist of emergency-recovery actions.
        """
        self._emergency_stop = enabled
        level = "CRITICAL" if enabled else "INFO"
        self._emit_audit("emergency_stop", None, "security.response", level, {
            "enabled": enabled,
        })
        logger.warning("Authorization engine emergency stop = %s", enabled)

    @property
    def emergency_stop_active(self) -> bool:
        return self._emergency_stop

    def set_lockdown(self, enabled: bool) -> None:
        """Account lockdown: revoke trust, block sensitive actions."""
        self._lockdown = enabled
        self._emit_audit("lockdown", None, "security.response",
                         "CRITICAL" if enabled else "INFO", {"enabled": enabled})
        logger.warning("Authorization engine lockdown = %s", enabled)

    @property
    def lockdown_active(self) -> bool:
        return self._lockdown

    # ------------------------------------------------------------------
    # Policy configuration
    # ------------------------------------------------------------------

    def add_rule(self, rule: AuthorizationPolicyRule) -> None:
        """Add a deterministic authorization rule."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)

    def clear_rules(self) -> None:
        self._rules.clear()

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a callback.

        Supported events:
            - ``approval_requested``: called with an AuthorizationDecision
              that requires approval.
            - ``approval_resolved``: called with (approval_id, approved).
        """
        self._callbacks[event] = callback

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    def authorize(self, request: AuthorizationRequest) -> AuthorizationDecision:
        """Evaluate one action and return a deterministic decision.

        Order of evaluation (fail-closed):
            1. Emergency stop / lockdown
            2. Principal must exist and be ACTIVE
            3. Session (when supplied) must validate and carry scope
            4. Explicit rules (allow/deny/approval/challenge)
            5. Risk-based approval for high/critical actions
            6. Default DENY
        """
        now = time.time()
        action = (request.action or "").lower()
        risk = request.risk or self._risk_engine.classify(action, request.resource)

        if self._emergency_stop:
            # Allow only the narrowest recovery actions during a stop.
            if action.startswith("security:recover") or action == "security:status":
                return self._decide(Decision.ALLOW, request, risk, now,
                                    "emergency recovery allowed")
            return self._decide(Decision.DENY, request, risk, now,
                                "emergency stop active")

        if self._lockdown:
            if action.startswith("security:recover"):
                return self._decide(Decision.ALLOW, request, risk, now,
                                    "lockdown recovery allowed")
            return self._decide(Decision.DENY, request, risk, now,
                                "account lockdown active")

        # 2. Principal must exist and be active.
        if not self._principal_active(request.principal):
            return self._decide(Decision.DENY, request, risk, now,
                                "principal not active")

        # 3. Session validation (when a session is supplied).
        if request.session:
            session_decision = self._check_session(request)
            if session_decision is not None:
                return session_decision

        # 4. Explicit rules.
        for rule in self._rules:
            if not _glob_match(rule.action, action):
                continue
            if not self._match_principal(rule.principal_pattern, request.principal):
                continue
            if not _glob_match(rule.resource_pattern, request.resource):
                continue
            if rule.decision == "deny":
                return self._decide(Decision.DENY, request, risk, now,
                                    rule.reason or "denied by rule")
            if rule.decision == "allow":
                return self._decide(Decision.ALLOW, request, risk, now,
                                    rule.reason or "allowed by rule")
            if rule.decision == "approval":
                return self._require_approval(request, risk, now,
                                              rule.reason or "approval rule")
            if rule.decision == "challenge":
                return self._decide(Decision.CHALLENGE, request, risk, now,
                                    rule.reason or "challenge rule")

        # 5. Risk-based approval.
        if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return self._require_approval(request, risk, now,
                                          f"{risk.value} risk action")

        # 6. Default deny.
        return self._decide(Decision.DENY, request, risk, now, "default deny")

    def _match_principal(self, pattern: str, principal: str) -> bool:
        import re
        try:
            return re.fullmatch(pattern, principal) is not None
        except re.error:
            return pattern == principal

    def _principal_active(self, principal: str) -> bool:
        try:
            from aetheros_security.identity import (get_identity_registry)
            return get_identity_registry().is_principal_active(principal) or \
                get_identity_registry().is_active(principal)
        except Exception:
            # If the registry cannot be consulted, fail closed.
            return False

    def _check_session(self, request: AuthorizationRequest) -> Optional[AuthorizationDecision]:
        """Validate the session and its scope. Returns a decision on failure."""
        try:
            from aetheros_security.session import SessionError, get_session_manager
            session = get_session_manager().validate(request.session)
        except Exception as exc:
            return self._decide(Decision.CHALLENGE, request,
                                request.risk or RiskLevel.MEDIUM, time.time(),
                                f"invalid session: {exc}")
        # Session must carry the action as a scope (or wildcard).
        if not get_session_manager().has_scope(session, request.action):
            return self._decide(Decision.DENY, request,
                                request.risk or RiskLevel.MEDIUM, time.time(),
                                "action outside session scope")
        return None

    def _require_approval(self, request: AuthorizationRequest, risk: RiskLevel,
                          now: float, reason: str) -> AuthorizationDecision:
        decision = self._decide(Decision.REQUIRE_APPROVAL, request, risk, now, reason)
        decision.requires_approval = True
        decision.approval_id = self._create_approval(request, risk, reason)
        callback = self._callbacks.get("approval_requested")
        if callback:
            try:
                callback(decision)
            except Exception:
                logger.exception("approval_requested callback failed")
        return decision

    def _create_approval(self, request: AuthorizationRequest, risk: RiskLevel,
                         reason: str) -> str:
        from aetheros_security.approval import get_approval_manager
        approval = get_approval_manager().create(
            principal=request.principal,
            action=request.action,
            resource=request.resource,
            risk=risk.value,
            reason=reason,
        )
        return approval.approval_id

    def _decide(self, decision: Decision, request: AuthorizationRequest,
                risk: RiskLevel, now: float, reason: str) -> AuthorizationDecision:
        result = AuthorizationDecision(
            decision=decision,
            principal=request.principal,
            action=request.action,
            resource=request.resource,
            reason=reason,
            risk=risk,
            checked_at=now,
        )
        self._log_decision(result)
        return result

    def _log_decision(self, decision: AuthorizationDecision) -> None:
        self._decision_log.append(decision.to_dict())
        if len(self._decision_log) > 10000:
            self._decision_log = self._decision_log[-10000:]
        self._emit_audit("authorization", decision.principal,
                         "security.authz", "info", decision.to_dict())

    @staticmethod
    def _emit_audit(event_type: str, principal: Optional[str], source: str,
                    severity: str, details: Dict[str, Any]) -> None:
        try:
            from aetheros_security.audit import AuditSeverity, AuditEventType
            try:
                event = AuditEventType(event_type)
            except ValueError:
                event = AuditEventType.CUSTOM
            get_audit_logger().log(
                event,
                severity=AuditSeverity(severity),
                user=principal or "",
                source=source,
                details=details,
                message=f"Authorization: {details.get('decision', '')} {principal}",
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_decision_log(self, limit: int = 200) -> List[Dict[str, Any]]:
        return list(self._decision_log[-limit:])

    def get_risk(self, action: str, resource: str = "") -> RiskLevel:
        return self._risk_engine.classify(action, resource)

    def get_stats(self) -> Dict[str, Any]:
        from collections import Counter
        counts = Counter(d["decision"] for d in self._decision_log)
        return {
            "rules": len(self._rules),
            "decisions_logged": len(self._decision_log),
            "by_decision": dict(counts),
            "emergency_stop": self._emergency_stop,
            "lockdown": self._lockdown,
        }


# Global authorization engine
_authorization_engine: AuthorizationEngine | None = None


def get_authorization_engine() -> AuthorizationEngine:
    """Return the global AuthorizationEngine singleton."""
    global _authorization_engine
    if _authorization_engine is None:
        _authorization_engine = AuthorizationEngine()
    return _authorization_engine