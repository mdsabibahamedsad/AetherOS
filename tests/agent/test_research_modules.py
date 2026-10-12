"""Unit coverage for Master 17 wave-2 modules (P6-93)."""

import time

import pytest

from agent.research.webops import (
    FetchPipeline,
    FreshnessPolicy,
    PageCache,
    PolitenessLimiter,
    RobotsGate,
    detect_live_intent,
)
from agent.research.privacy import (
    ExfilBlocked,
    PrivateBoundary,
    guard_outbound_query,
    scan_outbound,
)
from agent.research.models import (
    Claim,
    ClaimStatus,
    Evidence,
    ResearchSource,
    SourceType,
    SourceVisibility,
)
from agent.research.temporal import (
    build_timeline,
    detect_changes,
    classify_change_kind,
    extract_dates,
    as_of_stamp,
    primary_date,
)
from agent.research.knowledge_graph import ResearchKnowledgeGraph
from agent.research.memory_bridge import build_memory_records
from agent.research.targets import (
    classify_news_language,
    github_research_urls,
    is_technical_query,
    parse_arxiv_ref,
    summarize_repository,
)
from agent.research.agents import (
    build_subtasks,
    independently_verified,
    merge_through_evidence,
    run_research_team,
)
from agent.research.adversarial import (
    absorb_disprove_result,
    build_disprove_tasks,
    detect_bias,
    diversify_candidates,
)
from agent.research.multiprovider import FanOutSearch, FallbackChain


class TestWebops:
    def test_live_intent_detection(self):
        assert detect_live_intent("latest mcp spec changes")
        assert detect_live_intent("who won TODAY")
        assert not detect_live_intent("history of the printing press")

    def test_freshness_policy_varies_by_type(self):
        policy = FreshnessPolicy()
        assert policy.ttl_for(SourceType.NEWS) < policy.ttl_for(SourceType.OFFICIAL)
        assert policy.ttl_for(SourceType.OFFICIAL) < policy.ttl_for(SourceType.ACADEMIC)

    def test_politeness_limiter_enforces_delay(self):
        limiter = PolitenessLimiter(min_delay_seconds=0.05)
        limiter.wait("a.test")
        start = time.time()
        limiter.wait("a.test")
        assert time.time() - start >= 0.04

    def test_robots_gate_blocks_disallowed(self):
        gate = RobotsGate()
        robots_body = "User-agent: *\nDisallow: /private\n"
        ok_private, _ = gate.allowed(
            "https://site.test/private/x",
            fetcher=lambda url: robots_body if url.endswith("/robots.txt") else "",
        )
        ok_public, detail = gate.allowed(
            "https://site.test/public/y",
            fetcher=lambda url: robots_body,
        )
        assert not ok_private
        assert ok_public
        cached_ok, cached_detail = gate.allowed(
            "https://site.test/public/z", fetcher=None
        )
        assert cached_ok and cached_detail == "cached_rules"

    def test_robots_gate_fail_open_on_unreachable(self):
        gate = RobotsGate()

        def broken_fetcher(url):
            raise OSError("down")

        ok, detail = gate.allowed("https://down.test/page", fetcher=broken_fetcher)
        assert ok and detail == "robots_unreachable_fail_open"

    def test_page_cache_ttl_by_type(self, tmp_path):
        cache = PageCache(tmp_path / "cache.db")
        cache.put("k-news", "https://n.test/1", "t", "c", "h", SourceType.NEWS,
                  fetched_at=time.time() - 7200)
        cache.put("k-acad", "https://a.test/1", "t", "c", "h", SourceType.ACADEMIC,
                  fetched_at=time.time() - 7200)
        assert cache.get_fresh("k-news", SourceType.NEWS) is None
        fresh = cache.get_fresh("k-acad", SourceType.ACADEMIC)
        assert fresh and fresh["content"] == "c"
        assert cache.get_fresh("k-acad", SourceType.ACADEMIC, force_refresh=True) is None
        cache.close()

    def test_fetch_pipeline_order_cache_robots_network(self, tmp_path):
        cache = PageCache(tmp_path / "cache.db")
        calls = []

        def network(url):
            calls.append(url)
            return "Title", "body text"

        pipeline = FetchPipeline(cache=cache, robots=RobotsGate())
        page1, prov1 = pipeline.fetch("https://x.test/a", "k1", SourceType.NEWS,
                                      network_fetch=network)
        page2, prov2 = pipeline.fetch("https://x.test/a", "k1", SourceType.NEWS,
                                      network_fetch=network)
        assert prov1 == "network_fetch" and prov2 == "cache_hit"
        assert calls == ["https://x.test/a"]
        blocked, prov3 = pipeline.fetch(
            "https://y.test/blocked", "k2", SourceType.NEWS,
            network_fetch=network,
            robots_fetcher=lambda u: "User-agent: *\nDisallow: /\n",
        )
        assert blocked is None and prov3.startswith("robots_blocked")
        none_page, prov4 = pipeline.fetch("https://z.test/c", "k3",
                                          SourceType.NEWS, network_fetch=None)
        assert none_page is None and prov4 == "no_fetcher"
        cache.close()


