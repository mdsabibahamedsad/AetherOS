"""P98 — API contract: backward compatibility, serialization, error
handling, timeouts, authorization on new/modified orchestration APIs."""

import dataclasses
import json

import pytest

from agent.orchestration import types as orch_types
from agent.orchestration.blackboard import Artifact, TaskBlackboard
from agent.orchestration.catalog import get_specialists, select_team
from agent.orchestration.consensus import ConsensusOutcome, compare_results
from agent.orchestration.swarm import (
    ApprovalBoard,
    GlobalBudget,
    SwarmOrchestrator,
)
from agent.orchestration.swarm_guards import GrantedCapabilities, risk_from_capabilities
from agent.orchestration.types import FailureType, RiskLevel, TaskResult


def test_backward_compat_enum_members_preserved():
    # pre-M19 members must all still exist (additive-only evolution)
    assert {r.value for r in RiskLevel} >= {"low", "medium", "high", "critical"}
    assert {f.value for f in FailureType} >= {
        "timeout", "rate_limit", "auth_error", "provider_error", "tool_error",
        "permission_denied", "model_error", "validation_error",
        "network_error", "resource_exhausted", "unknown"}
    assert {r.value for r in orch_types.AgentRole} >= {
        "coordinator", "planner", "coding", "browser", "research", "qa",
        "security"}


def test_new_members_are_additive():
    assert RiskLevel.READ_ONLY.value == "read_only"
    assert FailureType.POLICY_ERROR.value == "policy_error"
    assert FailureType.SECURITY_ERROR.value == "security_error"
    assert FailureType.VERIFICATION_FAILURE.value == "verification_failure"


def test_task_result_new_fields_defaulted_for_compat():
    # old-style positional/keyword construction still works
    r = TaskResult(task_id="x", success=True)
    assert r.summary == "" and r.confidence == 0.5
    assert r.verification_needed is False and r.evidence_ids == []
    # is a plain dataclass → serializable via asdict
    payload = json.dumps(dataclasses.asdict(r), default=str)
    assert "task_id" in payload


def test_specialist_catalog_serializable_and_valid():
    for sid, m in get_specialists().items():
        d = m.to_dict()
        assert d["agent_id"] == sid
        assert d["risk_level"] in {"read_only", "low", "medium", "high",
                                   "critical"}
        json.dumps(d)  # must not raise


def test_team_selection_capability_based_contract():
    team = select_team(frozenset({"WEB_SEARCH", "RESEARCH", "TEST_EXECUTE"}),
                       max_agents=3)
    covered = set()
    for m in team:
        covered |= set(m.capabilities)
    assert {"WEB_SEARCH", "RESEARCH"} <= covered
    # unhealthy agents are never selected
    specialists = get_specialists()
    specialists["swarm.research"].health_status = "unavailable"
    try:
        team2 = select_team(frozenset({"WEB_SEARCH"}))
        assert all(m.health_status != "unavailable" for m in team2)
    finally:
        specialists["swarm.research"].health_status = "healthy"


def test_error_handling_unknown_agent_key(tmp_path):
    o = SwarmOrchestrator(executors={}, checkpoint_dir=None,
                          sleeper=lambda s: None)
    o.add_node("n", objective="x", agent_id="does-not-exist",
               required_capabilities={"FILE_READ"})
    result = o.run()   # must terminate, not hang or raise
    assert result["failed"] == 1
    assert o.nodes["n"].failure_kind is FailureType.AGENT_ERROR


def test_authorization_on_every_grant_check():
    g = GrantedCapabilities.grant(agent_id="a", task_id="t",
                                  requested=[], manifest_caps=[])
    with pytest.raises(Exception):
        g.check("MEMORY_READ")


def test_approval_board_contract_shapes():
    board = ApprovalBoard()
    rid = board.request(action="side_effect:SEND", task_id="t",
                        requested_by="agent")
    assert isinstance(rid, str) and rid
    assert isinstance(board.decide(rid, approved_by="human", approve=True),
                      bool)
    assert isinstance(board.authorize(action="side_effect:SEND", task_id="t",
                                      requester="agent"), bool)


def test_global_budget_serialization_shape():
    gb = GlobalBudget(total_tool_calls=10, remaining_tool_calls=7,
                      allocations={"n": 3})
    snap = {"total": gb.total_tool_calls, "remaining": gb.remaining_tool_calls,
            "allocations": dict(gb.allocations)}
    assert json.loads(json.dumps(snap))["remaining"] == 7


def test_consensus_outcome_values_stable():
    assert [o.value for o in ConsensusOutcome] == [
        "agreement", "disagreement", "partial_agreement",
        "insufficient_evidence"]


def test_compare_results_handles_empty_and_single():
    assert compare_results([]).outcome is ConsensusOutcome.INSUFFICIENT_EVIDENCE
    v = compare_results([__import__(
        "agent.orchestration.consensus",
        fromlist=["CandidateResult"]).CandidateResult("solo", "ans")])
    assert v.outcome is ConsensusOutcome.INSUFFICIENT_EVIDENCE


def test_blackboard_artifact_dataclass_fields():
    fields = {f.name for f in dataclasses.fields(Artifact)}
    assert {"artifact_id", "version", "kind", "content", "creator_agent",
            "task_id", "created_at", "parent_artifact", "hash",
            "provenance"} <= fields


def test_risk_derivation_total_over_all_capabilities():
    caps = __import__("agent.orchestration.swarm_guards",
                      fromlist=["ALL_CAPABILITIES"]).ALL_CAPABILITIES
    level = risk_from_capabilities(caps)
    assert level is RiskLevel.CRITICAL
