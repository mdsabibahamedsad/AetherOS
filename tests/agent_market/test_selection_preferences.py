"""Unit: selection scoring + explanations + preferences/policy."""

from aetheros_agent_market.preferences import (
    AgentPreferences, PreferenceStore, apply_preferences, preference_veto,
)
from aetheros_agent_market.selection import (
    AgentSelectionEngine, CandidateSignals,
)
from aetheros_agent_market.taxonomy import MatchRequest


def _cand(**kw):
    base = dict(agent_id="a1", service_id="s1", capability_fit=1.0,
                trust_overall=0.8, trust_confidence=0.9, reliability=0.9,
                reliability_confidence=0.8, security=0.9,
                evidence_quality=0.8, price_minor=100, latency_ms=500.0)
    base.update(kw)
    return CandidateSignals(**base)


def test_hard_gates_reject():
    eng = AgentSelectionEngine()
    assert eng.score(_cand(available=False)).eligible is False
    assert eng.score(_cand(sla_ok=False)).rejection == "SLA requirements unmet"
    assert eng.score(_cand(privacy_ok=False)).rejection == "data policy violation"
    r = eng.score(_cand(price_minor=600), budget_minor=500)
    assert r.eligible is False and "budget" in r.rejection


def test_negative_trust_zeroes_score():
    eng = AgentSelectionEngine()
    assert eng.score(_cand(trust_overall=-1.0)).score == 0.0


def test_low_confidence_dampens():
    eng = AgentSelectionEngine()
    hi = eng.score(_cand()).score
    lo = eng.score(_cand(trust_confidence=0.0,
                         reliability_confidence=0.0)).score
    assert lo < hi


def test_explanation_references_real_breakdown():
    s = AgentSelectionEngine().score(_cand())
    text = s.explanation()
    for token in ("capability_fit", "trust=", "reliability=", "security=",
                  "evidence=", "cost_adj=", "latency_adj="):
        assert token in text


def test_rank_orders_and_tiebreaks():
    eng = AgentSelectionEngine()
    ranked = eng.rank([_cand(agent_id="b", reliability=0.5),
                       _cand(agent_id="a", reliability=0.9)])
    assert [r.agent_id for r in ranked] == ["a", "b"]
    tied = eng.rank([_cand(agent_id="b"), _cand(agent_id="a")])
    assert [r.agent_id for r in tied] == ["a", "b"]


def test_goals_change_weighting():
    cheap = _cand(agent_id="cheap", price_minor=0, latency_ms=5000.0,
                  reliability=0.7)
    fast = _cand(agent_id="fast", price_minor=5000, latency_ms=100.0,
                 reliability=0.7)
    assert AgentSelectionEngine("cheapest").rank([cheap, fast])[0].agent_id == "cheap"
    assert AgentSelectionEngine("fastest").rank([cheap, fast])[0].agent_id == "fast"


def test_bad_goal_rejected():
    import pytest
    with pytest.raises(ValueError):
        AgentSelectionEngine("vibes")


def test_compare_matrix():
    eng = AgentSelectionEngine()
    a, b = eng.score(_cand(agent_id="a")), eng.score(_cand(agent_id="b", reliability=0.1))
    m = eng.compare(a, b)
    assert m["A"]["agent_id"] == "a"
    row = next(r for r in m["rows"] if r["metric"] == "reliability_component")
    assert row["winner"] == "A"


def test_preferences_fold_into_request():
    prefs = AgentPreferences(min_trust_rank=4, max_price_minor=300,
                             blocked_agents=["evil"],
                             max_data_class="CONFIDENTIAL")
    req = apply_preferences(MatchRequest(data_class="PRIVATE"), prefs)
    assert req.min_trust_rank == 4
    assert req.max_price_minor == 300
    assert "evil" in req.exclude_agents
    # Ceiling tightens: PRIVATE request lowered to CONFIDENTIAL.
    assert req.data_class == "CONFIDENTIAL"


def test_preferences_never_loosen_request():
    prefs = AgentPreferences(max_data_class="HIGHLY_SENSITIVE")
    req = apply_preferences(MatchRequest(data_class="PUBLIC"), prefs)
    assert req.data_class == "PUBLIC"


def test_veto():
    prefs = AgentPreferences(blocked_agents=["a1"], blocked_orgs=["evil"])
    assert preference_veto("a1", "acme", prefs) is not None
    assert preference_veto("a2", "evil", prefs) is not None
    assert preference_veto("a2", "acme", prefs) is None


def test_effective_merge_tightens(home):
    store = PreferenceStore(home)
    store.put(AgentPreferences(min_trust_rank=4), scope="global")
    store.put(AgentPreferences(min_trust_rank=2, max_price_minor=100),
              scope="user", scope_id="u1")
    eff = store.effective([{"scope": "user", "scope_id": "u1"}])
    assert eff.min_trust_rank == 4  # floors only tighten
    assert eff.max_price_minor == 100
