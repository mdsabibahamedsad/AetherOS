"""Unit: payments, ledger, accounting, disputes."""

import pytest

from aetheros_agent_market import schemas as S
from aetheros_agent_market.accounting import CostAccounting
from aetheros_agent_market.disputes import DisputeEngine
from aetheros_agent_market.ledger import Ledger
from aetheros_agent_market.payments import (
    PaymentError, get_provider,
)


def _quote(total=0):
    return S.Quote(quote_id=S.new_id("q"), service_id="s", agent_id="a",
                   price_minor=total, currency="USD",
                   idempotency_key=S.new_id("idem"))


def test_unknown_provider_rejected(home):
    with pytest.raises(ValueError, match="unknown payment provider"):
        get_provider("stripe", home)


def test_no_payment_free_lifecycle(home):
    p = get_provider("none", home)
    tx = p.authorize(_quote(0), "idem-1")
    assert tx.status == "authorized" and tx.amount_minor == 0
    # Idempotent re-authorize returns same tx.
    assert p.authorize(_quote(0), "idem-1").transaction_id == tx.transaction_id
    captured = p.capture(tx.transaction_id, "cap-1")
    assert captured.status == "captured"
    # Same idempotency key => same result (retry-safe, spec 38).
    assert p.capture(tx.transaction_id, "cap-1").transaction_id == tx.transaction_id
    # A NEW capture attempt after settlement is refused (no double spend).
    with pytest.raises(PaymentError):
        p.capture(tx.transaction_id, "cap-2")


def test_no_payment_refuses_priced_quote(home):
    p = get_provider("none", home)
    with pytest.raises(PaymentError):
        p.authorize(_quote(500), "idem-x")


def test_credits_balance_accounting(home):
    p = get_provider("credits", home, initial_minor=1000)
    assert p.balance() == 1000
    tx = p.authorize(_quote(400), "idem-1")
    assert p.balance() == 600
    with pytest.raises(PaymentError, match="insufficient"):
        p.authorize(_quote(700), "idem-2")
    p.void(tx.transaction_id, "v-1")
    assert p.balance() == 1000
    tx2 = p.authorize(_quote(400), "idem-3")
    p.capture(tx2.transaction_id, "c-3")
    p.refund(tx2.transaction_id, None, "r-3", "failed verify")
    assert p.balance() == 1000
    assert p.get_transaction(tx2.transaction_id).status == "refunded"


def test_credits_partial_and_over_refund(home):
    p = get_provider("credits", home, initial_minor=1000)
    tx = p.authorize(_quote(400), "idem-1")
    p.capture(tx.transaction_id, "c-1")
    with pytest.raises(PaymentError, match="exceeds"):
        p.refund(tx.transaction_id, 500, "r-1", "x")


def test_org_budget_lifecycle(home):
    p = get_provider("org_budget", home)
    tx = p.authorize(_quote(250), "idem-1")
    assert tx.provider == "org_budget"
    assert p.capture(tx.transaction_id, "c-1").status == "captured"
    assert p.reconcile()["provider"] == "org_budget"


def test_ledger_chain_and_idempotency(home):
    ledger = Ledger(home / "ledger.jsonl")
    e1 = ledger.append("QUOTE_CREATED", agent_id="a", amount_minor=100,
                       currency="USD", idempotency_key="k1")
    e2 = ledger.append("AUTHORIZATION_CREATED", agent_id="a",
                       amount_minor=100, currency="USD",
                       idempotency_key="k2")
    assert e2.prev_hash == e1.entry_hash
    # Same idempotency key + event => same entry, no duplicate.
    assert ledger.append("QUOTE_CREATED", agent_id="a", amount_minor=100,
                         currency="USD",
                         idempotency_key="k1").entry_id == e1.entry_id
    assert ledger.verify_chain()["ok"] is True


def test_ledger_bad_event_rejected(home):
    ledger = Ledger(home / "ledger.jsonl")
    with pytest.raises(ValueError):
        ledger.append("PRINT_MONEY")


def test_ledger_tamper_detected(home):
    ledger = Ledger(home / "ledger.jsonl")
    ledger.append("QUOTE_CREATED", agent_id="a", idempotency_key="k1")
    ledger.append("CAPTURED", agent_id="a", amount_minor=50,
                  currency="USD", idempotency_key="k2")
    # Tamper: rewrite last line amount without fixing hashes.
    lines = (home / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    import json
    last = json.loads(lines[-1])
    last["amount_minor"] = 999999
    lines[-1] = json.dumps(last, sort_keys=True)
    (home / "ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = ledger.verify_chain()
    assert result["ok"] is False


def test_adjust_is_compensating_only(home):
    ledger = Ledger(home / "ledger.jsonl")
    e = ledger.append("CAPTURED", agent_id="a", amount_minor=100,
                      currency="USD", idempotency_key="k1")
    adj = ledger.adjust(e.entry_id, -20, "partial goodwill",
                        agent_id="a", currency="USD")
    assert adj.event == "ADJUSTED"
    assert ledger.verify_chain()["ok"] is True


def test_accounting_never_claims_unsettled(home):
    acc = CostAccounting(home)
    acc.record_estimate("dlg-1", {"agent": 400, "verification": 50})
    v = acc.variance("dlg-1")
    assert v["settled"] is False and v["actual_minor"] is None
    ledger = Ledger(home / "ledger.jsonl")
    ledger.append("CAPTURED", delegation_id="dlg-1", agent_id="a",
                  amount_minor=400, currency="USD", idempotency_key="k1")
    v2 = acc.variance("dlg-1")
    assert v2["settled"] is True and v2["actual_minor"] == 400
    assert v2["variance_minor"] == -50


def test_dispute_lifecycle(home):
    eng = DisputeEngine(home)
    d = eng.open(S.Dispute(transaction_id="tx-1", contract_id="ct-1",
                            agent_id="a", reason="overcharge",
                            description="charged twice"))
    assert d.status == "open"
    with pytest.raises(ValueError):
        eng.transition(d.dispute_id, "resolved")  # must go via review
    eng.transition(d.dispute_id, "under_review", by="ops")
    eng.attach_evidence(d.dispute_id, "ev-1", by="user")
    called = []
    eng.resolve(d.dispute_id, "refund: duplicate charge",
                refund_fn=lambda dispute: called.append(dispute.dispute_id),
                by="ops")
    assert called == [d.dispute_id]
    assert eng.get(d.dispute_id).status == "refunded"


def test_dispute_refund_without_callback_rejected(home):
    eng = DisputeEngine(home)
    d = eng.open(S.Dispute(transaction_id="t", contract_id="c",
                            agent_id="a", reason="overcharge"))
    eng.transition(d.dispute_id, "under_review")
    with pytest.raises(ValueError):
        eng.resolve(d.dispute_id, "refund it")


def test_dispute_evidence_frozen_after_terminal(home):
    eng = DisputeEngine(home)
    d = eng.open(S.Dispute(transaction_id="t", contract_id="c",
                            agent_id="a", reason="sla_violation"))
    eng.transition(d.dispute_id, "under_review")
    eng.transition(d.dispute_id, "resolved")
    with pytest.raises(ValueError):
        eng.attach_evidence(d.dispute_id, "ev-1")
