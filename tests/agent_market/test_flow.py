"""Integration: full gated pipeline through MarketplaceFlow (stub A2A)."""

import pytest

from aetheros_agent_market.flow import FlowError, MarketplaceFlow
from tests.agent_market.conftest import StubGateway, seed_service


def _enable(flow):
    flow.flags.set("marketplace", True, by="test")
    flow.flags.set("remote_delegation", True, by="test")


def _task(**kw):
    base = {"summary": "summarize test doc",
            "capabilities": ["documents.summarize"],
            "data_class": "INTERNAL",
            "verification_requirements": ["schema"],
            "payment_provider": "none",
            "requester": "test-user"}
    base.update(kw)
    return base


def test_safe_defaults_block_delegation(flow):
    _ident, svc = seed_service(flow)
    with pytest.raises(PermissionError, match="remote_delegation"):
        flow.delegate(_task(), {"service_id": svc.service_id,
                                "agent_id": svc.agent_id})


def test_free_end_to_end(flow):
    _ident, svc = seed_service(flow)
    _enable(flow)
    rec = flow.recommend({"query": "summarize research",
                          "capabilities": ["research.web_search"]})
    assert rec["candidates"], "seeded service must be discoverable"
    assert rec["local"]["local_capable"] is True
    assert rec["explanations"] and "capability_fit" in rec["explanations"][0]

    out = flow.delegate(_task(), {"service_id": svc.service_id,
                                  "agent_id": svc.agent_id})
    assert out["status"] == "running"
    assert out["network_task_id"].startswith("rt-")

    polled = flow.poll(out["delegation_id"])
    assert polled["status"] == "evidence_received"  # stub reports completed

    done = flow.complete(out["delegation_id"], {"summary": "done"})
    assert done["status"] == "completed"
    assert done["verification"]["passed"] is True

    # Settlement: zero-amount capture recorded, reputation updated.
    txs = flow.ledger.entries()
    kinds = {e.event for e in txs}
    assert {"QUOTE_CREATED", "AUTHORIZATION_CREATED", "EXECUTION_STARTED",
            "EXECUTION_COMPLETED", "CAPTURED"} <= kinds
    assert flow.reputation.metric(svc.agent_id, "task_success").sample_count >= 1
    assert flow.accounting.variance(out["delegation_id"])["settled"] is True
    events = flow.events.list(correlation_id=out["correlation_id"])
    assert {e["type"] for e in events} >= {"ContractCreated", "ContractApproved",
                                           "PaymentAuthorized", "DelegationStarted",
                                           "VerificationPassed", "PaymentCaptured",
                                           "ReputationUpdated"}
    dlg_events = flow.events.list(delegation_id=out["delegation_id"])
    assert {e["type"] for e in dlg_events} >= {"PaymentAuthorized",
                                               "DelegationStarted",
                                               "VerificationPassed",
                                               "PaymentCaptured",
                                               "ReputationUpdated"}


def test_verification_failure_voids_and_fails(flow):
    _ident, svc = seed_service(flow)
    _enable(flow)
    out = flow.delegate(_task(verification_requirements=["expected_output"],
                              success_criteria=["$12m revenue figure"]),
                        {"service_id": svc.service_id, "agent_id": svc.agent_id})
    done = flow.complete(out["delegation_id"], "wrong content entirely")
    assert done["status"] == "failed"
    assert done["verification"]["passed"] is False
    kinds = {e.event for e in flow.ledger.entries()}
    assert "VOIDED" in kinds


def test_paid_requires_flag_budget_and_approval(flow, home):
    _ident, svc = seed_service(flow, pricing="per_task", price_minor=400)
    _enable(flow)
    task = _task(payment_provider="credits")
    # Paid agents disabled by default.
    with pytest.raises(PermissionError, match="paid_agents"):
        flow.delegate(task, {"service_id": svc.service_id, "agent_id": svc.agent_id})
    flow.flags.set("paid_agents", True, by="test")
    # No budget configured: spend check passes (no limits) but tier is HUMAN.
    out = flow.delegate(task, {"service_id": svc.service_id, "agent_id": svc.agent_id})
    assert out["status"] == "awaiting_approval"
    assert out["tier"] == "HUMAN_APPROVAL"
    assert out["amount_minor"] == 400


