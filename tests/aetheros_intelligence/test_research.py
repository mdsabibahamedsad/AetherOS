"""Tests for the AetherOS Research Mode (aetheros_intelligence.research).

These tests assert the honesty contracts of the research engine:
  * Findings never carry fabricated URLs (no ``web.search`` style stubs).
  * Web/docs/github searches return only what the real backend returns.
  * Unavailable backends degrade to empty results, never fake ones.
  * Duplicate sources are deduplicated across backends.
"""

import json
from unittest import mock

import pytest

from aetheros_intelligence.research import (
    ResearchFinding,
    ResearchMode,
    ResearchReport,
)


def _search_payload(rows):
    """Build the JSON string shape ``web_search_tool`` returns."""
    return json.dumps({
        "success": True,
        "data": {
            "web": [
                {
                    "title": row.get("title", f"Title {i}"),
                    "url": row.get("url", f"https://example.com/{i}"),
                    "description": row.get("description", f"Description {i}"),
                    "position": i + 1,
                }
                for i, row in enumerate(rows)
            ]
        },
    })


class TestSearchWeb:
    def test_returns_real_results_from_backend(self):
        rm = ResearchMode()
        payload = _search_payload([
            {"url": "https://realpy.org/async", "title": "Async guide"},
        ])
        with mock.patch("tools.web_tools.web_search_tool",
                        return_value=payload) as mock_search:
            findings = rm._search_web("python async")

        assert len(findings) == 1
        assert findings[0].url == "https://realpy.org/async"
        assert findings[0].title == "Async guide"
        assert findings[0].source == "web"
        assert mock_search.called

    def test_no_fabricated_urls_in_web_results(self):
        rm = ResearchMode()
        payload = _search_payload([
            {"url": "https://example.org/a", "title": "A"},
            {"url": "https://example.org/b", "title": "B"},
        ])
        with mock.patch("tools.web_tools.web_search_tool",
                        return_value=payload):
            findings = rm._search_web("something")

        urls = [f.url for f in findings]
        assert all(u.startswith("https://") for u in urls)
        assert not any("web.search" in u for u in urls)
        assert not any("fabricat" in u.lower() for u in urls)

    def test_skips_entries_missing_url_or_title(self):
        rm = ResearchMode()
        payload = json.dumps({
            "success": True,
            "data": {"web": [
                {"title": "No url", "description": "d"},
                {"url": "https://example.org/t", "title": "", "description": "d"},
                {"url": "https://example.org/t2", "title": "Valid"},
            ]},
        })
        with mock.patch("tools.web_tools.web_search_tool",
                        return_value=payload):
            findings = rm._search_web("q")

        assert len(findings) == 1
        assert findings[0].title == "Valid"

    def test_graceful_when_backend_unconfigured(self):
        rm = ResearchMode()
        payload = json.dumps({
            "success": False,
            "error": "No web search provider configured",
        })
        with mock.patch("tools.web_tools.web_search_tool",
                        return_value=payload):
            findings = rm._search_web("python")

        assert findings == []

    def test_graceful_when_backend_raises(self):
        rm = ResearchMode()
        with mock.patch("tools.web_tools.web_search_tool",
                        side_effect=RuntimeError("boom")):
            findings = rm._search_web("python")

        assert findings == []


class TestSearchDocs:
    def test_returns_only_real_doc_results(self):
        rm = ResearchMode()
        payload = _search_payload([
            {"url": "https://docs.python.org/3/tutorial/", "title": "Tutorial"},
            {"url": "https://example.org/random", "title": "Random"},
        ])
        with mock.patch("tools.web_tools.web_search_tool",
                        return_value=payload) as mock_search:
            findings = rm._search_docs("python")

        assert len(findings) == 1
        assert findings[0].source == "docs"
        assert findings[0].url == "https://docs.python.org/3/tutorial/"
        # Backend must be invoked with a site-scoped query
        assert mock_search.call_args[0][0].startswith("python")

    def test_empty_when_backend_unavailable(self):
        rm = ResearchMode()
        with mock.patch("tools.web_tools.web_search_tool",
                        return_value='{"success": false}'):
            assert rm._search_docs("python") == []


class TestSearchGithub:
    def test_keeps_only_github_urls(self):
        rm = ResearchMode()
        payload = _search_payload([
            {"url": "https://github.com/a/b", "title": "Repo"},
            {"url": "https://pypi.org/project/x", "title": "Not gh"},
            {"url": "https://github.com/c/d", "title": "Repo 2"},
        ])
        with mock.patch("tools.web_tools.web_search_tool",
                        return_value=payload):
            findings = rm._search_github("python")

        assert len(findings) == 2
        assert all("github.com" in f.url for f in findings)
        assert all(f.source == "github" for f in findings)

    def test_empty_when_no_github_results(self):
        rm = ResearchMode()
        payload = _search_payload([
            {"url": "https://pypi.org/project/x", "title": "Not gh"},
        ])
        with mock.patch("tools.web_tools.web_search_tool",
                        return_value=payload):
            assert rm._search_github("python") == []


class TestSearchKnowledge:
    def test_returns_real_knowledge_results(self):
        rm = ResearchMode()
        engine_results = [
            {"title": "KB doc", "content": "content", "score": 0.9, "url": "file:///kb/x"},
        ]
        with mock.patch("aetheros_knowledge.search.engine.SearchEngine") as mock_engine:
            mock_engine.return_value.hybrid_search.return_value = engine_results
            findings = rm._search_knowledge("python")

        assert len(findings) == 1
        assert findings[0].source == "knowledge"
        assert findings[0].url == "file:///kb/x"

    def test_empty_on_backend_error(self):
        rm = ResearchMode()
        with mock.patch("aetheros_knowledge.search.engine.SearchEngine",
                        side_effect=ImportError("no kb")):
            assert rm._search_knowledge("python") == []


