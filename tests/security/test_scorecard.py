"""Tests for aetheros_security.scorecard (security posture evaluation)."""

from aetheros_security.scorecard import (
    ScoreStatus,
    SecurityScorecard,
    generate_scorecard,
    get_scorecard,
)


class TestScorecard:
    def test_generate_returns_full_schema(self):
        card = generate_scorecard()
        assert set(card.keys()) == {"generated_at", "categories", "summary", "overall"}
        assert card["summary"]["total"] == len(card["categories"])
        assert card["summary"]["total"] >= 20  # every subsystem probed

    def test_every_category_has_status(self):
        card = generate_scorecard()
        for row in card["categories"]:
            assert row["category"]
            assert row["status"] in {s.value for s in ScoreStatus}
            assert row["checks"]

    def test_core_categories_present(self):
        card = generate_scorecard()
        categories = {row["category"] for row in card["categories"]}
        for expected in ("Identity", "Authentication", "Authorization",
                         "Secrets", "Data Protection", "Tool Security",
                         "Network Security", "Audit", "Emergency Controls"):
            assert expected in categories

    def test_fail_safe_defaults_score_high(self):
        # Probes are fail-safe; on a fresh hermetic env, most should PASS.
        card = generate_scorecard()
        assert card["overall"]["score"] >= 50
        assert card["overall"]["verdict"] in {"STRONG", "GOOD", "NEEDS_ATTENTION", "WEAK"}

    def test_default_deny_probe_holds(self):
        # Authorization probe asserts an unknown principal is denied.
        card = generate_scorecard()
        by_name = {row["category"]: row["status"] for row in card["categories"]}
        assert by_name["Authorization"] == ScoreStatus.PASS.value

    def test_singleton(self):
        assert get_scorecard() is get_scorecard()
        assert isinstance(get_scorecard(), SecurityScorecard)