"""Benchmarks: discovery/selection/quote/contract/delegate/verify/settle
overhead at 1/10/100/1000 agents + 10k listings. Real local measurements;
no fabricated remote latencies. Prints a results table (evidence)."""

import time

from aetheros_agent_market import schemas as S
from aetheros_agent_market.flow import MarketplaceFlow
from aetheros_agent_market.selection import AgentSelectionEngine, CandidateSignals
from aetheros_agent_market.taxonomy import MatchRequest
from tests.agent_market.conftest import StubGateway


def _bench(name, fn, rounds=5):
    samples = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    best = min(samples)
    print(f"\nBENCH {name}: {best:.2f}ms (best of {rounds})")
    return best


def _seed_many(flow, n):
    for i in range(n):
        agent_id = f"bench-agent-{i}"
        ident = S.MarketplaceIdentity(
            identity_id=S.new_id("ident"), agent_id=agent_id,
            organization_id="bench", display_name=f"Bench {i}",
            issuer="bench", verification_status="verified")
        flow.registry.register_agent(ident)
        flow.registry.publish_service(S.AgentService(
            service_id=f"bench-svc-{i}", agent_id=agent_id,
            name=f"Bench service {i}", description="research coding data",
            capabilities=[{"capability_id": "research.web_search",
                           "protocols": ["A2A"],
                           "data_classes": ["PUBLIC", "INTERNAL"]}],
            supported_protocols=["A2A"], availability="available",
            pricing_model="free", status="published"))
        flow.trust.record_signal(S.TrustSignal(
            agent_id=agent_id, dimension="execution", source="outcome",
            kind="task_success", value=0.7, confidence=0.9))


def test_bench_discovery_scales(tmp_path):
    home = tmp_path / "m"
    home.mkdir()
    flow = MarketplaceFlow(home, gateway_factory=StubGateway)
    results = {}
    for n in (1, 10, 100, 1000):
        # Top up to exactly n services.
        have = len(flow.registry.discover_services({"status": "published"}))
        if have < n:
            _seed_many(flow, n - have)
        req = MatchRequest(query="research analysis",
                           exact_capabilities=["research.web_search"])
        ms = _bench(f"discovery@{n}", lambda: flow.index.search(req, limit=50))
        results[n] = round(ms, 2)
    print(f"\nBENCH-TABLE discovery_ms={results}")
    assert results[1000] < 2000, "1k-agent discovery must stay under 2s"


def test_bench_selection_ranking(tmp_path):
    cands = [CandidateSignals(
        agent_id=f"a{i}", service_id=f"s{i}", capability_fit=1.0,
        trust_overall=0.5, trust_confidence=0.8, reliability=0.8,
        reliability_confidence=0.8, security=0.9, evidence_quality=0.7,
        price_minor=i * 10, latency_ms=float(100 + i)) for i in range(1000)]
    eng = AgentSelectionEngine()
    ms = _bench("rank-1000", lambda: eng.rank(cands, limit=10))
    assert ms < 1000


def test_bench_full_pipeline_overhead(tmp_path):
    home = tmp_path / "m"
    home.mkdir()
    flow = MarketplaceFlow(home, gateway_factory=StubGateway)
    flow.flags.set("marketplace", True, by="t")
    flow.flags.set("remote_delegation", True, by="t")
    _seed_many(flow, 1)
    svc = flow.registry.discover_services({"status": "published"})[0]
    sel = {"service_id": svc["service_id"], "agent_id": svc["agent_id"]}

    def one_pipeline():
        task = {"summary": "bench", "capabilities": [],
                "data_class": "INTERNAL",
                "verification_requirements": ["schema"],
                "payment_provider": "none", "requester": "bench"}
        out = flow.delegate(task, sel)
        return flow.complete(out["delegation_id"], {"ok": True})

    ms = _bench("full-pipeline", one_pipeline)
    print("\nBENCH-TABLE pipeline_full_ms measured (delegate+complete)")
    assert ms < 5000


def test_bench_10k_listings_search_only():
    # 10k listings measured IN-MEMORY (no persistence): per-write full-file
    # JSON rewrites are O(n^2) and unsuitable for bulk import — recorded as
    # a known limitation (bulk import path is BLOCKED, see certification).
    from aetheros_agent_market.discovery import CapabilityIndex, IndexedService
    idx = CapabilityIndex()
    services = []
    for i in range(10000):
        services.append(IndexedService(
            service={"service_id": f"bench-svc-{i}", "agent_id": f"a{i}",
                     "status": "published", "availability": "available",
                     "capabilities": [{"capability_id": "research.web_search",
                                       "data_classes": ["PUBLIC", "INTERNAL"]}],
                     "supported_protocols": ["A2A"]},
            source="bench", trust_rank=5))
    idx.add_provider("bench", lambda: services)
    req = MatchRequest(query="research",
                       exact_capabilities=["research.web_search"])
    ms = _bench("search-10k", lambda: idx.search(req, limit=50), rounds=3)
    print(f"\nBENCH-TABLE search_10k_ms={round(ms, 2)}")
    assert ms < 10000
