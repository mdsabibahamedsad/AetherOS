"""Tests for the Jarvis permission layer (aetheros_jarvis.permissions)."""

from aetheros_jarvis.permissions import PermissionLayer
from aetheros_jarvis.models import PermissionDecision


class TestPermissionLayer:
    def test_default_deny_without_resolver(self):
        layer = PermissionLayer()
        assert layer.require("system:change", reason="test") is False

    def test_resolver_allows(self):
        layer = PermissionLayer()
        layer.set_approval_resolver(lambda ctx: True)
        assert layer.require("filesystem:delete", target="/tmp/x", reason="cleanup") is True

    def test_resolver_denies(self):
        layer = PermissionLayer()
        layer.set_approval_resolver(lambda ctx: False)
        assert layer.require("git:push", reason="nope") is False

    def test_resolver_receives_context(self):
        layer = PermissionLayer()
        seen = {}
        layer.set_approval_resolver(lambda ctx: seen.update(permission=ctx.permission, target=ctx.target) or True)
        layer.require("payment:execute", target="$10", reason="refund")
        assert seen["permission"] == "payment:execute"
        assert seen["target"] == "$10"

    def test_risk_level_mapping(self):
        layer = PermissionLayer()
        assert layer.risk_level("payment:execute") == "critical"
        assert layer.risk_level("system:change") == "high"
        assert layer.risk_level("proactive:suggest") == "low"
        assert layer.risk_level("unknown:thing") == "low"

    def test_grant_persists_for_session(self):
        layer = PermissionLayer()
        layer.set_approval_resolver(lambda ctx: True)
        assert layer.require("system:change", reason="install")
        assert layer.check("system:change") is True

    def test_denied_actions_are_not_granted(self):
        layer = PermissionLayer()
        layer.set_approval_resolver(lambda ctx: False)
        layer.require("system:change", reason="no")
        assert layer.check("system:change") is False

    def test_convenience_gates(self):
        layer = PermissionLayer()
        layer.set_approval_resolver(lambda ctx: True)
        assert layer.system_change("restart")
        assert layer.file_delete("/tmp/f")
        assert layer.git_push("repo")
        assert layer.payment("$1")
        assert layer.account_login("acct")
        assert layer.mission_execute("build docs")

    def test_convenience_gates_deny_without_resolver(self):
        layer = PermissionLayer()
        assert layer.file_delete("/tmp/f") is False
        assert layer.payment("$1") is False

    def test_history_records_decisions(self):
        layer = PermissionLayer()
        layer.require("system:change", reason="a")
        layer.set_approval_resolver(lambda ctx: True)
        layer.require("git:push", reason="b")
        history = layer.history()
        assert len(history) == 2
        assert history[0]["decision"] == PermissionDecision.DENIED.value
        assert history[1]["decision"] == PermissionDecision.ALLOWED.value
        assert history[1]["permission"] == "git:push"

    def test_history_respects_limit(self):
        layer = PermissionLayer()
        for _ in range(5):
            layer.require("system:change", reason="x")
        assert len(layer.history(limit=2)) == 2