class TestPrivacy:
    def test_credential_shaped_queries_blocked(self):
        for bad in [
            "search for docs sk-ant-api03-abcdef123456",
            "bearer abcdef123456 find me",
            "api_key=hunter2 something",
            "AKIAIOSFODNN7EXAMPLE bucket policy",
        ]:
            with pytest.raises(ExfilBlocked):
                guard_outbound_query(bad)

    def test_clean_queries_pass(self):
        assert guard_outbound_query("what is the mcp specification") == \
            "what is the mcp specification"

    def test_boundary_blocks_private_term_leakage(self):
        boundary = PrivateBoundary()
        boundary.register_private_text(
            "Internal codename Zephyrion-Prime revenue projections Q7"
        )
        ok, reason = boundary.check_query("Zephyrion-Prime public news")
        assert not ok and reason.startswith("private_term")

    def test_public_terms_pass_boundary(self):
        boundary = PrivateBoundary()
        boundary.register_private_text("codename zephyrion internal")
        ok, _ = boundary.check_query("public specification of http caching")
        assert ok


class TestTemporal:
    def test_extract_dates_variants(self):
        text = "On 2026-08-15 and August 16, 2026 (also 2026/08/17)."
        dates = {d.iso: d.kind for d in extract_dates(text)}
        assert dates["2026-08-15"] == "iso"
        assert dates["2026-08-16"] == "long_form"
        assert dates["2026-08-17"] == "slash"

    def test_year_only_fallback_when_no_full_date(self):
        dates = {d.iso: d.kind for d in extract_dates("since 2019 things improved")}
        assert dates == {"2019": "year_only"}

    def test_primary_date_prefers_iso(self):
        assert primary_date("since 2019, released 2026-01-02") == "2026-01-02"

    def test_timeline_orders_and_excludes_undated(self):
        events = build_timeline([
            ("later event", "2026-03-01", ["s1"]),
            ("earlier event", "2025-11-02", ["s2"]),
            ("undated claim", None, ["s3"]),
        ])
        assert [e.date_iso for e in events] == ["2025-11-02", "2026-03-01"]
        assert all(e.text != "undated claim" for e in events)

    def test_change_detection_classes(self):
        old = "line one stays\nfeature X costs five\nlegacy mode removed here\ntail"
        new = "line one stays\nfeature X costs six\ntail\nbrand new capability"
        report = detect_changes(old, new)
        kinds = classify_change_kind(report)
        assert report.has_changes
        assert any("six" in b for _a, b in report.changed)
        assert "legacy mode removed here" in report.removed
        assert "brand new capability" in report.added
        assert "changed" in kinds and "added" in kinds and "removed" in kinds

    def test_as_of_stamp_format(self):
        stamp = as_of_stamp(1750000000.0)
        assert stamp.endswith("UTC") and "-" in stamp


class TestKnowledgeGraph:
    def test_no_merge_without_shared_evidence(self):
        graph = ResearchKnowledgeGraph()
        a, created_a = graph.add_entity("Acme Rocket", "product", source_ids=["s1"])
        b, created_b = graph.add_entity("acme rocket", "product", source_ids=["s2"])
        assert created_a and created_b and a != b

    def test_merge_with_shared_source(self):
        graph = ResearchKnowledgeGraph()
        a, _ = graph.add_entity("Acme", "organization", source_ids=["s1"])
        b, created = graph.add_entity("ACME", "organization", source_ids=["s1", "s9"])
        assert not created and a == b

    def test_alias_resolution_requires_evidence(self):
        graph = ResearchKnowledgeGraph()
        canon, _ = graph.add_entity("Model Context Protocol", "technology",
                                    source_ids=["s1"])
        dup, _ = graph.add_entity("MCP", "technology", source_ids=["s2"])
        assert graph.declare_alias(canon, "MCP") is False
        assert len(graph.entities) == 2
        assert graph.declare_alias(canon, "MCP", evidence_source_ids=["s2"]) is True
        assert len(graph.entities) == 1
        assert graph.find_by_name("model context protocol")[0].aliases == ["MCP"]

    def test_edges_require_confidence_and_support_multi_hop(self):
        graph = ResearchKnowledgeGraph()
        src, _ = graph.add_entity("example.com", "source")
        tech, _ = graph.add_entity("Widget", "technology")
        person, _ = graph.add_entity("Ada", "person")
        assert graph.link(src, "mentions", tech,
                          confidence=0.8, evidence_refs=["ev1"], source_ids=["s1"])
        assert graph.link(person, "authored", tech, confidence=0.6)
        chains = graph.multi_hop(src, max_hops=2)
        two_hop = [c for c in chains if len(c) == 2]
        assert chains and two_hop

    def test_relation_validation(self):
        graph = ResearchKnowledgeGraph()
        a, _ = graph.add_entity("X", "technology")
        b, _ = graph.add_entity("Y", "technology")
        with pytest.raises(ValueError):
            graph.link(a, "married_to", b)


