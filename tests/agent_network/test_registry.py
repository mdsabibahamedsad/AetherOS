"""Registry: upsert, re-verify on sensitive change, removal preserves history."""

from aetheros_network.agent_card import parse_agent_card
from aetheros_network.identity import AgentIdentity, new_agent_id
from aetheros_network.registry import AgentRegistry

CARD = {"protocolVersion": "1.0", "name": "R", "version": "1.0",
        "url": "https://r.example.com/",
        "skills": [{"id": "research.search"}]}


def _rec(url="https://r.example.com/", skills=None):
    d = dict(CARD, url=url)
    if skills is not None:
        d["skills"] = [{"id": s} for s in skills]
    card = parse_agent_card(d)
    ident = AgentIdentity(agent_id=new_agent_id("ext"), canonical_name="R",
                          organization_id="ext", endpoints=[url])
    return ident, card


def test_upsert_and_get(tmp_path):
    reg = AgentRegistry(tmp_path / "r.json")
    ident, card = _rec()
    reg.upsert(ident.agent_id, ident, card, source="direct_url")
    got = reg.get(ident.agent_id)
    assert got is not None and got.source == "direct_url"


def test_sensitive_change_flags_reverify(tmp_path):
    reg = AgentRegistry(tmp_path / "r.json")
    ident, card = _rec()
    reg.upsert(ident.agent_id, ident, card, source="direct_url")
    ident2, card2 = _rec(url="https://evil.example.net/")
    ident2.agent_id = ident.agent_id
    rec = reg.upsert(ident.agent_id, ident2, card2, source="direct_url")
    assert rec.provenance.get("reverify_required") is True


def test_new_capability_flags_reverify(tmp_path):
    reg = AgentRegistry(tmp_path / "r.json")
    ident, card = _rec()
    reg.upsert(ident.agent_id, ident, card, source="direct_url")
    ident2, card2 = _rec(skills=["research.search", "computer.request"])
    ident2.agent_id = ident.agent_id
    rec = reg.upsert(ident.agent_id, ident2, card2, source="direct_url")
    assert rec.provenance.get("reverify_required") is True


def test_remove_preserves_history(tmp_path):
    reg = AgentRegistry(tmp_path / "r.json")
    ident, card = _rec()
    reg.upsert(ident.agent_id, ident, card, source="direct_url")
    assert reg.remove(ident.agent_id) is True
    assert reg.get(ident.agent_id) is None  # hidden from normal views
    kept = reg.get_including_removed(ident.agent_id)
    assert kept is not None and kept.removed is True  # history preserved


def test_heartbeat_tracks_health(tmp_path):
    reg = AgentRegistry(tmp_path / "r.json")
    ident, card = _rec()
    reg.upsert(ident.agent_id, ident, card, source="direct_url")
    reg.record_heartbeat(ident.agent_id, "online", latency_ms=12.0, success=True)
    got = reg.get(ident.agent_id)
    assert got.health == "online" and got.latency_ms == 12.0
    assert got.success_count == 1
