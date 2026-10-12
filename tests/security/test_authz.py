"""Tests for aetheros_security.authz (AuthorizationEngine + risk).

The engine consults the GLOBAL identity registry / session manager / approval
manager singletons. Tests register principals on the global identity registry.
"""

import pytest

from aetheros_security.authz import (
    ActionRiskEngine,
    AuthorizationEngine,
    AuthorizationPolicyRule,
    AuthorizationRequest,
    Decision,
    RiskLevel,
)
from aetheros_security.identity import TrustLevel, get_identity_registry


def _register_alice():
    reg = get_identity_registry()
    if not reg.is_principal_active("alice"):
        reg.register_user("alice", trust_level=TrustLevel.ELEVATED)


@pytest.fixture
def engine():
    eng = AuthorizationEngine()
    eng.clear_rules()
    _register_alice()
    return eng


class TestActionRiskEngine:
    def test_critical_actions(self):
        risk = ActionRiskEngine()
        assert risk.classify("credential:read", "~/.ssh/id_rsa") == RiskLevel.CRITICAL
        assert risk.classify("security_policy:modify") == RiskLevel.CRITICAL

    def test_high_actions(self):
        risk = ActionRiskEngine()
        assert risk.classify("email:send", "john@example.com") == RiskLevel.HIGH
        assert risk.classify("terminal:execute") == RiskLevel.HIGH
        assert risk.classify("filesystem:delete") == RiskLevel.HIGH

    def test_low_actions(self):
        risk = ActionRiskEngine()
        assert risk.classify("filesystem:read") == RiskLevel.LOW
        assert risk.classify("web:read") == RiskLevel.LOW

    def test_unknown_defaults_medium(self):
        risk = ActionRiskEngine()
        assert risk.classify("widget:frobnicate") == RiskLevel.MEDIUM

    def test_requires_approval(self):
        risk = ActionRiskEngine()
        assert risk.requires_approval("email:send")
        assert risk.requires_approval("credential:delete")
        assert not risk.requires_approval("filesystem:read")

    def test_weight(self):
        assert ActionRiskEngine.weight(RiskLevel.LOW) == 1
        assert ActionRiskEngine.weight(RiskLevel.CRITICAL) == 4