class TestMemoryBridge:
    def test_records_carry_full_provenance(self):
        from agent.research.models import ResearchTask

        task = ResearchTask(user_query="q", research_id="abc123")
        claim = Claim(text="A strong corroborated finding.", status=ClaimStatus.CONFIRMED,
                      confidence=0.9, source_ids=["s1"])
        records = build_memory_records(task, [claim])
        meta = records[0].metadata
        assert {"source", "timestamp", "confidence", "scope"} <= set(meta)
        assert meta["source"] == "research:abc123"

    def test_empty_research_still_records_negative_result(self):
        from agent.research.models import ResearchTask

        task = ResearchTask(user_query="nothing found", research_id="zzz")
        records = build_memory_records(task, [])
        assert "No corroborated findings" in records[0].content


class TestTargets:
    def test_github_urls_and_classification(self):
        urls = github_research_urls("aetheros/aetheros/")
        assert urls["overview"].rstrip("/") == "https://github.com/aetheros/aetheros"
        from agent.research.models import classify_source_type

        assert classify_source_type(urls["overview"]).value == "TECHNICAL"

    def test_arxiv_ref_parsing_tracks_version(self):
        ref = parse_arxiv_ref("https://arxiv.org/abs/2401.12345v3")
        assert ref == {"arxiv_id": "2401.12345", "version": "v3"}

    def test_news_language_markers(self):
        assert classify_news_language("It was confirmed officially today.") == "confirmed"
        assert classify_news_language("allegedly, per unverified claims") == "alleged"
        assert classify_news_language("In my view this should be seen as good") == "opinion"
        assert classify_news_language("The company reported results according to filings") == "reported"

    def test_technical_query_hint(self):
        assert is_technical_query("how to install the sdk")
        assert not is_technical_query("best pizza toppings")


class TestRepository:
    def test_summarize_local_repo(self, tmp_path):
        root = tmp_path / "proj"
        (root / "pkg").mkdir(parents=True)
        (root / "pyproject.toml").write_text(
            '[project]\ndependencies = [\n "httpx>=0.28,<1",\n "click",\n]\n'
        )
        (root / "pkg" / "mod.py").write_text("def loader():\n    pass\n\nclass Engine:\n    pass\n")
        (root / "README.md").write_text("# proj\nDoes things.\n")
        summary = summarize_repository(str(root))
        assert summary.dependencies == ["httpx", "click"]
        assert summary.languages.get("python") == 1
        assert "loader" in summary.entry_points and "Engine" in summary.entry_points
        assert "Does things." in summary.readme_excerpt

    def test_missing_repo_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            summarize_repository(str(tmp_path / "nope"))


class TestAgents:
    def test_role_subtasks_shape(self):
        tasks = build_subtasks("mcp tasks api", ["primary_sources", "contradiction"])
        assert all(t.toolsets == ["web"] for t in tasks)
        delegate_payload = [t.to_delegate_dict() for t in tasks]
        assert delegate_payload[0]["role"] == "leaf"
        assert all("goal" in d for d in delegate_payload)

    def test_verification_task_includes_claims(self):
        tasks = build_subtasks("q", ["verification"], claims_to_verify=["claim one text"])
        assert tasks and "claim one text" in tasks[0].goal

    def test_team_runs_with_local_runner_and_merges_via_evidence(self):
        def runner(task):
            if task.role == "search":
                return [Claim(text="Widget v2 launched on 2026-05-01.",
                              source_ids=["s1"],
                              evidence=[Evidence(source_id="s1", location="l1")])]
            return [Claim(text="Widget v2 launched on 2026-05-01.",
                          source_ids=["s2"],
                          evidence=[Evidence(source_id="s2", location="l2")])]

        results = run_research_team(build_subtasks("widget", ["search", "industry"]),
                                    runner=runner)
        flat = [c for claims in results.values() for c in claims]
        merged = merge_through_evidence([flat], sources={})
        assert len(merged) == 1
        assert set(merged[0].source_ids) == {"s1", "s2"}
        assert len(merged[0].evidence) == 2

    def test_independent_verification_needs_domains(self):
        s_a = ResearchSource(url="https://a.example.com/x")
        s_b = ResearchSource(url="https://b.example.org/y")
        sources = {s_a.source_id: s_a, s_b.source_id: s_b}
        single_domain_claim = Claim(text="same", source_ids=[s_a.source_id])
        cross_domain_claim = Claim(text="other", source_ids=[s_a.source_id, s_b.source_id])
        assert not independently_verified(single_domain_claim, sources)
        assert independently_verified(cross_domain_claim, sources)

    def test_agent_output_arrives_unverified(self):
        from agent.research.agents import _claims_from_agent_output

        claims = _claims_from_agent_output(
            {"summary": "Totally true universal fact which must be checked carefully."}, "search"
        )
        assert claims[0].status == ClaimStatus.UNVERIFIED


