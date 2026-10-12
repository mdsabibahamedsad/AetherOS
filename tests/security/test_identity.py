"""Tests for aetheros_security.identity (principals + agent identity)."""

import pytest

from aetheros_security.identity import (
    AgentIdentity,
    IdentityRegistry,
    Principal,
    PrincipalStatus,
    PrincipalType,
    TrustLevel,
    trust_at_least,
)


class TestTrustLevels:
    def test_ordering(self):
        assert trust_at_least(TrustLevel.STANDARD, TrustLevel.LOW)
        assert trust_at_least(TrustLevel.PRIVILEGED, TrustLevel.STANDARD)
        assert not trust_at_least(TrustLevel.LOW, TrustLevel.PRIVILEGED)

    def test_unknown_level_is_untrusted(self):
        assert not trust_at_least("nope", TrustLevel.LOW)


class TestAgentIdentity:
    def test_auto_id_and_timestamps(self):
        identity = AgentIdentity(owner="alice")
        assert identity.agent_id
        assert identity.created_at > 0
        assert identity.updated_at > 0

    def test_roundtrip_dict(self):
        identity = AgentIdentity(
            agent_id="research-1",
            agent_type="research",
            agent_version="2.1.0",
            owner="alice",
            trust_level=TrustLevel.ELEVATED,
            capabilities=["browse", "search"],
            permissions=["web:read", "search:query"],
            workspace="workspace/research",
            session_scope="session-42",
        )
        restored = AgentIdentity.from_dict(identity.to_dict())
        assert restored.agent_id == "research-1"
        assert restored.trust_level == TrustLevel.ELEVATED
        assert restored.permissions == ["web:read", "search:query"]


class TestIdentityRegistry:
    def test_register_and_get(self):
        reg = IdentityRegistry()
        identity = AgentIdentity(agent_id="a1", owner="alice")
        reg.register_agent(identity)
        assert reg.get_agent("a1") is identity
        assert reg.get_agent("missing") is None

    def test_default_status_active(self):
        reg = IdentityRegistry()
        identity = reg.register_agent(AgentIdentity(agent_id="a2"))
        assert reg.is_active("a2")
        assert identity.status == PrincipalStatus.ACTIVE

    def test_quarantine_removes_trust(self):
        reg = IdentityRegistry()
        reg.register_agent(AgentIdentity(agent_id="a3",
                                         trust_level=TrustLevel.PRIVILEGED))
        assert reg.quarantine("a3")
        identity = reg.require_agent("a3")
        assert identity.status == PrincipalStatus.QUARANTINED
        assert identity.trust_level == TrustLevel.UNTRUSTED
        assert not reg.is_active("a3")

    def test_suspend_revoke_restore(self):
        reg = IdentityRegistry()
        reg.register_agent(AgentIdentity(agent_id="a4"))
        assert reg.suspend("a4")
        assert not reg.is_active("a4")
        assert reg.restore("a4", trust_level=TrustLevel.STANDARD)
        assert reg.is_active("a4")
        assert reg.require_agent("a4").trust_level == TrustLevel.STANDARD
        assert reg.revoke("a4")
        assert not reg.is_active("a4")

    def test_scopes(self):
        reg = IdentityRegistry()
        reg.register_agent(AgentIdentity(agent_id="a5"))
        assert reg.grant_scope("a5", "filesystem:read")
        assert reg.grant_scope("a5", "filesystem:read")  # idempotent
        assert reg.require_agent("a5").permissions == ["filesystem:read"]
        assert reg.revoke_scope("a5", "filesystem:read")
        assert reg.require_agent("a5").permissions == []

    def test_unknown_agent_operations_fail(self):
        reg = IdentityRegistry()
        assert not reg.quarantine("missing")
        assert not reg.grant_scope("missing", "x")
        with pytest.raises(Exception):
            reg.require_agent("missing")

    def test_register_user_and_principals(self):
        reg = IdentityRegistry()
        user = reg.register_user("alice", scopes=["filesystem:read"])
        assert user.principal_type == PrincipalType.USER
        tool = reg.register_tool("file.read")
        assert tool.principal_type == PrincipalType.TOOL
        assert reg.is_principal_active("alice")
        assert reg.get("file.read") is tool

    def test_principal_quarantine_and_revoke(self):
        reg = IdentityRegistry()
        reg.register_user("mallory")
        assert reg.quarantine_principal("mallory")
        assert not reg.is_principal_active("mallory")
        assert reg.trust_level_of("mallory") == TrustLevel.UNTRUSTED

    def test_trust_level_resolution(self):
        reg = IdentityRegistry()
        reg.register_user("u1", trust_level=TrustLevel.ELEVATED)
        reg.register_agent(AgentIdentity(agent_id="ag1",
                                         trust_level=TrustLevel.STANDARD))
        assert reg.trust_level_of("u1") == TrustLevel.ELEVATED
        assert reg.trust_level_of("ag1") == TrustLevel.STANDARD
        assert reg.trust_level_of("unknown") == TrustLevel.UNTRUSTED

    def test_stats(self):
        reg = IdentityRegistry()
        reg.register_agent(AgentIdentity(agent_id="a"))
        reg.register_user("u")
        assert reg.get_stats()["agents"] == 1
        assert reg.get_stats()["principals"] == 1

    def test_principal_register_sets_type(self):
        reg = IdentityRegistry()
        p = reg.register(Principal(principal_id="svc-1",
                                   principal_type=PrincipalType.SERVICE))
        assert reg.get("svc-1") is p
        assert p.principal_type == PrincipalType.SERVICE