class TestAuthorizationEngine:
    def test_default_deny_unknown_principal(self, engine):
        decision = engine.authorize(AuthorizationRequest(
            principal="ghost", action="filesystem:read"))
        assert decision.decision == Decision.DENY

    def test_default_deny_active_principal_no_rule(self, engine):
        decision = engine.authorize(AuthorizationRequest(
            principal="alice", action="filesystem:read", resource="x.txt"))
        assert decision.decision == Decision.DENY

    def test_allow_rule(self, engine):
        engine.add_rule(AuthorizationPolicyRule(
            decision="allow", action="filesystem:read", principal_pattern="alice",
            resource_pattern="workspace/**"))
        decision = engine.authorize(AuthorizationRequest(
            principal="alice", action="filesystem:read",
            resource="workspace/notes.md"))
        assert decision.decision == Decision.ALLOW

    def test_deny_rule_wins_over_allow(self, engine):
        engine.add_rule(AuthorizationPolicyRule(
            decision="allow", action="*", principal_pattern=".*"))
        engine.add_rule(AuthorizationPolicyRule(
            decision="deny", action="filesystem:delete", principal_pattern=".*",
            priority=1))
        decision = engine.authorize(AuthorizationRequest(
            principal="alice", action="filesystem:delete", resource="workspace/x"))
        assert decision.decision == Decision.DENY

    def test_high_risk_requires_approval(self, engine):
        decision = engine.authorize(AuthorizationRequest(
            principal="alice", action="email:send", resource="john@example.com"))
        assert decision.decision == Decision.REQUIRE_APPROVAL
        assert decision.requires_approval
        assert decision.approval_id

    def test_approval_not_allowed_until_resolved(self, engine):
        from aetheros_security.approval import get_approval_manager
        decision = engine.authorize(AuthorizationRequest(
            principal="alice", action="email:send", resource="j@e.com"))
        am = get_approval_manager()
        # Pending approvals do not authorize.
        assert not am.is_valid(decision.approval_id, "email:send", "j@e.com")
        # Approve, then the binding validates.
        assert am.resolve(decision.approval_id, approved=True)
        assert am.is_valid(decision.approval_id, "email:send", "j@e.com")
        # Binding does not extend to a different recipient.
        assert not am.is_valid(decision.approval_id, "email:send", "other@e.com")

    def test_approval_rule(self, engine):
        engine.add_rule(AuthorizationPolicyRule(
            decision="approval", action="git:push", principal_pattern=".*",
            resource_pattern="*"))
        decision = engine.authorize(AuthorizationRequest(
            principal="alice", action="git:push", resource="origin main"))
        assert decision.decision == Decision.REQUIRE_APPROVAL

    def test_challenge_rule(self, engine):
        engine.add_rule(AuthorizationPolicyRule(
            decision="challenge", action="credential:read", principal_pattern=".*"))
        decision = engine.authorize(AuthorizationRequest(
            principal="alice", action="credential:read"))
        assert decision.decision == Decision.CHALLENGE

    def test_session_scope_enforced(self, engine):
        from aetheros_security.session import get_session_manager
        token = get_session_manager().create(
            "alice", scope=["filesystem:read"])
        engine.add_rule(AuthorizationPolicyRule(
            decision="allow", action="*", principal_pattern=".*"))
        # Action within session scope.
        decision = engine.authorize(AuthorizationRequest(
            principal="alice", action="filesystem:read", session=token))
        assert decision.decision == Decision.ALLOW
        # Action outside session scope -> denied.
        decision2 = engine.authorize(AuthorizationRequest(
            principal="alice", action="network:connect", session=token))
        assert decision2.decision == Decision.DENY
        # Invalid session -> challenge.
        decision3 = engine.authorize(AuthorizationRequest(
            principal="alice", action="filesystem:read", session="bogus"))
        assert decision3.decision == Decision.CHALLENGE

    def test_emergency_stop_denies_all_but_recovery(self, engine):
        engine.add_rule(AuthorizationPolicyRule(
            decision="allow", action="*", principal_pattern=".*"))
        engine.set_emergency_stop(True)
        assert engine.emergency_stop_active
        decision = engine.authorize(AuthorizationRequest(
            principal="alice", action="filesystem:read"))
        assert decision.decision == Decision.DENY
        recovery = engine.authorize(AuthorizationRequest(
            principal="alice", action="security:status"))
        assert recovery.decision == Decision.ALLOW
        engine.set_emergency_stop(False)

    def test_lockdown_denies(self, engine):
        engine.set_lockdown(True)
        assert engine.lockdown_active
        decision = engine.authorize(AuthorizationRequest(
            principal="alice", action="filesystem:read"))
        assert decision.decision == Decision.DENY
        engine.set_lockdown(False)

    def test_unknown_principal_fails_closed_even_with_allow_all(self, engine):
        engine.add_rule(AuthorizationPolicyRule(
            decision="allow", action="*", principal_pattern=".*"))
        decision = engine.authorize(AuthorizationRequest(
            principal="unknown-agent", action="filesystem:read"))
        assert decision.decision == Decision.DENY

    def test_decision_log_and_stats(self, engine):
        engine.authorize(AuthorizationRequest(principal="alice",
                                              action="filesystem:read"))
        assert len(engine.get_decision_log()) >= 1
        stats = engine.get_stats()
        assert stats["decisions_logged"] >= 1

    def test_continuous_authorization_rechecks_principal(self, engine):
        """Authorization is re-evaluated at execution time: revoking the
        principal mid-flight changes the outcome of a new request."""
        reg = get_identity_registry()
        reg.register_user("carol", trust_level=TrustLevel.STANDARD)
        engine.add_rule(AuthorizationPolicyRule(
            decision="allow", action="*", principal_pattern=".*"))
        decision = engine.authorize(AuthorizationRequest(
            principal="carol", action="filesystem:read"))
        assert decision.decision == Decision.ALLOW
        reg.revoke_principal("carol")
        decision2 = engine.authorize(AuthorizationRequest(
            principal="carol", action="filesystem:read"))
        assert decision2.decision == Decision.DENY

    def test_resource_scoped_allow(self, engine):
        engine.add_rule(AuthorizationPolicyRule(
            decision="allow", action="filesystem:read", principal_pattern=".*",
            resource_pattern="workspace/projectA/**"))
        ok = engine.authorize(AuthorizationRequest(
            principal="alice", action="filesystem:read",
            resource="workspace/projectA/file.txt"))
        bad = engine.authorize(AuthorizationRequest(
            principal="alice", action="filesystem:read",
            resource="workspace/projectB/file.txt"))
        assert ok.decision == Decision.ALLOW
        assert bad.decision == Decision.DENY