"""Unit: taxonomy matching + capability index (deterministic first)."""

from aetheros_agent_market import taxonomy as T
from aetheros_agent_market.discovery import CapabilityIndex, IndexedService


def _svc(**kw):
    base = {"service_id": "s1", "agent_id": "a1", "status": "published",
            "availability": "available",
            "capabilities": [{"capability_id": "research.web_search",
                              "protocols": ["A2A"],
                              "data_classes": ["PUBLIC", "INTERNAL"]}],
            "supported_protocols": ["A2A"],
            "supported_modalities": ["text"]}
    base.update(kw)
    return base


def test_exact_match_wins():
    req = T.MatchRequest(query="research stuff",
                         exact_capabilities=["research.web_search"])
    hit = T.match_service(_svc(), req, agent_trust_rank=3)
    assert hit is not None and hit.exact is True


def test_missing_exact_capability_rejected():
    req = T.MatchRequest(exact_capabilities=["coding.code_write"])
    assert T.match_service(_svc(), req) is None


def test_dotted_prefix_match():
    req = T.MatchRequest(exact_capabilities=["research"])
    hit = T.match_service(_svc(), req)
    assert hit is not None and hit.exact is True


def test_protocol_filter_first():
    req = T.MatchRequest(exact_capabilities=["research.web_search"],
                         protocols=["MCP"])
    assert T.match_service(_svc(), req) is None


def test_trust_filter():
    req = T.MatchRequest(min_trust_rank=4)
    assert T.match_service(_svc(), req, agent_trust_rank=3) is None
    assert T.match_service(_svc(), req, agent_trust_rank=5) is not None


def test_cost_filter():
    req = T.MatchRequest(max_price_minor=100)
    assert T.match_service(_svc(), req, price_minor=500) is None
    assert T.match_service(_svc(), req, price_minor=50) is not None


def test_data_class_filter():
    req = T.MatchRequest(data_class="PRIVATE")
    # Service accepts only up to INTERNAL => rejected.
    assert T.match_service(_svc(), req) is None
    svc = _svc(capabilities=[{"capability_id": "research.web_search",
                              "data_classes": ["HIGHLY_SENSITIVE"]}])
    assert T.match_service(svc, req) is not None


def test_unpublished_rejected():
    req = T.MatchRequest()
    assert T.match_service(_svc(status="draft"), req) is None


def test_keyword_only_never_filters():
    # Keyword overlap ranks but deterministic constraints decide.
    req = T.MatchRequest(query="totally unrelated pottery")
    hit = T.match_service(_svc(), req)
    assert hit is not None and hit.exact is False and hit.keyword_score == 0.0


def test_index_orders_exact_first():
    idx = CapabilityIndex()
    idx.add_provider("p", lambda: [
        IndexedService(service=_svc(service_id="kw", agent_id="a2",
                                    capabilities=[{"capability_id": "coding.code_write",
                                                   "data_classes": ["INTERNAL"]}]),
                       source="p", trust_rank=5),
        IndexedService(service=_svc(service_id="ex", agent_id="a1"),
                       source="p", trust_rank=5),
    ])
    hits = idx.search(T.MatchRequest(query="research",
                                     exact_capabilities=["research.web_search"]))
    assert [h.service["service_id"] for h in hits] == ["ex"]


def test_dead_source_does_not_break_discovery():
    idx = CapabilityIndex()

    def _boom():
        raise RuntimeError("registry down")

    idx.add_provider("bad", _boom)
    idx.add_provider("good", lambda: [IndexedService(service=_svc(), source="good")])
    hits = idx.search(T.MatchRequest())
    assert len(hits) == 1 and hits[0].source == "good"


def test_exclude_and_only_agents():
    req = T.MatchRequest(exclude_agents=["a1"])
    assert T.match_service(_svc(), req) is None
    req2 = T.MatchRequest(only_agents=["a9"])
    assert T.match_service(_svc(), req2) is None
