"""Two-phase completion, critic, consensus, layered confidence (P24-30)."""

import pytest

from agent.orchestration.consensus import (
    CandidateResult,
    ConsensusOutcome,
    LayeredConfidence,
    compare_results,
    critique,
)
from agent.orchestration.synthesis import (
    FinalStatus,
    FinalValidation,
    VerifiedContribution,
    synthesize,
)


def test_critic_flags_missing_evidence_and_hedging():
    r = critique(task_id="t1", result_summary="should work now",
                 success_criteria=["tests pass"], evidence_ids=[])
    assert r.verdict == "concerns"
    assert any("no artifacts" in m for m in r.missing_evidence)
    assert any("hedged" in a for a in r.assumptions)


def test_critic_passes_clean_result():
    r = critique(task_id="t2", result_summary="all tests pass locally",
                 success_criteria=["tests pass"],
                 evidence_ids=["art-1"])
    assert r.verdict == "pass"


def test_consensus_agreement():
    a = CandidateResult(agent_id="r1", answer="python",
                        key_facts=["python is the implementation language"],
                        confidence=0.9)
    b = CandidateResult(agent_id="r2", answer="python",
                        key_facts=["python is the implementation language"],
                        confidence=0.8)
    v = compare_results([a, b])
    assert v.outcome is ConsensusOutcome.AGREEMENT
    assert v.agreement_ratio >= 0.5


def test_consensus_disagreement_not_forced():
    a = CandidateResult(agent_id="r1", answer="postgres",
                        key_facts=["database engine postgres"])
    b = CandidateResult(agent_id="r2", answer="mysql",
                        key_facts=["database engine mysql"])
    v = compare_results([a, b])
    assert v.outcome is ConsensusOutcome.DISAGREEMENT
    assert v.dissenting_agents


def test_single_candidate_is_insufficient_evidence():
    v = compare_results([CandidateResult(agent_id="solo", answer="x")])
    assert v.outcome is ConsensusOutcome.INSUFFICIENT_EVIDENCE


def test_layered_confidence_gated_by_verification():
    lc = LayeredConfidence(result=0.9, evidence=0.8, verification=0.0)
    low = lc.compose()
    lc2 = LayeredConfidence(result=0.9, evidence=0.8, verification=0.9)
    high = lc2.compose()
    assert high > low
    assert 0.0 <= low <= 1.0 and 0.0 <= high <= 1.0


# -- two-phase completion (P27) --------------------------------------------------

def _contrib(verified, required=True):
    return VerifiedContribution(
        task_id="t", agent_id="a", summary="work done", verified=verified,
        required=required,
        conflicts=["two agents disagree on X"] if verified else [],
        uncertainties=["latency numbers approximate"] if verified else [],
        citations=["source://docs/1"] if verified else [],
    )


def test_unverified_required_never_success():
    v = FinalValidation(requirements_satisfied=True, artifacts_exist=True)
    res = synthesize([_contrib(verified=False)], validation=v)
    assert res.status in (FinalStatus.PARTIAL, FinalStatus.FAILED)
    assert res.status is not FinalStatus.SUCCESS


def test_verified_with_clean_validation_is_success():
    v = FinalValidation(requirements_satisfied=True, artifacts_exist=True)
    res = synthesize([_contrib(verified=True)], validation=v,
                     objective="ship it")
    assert res.status is FinalStatus.SUCCESS
    # P88 — conflicts/uncertainty preserved verbatim
    assert res.conflicts_preserved and res.uncertainties_preserved
    assert res.citations == ["source://docs/1"]
    assert "Objective: ship it" in res.answer


def test_failed_validation_downgrades_to_partial():
    v = FinalValidation(requirements_satisfied=True, artifacts_exist=False)
    res = synthesize([_contrib(verified=True)], validation=v)
    assert res.status is FinalStatus.PARTIAL


def test_empty_contributions_fail():
    res = synthesize([], validation=FinalValidation(requirements_satisfied=True))
    assert res.status is FinalStatus.FAILED
