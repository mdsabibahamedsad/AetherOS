"""Trust levels, transitions, persistence (Master 46 sections 11-13)."""

import pytest

from aetheros_network.trust import TrustStore, can_transition


def test_discovery_does_not_imply_trust(tmp_path):
    store = TrustStore(tmp_path / "trust.json")
    rec = store.get("aetheros:ext:abc123")
    assert rec.level == "discovered"


def test_explicit_upgrade_path(tmp_path):
    store = TrustStore(tmp_path / "trust.json")
    store.set_level("a:1", "unverified", by="verification")
    store.set_level("a:1", "verified", by="verification")
    store.set_level("a:1", "user_trusted", by="user")
    assert store.level("a:1") == "user_trusted"


def test_skip_levels_rejected(tmp_path):
    store = TrustStore(tmp_path / "trust.json")
    with pytest.raises(ValueError, match="not allowed"):
        store.set_level("a:1", "fully_trusted", by="user")


def test_revoked_is_terminal(tmp_path):
    store = TrustStore(tmp_path / "trust.json")
    store.set_level("a:1", "unverified", by="v")
    store.set_level("a:1", "revoked", by="user")
    with pytest.raises(ValueError, match="not allowed"):
        store.set_level("a:1", "verified", by="user")
    assert store.is_blocked("a:1") is True


def test_blocked_blocks(tmp_path):
    store = TrustStore(tmp_path / "trust.json")
    store.set_level("a:1", "blocked", by="user")
    assert store.is_blocked("a:1") is True


def test_history_recorded(tmp_path):
    store = TrustStore(tmp_path / "trust.json")
    store.set_level("a:1", "unverified", by="v")
    rec = store.get("a:1")
    assert rec.history and rec.history[-1]["to"] == "unverified"


def test_persistence_roundtrip(tmp_path):
    path = tmp_path / "trust.json"
    s1 = TrustStore(path)
    s1.set_level("a:1", "unverified", by="v")
    s2 = TrustStore(path)
    assert s2.level("a:1") == "unverified"


def test_unknown_level_rejected(tmp_path):
    store = TrustStore(tmp_path / "trust.json")
    with pytest.raises(ValueError, match="unknown trust level"):
        store.set_level("a:1", "super_trusted", by="user")


def test_can_transition_table():
    assert can_transition("discovered", "verified") is True
    assert can_transition("verified", "fully_trusted") is False
    assert can_transition("revoked", "verified") is False
