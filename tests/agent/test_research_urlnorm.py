"""Tests for URL canonicalization, domain intelligence, deduplication."""

import pytest

from agent.research.urlnorm import (
    SourceDeduplicator,
    dedup_key,
    is_subdomain_of,
    jaccard,
    near_duplicate,
    normalize_url,
    registrable_domain,
)


class TestNormalizeUrl:
    def test_strips_tracking_params_keeps_meaningful(self):
        url = (
            "https://WWW.Example.com/a/page?utm_source=x&id=42&fbclid=abc"
            "&q=keepme#section-2"
        )
        out = normalize_url(url)
        assert "utm_source" not in out
        assert "fbclid" not in out
        assert "id=42" in out
        assert "q=keepme" in out
        assert "#section-2" not in out
        assert out.startswith("https://example.com")

    def test_sorts_remaining_params(self):
        a = normalize_url("https://example.com/?b=2&a=1")
        b = normalize_url("https://example.com/?a=1&b=2")
        assert a == b

    def test_default_port_dropped_custom_port_kept(self):
        assert ":443" not in normalize_url("https://example.com:443/x")
        assert ":8443" in normalize_url("https://example.com:8443/x")

    def test_collapses_slashes_and_trailing(self):
        assert normalize_url("https://example.com/a//b///") == "https://example.com/a/b"

    def test_garbage_passthrough(self):
        assert normalize_url("") == ""
        assert normalize_url("not a url") == "not a url"


class TestDedupKey:
    def test_query_fragment_and_slash_ignored(self):
        base = "https://example.com/story"
        variants = [
            base,
            base + "/",
            base + "?utm_campaign=z",
            base + "?id=9",
            base + "#top",
        ]
        keys = {dedup_key(v) for v in variants}
        assert len(keys) == 1


class TestRegistrableDomain:
    @pytest.mark.parametrize(
        "host,expected",
        [
            ("a.b.example.com", "example.com"),
            ("www.example.co.uk", "example.co.uk"),
            ("foo.bar.gov.uk", "bar.gov.uk"),
            ("https://news.ycombinator.com/item?id=1", "ycombinator.com"),
            ("localhost", "localhost"),
        ],
    )
    def test_registrable(self, host, expected):
        assert registrable_domain(host) == expected

    def test_subdomain_check(self):
        assert is_subdomain_of("docs.a.example.com", "example.com")
        assert is_subdomain_of("example.com", "example.com")
        assert not is_subdomain_of("notexample.com", "example.com")


class TestSourceDeduplicator:
    def test_url_dedup(self):
        d = SourceDeduplicator()
        assert d.register_url("https://example.com/x?utm_source=t") is True
        assert d.register_url("https://www.example.com/x") is False
        assert d.seen_url("https://example.com/x#frag") == "https://example.com/x?utm_source=t"

    def test_mirror_counting(self):
        d = SourceDeduplicator()
        new1, n1 = d.register_content("hash1", "https://a.example/one")
        assert (new1, n1) == (True, 1)
        new2, n2 = d.register_content("hash1", "https://b.example/mirror")
        assert (new2, n2) == (False, 2)
        assert d.mirrors_of("hash1") == ["https://a.example/one", "https://b.example/mirror"]

    def test_independent_domains_counts_distinct(self):
        d = SourceDeduplicator()
        n = d.independent_domains(
            ["a.example.com", "b.example.org", "a.example.com", "c.org"]
        )
        assert n == 3

    def test_unique_pages(self):
        d = SourceDeduplicator()
        d.register_url("https://x.test/1")
        d.register_url("https://x.test/1?utm=a")
        d.register_url("https://x.test/2")
        assert d.unique_pages == 2


class TestNearDuplicate:
    LONG_A = (
        "the deployment pipeline builds every container image nightly then "
        "runs the full integration suite across three regional clusters "
        "before promoting artifacts into the production registry"
    )
    LONG_B = (
        "the deployment pipeline builds every container image nightly then "
        "runs the full integration suite across three regional clusters "
        "before promoting artifacts into the production registries"
    )

    def test_minor_edit_is_near_dup(self):
        assert near_duplicate(self.LONG_A, self.LONG_B)

    def test_different_topics_are_not(self):
        b = ("sourdough fermentation relies on wild yeast cultures kept at "
             "hydration ratios that shape crumb structure and flavor depth")
        assert not near_duplicate(self.LONG_A, b)

    def test_jaccard_bounds(self):
        assert 0.0 <= jaccard({"a", "b"}, {"b", "c"}) <= 1.0
        assert jaccard(set(), {"a"}) == 0.0
