"""Tests for aetheros_comm.identity — agent registration, cards, status."""

from __future__ import annotations

import pytest

from aetheros_comm.identity import (AgentCard, AgentIdentity, AgentRegistry,
                                    AgentStatus, IdentityError)


def make_identity(agent_id="worker", **overrides) -> AgentIdentity:
    data = {
        "capabilities": ["task:request", "repository_read"],
        "trustZone": "ZONE_1",
        "trustLevel": "standard",
    }
    data.update(overrides)
    return AgentIdentity(agentId=agent_id, **data)


class TestRegistration:
    def test_register_and_get(self):
        reg = AgentRegistry()
        reg.register(make_identity("a"))
        identity = reg.get("a")
        assert identity is not None
        assert identity.agentId == "a"
        assert identity.status == AgentStatus.ACTIVE

    def test_duplicate_register_updates(self):
        reg = AgentRegistry()
        reg.register(make_identity("a"))
        reg.register(make_identity("a", capabilities=["extra"]))
        assert len(reg.list_agents()) == 1
        assert reg.get("a").capabilities == ["extra"]

    def test_invalid_agent_id_rejected(self):
        reg = AgentRegistry()
        with pytest.raises(IdentityError):
            reg.register(make_identity(agent_id="bad id with spaces!"))

    def test_empty_capabilities_rejected(self):
        reg = AgentRegistry()
        with pytest.raises(IdentityError):
            reg.register(make_identity("a", capabilities=[]))

    def test_list_agents(self):
        reg = AgentRegistry()
        reg.register(make_identity("a"))
        reg.register(make_identity("b"))
        ids = {a["agentId"] for a in reg.list_agents()}
        assert ids == {"a", "b"}

    def test_get_unknown_returns_none(self):
        assert AgentRegistry().get("ghost") is None

    def test_require_unknown_raises(self):
        with pytest.raises(IdentityError):
            AgentRegistry().require("ghost")

    def test_default_zone_and_level(self):
        reg = AgentRegistry()
        reg.register(make_identity("a", capabilities=["read"]))
        identity = reg.get("a")
        assert identity.trustZone == "ZONE_1"
        assert identity.trustLevel == "standard"


class TestStatus:
    def test_remove_via_quarantine(self):
        reg = AgentRegistry()
        reg.register(make_identity("a"))
        assert reg.quarantine("a")
        assert reg.get("a").status == AgentStatus.QUARANTINED

    def test_update_status(self):
        reg = AgentRegistry()
        reg.register(make_identity("a"))
        assert reg.update_status("a", AgentStatus.SUSPENDED)
        assert reg.get("a").status == AgentStatus.SUSPENDED

    def test_update_status_unknown_false(self):
        assert not AgentRegistry().update_status("ghost", AgentStatus.SUSPENDED)

    def test_quarantine_and_reactivate(self):
        reg = AgentRegistry()
        reg.register(make_identity("a"))
        reg.quarantine("a")
        assert reg.get("a").status == AgentStatus.QUARANTINED
        reg.reactivate("a")
        assert reg.get("a").status == AgentStatus.ACTIVE

    def test_quarantine_sets_untrusted(self):
        reg = AgentRegistry()
        reg.register(make_identity("a"))
        reg.quarantine("a")
        assert reg.get("a").trustLevel == "untrusted"

    def test_is_active(self):
        reg = AgentRegistry()
        reg.register(make_identity("a"))
        assert reg.is_active("a")
        reg.suspend("a")
        assert not reg.is_active("a")


class TestCard:
    def test_card_from_identity(self):
        identity = make_identity("a", capabilities=["read"])
        card = identity.to_card()
        assert card.agentId == "a"
        assert "read" in card.capabilities
        assert card.trustZone == "ZONE_1"

    def test_card_roundtrip_dict(self):
        identity = make_identity("a")
        card = identity.to_card()
        restored = AgentCard.from_dict(card.to_dict())
        assert restored.agentId == card.agentId
        assert restored.capabilities == card.capabilities

    def test_card_is_advertisement_not_authority(self):
        reg = AgentRegistry()
        reg.register(make_identity("a"))
        # registry overwrites card capabilities from the identity
        card = AgentCard.from_dict({
            "agentId": "a", "capabilities": ["self_declared_privilege"]})
        assert reg.register(make_identity("a"), card)
        assert reg.get_card("a").capabilities == ["task:request",
                                                  "repository_read"]


class TestCapabilities:
    def test_agents_with_capability(self):
        reg = AgentRegistry()
        reg.register(make_identity("a", capabilities=["read"]))
        reg.register(make_identity("b", capabilities=["write"]))
        assert reg.agents_with_capability("read") == ["a"]

    def test_registration_requires_instance(self):
        reg = AgentRegistry()
        identity = AgentIdentity(agentId="x", capabilities=["read"],
                                 instanceId="")
        assert identity.instanceId  # auto-generated
        reg.register(identity)