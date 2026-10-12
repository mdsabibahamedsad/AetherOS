"""Tests for aetheros_security.action_guard (the guarded-action pipeline)."""

import re
from contextlib import contextmanager

import pytest

from aetheros_security.action_guard import (
    ActionGuard,
    ActionGuardError,
    GuardConfig,
    GuardRequest,
    Reversibility,
    RiskTier,
    TransactionError,
    TransactionalAction,
    get_action_guard,
    risk_at_least,
)


@contextmanager
def _permit(principal, action, resource="*"):
    """Register the principal as active and allow one action on the singleton
    authorization engine. No process isolation, so rules are cleared on exit."""
    from aetheros_security.authz import (AuthorizationPolicyRule,
                                         get_authorization_engine)
    from aetheros_security.identity import get_identity_registry
    get_identity_registry().register_user(principal)
    get_authorization_engine().add_rule(AuthorizationPolicyRule(
        decision="allow",
        action=action,
        principal_pattern=re.escape(principal),
        resource_pattern=resource))
    try:
        yield
    finally:
        get_authorization_engine().clear_rules()


class TestRiskClassification:
    def test_risk_tiers(self):
        guard = ActionGuard()
        assert guard.classify_risk("filesystem:read") == RiskTier.R1_LOW
        assert guard.classify_risk("filesystem:write") == RiskTier.R2_MODERATE
        assert guard.classify_risk("filesystem:delete") == RiskTier.R4_CRITICAL
        assert guard.classify_risk("terminal:execute") == RiskTier.R3_HIGH
        assert guard.classify_risk("credential:read") == RiskTier.R4_CRITICAL
        assert guard.classify_risk("email:send") == RiskTier.R3_HIGH
        assert guard.classify_risk("search:query") == RiskTier.R0_INFORMATIONAL

    def test_risk_at_least(self):
        assert risk_at_least(RiskTier.R4_CRITICAL, RiskTier.R3_HIGH)
        assert not risk_at_least(RiskTier.R1_LOW, RiskTier.R3_HIGH)

    def test_reversibility(self):
        guard = ActionGuard()
        assert guard.classify_reversibility("filesystem:delete") == Reversibility.IRREVERSIBLE
        assert guard.classify_reversibility("email:send") == Reversibility.PARTIALLY_REVERSIBLE
        assert guard.classify_reversibility("filesystem:read") == Reversibility.REVERSIBLE


class TestSchemaValidation:
    def test_valid_output(self):
        guard = ActionGuard()
        schema = {"type": "object",
                  "required": ["action", "resource"],
                  "properties": {"action": {"type": "string"},
                                 "resource": {"type": "string"}}}
        assert guard.validate_schema(schema, {"action": "deploy",
                                              "resource": "svc"}) is None

    def test_missing_required(self):
        guard = ActionGuard()
        schema = {"required": ["action", "resource"]}
        assert guard.validate_schema(schema, {"action": "x"}) is not None

    def test_wrong_type(self):
        guard = ActionGuard()
        schema = {"properties": {"count": {"type": "integer"}}}
        assert guard.validate_schema(schema, {"count": "not-an-int"}) is not None

    def test_non_object_output(self):
        guard = ActionGuard()
        assert guard.validate_schema({"type": "object"}, ["not", "object"]) is not None

    def test_none_schema_passes(self):
        guard = ActionGuard()
        assert guard.validate_schema(None, {"anything": 1}) is None


