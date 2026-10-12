"""
Action Guard for AetherOS
=========================

Deterministic pipeline every privileged action passes through (master
security spec step 35)::

    intent validation
        → permission check
        → parameter validation
        → risk evaluation
        → approval if required
        → execution
        → postcondition validation
        → audit

Also provides:

    - Risk tiers R0-R4 (step 36)
    - Dry-run support (step 41)
    - Reversibility classification (step 42)
    - Transactional action helper (step 43)
    - Bulk-action protection (step 44)
    - Structured output schema validation (steps 34, 59)
    - Dual control for critical actions (step 60)
    - Post-condition validation (step 61)

Usage::

    from aetheros_security.action_guard import (
        ActionGuard, GuardRequest, GuardConfig, RiskTier,
    )

    guard = ActionGuard()
    result = guard.execute(
        GuardRequest(
            principal="research-agent",
            action="filesystem:write",
            resource="/project/docs/notes.md",
            parameters={"path": "/project/docs/notes.md", "content": "..."},
            dry_run=True,
        ),
    )
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RiskTier(Enum):
    """Action risk tiers R0-R4 (step 36)."""
    R0_INFORMATIONAL = "R0"
    R1_LOW = "R1"
    R2_MODERATE = "R2"
    R3_HIGH = "R3"
    R4_CRITICAL = "R4"


_RISK_ORDER = {RiskTier.R0_INFORMATIONAL: 0, RiskTier.R1_LOW: 1,
               RiskTier.R2_MODERATE: 2, RiskTier.R3_HIGH: 3,
               RiskTier.R4_CRITICAL: 4}


def risk_at_least(tier: RiskTier, minimum: RiskTier) -> bool:
    return _RISK_ORDER.get(tier, 0) >= _RISK_ORDER.get(minimum, 0)


class Reversibility(Enum):
    """Operation reversibility classification (step 42)."""
    REVERSIBLE = "reversible"
    PARTIALLY_REVERSIBLE = "partially_reversible"
    IRREVERSIBLE = "irreversible"


#: Default risk mapping for common actions.
_DEFAULT_RISK_TIERS = {
    "filesystem:read": RiskTier.R1_LOW,
    "web:read": RiskTier.R1_LOW,
    "search:query": RiskTier.R0_INFORMATIONAL,
    "knowledge:read": RiskTier.R1_LOW,
    "memory:read": RiskTier.R2_MODERATE,
    "filesystem:write": RiskTier.R2_MODERATE,
    "filesystem:delete": RiskTier.R4_CRITICAL,
    "terminal:execute": RiskTier.R3_HIGH,
    "email:send": RiskTier.R3_HIGH,
    "message:send": RiskTier.R3_HIGH,
    "network:connect": RiskTier.R3_HIGH,
    "cloud:upload": RiskTier.R3_HIGH,
    "git:push": RiskTier.R3_HIGH,
    "credential:read": RiskTier.R4_CRITICAL,
    "credential:delete": RiskTier.R4_CRITICAL,
    "security_policy:modify": RiskTier.R4_CRITICAL,
    "admin:deploy": RiskTier.R4_CRITICAL,
    "payment:send": RiskTier.R4_CRITICAL,
}


@dataclass
class GuardRequest:
    """A request to run one guarded action."""
    principal: str
    action: str
    resource: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    session: str = ""
    mission: str = ""
    task: str = ""
    agent: str = ""
    risk: Optional[RiskTier] = None
    reversibility: Optional[Reversibility] = None
    dry_run: bool = False
    #: Number of discrete items this action touches (for bulk detection).
    item_count: int = 1
    expected_output_schema: Optional[Dict[str, Any]] = None


@dataclass
class GuardConfig:
    """Configuration for a guarded action."""
    require_approval_above: RiskTier = RiskTier.R3_HIGH
    dry_run_required_above: RiskTier = RiskTier.R3_HIGH
    dual_control_above: RiskTier = RiskTier.R4_CRITICAL
    bulk_threshold: int = 100
    deny_irreversible_without_approval: bool = True


@dataclass
class GuardResult:
    """Result of a guarded action execution."""
    allowed: bool
    decision: str = "allow"           # allow | deny | approval_required | dry_run
    principal: str = ""
    action: str = ""
    resource: str = ""
    risk: str = "R2"
    reason: str = ""
    approval_id: str = ""
    output: Any = None
    postcondition_ok: bool = True
    postcondition_message: str = ""
    dry_run: bool = False
    checked_at: float = 0.0
    audited: bool = False

    @property
    def executed(self) -> bool:
        return self.allowed and not self.dry_run

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "decision": self.decision,
            "principal": self.principal,
            "action": self.action,
            "resource": self.resource,
            "risk": self.risk,
            "reason": self.reason,
            "approval_id": self.approval_id,
            "postcondition_ok": self.postcondition_ok,
            "dry_run": self.dry_run,
            "checked_at": self.checked_at,
            "audited": self.audited,
        }


class ActionGuardError(Exception):
    """Raised for invalid guard operations."""


class ActionGuard:
    """Deterministic privileged-action pipeline (step 35).

    Wiring::

        guard = ActionGuard()
        guard.register_executor("filesystem:write", my_executor)
        guard.register_parameter_validator("filesystem:write", my_validator)
        guard.register_postcondition("filesystem:write", my_check)
        guard.register_approval_resolver(my_resolver)
    """

    def __init__(self, config: Optional[GuardConfig] = None) -> None:
        self._config = config or GuardConfig()
        self._executors: Dict[str, Callable[[GuardRequest], Any]] = {}
        self._param_validators: Dict[str, Callable[[Dict[str, Any]], Optional[str]]] = {}
        self._postconditions: Dict[str, Callable[[GuardRequest, Any], Optional[str]]] = {}
        self._intent_validators: List[Callable[[GuardRequest], Optional[str]]] = []
        self._approval_resolver: Optional[Callable[[str, GuardRequest], bool]] = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_executor(self, action: str, executor: Callable[[GuardRequest], Any]) -> None:
        self._executors[action] = executor

    def register_parameter_validator(
        self, action: str, validator: Callable[[Dict[str, Any]], Optional[str]]) -> None:
        self._param_validators[action] = validator

    def register_postcondition(
        self, action: str, check: Callable[[GuardRequest, Any], Optional[str]]) -> None:
        """Register a post-condition validator (step 61).

        ``check(request, output)`` returns ``None`` on success or an error
        string describing why the postcondition failed.
        """
        self._postconditions[action] = check

    def register_intent_validator(self, validator: Callable[[GuardRequest], Optional[str]]) -> None:
        """Register an intent validator (step 35, first stage).

        ``validator(request)`` returns ``None`` if the intent is sound or an
        error string describing why it is rejected.
        """
        self._intent_validators.append(validator)

    def register_approval_resolver(self, resolver: Callable[[str, GuardRequest], bool]) -> None:
        """Register the deterministic human-approval resolver.

        ``resolver(approval_id, request)`` returns True to allow, False to
        deny. The model NEVER decides.
        """
        self._approval_resolver = resolver

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    def classify_risk(self, action: str, resource: str = "") -> RiskTier:
        action = (action or "").lower()
        if action in _DEFAULT_RISK_TIERS:
            return _DEFAULT_RISK_TIERS[action]
        for prefix, tier in (("credential:", RiskTier.R4_CRITICAL),
                             ("key:", RiskTier.R4_CRITICAL),
                             ("secret:", RiskTier.R4_CRITICAL),
                             ("auth:", RiskTier.R4_CRITICAL),
                             ("admin:", RiskTier.R4_CRITICAL),
                             ("policy:", RiskTier.R4_CRITICAL),
                             ("security:", RiskTier.R4_CRITICAL),
                             ("payment:", RiskTier.R4_CRITICAL),
                             ("email:", RiskTier.R3_HIGH),
                             ("message:", RiskTier.R3_HIGH),
                             ("network:", RiskTier.R3_HIGH),
                             ("terminal:", RiskTier.R3_HIGH),
                             ("cloud:", RiskTier.R3_HIGH),
                             ("git:push", RiskTier.R3_HIGH)):
            if action.startswith(prefix):
                return tier
        if action.startswith("filesystem:"):
            op = action.split(":", 1)[1]
            if op == "delete":
                return RiskTier.R4_CRITICAL
            if op in ("write", "move", "archive"):
                return RiskTier.R2_MODERATE
            if op == "read":
                return RiskTier.R1_LOW
        return RiskTier.R2_MODERATE

    def classify_reversibility(self, action: str) -> Reversibility:
        action = (action or "").lower()
        if any(prefix in action for prefix in ("delete", "destroy", "purge",
                                                "drop", "truncate")):
            return Reversibility.IRREVERSIBLE
        if any(prefix in action for prefix in ("deploy", "publish", "send",
                                               "push", "upload", "execute",
                                               "configure", "modify")):
            return Reversibility.PARTIALLY_REVERSIBLE
        return Reversibility.REVERSIBLE

    # ------------------------------------------------------------------
    # Schema / output validation (steps 34, 59)
    # ------------------------------------------------------------------

    def validate_schema(self, schema: Dict[str, Any],
                        output: Any) -> Optional[str]:
        """Validate a structured action output against a JSON-schema-like dict.

        Supported schema keywords: ``type``, ``required``, ``properties``
        (with ``type`` per property). Returns an error string or None.
        """
        if schema is None:
            return None
        if not isinstance(output, dict):
            return f"output must be an object (got {type(output).__name__})"
        required = schema.get("required", [])
        for key in required:
            if key not in output:
                return f"missing required field: {key}"
        props = schema.get("properties", {})
        for key, spec in props.items():
            if key not in output:
                continue
            expected = spec.get("type")
            if expected == "string" and not isinstance(output[key], str):
                return f"field '{key}' must be string"
            if expected == "integer" and not isinstance(output[key], int):
                return f"field '{key}' must be integer"
            if expected == "number" and not isinstance(output[key], (int, float)):
                return f"field '{key}' must be number"
            if expected == "boolean" and not isinstance(output[key], bool):
                return f"field '{key}' must be boolean"
            if expected == "array" and not isinstance(output[key], list):
                return f"field '{key}' must be array"
        return None

    # ------------------------------------------------------------------
    # Bulk action protection (step 44)
    # ------------------------------------------------------------------

    def is_bulk(self, request: GuardRequest) -> bool:
        return request.item_count > self._config.bulk_threshold

    # ------------------------------------------------------------------
    # The pipeline
    # ------------------------------------------------------------------

    def execute(self, request: GuardRequest) -> GuardResult:
        """Run the full guarded-action pipeline."""
        now = time.time()
        action = (request.action or "").lower()
        risk = request.risk or self.classify_risk(action, request.resource)
        reversibility = request.reversibility or self.classify_reversibility(action)

        # 0. Intent validation.
        for validator in self._intent_validators:
            try:
                error = validator(request)
            except Exception as exc:
                return self._fail(request, risk, now, f"intent validation error: {exc}")
            if error:
                return self._fail(request, risk, now, f"intent rejected: {error}")

        # 1. Kill switch: autonomous actions.
        try:
            from aetheros_security.kill_switch import (KillSwitch,
                                                       get_kill_switch_registry)
            if (get_kill_switch_registry().is_active(KillSwitch.DISABLE_AUTONOMOUS_ACTIONS)
                    and request.agent and not request.session):
                return self._fail(request, risk, now,
                                  "autonomous actions disabled by kill switch")
        except Exception:
            pass

        # 2. Permission check (authorization engine).
        permission_decision = self._check_permission(request, action, risk, now)
        if permission_decision is not None:
            return permission_decision

        # 3. Parameter validation.
        param_error = self._validate_params(request, action)
        if param_error:
            return self._fail(request, risk, now, f"invalid parameters: {param_error}")

        # 4. Risk evaluation + approval requirement.
        if risk_at_least(risk, self._config.require_approval_above):
            approval = self._require_approval(request, risk, now)
            if approval is not None:
                return approval

        # 5. Irreversible requires approval.
        if (reversibility == Reversibility.IRREVERSIBLE
                and self._config.deny_irreversible_without_approval
                and not risk_at_least(risk, self._config.require_approval_above)):
            approval = self._require_approval(request, risk, now)
            if approval is not None:
                return approval

        # 6. Bulk protection.
        if self.is_bulk(request):
            approval = self._require_approval(request, risk, now,
                                              bulk=True)
            if approval is not None:
                return approval

        # 7. Dry-run.
        if request.dry_run or risk_at_least(risk, self._config.dry_run_required_above):
            return self._dry_run(request, risk, now)

        # 8. Dual control for critical actions.
        if risk_at_least(risk, self._config.dual_control_above):
            if not self._dual_control(request, risk, now):
                return self._fail(request, risk, now,
                                  "dual-control verification failed")

        # 9. Execute.
        executor = self._executors.get(action)
        if executor is None:
            return self._fail(request, risk, now, "no executor registered")
        try:
            output = executor(request)
        except Exception as exc:
            return self._fail(request, risk, now, f"execution failed: {exc}")

        # 10. Post-condition validation.
        postcondition = self._postconditions.get(action)
        if postcondition is not None:
            try:
                pc_error = postcondition(request, output)
            except Exception as exc:
                return self._fail(request, risk, now,
                                  f"postcondition check error: {exc}")
            if pc_error:
                return self._fail(request, risk, now,
                                  f"postcondition failed: {pc_error}",
                                  output=output)

        result = GuardResult(True, "allow", request.principal, action,
                             request.resource, risk.value, "allowed",
                             output=output, postcondition_ok=True,
                             checked_at=now)
        self._audit("allow", request, risk, result)
        return result

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    def _check_permission(self, request: GuardRequest, action: str,
                          risk: RiskTier, now: float) -> Optional[GuardResult]:
        try:
            from aetheros_security.authz import (
                AuthorizationRequest, Decision, get_authorization_engine,
            )
            engine = get_authorization_engine()
            decision = engine.authorize(AuthorizationRequest(
                principal=request.principal,
                action=action,
                resource=request.resource,
                session=request.session,
                mission=request.mission,
                details={"task": request.task, "agent": request.agent},
            ))
            if decision.decision == Decision.ALLOW:
                return None
            if decision.decision == Decision.REQUIRE_APPROVAL:
                result = self._make_approval_result(request, risk, now,
                                                    decision.reason,
                                                    decision.approval_id)
                self._audit("approval_required", request, risk, result)
                return result
            return self._fail(request, risk, now, decision.reason or "denied")
        except Exception as exc:
            # Fail closed.
            return self._fail(request, risk, now,
                              f"authorization unavailable: {exc}")

    def _validate_params(self, request: GuardRequest, action: str) -> Optional[str]:
        validator = self._param_validators.get(action)
        if validator is None:
            return None
        try:
            return validator(request.parameters)
        except Exception as exc:
            return f"parameter validator error: {exc}"

    def _require_approval(self, request: GuardRequest, risk: RiskTier,
                          now: float, bulk: bool = False) -> Optional[GuardResult]:
        from aetheros_security.approval import get_approval_manager
        reason = ("bulk action" if bulk else f"{risk.value} risk action")
        approval = get_approval_manager().create(
            principal=request.principal,
            action=request.action,
            resource=request.resource,
            risk=risk.value,
            reason=reason,
            parameters=request.parameters,
        )
        approved = False
        if self._approval_resolver is not None:
            try:
                approved = bool(self._approval_resolver(approval.approval_id, request))
                get_approval_manager().resolve(approval.approval_id,
                                               approved=approved)
            except Exception:
                get_approval_manager().resolve(approval.approval_id, approved=False)
        if not approved:
            result = self._make_approval_result(request, risk, now, reason,
                                                approval.approval_id)
            self._audit("approval_required", request, risk, result)
            return result
        return None

    def _dual_control(self, request: GuardRequest, risk: RiskTier,
                      now: float) -> bool:
        """Second independent check for critical actions (step 60)."""
        try:
            from aetheros_security.authz import (
                AuthorizationRequest, Decision, get_authorization_engine,
            )
            engine = get_authorization_engine()
            decision = engine.authorize(AuthorizationRequest(
                principal="security:" + request.principal,
                action=request.action,
                resource=request.resource,
                details={"dual_control": True},
            ))
            return decision.decision == Decision.ALLOW
        except Exception:
            return False

    def _dry_run(self, request: GuardRequest, risk: RiskTier, now: float) -> GuardResult:
        result = GuardResult(True, "dry_run", request.principal,
                             (request.action or "").lower(), request.resource,
                             risk.value, "dry run (no changes made)",
                             dry_run=True, checked_at=now)
        self._audit("dry_run", request, risk, result)
        return result

    def _make_approval_result(self, request: GuardRequest, risk: RiskTier,
                              now: float, reason: str,
                              approval_id: str) -> GuardResult:
        return GuardResult(False, "approval_required", request.principal,
                           (request.action or "").lower(), request.resource,
                           risk.value, reason, approval_id=approval_id,
                           checked_at=now)

    def _fail(self, request: GuardRequest, risk: RiskTier, now: float,
              reason: str, output: Any = None) -> GuardResult:
        result = GuardResult(False, "deny", request.principal,
                             (request.action or "").lower(), request.resource,
                             risk.value, reason, output=output, checked_at=now)
        self._audit("deny", request, risk, result)
        return result

    def _audit(self, decision: str, request: GuardRequest, risk: RiskTier,
               result: GuardResult) -> None:
        try:
            from aetheros_security.audit import (AuditEventType, AuditSeverity,
                                                 get_audit_logger)
            try:
                event = AuditEventType("authorization")
            except ValueError:
                event = AuditEventType.CUSTOM
            get_audit_logger().log(
                event,
                severity=AuditSeverity.INFO,
                user=request.principal,
                source="action_guard",
                details={"action": request.action, "resource": request.resource,
                         "risk": risk.value, "decision": decision,
                         "mission": request.mission, "task": request.task},
                message=f"ActionGuard {decision}: {request.action}",
            )
            result.audited = True
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        return {
            "executors": len(self._executors),
            "param_validators": len(self._param_validators),
            "postconditions": len(self._postconditions),
            "intent_validators": len(self._intent_validators),
            "bulk_threshold": self._config.bulk_threshold,
        }


# ---------------------------------------------------------------------------
# Transactional action helper (step 43)
# ---------------------------------------------------------------------------

class TransactionError(Exception):
    """Raised when a transactional action cannot complete."""


class TransactionalAction:
    """prepare → validate → commit / rollback (step 43).

    Usage::

        tx = TransactionalAction(prepare=prepare_fn, validate=validate_fn,
                                 commit=commit_fn, rollback=rollback_fn)
        with tx as committed:
            ...  # if an exception escapes, rollback runs
    """

    def __init__(self, *, prepare: Optional[Callable[[], Any]] = None,
                 validate: Optional[Callable[[Any], Optional[str]]] = None,
                 commit: Optional[Callable[[Any], Any]] = None,
                 rollback: Optional[Callable[[], None]] = None) -> None:
        self._prepare = prepare
        self._validate = validate
        self._commit = commit
        self._rollback = rollback
        self._committed = False
        self._prepared: Any = None

    def __enter__(self) -> "TransactionalAction":
        if self._prepare is not None:
            self._prepared = self._prepare()
        if self._validate is not None:
            error = self._validate(self._prepared)
            if error:
                raise TransactionError(f"validation failed: {error}")
        return self

    def commit(self) -> Any:
        if self._committed:
            return None
        result = self._commit(self._prepared) if self._commit else None
        self._committed = True
        return result

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            if self._rollback is not None:
                try:
                    self._rollback()
                except Exception as rb_exc:  # pragma: no cover
                    logger.error("rollback failed: %s", rb_exc)
            return False
        return False


# Global action guard
_action_guard: ActionGuard | None = None


def get_action_guard() -> ActionGuard:
    """Return the global ActionGuard singleton."""
    global _action_guard
    if _action_guard is None:
        _action_guard = ActionGuard()
    return _action_guard