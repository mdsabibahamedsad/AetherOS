"""Unit: swarm/automation/research/memory/router adapters."""

from aetheros_agent_market import integrations as I
from tests.agent_market.conftest import seed_service


def _enable(flow):
    flow.flags.set("marketplace", True, by="test")
    flow.flags.set("remote_delegation", True, by="test")


def test_swarm_proposals_are_data_not_spawns(flow):
    _ident, svc = seed_service(flow)
    props = I.swarm_member_proposals(
        flow, {"query": "summarize", "capabilities": ["research.web_search"]})
    assert props and props[0]["agent_id"] == svc.agent_id
    assert "why" in props[0] and props[0]["origin"] == "marketplace"


def test_swarm_evidence_claim_mapping():
    claim = I.swarm_evidence_claim("ct-1", {"passed": True, "details": {}},
                                   agent_id="a1")
    assert claim["confidence"] == 1.0 and claim["agent"] == "a1"
    bad = I.swarm_evidence_claim("ct-2", {"passed": False, "details": {}})
    assert bad["confidence"] == 0.0 and "FAILED" in bad["claim"]


def test_automation_spec_validated_and_executed(flow):
    import pytest
    _ident, svc = seed_service(flow)
    _enable(flow)
    with pytest.raises(ValueError):
        I.scheduled_delegation_spec({}, {"service_id": "s"})
    spec = I.scheduled_delegation_spec(
        {"summary": "weekly report", "verification_requirements": ["schema"],
         "payment_provider": "none"},
        {"service_id": svc.service_id, "agent_id": svc.agent_id})
    assert spec["gates"][0] == "discover" and spec["gates"][-1] == "reputation"
    out = I.run_scheduled(flow, spec)
    assert out["status"] == "running"
    with pytest.raises(ValueError):
        I.run_scheduled(flow, {"version": 99})


def test_research_subtask_enforces_citations(flow):
    import pytest
    _ident, svc = seed_service(flow)
    _enable(flow)
    with pytest.raises(ValueError):
        I.research_subtask(flow, "", {"service_id": "s", "agent_id": "a"})
    out = I.research_subtask(flow, "What caused the 2024 outage?",
                             {"service_id": svc.service_id,
                              "agent_id": svc.agent_id})
    assert out["citation_policy"]["strategy"] == "citation_presence"
    assert out["status"] == "running"


def test_remember_fact_with_provenance(flow):
    res = I.remember_marketplace_fact(flow, "User prefers Agent X for translation.",
                                      agent_id="agent-x")
    assert res["evidence_id"].startswith("ev-")
    assert isinstance(res["mirrored_to_memory"], bool)
    import pytest
    with pytest.raises(ValueError):
        I.remember_marketplace_fact(flow, "")


def test_routing_comparison_honest_uncertainty(flow):
    _ident, svc = seed_service(flow)
    out = I.routing_comparison(flow, {"query": "summarize"})
    assert "uncertainty" in out and out["local"]["local_capable"] in (True, False)
