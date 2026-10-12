"""Red-team campaign (P97), lookalike detection, risk history, P89 gate."""

import pytest

from agent.research.redteam import run_campaign, render_report
from agent.research.lookalike import assess_domain
from agent.research.approval_gate import (
    ConsequentialActionBlocked,
    is_readonly_research_action,
    request_consequential_action,
)
from agent.research.models import ResearchDepth
from agent.research.store import ResearchStore


@pytest.fixture(scope="module")
def campaign():
    return run_campaign()


class TestRedTeamCampaign:
    def test_no_vector_escaped(self, campaign):
        escaped = [r for r in campaign if r.outcome == "escaped"]
        assert not escaped, [r.vector for r in escaped]

    def test_all_vectors_reported(self, campaign):
        assert len(campaign) >= 12
        assert all(r.outcome in ("blocked", "flagged", "escaped")
                   for r in campaign)

    def test_critical_vectors_blocked(self, campaign):
        by_name = {r.vector: r for r in campaign}
        for name in ("prompt_injection_webpage", "redirect_to_metadata_ip",
                     "secret_exfil_query", "private_term_echo",
                     "mcp_output_exfiltration", "citation_poisoning_via_store"):
            assert by_name[name].outcome == "blocked", name

    def test_spoofing_vectors_at_least_flagged(self, campaign):
        by_name = {r.vector: r for r in campaign}
        assert by_name["homoglyph_brand_spoof"].outcome != "escaped"
        assert by_name["typosquat_tld_swap"].outcome != "escaped"
        assert by_name["source_spoofing_by_title"].outcome == "blocked"

    def test_markdown_report_renders(self, campaign):
        report = render_report(campaign)
        assert "Escaped: 0 /" in report


class TestLookalikeDomains:
    def test_homoglyph_cyrillic_detected(self):
        verdict = assess_domain("https://pаypal.com/login")  # Cyrillic 'а'
        assert verdict.kind == "homoglyph"
        assert verdict.lookalike_of.endswith("paypal.com")

    def test_typosquat_tld_swap(self):
        verdict = assess_domain("github.org")
        assert verdict.kind in ("typosquat", "skeleton_match")
        assert "github" in verdict.lookalike_of

    def test_legitimate_exact_domains_clean(self):
        for domain in ("github.com", "arxiv.org", "example.com",
                       "docs.python.org"):
            assert assess_domain(domain).kind == "none", domain

    def test_extra_references_considered(self):
        verdict = assess_domain("mybank-secure.com", extra_references=["mybank.com"])
        assert verdict.kind in ("typosquat", "skeleton_match")

    def test_risk_bump_ordering(self):
        from agent.research.lookalike import LookalikeVerdict, risk_bump

        assert risk_bump(LookalikeVerdict("none")) == 0.0
        assert risk_bump(LookalikeVerdict("typosquat")) < \
            risk_bump(LookalikeVerdict("homoglyph"))


class TestDomainRiskHistory:
    def test_bump_and_factor(self, tmp_path):
        store = ResearchStore(db_path=tmp_path / "dom.db")
        try:
            store.bump_domain("shady.test", "fetches")
            store.bump_domain("shady.test", "quarantined")
            factor = store.domain_risk_factor("shady.test")
            assert 0 < factor <= 1.0
            assert store.domain_risk_factor("unknown.test") == 0.0
            with pytest.raises(ValueError):
                store.bump_domain("x.test", "nonsense_field")
        finally:
            store.close()

    def test_history_raises_admission_risk(self, tmp_path):
        from agent.research.engine import ResearchEngine
        from tests.agent.test_research_scenarios import (
            FakeSearch,
            FakeExtract,
            simple_results,
        )

        store = ResearchStore(db_path=tmp_path / "hist.db")
        try:
            store.bump_domain("repeat.test", "quarantined")
            store.bump_domain("repeat.test", "quarantined")
            engine = ResearchEngine(
                store=store, url_gate=lambda u: (True, ""),
                search_provider=FakeSearch(simple_results([
                    ("https://repeat.test/page", "R", "")])),
                extract_provider=FakeExtract({}),
            )
            task = engine.start("history check", depth=ResearchDepth.QUICK)
            engine.run(task.research_id)
            src = next(s for s in store.list_sources(task.research_id))
            assert src.risk > 0
            assert src.metadata.get("domain_history_risk", 0) > 0
        finally:
            store.close()


class TestApprovalGate:
    def test_readonly_actions_pass_without_approver(self):
        assert request_consequential_action("research.search", "q") is True
        assert request_consequential_action("research.fetch", "url") is True
        assert request_consequential_action("research.ingest_local", "p") is True

    def test_consequential_fails_closed(self):
        with pytest.raises(ConsequentialActionBlocked):
            request_consequential_action("email.send", "to ops@x")
        with pytest.raises(ConsequentialActionBlocked):
            request_consequential_action("repo.push", "origin main")

    def test_approver_decision_honored_both_ways(self):
        assert request_consequential_action(
            "file.upload", "report.md",
            approver=lambda a, d: True) is True
        with pytest.raises(ConsequentialActionBlocked):
            request_consequential_action(
                "file.upload", "report.md",
                approver=lambda a, d: False)

    def test_prefix_scope_is_tight(self):
        assert not is_readonly_research_action("research.publish")
        assert not is_readonly_research_action("terminal.exec")
