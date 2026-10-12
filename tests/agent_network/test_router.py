"""Router: trust outranks speed, privacy gates, SLA (sections 27-30, 90)."""

from aetheros_network.router import AgentNetworkRouter, RouteCandidate


def _cands():
    return [
        RouteCandidate("fast-untrusted", "remote",
                       capabilities=["research.search"], trust="discovered",
                       latency_ms=5.0, cost=0.1, reliability=0.99),
        RouteCandidate("slow-verified", "remote",
                       capabilities=["research.search"], trust="verified",
                       latency_ms=900.0, cost=1.0, reliability=0.7),
        RouteCandidate("local-agent", "local",
                       capabilities=["research.search"], trust="verified",
                       latency_ms=50.0, reliability=0.9),
    ]


def test_untrusted_never_wins_on_speed():
    r = AgentNetworkRouter().route("t1", ["research.search"], _cands(), mode="auto")
    assert r.selected != "fast-untrusted"
    assert "fast-untrusted" in r.rejected


def test_verified_remote_selected_over_untrusted():
    r = AgentNetworkRouter().route("t1", ["research.search"], _cands(), mode="auto")
    assert r.selected in ("slow-verified", "local-agent")
    assert r.trust in ("verified",)


def test_local_only_excludes_remote():
    r = AgentNetworkRouter().route("t1", ["research.search"], _cands(), mode="local_only")
    assert r.selected == "local-agent"


def test_sensitive_data_excludes_low_trust():
    cands = [RouteCandidate("remote-ok", "remote", capabilities=["research.search"],
                            trust="verified", latency_ms=10.0)]
    r = AgentNetworkRouter().route("t1", ["research.search"], cands,
                                   mode="auto", max_data_class="sensitive")
    assert r.selected == ""
    assert "remote-ok" in r.rejected


def test_sla_latency_enforced():
    cands = [RouteCandidate("r1", "remote", capabilities=["research.search"],
                            trust="verified", latency_ms=5000.0)]
    r = AgentNetworkRouter().route("t1", ["research.search"], cands,
                                   mode="auto", sla={"max_latency_ms": 100})
    assert r.selected == ""
    assert "latency" in r.rejected["r1"]


def test_missing_capability_rejected_with_reason():
    cands = [RouteCandidate("r1", "remote", capabilities=["other.thing"],
                            trust="fully_trusted")]
    r = AgentNetworkRouter().route("t1", ["research.search"], cands, mode="auto")
    assert r.selected == "" and "missing capabilities" in r.rejected["r1"]


def test_decision_trace_complete():
    r = AgentNetworkRouter().route("t1", ["research.search"], _cands(), mode="auto")
    d = r.to_dict()
    for key in ("task_id", "candidates", "eligible", "rejected", "selected",
                "trust", "policy", "privacy", "timestamp"):
        assert key in d, key


def test_organization_only_requires_membership():
    cands = [RouteCandidate("ext", "remote", capabilities=["research.search"],
                            trust="fully_trusted", organization_id="other")]
    r = AgentNetworkRouter(organization_id="acme").route(
        "t1", ["research.search"], cands, mode="organization_only")
    assert r.selected == ""