class TestActionGuardPipeline:
    def test_low_risk_action_executes(self):
        with _permit("alice", "filesystem:read"):
            guard = ActionGuard()
            executed = {"ran": False}
            guard.register_executor("filesystem:read",
                                    lambda req: executed.__setitem__("ran", True))
            result = guard.execute(GuardRequest(
                principal="alice", action="filesystem:read",
                resource="/tmp/notes.md"))
            assert result.allowed
            assert result.executed
            assert executed["ran"] is True

    def test_high_risk_requires_approval_without_resolver(self):
        # Principal active, no allow rule: the engine requires approval.
        from aetheros_security.identity import get_identity_registry
        get_identity_registry().register_user("alice")
        guard = ActionGuard()
        guard.register_executor("filesystem:delete", lambda req: None)
        result = guard.execute(GuardRequest(
            principal="alice", action="filesystem:delete", resource="/tmp/x"))
        assert not result.allowed
        assert result.decision == "approval_required"

    def test_approval_resolver_allows(self):
        with _permit("alice", "filesystem:write"):
            guard = ActionGuard(config=GuardConfig(
                require_approval_above=RiskTier.R2_MODERATE,
                dry_run_required_above=RiskTier.R4_CRITICAL))
            output = {}
            guard.register_executor("filesystem:write",
                                    lambda req: output.__setitem__("done", True))
            guard.register_approval_resolver(lambda aid, req: True)
            result = guard.execute(GuardRequest(
                principal="alice", action="filesystem:write", resource="/tmp/x"))
            assert result.allowed
            assert result.decision == "allow"
            assert output.get("done") is True

    def test_approval_resolver_denies(self):
        with _permit("alice", "filesystem:write"):
            guard = ActionGuard(config=GuardConfig(
                require_approval_above=RiskTier.R2_MODERATE,
                dry_run_required_above=RiskTier.R4_CRITICAL))
            guard.register_executor("filesystem:write", lambda req: None)
            guard.register_approval_resolver(lambda aid, req: False)
            result = guard.execute(GuardRequest(
                principal="alice", action="filesystem:write", resource="/tmp/x"))
            assert not result.allowed
            assert result.decision == "approval_required"

    def test_intent_validator_rejects(self):
        with _permit("alice", "filesystem:write"):
            guard = ActionGuard()
            guard.register_executor("filesystem:write", lambda req: None)
            guard.register_intent_validator(
                lambda req: "refusing" if "harmful" in str(req.parameters) else None)
            result = guard.execute(GuardRequest(
                principal="alice", action="filesystem:write",
                resource="/tmp/x", parameters={"content": "harmful stuff"}))
            assert not result.allowed
            assert "intent" in result.reason

    def test_parameter_validator_rejects(self):
        with _permit("alice", "filesystem:write"):
            guard = ActionGuard()
            guard.register_executor("filesystem:write", lambda req: None)
            guard.register_parameter_validator(
                "filesystem:write",
                lambda params: "traversal" if ".." in str(params.get("path", "")) else None)
            result = guard.execute(GuardRequest(
                principal="alice", action="filesystem:write",
                resource="/tmp/x", parameters={"path": "../escape"}))
            assert not result.allowed
            assert "parameters" in result.reason

    def test_no_executor_denied(self):
        with _permit("alice", "never:registered"):
            guard = ActionGuard()
            result = guard.execute(GuardRequest(
                principal="alice", action="never:registered"))
            assert not result.allowed
            assert "no executor" in result.reason

    def test_dry_run_never_executes(self):
        with _permit("alice", "filesystem:write"):
            guard = ActionGuard()
            executed = {"ran": False}
            guard.register_executor("filesystem:write",
                                    lambda req: executed.__setitem__("ran", True))
            result = guard.execute(GuardRequest(
                principal="alice", action="filesystem:write",
                resource="/tmp/x", dry_run=True))
            assert result.dry_run
            assert not result.executed
            assert executed["ran"] is False

    def test_postcondition_failure(self):
        with _permit("alice", "filesystem:write"):
            guard = ActionGuard()
            guard.register_executor("filesystem:write", lambda req: {"wrote": False})
            guard.register_postcondition(
                "filesystem:write",
                lambda req, output: "file was not actually written" if not output.get("wrote") else None)
            result = guard.execute(GuardRequest(
                principal="alice", action="filesystem:write", resource="/tmp/x"))
            assert not result.allowed
            assert "postcondition" in result.reason

    def test_postcondition_success(self):
        with _permit("alice", "filesystem:write"):
            guard = ActionGuard()
            guard.register_executor("filesystem:write", lambda req: {"wrote": True})
            guard.register_postcondition(
                "filesystem:write",
                lambda req, output: None if output.get("wrote") else "not written")
            result = guard.execute(GuardRequest(
                principal="alice", action="filesystem:write", resource="/tmp/x"))
            assert result.allowed
            assert result.postcondition_ok

    def test_bulk_action_requires_approval(self):
        with _permit("alice", "filesystem:read"):
            guard = ActionGuard()
            guard.register_executor("filesystem:read", lambda req: "ok")
            result = guard.execute(GuardRequest(
                principal="alice", action="filesystem:read",
                resource="/tmp/*", item_count=50_000))
            assert not result.allowed
            assert result.decision == "approval_required"

    def test_dual_control_fails_closed(self):
        # With dual control required at R2, the second independent check runs;
        # the security-scoped principal is unknown → fails closed.
        with _permit("alice", "filesystem:write"):
            guard = ActionGuard(config=GuardConfig(
                require_approval_above=RiskTier.R3_HIGH,
                dry_run_required_above=RiskTier.R4_CRITICAL,
                dual_control_above=RiskTier.R2_MODERATE))
            guard.register_executor("filesystem:write", lambda req: "wrote")
            result = guard.execute(GuardRequest(
                principal="alice", action="filesystem:write", resource="/tmp/x"))
            assert not result.allowed
            assert "dual-control" in result.reason

    def test_audited(self):
        with _permit("alice", "filesystem:read"):
            guard = ActionGuard()
            guard.register_executor("filesystem:read", lambda req: None)
            result = guard.execute(GuardRequest(
                principal="alice", action="filesystem:read"))
            assert result.audited

    def test_stats(self):
        guard = ActionGuard()
        guard.register_executor("filesystem:read", lambda req: None)
        stats = guard.get_stats()
        assert stats["executors"] >= 1


