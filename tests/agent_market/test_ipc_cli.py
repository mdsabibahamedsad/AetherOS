"""Unit: IPC validation + CLI wiring (no ModelProvider surprises)."""

import pytest

from aetheros_agent_market import ipc as IPC


def test_ipc_method_surface():
    expected = {"marketplace.search", "marketplace.agent.get",
                "marketplace.service.get", "marketplace.compare",
                "marketplace.quote", "marketplace.contract.create",
                "marketplace.contract.approve", "marketplace.delegate",
                "marketplace.task.status", "marketplace.transaction.get",
                "marketplace.reputation.get", "marketplace.trust.get",
                "marketplace.budget.get", "marketplace.policy.get",
                "marketplace.policy.update", "marketplace.dispute.create"}
    assert set(IPC.IPC_METHODS) == expected


def test_ipc_rejects_bad_ids():
    with pytest.raises(ValueError):
        IPC.agent_get({"id": ""})
    with pytest.raises(ValueError):
        IPC.agent_get({"id": "x" * 200})
    with pytest.raises(ValueError):
        IPC.agent_get({"id": "a\nb"})


def test_ipc_rejects_bad_amounts():
    with pytest.raises(ValueError):
        IPC.search({"query": "x", "max_price_minor": -5})
    with pytest.raises(ValueError):
        IPC.search({"query": "x", "max_price_minor": 1.5})


def test_ipc_compare_requires_2_to_3():
    with pytest.raises(ValueError):
        IPC.compare({"agent_ids": ["only-one"]})
    with pytest.raises(KeyError):
        IPC.compare({"agent_ids": ["ghost-1", "ghost-2"]})


def test_ipc_quote_contract_require_objects():
    with pytest.raises(ValueError):
        IPC.quote_create({})
    with pytest.raises(ValueError):
        IPC.contract_create({"contract": "not-an-object"})


def test_ipc_delegate_requires_task_and_selection():
    with pytest.raises(ValueError):
        IPC.delegate({"task": {}})


def test_ipc_dispute_validates_fields():
    with pytest.raises(ValueError):
        IPC.dispute_create({"dispute": {"reason": "overcharge"}})


def test_ipc_budget_scope_validated():
    with pytest.raises(ValueError):
        IPC.budget_get({"scope": "everything"})


def test_ipc_search_empty_index_ok():
    res = IPC.search({"query": "translate legal docs", "limit": 5})
    assert res["hits"] == [] and res["query"] == "translate legal docs"


def test_ipc_policy_roundtrip():
    before = IPC.policy_get({})
    assert "preferences" in before and "flags" in before
    updated = IPC.policy_update({"preferences": {
        **before["preferences"], "min_trust_rank": 5}})
    assert updated["preferences"]["min_trust_rank"] == 5
    # Restore safe default for other tests (isolated home per process, but be polite).
    IPC.policy_update({"preferences": {
        **updated["preferences"], "min_trust_rank": 3}})


def test_cli_parser_builds():
    import argparse
    from aetheros_cli.marketplace_cmd import build_parser
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    build_parser(sub)
    args = parser.parse_args(["agent-marketplace", "search", "translate docs"])
    assert args.market_verb == "search" and args.query == "translate docs"
    args = parser.parse_args(["agent-market", "compare", "a", "b"])
    assert args.ids == ["a", "b"]
    args = parser.parse_args(["agent-marketplace", "budget", "--scope", "user"])
    assert args.scope == "user"
