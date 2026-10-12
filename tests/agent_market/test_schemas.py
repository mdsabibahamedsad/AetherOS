"""Unit: schemas, money, versioning, validation."""

import pytest

from aetheros_agent_market import schemas as S


def test_money_validation():
    assert S.check_amount_minor(0) == 0
    with pytest.raises(ValueError):
        S.check_amount_minor(-1)
    with pytest.raises(ValueError):
        S.check_amount_minor(1.5)
    with pytest.raises(ValueError):
        S.check_amount_minor(True)
    assert S.check_currency("USD") == "USD"
    with pytest.raises(ValueError):
        S.check_currency("usd")
    with pytest.raises(ValueError):
        S.check_currency("USDD")


def test_ids_unique():
    assert S.new_id("ct") != S.new_id("ct")


def test_identity_requires_binding():
    ident = S.MarketplaceIdentity(identity_id="x")
    assert any("agent_id" in e for e in ident.validate())
    ident.agent_id = "agent-1"
    assert ident.validate() == []


def test_contract_price_over_budget_rejected():
    c = S.DelegationContract(contract_id="ct-1", provider_agent_id="a",
                             service_id="s", price_minor=100,
                             budget_minor=50, currency="USD",
                             idempotency_key="k")
    assert any("budget" in e for e in c.validate())


def test_contract_requires_idempotency():
    c = S.DelegationContract(contract_id="ct-1", provider_agent_id="a",
                             service_id="s")
    assert any("idempotency" in e for e in c.validate())


def test_offer_expiry():
    import time
    o = S.Offer(offer_id="o", service_id="s", agent_id="a",
                expires_at=time.time() - 1)
    assert o.is_expired is True


def test_quote_total():
    q = S.Quote(quote_id="q", service_id="s", agent_id="a",
                price_minor=400, fees_minor=100, currency="USD",
                idempotency_key="k")
    assert q.total_minor == 500
    assert q.validate() == []


def test_schema_version_rejected():
    with pytest.raises(ValueError, match="schema_version"):
        S.Offer.from_dict({"schema_version": "99", "offer_id": "o"})


def test_unknown_fields_ignored():
    o = S.Offer.from_dict({"schema_version": "1", "offer_id": "o",
                           "service_id": "s", "agent_id": "a",
                           "future_field": 123})
    assert o.offer_id == "o"


def test_metric_defaults_zero_confidence():
    from aetheros_agent_market.schemas import ReputationProfile
    p = ReputationProfile(agent_id="a")
    m = p.get("task_success")
    assert m.value == 0.0 and m.confidence == 0.0 and m.sample_count == 0


def test_trust_signal_decay():
    import time
    s = S.TrustSignal(agent_id="a", dimension="execution", value=1.0,
                      confidence=1.0, decay_half_life_days=30.0,
                      created_at=time.time() - 30 * 86400)
    assert abs(s.decayed_value() - 0.5) < 0.01


def test_dispute_validation():
    d = S.Dispute(reason="bogus")
    assert any("reason" in e for e in d.validate())
    d2 = S.Dispute(reason="overcharge", status="bogus")
    assert any("status" in e for e in d2.validate())


def test_ledger_entry_canonical_stable():
    e1 = S.LedgerEntry(entry_id="e1", event="CAPTURED")
    e2 = S.LedgerEntry(entry_id="e1", event="CAPTURED",
                       created_at=e1.created_at)
    assert e1.canonical_bytes() == e2.canonical_bytes()


def test_negotiable_fields_exclude_security():
    assert "security_constraints" not in S.NEGOTIABLE_FIELDS
    assert "data_class" not in S.NEGOTIABLE_FIELDS
    assert "price_minor" in S.NEGOTIABLE_FIELDS