class TestAdversarial:
    def test_disprove_targets_focus_on_strong_claims(self):
        strong = Claim(text="The flux capacitor enables time travel safely.", status=ClaimStatus.CONFIRMED)
        weak = Claim(text="Something uncertain remains unclear here overall.", status=ClaimStatus.UNVERIFIED)
        tasks = build_disprove_tasks([strong, weak], top_k=2)
        assert [t.claim_id for t in tasks] == [strong.claim_id]
        counter_vocab = ("criticism", "debunked", "disputed", "does not work")
        assert all(any(v in q for v in counter_vocab) for q in tasks[0].queries)

    def test_counter_evidence_marks_both_contradicted(self):
        claim = Claim(text="The migration completes within minutes reliably.",
                      status=ClaimStatus.CONFIRMED, source_ids=["s1"])
        absorbed = absorb_disprove_result(
            claim,
            "However the migration does not complete at all on large clusters",
            source_id="s2",
        )
        assert absorbed and claim.status == ClaimStatus.CONTRADICTED

    def test_bias_report_flags_concentration(self):
        sources = [
            ResearchSource(url=f"https://one.example.com/{i}") for i in range(4)
        ] + [ResearchSource(url="https://two.example.org/x")]
        claims = [Claim(text=f"c{i}", source_ids=[sources[0].source_id])
                  for i in range(3)]
        bias = detect_bias(sources, claims)
        assert bias.top_publisher_share > 0.5
        assert bias.single_source_ratio == 1.0
        assert bias.notes

    def test_diversify_caps_per_domain(self):
        candidates = [(f"https://same.example.com/{i}", f"t{i}") for i in range(5)]
        candidates.append(("https://other.example.org/a", "other"))
        kept = diversify_candidates(candidates, max_per_domain=2)
        domains = {url.split("//")[1].split("/")[0] for url, _ in kept}
        same_count = sum(1 for url, _ in kept if url.startswith("https://same."))
        assert same_count == 2 and "other.example.org" in {d.replace("www.", "") for d in domains}


class TestMultiProviderAndFallback:
    class _Provider:
        def __init__(self, name, results, available=True, fail=False):
            self._name = name
            self._results = results
            self._available = available
            self._fail = fail

        @property
        def name(self):
            return self._name

        def is_available(self):
            return self._available

        def supports_search(self):
            return True

        def search(self, query, limit=5):
            if self._fail:
                raise RuntimeError("boom")
            return {"success": True, "data": {"web": list(self._results)}}

    def test_fanout_merges_and_tags_providers(self):
        p1 = self._Provider("p1", [{"title": "T", "url": "https://x.test/a", "description": ""}])
        p2 = self._Provider("p2", [{"title": "T2", "url": "https://x.test/a", "description": ""},
                                   {"title": "B", "url": "https://b.test/", "description": ""}])
        fanout = FanOutSearch([p1, p2])
        response = fanout.search("q")
        web = response["data"]["web"]
        top = next(e for e in web if e["url"] == "https://x.test/a")
        assert top["providers"] == ["p1", "p2"]
        assert response["fanout"]["providers_queried"] == 2

    def test_fanout_survives_provider_failure(self):
        bad = self._Provider("bad", [], fail=True)
        good = self._Provider("good", [{"title": "ok", "url": "https://g.test/", "description": ""}])
        response = FanOutSearch([bad, good]).search("q")
        assert response["success"] and response["data"]["web"][0]["providers"] == ["good"]
        assert response["fanout"]["errors"]

    def test_fallback_chain_records_typed_failures(self):
        def step_timeout():
            raise TimeoutError("request timed out")

        chain = FallbackChain([
            ("timeout_step", step_timeout),
            ("fallback_step", lambda: {"found": True}),
        ])
        result = chain.run()
        assert result["success"] and result["via"] == "fallback_step"
        assert result["attempts"][0]["failure"] == "timeout"
