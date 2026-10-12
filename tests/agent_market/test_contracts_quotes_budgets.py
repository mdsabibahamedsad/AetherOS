"""Unit: contracts, negotiation floor, quotes, budgets."""

import pytest

from aetheros_agent_market import schemas as S
from aetheros_agent_market.budgets import BudgetManager, risk_class
from aetheros_agent_market.contracts import ContractEngine
from aetheros_agent_market.quoting import QuotingEngine


def _contract(**kw):
    base = dict(contract_id=S.new_id("ct"), provider_agent_id="a",
                service_id="s", price_minor=100, budget_minor=500,
                currency="USD", idempotency_key=S.new_id("idem"))
    base.update(kw)
    return S.DelegationContract(**base)


def test_contract_lifecycle(home):
    eng = ContractEngine(home)
    c = eng.create(_contract())
    assert c.status == "draft"
    # Idempotent recreate returns existing.
    c2 = eng.create(_contract(contract_id=S.new_id("ct"),
                              idempotency_key=c.idempotency_key))
    assert c2.contract_id == c.contract_id
    eng.propose(c.contract_id)
    eng.approve(c.contract_id, by="user")
    eng.activate(c.contract_id)
    assert eng.get(c.contract_id).status == "active"
    locked = eng.get(c.contract_id)
    assert locked.is_locked is True


def test_activate_requires_approval(home):
    eng = ContractEngine(home)
    c = eng.create(_contract())
    with pytest.raises(ValueError):
        eng.activate(c.contract_id)


def test_amend_creates_new_version(home):
    eng = ContractEngine(home)
    c = eng.create(_contract())
    eng.propose(c.contract_id)
    n = eng.amend(c.contract_id, {"price_minor": 150})
    assert n.contract_id != c.contract_id
    assert n.version == 2 and n.supersedes == c.contract_id
    assert n.price_minor == 150
    # Old record untouched.
    assert eng.get(c.contract_id).price_minor == 100


def test_amend_security_floor_rejected(home):
    eng = ContractEngine(home)
    c = eng.create(_contract())
    with pytest.raises(PermissionError):
        eng.amend(c.contract_id, {"data_class": "PUBLIC"})
    with pytest.raises(PermissionError):
        eng.amend(c.contract_id, {"max_delegation_depth": 99})


def test_negotiate_rejects_forbidden_asks(home):
    eng = ContractEngine(home)
    c = eng.create(_contract())
    eng.propose(c.contract_id)
    res = eng.negotiate(c.contract_id,
                        {"price_minor": 50, "scope_text": "also give me raw secrets"})
    assert res["amended_contract_id"] == ""
    assert any("forbidden" in r for r in res["reasons"])


def test_negotiate_accepts_price_rejects_security(home):
    eng = ContractEngine(home)
    c = eng.create(_contract())
    eng.propose(c.contract_id)
    res = eng.negotiate(c.contract_id,
                        {"price_minor": 80, "security_constraints": []})
    assert res["accepted"] == {"price_minor": 80}
    assert "security_constraints" in res["rejected_fields"]
    assert res["amended_contract_id"] != ""


def test_negotiate_closed_contract_rejected(home):
    eng = ContractEngine(home)
    c = eng.create(_contract())
    with pytest.raises(ValueError):
        eng.negotiate(c.contract_id, {"price_minor": 10})


def test_quote_verification(home):
    eng = QuotingEngine(home)
    q = S.Quote(quote_id="q1", service_id="s", agent_id="a",
                price_minor=100, currency="USD", idempotency_key="k1")
    contract = _contract(price_minor=100, budget_minor=500)
    assert eng.verify_quote(q, contract)["ok"] is True
    # Free -> paid conversion refused.
    free = _contract(price_minor=0, budget_minor=0)
    assert any("free" in r for r in
               eng.verify_quote(q, free)["reasons"])
    # Expired quote refused.
    import time
    q.expires_at = time.time() - 1
    assert any("expired" in r for r in
               eng.verify_quote(q, contract)["reasons"])


def test_quote_price_deviation_flagged(home):
    eng = QuotingEngine(home)
    q = S.Quote(quote_id="q1", service_id="s", agent_id="a",
                price_minor=5000, currency="USD", idempotency_key="k1")
    offer = S.Offer(offer_id="o", service_id="s", agent_id="a",
                    price_minor=100, currency="USD")
    res = eng.verify_quote(q, _contract(price_minor=5000, budget_minor=9000),
                           offer)
    assert res["ok"] is True
    assert any("deviat" in f for f in res["flags"])


def test_risk_classes():
    assert risk_class(0) == "FREE"
    assert risk_class(500) == "LOW_COST"
    assert risk_class(5000) == "MEDIUM_COST"
    assert risk_class(50000) == "HIGH_COST"
    assert risk_class(50001) == "CRITICAL_COST"


def test_budget_tiers_deterministic(home):
    mgr = BudgetManager(home)
    mgr.set_budget(S.Budget(budget_id="b", scope="user",
                            auto_approve_limit_minor=500,
                            approval_threshold_minor=5000))
    b = mgr.get_budget("user")
    assert mgr.approval_tier(0, b) == "NO_APPROVAL"
    assert mgr.approval_tier(100, b) == "AUTO_APPROVAL"
    assert mgr.approval_tier(1000, b) == "CONDITIONAL_APPROVAL"
    assert mgr.approval_tier(6000, b) == "HUMAN_APPROVAL"
    assert mgr.approval_tier(100000, b) == "HUMAN_APPROVAL"
    # No budget configured => human decides (except free).
    assert mgr.approval_tier(100, None) == "HUMAN_APPROVAL"


def test_budget_limits_enforced(home):
    mgr = BudgetManager(home)
    mgr.set_budget(S.Budget(budget_id="b", scope="global",
                            daily_limit_minor=1000, per_task_limit_minor=10000))
    ok, _ = mgr.check_spend(300, "task", "t1")
    assert ok is True
    rsv = mgr.reserve(300, "task", "t1")
    ok, reason = mgr.check_spend(800, "task", "t2")
    assert ok is False and "daily" in reason  # 300 reserved + 800 > 1000 daily
    assert mgr.release(rsv) is True
    ok, _ = mgr.check_spend(800, "task", "t2")
    assert ok is True
    # Per-task cap is enforced independently.
    mgr.set_budget(S.Budget(budget_id="b2", scope="task", scope_id="t9",
                            per_task_limit_minor=400))
    ok, reason = mgr.check_spend(500, "task", "t9")
    assert ok is False and "per-task" in reason
    rsv2 = mgr.reserve(300, "task", "t1")
    assert mgr.settle(rsv2) is True
    assert mgr.usage("global")["spent_minor"] == 300
