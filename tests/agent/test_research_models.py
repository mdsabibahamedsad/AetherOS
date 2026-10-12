"""Tests for agent.research.models — classification, scoring, objects."""

import pytest

from agent.research.models import (
    Claim,
    ClaimKind,
    ClaimStatus,
    Evidence,
    ResearchDepth,
    ResearchSource,
    TaskStatus,
    classify_source_type,
    compute_content_hash,
    detect_contradiction,
    score_source_quality,
)


class TestSourceTypeClassification:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://arxiv.org/abs/2401.12345", "ACADEMIC"),
            ("https://blog.acm.org/something", "ACADEMIC"),
            ("https://www.fda.gov/news", "GOVERNMENT"),
            ("https://docs.python.org/3/library/asyncio.html", "OFFICIAL"),
            ("https://developer.mozilla.org/en-US/docs/Web", "OFFICIAL"),
            ("https://www.reuters.com/world/item-123", "NEWS"),
            ("https://stackoverflow.com/q/12345", "COMMUNITY"),
            ("https://twitter.com/user/status/1", "SOCIAL"),
            ("https://github.com/aetheros/aetheros", "TECHNICAL"),
        ],
    )
    def test_classification(self, url, expected):
        assert classify_source_type(url).value == expected

    def test_unknown_for_empty(self):
        assert classify_source_type("") == classify_source_type("").UNKNOWN


class TestQualityScoring:
    def _source(self, **kw):
        return ResearchSource(url="https://example.com/doc", **kw)

    def test_score_bounds_and_flag(self):
        result = score_source_quality(self._source(), relevance=0.8)
        assert result["heuristic"] is True
        assert 0.0 <= result["total"] <= 1.0
        assert set(result["components"]) >= {
            "authority",
            "relevance",
            "recency",
            "independence",
        }

    def test_quarantine_degrades_score(self):
        clean = self._source()
        bad = self._source()
        bad.injection_flags = ["prompt_injection"]
        clean_score = score_source_quality(clean)["total"]
        bad_score = score_source_quality(bad)["total"]
        assert bad_score < clean_score

    def test_recency_uses_publication_date(self):
        old = self._source(publication_date="2001-01-01")
        new = self._source(publication_date="2026-01-01")
        assert score_source_quality(new)["components"]["recency"] > (
            score_source_quality(old)["components"]["recency"]
        )


class TestObjects:
    def test_claim_round_trip(self):
        ev = Evidence(
            claim_id="c1",
            source_id="s1",
            location="sentence:3",
            excerpt_reference="some excerpt",
            content_hash=compute_content_hash("some excerpt"),
        )
        claim = Claim(
            text="A statement of fact.",
            kind=ClaimKind.FACT,
            status=ClaimStatus.CONFIRMED,
            source_ids=["s1"],
            evidence=[ev],
            confidence=0.9,
        )
        restored = Claim.from_dict(claim.to_dict())
        assert restored.kind == ClaimKind.FACT
        assert restored.status == ClaimStatus.CONFIRMED
        assert restored.evidence[0].location == "sentence:3"

    def test_has_evidence_requires_linked_source(self):
        empty = Claim(text="x")
        assert not empty.has_evidence
        orphan = Claim(text="x", evidence=[Evidence(source_id="")])
        assert not orphan.has_evidence
        linked = Claim(text="x", evidence=[Evidence(source_id="s1")])
        assert linked.has_evidence

    def test_content_hash_stability(self):
        assert compute_content_hash("abc") == compute_content_hash("abc")
        assert compute_content_hash("abc") != compute_content_hash("abd")

    def test_depth_budgets_monotonic(self):
        from agent.research.models import ResearchTask

        order = [
            ResearchDepth.QUICK,
            ResearchDepth.STANDARD,
            ResearchDepth.DEEP,
            ResearchDepth.EXHAUSTIVE,
        ]
        prev_q = prev_s = 0
        for depth in order:
            b = ResearchTask(user_query="q", depth=depth).budget_for_depth()
            assert b["max_queries"] >= prev_q
            assert b["max_sources"] >= prev_s
            prev_q, prev_s = b["max_queries"], b["max_sources"]

    def test_task_round_trip_preserves_enums(self):
        from agent.research.models import ResearchTask

        task = ResearchTask(
            user_query="what?", depth=ResearchDepth.DEEP, status=TaskStatus.SEARCHING
        )
        restored = ResearchTask.from_dict(task.to_dict())
        assert restored.depth == ResearchDepth.DEEP
        assert restored.status == TaskStatus.SEARCHING


class TestContradictionDetection:
    def test_shared_keyword_plus_marker_flags(self):
        a = "The migration tool supports incremental checkpoints reliably"
        b = "However the migration tool does not support checkpoints at all"
        assert detect_contradiction(a, b)

    def test_unrelated_texts_are_clean(self):
        assert detect_contradiction(
            "Cats sleep sixteen hours daily on average",
            "Quantum processors require millikelvin temperatures",
        ) is None
