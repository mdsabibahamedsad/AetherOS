"""Tests for aetheros_comm.trust — trust-zone policy."""

from __future__ import annotations

from aetheros_comm.trust import TrustZonePolicy
from aetheros_comm.types import TrustZone


class TestSameZone:
    def test_same_zone_always_allowed(self):
        policy = TrustZonePolicy()
        assert policy.can_communicate(TrustZone.ZONE_1, TrustZone.ZONE_1)
        assert policy.can_communicate(TrustZone.ZONE_4, TrustZone.ZONE_4)

    def test_same_zone_cross_zone_flag_false(self):
        policy = TrustZonePolicy()
        assert not policy.is_cross_zone(TrustZone.ZONE_1, TrustZone.ZONE_1)


class TestCrossZone:
    def test_cross_zone_denied_by_default(self):
        policy = TrustZonePolicy()
        assert not policy.can_communicate(TrustZone.ZONE_1, TrustZone.ZONE_3)

    def test_unconditional_allowance(self):
        policy = TrustZonePolicy()
        policy.allow_cross_zone(TrustZone.ZONE_1, TrustZone.ZONE_3)
        assert policy.can_communicate(TrustZone.ZONE_1, TrustZone.ZONE_3)
        assert policy.can_communicate(TrustZone.ZONE_1, TrustZone.ZONE_3,
                                      capability="anything")

    def test_capability_scoped_allowance(self):
        policy = TrustZonePolicy()
        policy.allow_cross_zone(TrustZone.ZONE_1, TrustZone.ZONE_3,
                                capabilities=("task:request",))
        assert policy.can_communicate(TrustZone.ZONE_1, TrustZone.ZONE_3,
                                      capability="task:request")
        assert not policy.can_communicate(TrustZone.ZONE_1, TrustZone.ZONE_3,
                                          capability="repository_write")

    def test_source_zone4_may_reach_agents(self):
        policy = TrustZonePolicy()
        assert policy.can_communicate(TrustZone.ZONE_4, TrustZone.ZONE_1)

    def test_agent_cannot_reach_zone4_without_allowance(self):
        policy = TrustZonePolicy()
        assert not policy.can_communicate(TrustZone.ZONE_1, TrustZone.ZONE_4)

    def test_deny_removes_allowance(self):
        policy = TrustZonePolicy()
        policy.allow_cross_zone(TrustZone.ZONE_1, TrustZone.ZONE_3)
        policy.deny_cross_zone(TrustZone.ZONE_1, TrustZone.ZONE_3)
        assert not policy.can_communicate(TrustZone.ZONE_1, TrustZone.ZONE_3)

    def test_asymmetric(self):
        policy = TrustZonePolicy()
        policy.allow_cross_zone(TrustZone.ZONE_1, TrustZone.ZONE_3)
        assert not policy.can_communicate(TrustZone.ZONE_3, TrustZone.ZONE_1)


class TestIntrospection:
    def test_allowed_cross_zones(self):
        policy = TrustZonePolicy()
        policy.allow_cross_zone(TrustZone.ZONE_1, TrustZone.ZONE_3)
        policy.allow_cross_zone(TrustZone.ZONE_1, TrustZone.ZONE_4)
        zones = policy.allowed_cross_zones(TrustZone.ZONE_1)
        assert TrustZone.ZONE_3 in zones
        assert TrustZone.ZONE_4 in zones

    def test_policy_map(self):
        policy = TrustZonePolicy()
        policy.allow_cross_zone(TrustZone.ZONE_1, TrustZone.ZONE_3)
        assert "ZONE_1->ZONE_3" in policy.policy_map()