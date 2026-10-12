"""Unit: trust engine + reputation engine + attack defense."""

import time

import pytest

from aetheros_agent_market import schemas as S
from aetheros_agent_market.reputation import ReputationEngine
from aetheros_agent_market.trust_engine import AgentTrustEngine


def test_trust_no_signals_zero_confidence(home):
    eng = AgentTrustEngine(home)
    d = eng.dimension_score("ghost", "execution")
    assert d["score"] == 0.0 and d["confidence"] == 0.0 and d["samples"] == 0


def test_trust_bad_dimension_rejected(home):
    eng = AgentTrustEngine(home)
    with pytest.raises(ValueError):
        eng.record_signal(S.TrustSignal(agent_id="a", dimension="vibes", value=0.5))


def test_trust_value_bounds(home):
    eng = AgentTrustEngine(home)
    with pytest.raises(ValueError):
        eng.record_signal(S.TrustSignal(agent_id="a", dimension="execution", value=2.0))


def test_trust_decay_prefers_recent(home):
    eng = AgentTrustEngine(home)
    eng.record_signal(S.TrustSignal(
        agent_id="a", dimension="execution", source="outcome",
        kind="old", value=1.0, confidence=1.0,
        created_at=time.time() - 60 * 86400, decay_half_life_days=30.0))
    eng.record_signal(S.TrustSignal(
        agent_id="a", dimension="execution", source="outcome",
        kind="new", value=-1.0, confidence=1.0,
        created_at=time.time(), decay_half_life_days=30.0))
    d = eng.dimension_score("a", "execution")
    assert d["score"] < 0  # recent negative outweighs decayed positive


def test_incident_hits_security_hard_and_slow_decay(home):
    eng = AgentTrustEngine(home)
    eng.record_signal(S.TrustSignal(
        agent_id="a", dimension="security", source="verification",
        kind="clean", value=0.9, confidence=0.9,
        created_at=time.time() - 100 * 86400))
    eng.record_incident("a", "exfiltration")
    d = eng.dimension_score("a", "security")
    assert d["score"] < 0.2


def test_trust_profile_overall_with_components(home):
    eng = AgentTrustEngine(home)
    eng.record_outcome("a", "execution", True)
    eng.record_outcome("a", "execution", True)
    p = eng.profile("a")
    assert set(p["dimensions"]) == set(S.TRUST_DIMENSIONS)
    assert p["dimensions"]["execution"]["samples"] == 2


def test_reputation_empty_is_insufficient(home):
    eng = ReputationEngine(home)
    p = eng.profile("ghost")
    assert "insufficient_evidence" in p.flags
    assert p.get("task_success").confidence == 0.0


def test_reputation_verified_outweighs_noise(home):
    eng = ReputationEngine(home)
    for _ in range(5):
        eng.record("a", "task_success", 0.0, provenance="user_feedback",
                   reviewer="r1")
    eng.record("a", "task_success", 1.0, provenance="verified", tx_ref="tx-1")
    m = eng.metric("a", "task_success")
    assert m.sample_count == 6
    assert 0.0 < m.value < 1.0  # weighted, not raw average (5/6 would be 0.83)
    assert m.provenance in ("user_feedback", "verified")


def test_reputation_bad_metric_rejected(home):
    eng = ReputationEngine(home)
    with pytest.raises(ValueError):
        eng.record("a", "vibes", 0.5)


def test_review_burst_flagged_not_blacklisted(home):
    eng = ReputationEngine(home)
    for i in range(12):
        eng.record("a", "user_satisfaction", 1.0, provenance="user_feedback",
                   reviewer=f"r{i}")
    p = eng.profile("a")
    assert "suspected_review_burst" in p.flags
    # Metrics still computed; no permanent verdict.
    assert p.get("user_satisfaction").value == 1.0


def test_single_org_dominance_flagged(home):
    eng = ReputationEngine(home)
    for _ in range(6):
        eng.record("a", "task_success", 1.0, provenance="attestation", org="evilcorp")
    assert "single_org_dominance" in eng.profile("a").flags


def test_reciprocal_ratings_flagged(home):
    eng = ReputationEngine(home)
    for _ in range(5):
        eng.record("a", "user_satisfaction", 1.0, provenance="user_feedback",
                   reviewer="same-guy")
    assert "suspected_reciprocal_ratings" in eng.profile("a").flags


def test_task_outcome_helper(home):
    eng = ReputationEngine(home)
    eng.record_task_outcome("a", True, latency_ms=1000, verified=True,
                            tx_ref="tx-1", sla_met=True)
    assert eng.metric("a", "task_success").value == 1.0
    assert eng.metric("a", "sla_adherence").value == 1.0


def test_security_incident_recorded(home):
    eng = ReputationEngine(home)
    eng.record_security_incident("a", "prompt_injection", tx_ref="tx-9")
    assert eng.metric("a", "security").value == 0.0