class TestTransactionalAction:
    def test_commit_on_success(self):
        state = {"committed": False}
        tx = TransactionalAction(
            prepare=lambda: {"data": 1},
            validate=lambda prepared: None,
            commit=lambda prepared: state.__setitem__("committed", True))
        with tx:
            tx.commit()
        assert state["committed"] is True

    def test_rollback_on_error(self):
        state = {"rolled_back": False}
        tx = TransactionalAction(
            prepare=lambda: None,
            rollback=lambda: state.__setitem__("rolled_back", True))
        with pytest.raises(RuntimeError):
            with tx:
                raise RuntimeError("boom")
        assert state["rolled_back"] is True

    def test_validation_failure_aborts(self):
        tx = TransactionalAction(
            prepare=lambda: "x",
            validate=lambda prepared: "invalid",
            commit=lambda prepared: None)
        with pytest.raises(TransactionError):
            with tx:
                pass

    def test_idempotent_commit(self):
        calls = {"n": 0}
        tx = TransactionalAction(
            commit=lambda prepared: calls.__setitem__("n", calls["n"] + 1))
        with tx:
            tx.commit()
            tx.commit()
        assert calls["n"] == 1


class TestConfig:
    def test_custom_thresholds(self):
        # Raising the approval bar lets a high-risk (R3) action execute
        # without approval, and dry-run is also raised so it truly runs.
        with _permit("alice", "email:send"):
            guard = ActionGuard(config=GuardConfig(
                require_approval_above=RiskTier.R4_CRITICAL,
                dry_run_required_above=RiskTier.R4_CRITICAL))
            output = {}
            guard.register_executor("email:send",
                                    lambda req: output.__setitem__("sent", True))
            result = guard.execute(GuardRequest(
                principal="alice", action="email:send"))
            assert result.allowed
            assert output.get("sent") is True

    def test_singleton(self):
        assert get_action_guard() is get_action_guard()