class TestSearchFiles:
    def test_returns_real_local_matches(self, tmp_path):
        rm = ResearchMode()
        payload = json.dumps({"files": [str(tmp_path / "foo.py"),
                                        str(tmp_path / "bar.py")]})
        with mock.patch("tools.file_tools.search_tool",
                        return_value=payload) as mock_search:
            with mock.patch("os.getcwd", return_value=str(tmp_path)):
                findings = rm._search_files("def main")

        assert len(findings) == 2
        assert findings[0].source == "files"
        assert findings[0].url.startswith("file://")
        assert mock_search.called

    def test_empty_when_no_files(self, tmp_path):
        rm = ResearchMode()
        with mock.patch("tools.file_tools.search_tool",
                        return_value='{"files": []}'):
            with mock.patch("os.getcwd", return_value=str(tmp_path)):
                assert rm._search_files("zzzz") == []

    def test_empty_when_backend_fails(self, tmp_path):
        rm = ResearchMode()
        with mock.patch("tools.file_tools.search_tool",
                        side_effect=RuntimeError("no rg")):
            with mock.patch("os.getcwd", return_value=str(tmp_path)):
                assert rm._search_files("zzzz") == []


class TestDedupeFindings:
    def test_dedupes_by_url_keeps_highest_relevance(self):
        findings = [
            ResearchFinding(source="web", title="Low", url="https://x.com/a",
                            relevance=0.4),
            ResearchFinding(source="docs", title="High", url="https://x.com/a",
                            relevance=0.9),
        ]
        unique = ResearchMode._dedupe_findings(findings)
        assert len(unique) == 1
        assert unique[0].title == "High"
        assert unique[0].source == "docs"

    def test_dedupes_urlless_by_source_title(self):
        findings = [
            ResearchFinding(source="knowledge", title="Same", relevance=0.5),
            ResearchFinding(source="knowledge", title="Same", relevance=0.7),
            ResearchFinding(source="knowledge", title="Other", relevance=0.6),
        ]
        unique = ResearchMode._dedupe_findings(findings)
        assert len(unique) == 2

    def test_does_not_collapse_distinct_urls(self):
        findings = [
            ResearchFinding(source="web", title="A", url="https://x.com/a"),
            ResearchFinding(source="web", title="B", url="https://x.com/b"),
        ]
        assert len(ResearchMode._dedupe_findings(findings)) == 2


class TestResearchIntegration:
    def test_research_never_emits_fabricated_urls(self):
        rm = ResearchMode()
        payload = _search_payload([
            {"url": "https://example.org/r1", "title": "R1"},
            {"url": "https://example.org/r2", "title": "R2"},
        ])
        with mock.patch("tools.web_tools.web_search_tool", return_value=payload):
            result = rm.research("something", sources=["web"])

        assert result["findings"]
        assert len(result["findings"]) == 2
        for f in result["findings"]:
            assert f["url"].startswith("https://")
            assert "web.search" not in f["url"]

    def test_research_dedupes_cross_source_duplicates(self):
        rm = ResearchMode()
        # Both web and github sources resolve to the same URL.
        web_payload = _search_payload([
            {"url": "https://github.com/a/b", "title": "Same repo"},
        ])
        with mock.patch("tools.web_tools.web_search_tool", return_value=web_payload):
            result = rm.research("python", sources=["web", "github"])

        urls = [f["url"] for f in result["findings"]]
        assert len(urls) == len(set(urls))

    def test_research_summary_reports_empty_sources(self):
        rm = ResearchMode()
        with mock.patch("tools.web_tools.web_search_tool",
                        return_value='{"success": false}'):
            result = rm.research("python", sources=["web", "docs", "github"])

        assert result["findings"] == []
        assert "no results" in result["summary"].lower()
        assert "github" in result["summary"].lower()

    def test_deep_research_uses_all_sources(self):
        rm = ResearchMode()

        def _payload_for(query, *args, **kwargs):
            if "site:github.com" in query:
                rows = [{"url": "https://github.com/a/b", "title": "Repo"}]
            elif "site:" in query:
                rows = [{"url": "https://docs.python.org/3/", "title": "Docs"}]
            else:
                rows = [{"url": "https://example.org/d1", "title": "D1"}]
            return _search_payload(rows)

        with mock.patch("tools.web_tools.web_search_tool",
                        side_effect=_payload_for):
            result = rm.deep_research("python", depth=1)

        sources = {f["source"] for f in result["findings"]}
        # _research_topic_deep level 0 must consult web+docs+github, not
        # just a single hardcoded source.
        assert "web" in sources
        assert "docs" in sources
        assert "github" in sources
        for f in result["findings"]:
            assert "web.search" not in f["url"]

    def test_report_to_dict_includes_metadata(self):
        report = ResearchReport(query="q")
        report.findings = [
            ResearchFinding(source="web", title="T", url="https://x.com",
                            metadata={"position": 1}),
        ]
        out = ResearchMode()._report_to_dict(report)
        assert out["findings"][0]["metadata"]["position"] == 1


class TestExtractSubtopics:
    def test_no_crash_on_empty_words(self):
        rm = ResearchMode()
        findings = [
            ResearchFinding(source="web", title="   ", url="https://x.com"),
            ResearchFinding(source="web", title="", url="https://y.com"),
            ResearchFinding(source="web", title="Python Async Patterns",
                            url="https://z.com"),
        ]
        subs = rm._extract_subtopics(findings)
        assert isinstance(subs, list)
        assert len(subs) <= 3