def test_paid_approved_end_to_end(flow):
    from aetheros_agent_market import schemas as S
    from aetheros_agent_market.payments import get_provider
    _ident, svc = seed_service(flow, pricing="per_task", price_minor=400)
    get_provider("credits", flow.home).top_up(10000)
    _enable(flow)
    flow.flags.set("paid_agents", True, by="test")
    flow.flags.set("automatic_payment", True, by="test")
    flow.budgets.set_budget(S.Budget(
        budget_id="b", scope="user", currency="USD",
        daily_limit_minor=100000, per_task_limit_minor=10000,
        approval_threshold_minor=5000, auto_approve_limit_minor=1000))
    out = flow.delegate(_task(payment_provider="credits"),
                        {"service_id": svc.service_id, "agent_id": svc.agent_id},
                        approved_by="test-user")
    assert out["status"] == "running"
    done = flow.complete(out["delegation_id"], {"summary": "paid work done"})
    assert done["status"] == "completed"
    kinds = {e.event for e in flow.ledger.entries()}
    assert "CAPTURED" in kinds
    assert flow.budgets.usage("user")["spent_minor"] == 400


def test_autonomous_purchase_bounded_by_policy(flow):
    from aetheros_agent_market import schemas as S
    _ident, svc = seed_service(flow, pricing="per_task", price_minor=400)
    _enable(flow)
    flow.flags.set("paid_agents", True, by="test")
    flow.flags.set("automatic_payment", True, by="test")
    flow.budgets.set_budget(S.Budget(
        budget_id="b", scope="user", currency="USD",
        daily_limit_minor=100000, per_task_limit_minor=10000,
        approval_threshold_minor=5000, auto_approve_limit_minor=1000))
    from aetheros_agent_market.preferences import AgentPreferences
    flow.preferences.put(AgentPreferences(payment_limit_minor=100))
    with pytest.raises(FlowError, match="auto-purchase policy"):
        flow.delegate(_task(payment_provider="credits"),
                      {"service_id": svc.service_id, "agent_id": svc.agent_id},
                      auto=True)


def test_priced_quote_with_free_provider_refused(flow):
    _ident, svc = seed_service(flow, pricing="per_task", price_minor=400)
    _enable(flow)
    flow.flags.set("paid_agents", True, by="test")
    with pytest.raises(FlowError, match="explicit payment provider"):
        flow.delegate(_task(payment_provider="none"),
                      {"service_id": svc.service_id, "agent_id": svc.agent_id},
                      approved_by="test-user")


def test_fallback_rules(flow):
    _ident, svc = seed_service(flow)
    _enable(flow)
    out = flow.delegate(_task(), {"service_id": svc.service_id,
                                  "agent_id": svc.agent_id})
    # Contract forbids fallback by default.
    with pytest.raises(FlowError, match="forbids fallback"):
        flow.fallback(out["delegation_id"],
                      {"service_id": svc.service_id, "agent_id": svc.agent_id})
    # Mark failed, allow fallback via amendment, then succeed cheaply.
    raw = flow._delegations.get(out["delegation_id"])
    raw["status"] = "failed"
    flow._delegations.put(out["delegation_id"], raw)
    amended = flow.contracts.amend(out["contract_id"], {"price_minor": 0})
    flow.contracts.propose(amended.contract_id)
    flow.contracts.approve(amended.contract_id, by="test")
    flow.contracts.activate(amended.contract_id)
    raw["contract_id"] = amended.contract_id
    flow._delegations.put(out["delegation_id"], raw)
    # Enable fallback on the amended contract record directly.
    crec = flow.contracts._contracts.get(amended.contract_id)
    crec["allow_fallback"] = True
    flow.contracts._contracts.put(amended.contract_id, crec)
    # More expensive fallback without approval is refused.
    with pytest.raises(FlowError, match="costs more"):
        flow.fallback(out["delegation_id"],
                      {"service_id": svc.service_id, "agent_id": svc.agent_id,
                       "price_minor": 5000})


def test_recursion_depth_enforced(flow):
    _ident, svc = seed_service(flow)
    _enable(flow)
    with pytest.raises(FlowError, match="recursion guard"):
        flow.delegate(_task(delegation_depth=99),
                      {"service_id": svc.service_id, "agent_id": svc.agent_id})


def test_unknown_service_refused(flow):
    _enable(flow)
    with pytest.raises(FlowError, match="unknown service"):
        flow.delegate(_task(), {"service_id": "nope", "agent_id": "ghost"})


def test_recommend_explains_and_vetoes(flow):
    from aetheros_agent_market.preferences import AgentPreferences, preference_veto
    _ident, svc = seed_service(flow)
    _enable(flow)
    # Blocked agents are excluded at discovery (first layer)...
    flow.preferences.put(AgentPreferences(blocked_agents=[svc.agent_id]))
    rec = flow.recommend({"query": "summarize"})
    assert rec["candidates"] == []
    # ...and vetoed at selection if they ever reach it (second layer).
    prefs = flow.preferences.effective()
    assert preference_veto(svc.agent_id, "acme", prefs) is not None
    assert "user-blocked" in preference_veto(svc.agent_id, "acme", prefs)
