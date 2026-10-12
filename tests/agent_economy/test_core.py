"""Unit tests for core economy components."""

import pytest
import tempfile
import secrets

from aetheros_agent_market import schemas as S
from aetheros_agent_market.flow import MarketplaceFlow
from aetheros_agent_economy.auction import AuctionRound
from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
from aetheros_agent_economy.tokens_risk_autopilot import RiskEngine, AutopilotEngine
from aetheros_agent_market.flags import FeatureFlags


def test_auction_round():
    """Test auction round with multiple bids."""
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap-1", rule="lowest_price")
        bid1 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
            "price_minor": 100, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        bid2 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a2", "service_id": "s1",
            "price_minor": 50, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        round_obj.submit(bid1)
        round_obj.submit(bid2)
        ranked = round_obj.rank()
        assert ranked[0]["bid"]["agent_id"] == "a2"
        assert ranked[0]["bid"]["price_minor"] == 50


def test_auction_cross_currency_rejected():
    """Cross-currency bids should be rejected."""
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap", currency="USD")
        with pytest.raises(ValueError, match="cross-currency"):
            bid = type("Bid", (), {
                "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
                "price_minor": 100, "currency": "EUR", "capacity": {}, "sla": {},
                "availability": "available", "execution_estimate_s": None,
                "quote_id": "", "offer_id": ""
            })()
            round_obj.submit(bid)


def test_composite_contract_lifecycle(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1", requester="test",
                          provider_milestones=[Milestone(milestone_id="m1", contract_id="ct-1",
                                                         provider_agent_id="a1", sequence=1,
                                                         description="Step 1")],
                          total_budget_minor=1000, currency="USD")
    engine.create(c)
    engine.propose(c.contract_id)
    engine.approve(c.contract_id, by="user")
    engine.activate(c.contract_id)
    assert engine.get(c.contract_id).status == "active"


def test_milestone_dependency(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1", description="Step 1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", description="Step 2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    order = engine.get(c.contract_id).dependency_order()
    assert order == ["m1", "m2"]


def test_milestone_dependency_enforced(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    engine.activate(c.contract_id)
    with pytest.raises(ValueError, match="dependency m1 not completed"):
        engine.start_milestone(c.contract_id, "m2", by="test")
    engine.start_milestone(c.contract_id, "m1", by="test")
    engine.complete_milestone(c.contract_id, "m1", {"ok": True})
    m2_started = engine.start_milestone(c.contract_id, "m2", by="test")
    assert m2_started.status == "running"


def test_risk_engine_assessment(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import RiskEngine
    engine = RiskEngine(tmp_path)
    task = {"summary": "translate legal doc", "budget_minor": 50000,
            "data_class": "CONFIDENTIAL", "delegation_depth": 2}
    risk = engine.assess(task)
    assert 0 <= risk.overall_risk <= 1
    assert risk.recommended_approval in ("none", "auto", "conditional", "human")


def test_autopilot_modes(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import AutopilotEngine
    from aetheros_agent_market.flags import FeatureFlags
    from aetheros_agent_market.store import JsonStore
    
    # Use real FeatureFlags for proper behavior
    flags = FeatureFlags(tmp_path)
    flow = type("Flow", (), {
        "flags": flags,
        "optimizer": type("Opt", (), {
            "recommend": lambda self, task: {"candidates": []}
        })()
    })
    auto = AutopilotEngine(flow)
    assert auto.MODES == ("OFF", "ASSISTED", "CONDITIONAL", "AUTONOMOUS")

    # OFF mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "declined"

    # ASSISTED mode
    flags.set("remote_delegation", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "recommendation"

    # CONDITIONAL mode - requires approval for paid
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("paid_agents", True, by="test")
    flags.set("automatic_payment", False, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "pending_approval"

    # AUTONOMOUS mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("automatic_payment", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "executing"


def test_auction_round():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap-1", rule="lowest_price")
        bid1 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
            "price_minor": 100, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        bid2 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a2", "service_id": "s1",
            "price_minor": 50, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        round_obj.submit(bid1)
        round_obj.submit(bid2)
        ranked = round_obj.rank()
        assert ranked[0]["bid"]["agent_id"] == "a2"


def test_auction_cross_currency_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap", currency="USD")
        with pytest.raises(ValueError, match="cross-currency"):
            bid = type("Bid", (), {
                "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
                "price_minor": 100, "currency": "EUR", "capacity": {}, "sla": {},
                "availability": "available", "execution_estimate_s": None,
                "quote_id": "", "offer_id": ""
            })()
            round_obj.submit(bid)


def test_composite_contract_lifecycle(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1", requester="test",
                          provider_milestones=[Milestone(milestone_id="m1", contract_id="ct-1",
                                                         provider_agent_id="a1", sequence=1,
                                                         description="Step 1")],
                          total_budget_minor=1000, currency="USD")
    engine.create(c)
    engine.propose(c.contract_id)
    engine.approve(c.contract_id, by="user")
    engine.activate(c.contract_id)
    assert engine.get(c.contract_id).status == "active"


def test_milestone_dependency(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1", description="Step 1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", description="Step 2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    order = engine.get(c.contract_id).dependency_order()
    assert order == ["m1", "m2"]


def test_milestone_dependency_enforced(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    engine.activate(c.contract_id)
    with pytest.raises(ValueError, match="dependency m1 not completed"):
        engine.start_milestone(c.contract_id, "m2", by="test")
    engine.start_milestone(c.contract_id, "m1", by="test")
    engine.complete_milestone(c.contract_id, "m1", {"ok": True})
    m2_started = engine.start_milestone(c.contract_id, "m2", by="test")
    assert m2_started.status == "running"


def test_risk_engine_assessment(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import RiskEngine
    engine = RiskEngine(tmp_path)
    task = {"summary": "translate legal doc", "budget_minor": 50000,
            "data_class": "CONFIDENTIAL", "delegation_depth": 2}
    risk = engine.assess(task)
    assert 0 <= risk.overall_risk <= 1
    assert risk.recommended_approval in ("none", "auto", "conditional", "human")


def test_autopilot_modes(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import AutopilotEngine
    from aetheros_agent_market.flags import FeatureFlags
    from aetheros_agent_market.store import JsonStore
    
    # Use real FeatureFlags for proper behavior
    flags = FeatureFlags(tmp_path)
    flow = type("Flow", (), {
        "flags": flags,
        "optimizer": type("Opt", (), {
            "recommend": lambda self, task: {"candidates": []}
        })()
    })
    auto = AutopilotEngine(flow)
    assert auto.MODES == ("OFF", "ASSISTED", "CONDITIONAL", "AUTONOMOUS")

    # OFF mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "declined"

    # ASSISTED mode
    flags.set("remote_delegation", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "recommendation"

    # CONDITIONAL mode - requires approval for paid
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("paid_agents", True, by="test")
    flags.set("automatic_payment", False, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "pending_approval"

    # AUTONOMOUS mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("automatic_payment", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "executing"


def test_auction_round():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap-1", rule="lowest_price")
        bid1 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
            "price_minor": 100, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        bid2 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a2", "service_id": "s1",
            "price_minor": 50, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        round_obj.submit(bid1)
        round_obj.submit(bid2)
        ranked = round_obj.rank()
        assert ranked[0]["bid"]["agent_id"] == "a2"


def test_auction_cross_currency_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap", currency="USD")
        with pytest.raises(ValueError, match="cross-currency"):
            bid = type("Bid", (), {
                "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
                "price_minor": 100, "currency": "EUR", "capacity": {}, "sla": {},
                "availability": "available", "execution_estimate_s": None,
                "quote_id": "", "offer_id": ""
            })()
            round_obj.submit(bid)


def test_composite_contract_lifecycle(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1", requester="test",
                          provider_milestones=[Milestone(milestone_id="m1", contract_id="ct-1",
                                                         provider_agent_id="a1", sequence=1,
                                                         description="Step 1")],
                          total_budget_minor=1000, currency="USD")
    engine.create(c)
    engine.propose(c.contract_id)
    engine.approve(c.contract_id, by="user")
    engine.activate(c.contract_id)
    assert engine.get(c.contract_id).status == "active"


def test_milestone_dependency(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1", description="Step 1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", description="Step 2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    order = engine.get(c.contract_id).dependency_order()
    assert order == ["m1", "m2"]


def test_milestone_dependency_enforced(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    engine.activate(c.contract_id)
    with pytest.raises(ValueError, match="dependency m1 not completed"):
        engine.start_milestone(c.contract_id, "m2", by="test")
    engine.start_milestone(c.contract_id, "m1", by="test")
    engine.complete_milestone(c.contract_id, "m1", {"ok": True})
    m2_started = engine.start_milestone(c.contract_id, "m2", by="test")
    assert m2_started.status == "running"


def test_risk_engine_assessment(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import RiskEngine
    engine = RiskEngine(tmp_path)
    task = {"summary": "translate legal doc", "budget_minor": 50000,
            "data_class": "CONFIDENTIAL", "delegation_depth": 2}
    risk = engine.assess(task)
    assert 0 <= risk.overall_risk <= 1
    assert risk.recommended_approval in ("none", "auto", "conditional", "human")


def test_autopilot_modes(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import AutopilotEngine
    from aetheros_agent_market.flags import FeatureFlags
    from aetheros_agent_market.store import JsonStore
    
    # Use real FeatureFlags for proper behavior
    flags = FeatureFlags(tmp_path)
    flow = type("Flow", (), {
        "flags": flags,
        "optimizer": type("Opt", (), {
            "recommend": lambda self, task: {"candidates": []}
        })()
    })
    auto = AutopilotEngine(flow)
    assert auto.MODES == ("OFF", "ASSISTED", "CONDITIONAL", "AUTONOMOUS")

    # OFF mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "declined"

    # ASSISTED mode
    flags.set("remote_delegation", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "recommendation"

    # CONDITIONAL mode - requires approval for paid
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("paid_agents", True, by="test")
    flags.set("automatic_payment", False, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "pending_approval"

    # AUTONOMOUS mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("automatic_payment", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "executing"


def test_auction_round():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap-1", rule="lowest_price")
        bid1 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
            "price_minor": 100, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        bid2 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a2", "service_id": "s1",
            "price_minor": 50, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        round_obj.submit(bid1)
        round_obj.submit(bid2)
        ranked = round_obj.rank()
        assert ranked[0]["bid"]["agent_id"] == "a2"


def test_auction_cross_currency_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap", currency="USD")
        with pytest.raises(ValueError, match="cross-currency"):
            bid = type("Bid", (), {
                "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
                "price_minor": 100, "currency": "EUR", "capacity": {}, "sla": {},
                "availability": "available", "execution_estimate_s": None,
                "quote_id": "", "offer_id": ""
            })()
            round_obj.submit(bid)


def test_composite_contract_lifecycle(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1", requester="test",
                          provider_milestones=[Milestone(milestone_id="m1", contract_id="ct-1",
                                                         provider_agent_id="a1", sequence=1,
                                                         description="Step 1")],
                          total_budget_minor=1000, currency="USD")
    engine.create(c)
    engine.propose(c.contract_id)
    engine.approve(c.contract_id, by="user")
    engine.activate(c.contract_id)
    assert engine.get(c.contract_id).status == "active"


def test_milestone_dependency(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1", description="Step 1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", description="Step 2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    order = engine.get(c.contract_id).dependency_order()
    assert order == ["m1", "m2"]


def test_milestone_dependency_enforced(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    engine.activate(c.contract_id)
    with pytest.raises(ValueError, match="dependency m1 not completed"):
        engine.start_milestone(c.contract_id, "m2", by="test")
    engine.start_milestone(c.contract_id, "m1", by="test")
    engine.complete_milestone(c.contract_id, "m1", {"ok": True})
    m2_started = engine.start_milestone(c.contract_id, "m2", by="test")
    assert m2_started.status == "running"


def test_risk_engine_assessment(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import RiskEngine
    engine = RiskEngine(tmp_path)
    task = {"summary": "translate legal doc", "budget_minor": 50000,
            "data_class": "CONFIDENTIAL", "delegation_depth": 2}
    risk = engine.assess(task)
    assert 0 <= risk.overall_risk <= 1
    assert risk.recommended_approval in ("none", "auto", "conditional", "human")


def test_autopilot_modes(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import AutopilotEngine
    from aetheros_agent_market.flags import FeatureFlags
    from aetheros_agent_market.store import JsonStore
    
    # Use real FeatureFlags for proper behavior
    flags = FeatureFlags(tmp_path)
    flow = type("Flow", (), {
        "flags": flags,
        "optimizer": type("Opt", (), {
            "recommend": lambda self, task: {"candidates": []}
        })()
    })
    auto = AutopilotEngine(flow)
    assert auto.MODES == ("OFF", "ASSISTED", "CONDITIONAL", "AUTONOMOUS")

    # OFF mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "declined"

    # ASSISTED mode
    flags.set("remote_delegation", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "recommendation"

    # CONDITIONAL mode - requires approval for paid
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("paid_agents", True, by="test")
    flags.set("automatic_payment", False, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "pending_approval"

    # AUTONOMOUS mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("automatic_payment", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "executing"


def test_auction_round():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap-1", rule="lowest_price")
        bid1 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
            "price_minor": 100, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        bid2 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a2", "service_id": "s1",
            "price_minor": 50, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        round_obj.submit(bid1)
        round_obj.submit(bid2)
        ranked = round_obj.rank()
        assert ranked[0]["bid"]["agent_id"] == "a2"


def test_auction_cross_currency_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap", currency="USD")
        with pytest.raises(ValueError, match="cross-currency"):
            bid = type("Bid", (), {
                "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
                "price_minor": 100, "currency": "EUR", "capacity": {}, "sla": {},
                "availability": "available", "execution_estimate_s": None,
                "quote_id": "", "offer_id": ""
            })()
            round_obj.submit(bid)


def test_composite_contract_lifecycle(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1", requester="test",
                          provider_milestones=[Milestone(milestone_id="m1", contract_id="ct-1",
                                                         provider_agent_id="a1", sequence=1,
                                                         description="Step 1")],
                          total_budget_minor=1000, currency="USD")
    engine.create(c)
    engine.propose(c.contract_id)
    engine.approve(c.contract_id, by="user")
    engine.activate(c.contract_id)
    assert engine.get(c.contract_id).status == "active"


def test_milestone_dependency(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1", description="Step 1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", description="Step 2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    order = engine.get(c.contract_id).dependency_order()
    assert order == ["m1", "m2"]


def test_milestone_dependency_enforced(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    engine.activate(c.contract_id)
    with pytest.raises(ValueError, match="dependency m1 not completed"):
        engine.start_milestone(c.contract_id, "m2", by="test")
    engine.start_milestone(c.contract_id, "m1", by="test")
    engine.complete_milestone(c.contract_id, "m1", {"ok": True})
    m2_started = engine.start_milestone(c.contract_id, "m2", by="test")
    assert m2_started.status == "running"


def test_risk_engine_assessment(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import RiskEngine
    engine = RiskEngine(tmp_path)
    task = {"summary": "translate legal doc", "budget_minor": 50000,
            "data_class": "CONFIDENTIAL", "delegation_depth": 2}
    risk = engine.assess(task)
    assert 0 <= risk.overall_risk <= 1
    assert risk.recommended_approval in ("none", "auto", "conditional", "human")


def test_autopilot_modes(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import AutopilotEngine
    from aetheros_agent_market.flags import FeatureFlags
    from aetheros_agent_market.store import JsonStore
    
    # Use real FeatureFlags for proper behavior
    flags = FeatureFlags(tmp_path)
    flow = type("Flow", (), {
        "flags": flags,
        "optimizer": type("Opt", (), {
            "recommend": lambda self, task: {"candidates": []}
        })()
    })
    auto = AutopilotEngine(flow)
    assert auto.MODES == ("OFF", "ASSISTED", "CONDITIONAL", "AUTONOMOUS")

    # OFF mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "declined"

    # ASSISTED mode
    flags.set("remote_delegation", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "recommendation"

    # CONDITIONAL mode - requires approval for paid
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("paid_agents", True, by="test")
    flags.set("automatic_payment", False, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "pending_approval"

    # AUTONOMOUS mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("automatic_payment", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "executing"


def test_auction_round():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap-1", rule="lowest_price")
        bid1 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
            "price_minor": 100, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        bid2 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a2", "service_id": "s1",
            "price_minor": 50, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        round_obj.submit(bid1)
        round_obj.submit(bid2)
        ranked = round_obj.rank()
        assert ranked[0]["bid"]["agent_id"] == "a2"


def test_auction_cross_currency_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap", currency="USD")
        with pytest.raises(ValueError, match="cross-currency"):
            bid = type("Bid", (), {
                "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
                "price_minor": 100, "currency": "EUR", "capacity": {}, "sla": {},
                "availability": "available", "execution_estimate_s": None,
                "quote_id": "", "offer_id": ""
            })()
            round_obj.submit(bid)


def test_composite_contract_lifecycle(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1", requester="test",
                          provider_milestones=[Milestone(milestone_id="m1", contract_id="ct-1",
                                                         provider_agent_id="a1", sequence=1,
                                                         description="Step 1")],
                          total_budget_minor=1000, currency="USD")
    engine.create(c)
    engine.propose(c.contract_id)
    engine.approve(c.contract_id, by="user")
    engine.activate(c.contract_id)
    assert engine.get(c.contract_id).status == "active"


def test_milestone_dependency(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1", description="Step 1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", description="Step 2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    order = engine.get(c.contract_id).dependency_order()
    assert order == ["m1", "m2"]


def test_milestone_dependency_enforced(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    engine.activate(c.contract_id)
    with pytest.raises(ValueError, match="dependency m1 not completed"):
        engine.start_milestone(c.contract_id, "m2", by="test")
    engine.start_milestone(c.contract_id, "m1", by="test")
    engine.complete_milestone(c.contract_id, "m1", {"ok": True})
    m2_started = engine.start_milestone(c.contract_id, "m2", by="test")
    assert m2_started.status == "running"


def test_risk_engine_assessment(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import RiskEngine
    engine = RiskEngine(tmp_path)
    task = {"summary": "translate legal doc", "budget_minor": 50000,
            "data_class": "CONFIDENTIAL", "delegation_depth": 2}
    risk = engine.assess(task)
    assert 0 <= risk.overall_risk <= 1
    assert risk.recommended_approval in ("none", "auto", "conditional", "human")


def test_autopilot_modes(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import AutopilotEngine
    from aetheros_agent_market.flags import FeatureFlags
    from aetheros_agent_market.store import JsonStore
    
    # Use real FeatureFlags for proper behavior
    flags = FeatureFlags(tmp_path)
    flow = type("Flow", (), {
        "flags": flags,
        "optimizer": type("Opt", (), {
            "recommend": lambda self, task: {"candidates": []}
        })()
    })
    auto = AutopilotEngine(flow)
    assert auto.MODES == ("OFF", "ASSISTED", "CONDITIONAL", "AUTONOMOUS")

    # OFF mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "declined"

    # ASSISTED mode
    flags.set("remote_delegation", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "recommendation"

    # CONDITIONAL mode - requires approval for paid
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("paid_agents", True, by="test")
    flags.set("automatic_payment", False, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "pending_approval"

    # AUTONOMOUS mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("automatic_payment", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "executing"


def test_auction_round():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap-1", rule="lowest_price")
        bid1 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
            "price_minor": 100, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        bid2 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a2", "service_id": "s1",
            "price_minor": 50, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        round_obj.submit(bid1)
        round_obj.submit(bid2)
        ranked = round_obj.rank()
        assert ranked[0]["bid"]["agent_id"] == "a2"


def test_auction_cross_currency_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap", currency="USD")
        with pytest.raises(ValueError, match="cross-currency"):
            bid = type("Bid", (), {
                "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
                "price_minor": 100, "currency": "EUR", "capacity": {}, "sla": {},
                "availability": "available", "execution_estimate_s": None,
                "quote_id": "", "offer_id": ""
            })()
            round_obj.submit(bid)


def test_composite_contract_lifecycle(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1", requester="test",
                          provider_milestones=[Milestone(milestone_id="m1", contract_id="ct-1",
                                                         provider_agent_id="a1", sequence=1,
                                                         description="Step 1")],
                          total_budget_minor=1000, currency="USD")
    engine.create(c)
    engine.propose(c.contract_id)
    engine.approve(c.contract_id, by="user")
    engine.activate(c.contract_id)
    assert engine.get(c.contract_id).status == "active"


def test_milestone_dependency(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1", description="Step 1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", description="Step 2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    order = engine.get(c.contract_id).dependency_order()
    assert order == ["m1", "m2"]


def test_milestone_dependency_enforced(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    engine.activate(c.contract_id)
    with pytest.raises(ValueError, match="dependency m1 not completed"):
        engine.start_milestone(c.contract_id, "m2", by="test")
    engine.start_milestone(c.contract_id, "m1", by="test")
    engine.complete_milestone(c.contract_id, "m1", {"ok": True})
    m2_started = engine.start_milestone(c.contract_id, "m2", by="test")
    assert m2_started.status == "running"


def test_risk_engine_assessment(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import RiskEngine
    engine = RiskEngine(tmp_path)
    task = {"summary": "translate legal doc", "budget_minor": 50000,
            "data_class": "CONFIDENTIAL", "delegation_depth": 2}
    risk = engine.assess(task)
    assert 0 <= risk.overall_risk <= 1
    assert risk.recommended_approval in ("none", "auto", "conditional", "human")


def test_autopilot_modes(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import AutopilotEngine
    from aetheros_agent_market.flags import FeatureFlags
    from aetheros_agent_market.store import JsonStore
    
    # Use real FeatureFlags for proper behavior
    flags = FeatureFlags(tmp_path)
    flow = type("Flow", (), {
        "flags": flags,
        "optimizer": type("Opt", (), {
            "recommend": lambda self, task: {"candidates": []}
        })()
    })
    auto = AutopilotEngine(flow)
    assert auto.MODES == ("OFF", "ASSISTED", "CONDITIONAL", "AUTONOMOUS")

    # OFF mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "declined"

    # ASSISTED mode
    flags.set("remote_delegation", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "recommendation"

    # CONDITIONAL mode - requires approval for paid
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("paid_agents", True, by="test")
    flags.set("automatic_payment", False, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "pending_approval"

    # AUTONOMOUS mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("automatic_payment", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "executing"


def test_auction_round():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap-1", rule="lowest_price")
        bid1 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
            "price_minor": 100, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        bid2 = type("Bid", (), {
            "bid_id": "", "round_id": "", "agent_id": "a2", "service_id": "s1",
            "price_minor": 50, "currency": "USD", "capacity": {}, "sla": {},
            "availability": "available", "execution_estimate_s": 1.0,
            "quote_id": "", "offer_id": ""
        })()
        round_obj.submit(bid1)
        round_obj.submit(bid2)
        ranked = round_obj.rank()
        assert ranked[0]["bid"]["agent_id"] == "a2"


def test_auction_cross_currency_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        round_obj = AuctionRound(tmp, "cap", currency="USD")
        with pytest.raises(ValueError, match="cross-currency"):
            bid = type("Bid", (), {
                "bid_id": "", "round_id": "", "agent_id": "a1", "service_id": "s1",
                "price_minor": 100, "currency": "EUR", "capacity": {}, "sla": {},
                "availability": "available", "execution_estimate_s": None,
                "quote_id": "", "offer_id": ""
            })()
            round_obj.submit(bid)


def test_composite_contract_lifecycle(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1", requester="test",
                          provider_milestones=[Milestone(milestone_id="m1", contract_id="ct-1",
                                                         provider_agent_id="a1", sequence=1,
                                                         description="Step 1")],
                          total_budget_minor=1000, currency="USD")
    engine.create(c)
    engine.propose(c.contract_id)
    engine.approve(c.contract_id, by="user")
    engine.activate(c.contract_id)
    assert engine.get(c.contract_id).status == "active"


def test_milestone_dependency(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1", description="Step 1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", description="Step 2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    order = engine.get(c.contract_id).dependency_order()
    assert order == ["m1", "m2"]


def test_milestone_dependency_enforced(tmp_path):
    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1")
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="a1")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="a2", depends_on=["m1"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    engine.activate(c.contract_id)
    with pytest.raises(ValueError, match="dependency m1 not completed"):
        engine.start_milestone(c.contract_id, "m2", by="test")
    engine.start_milestone(c.contract_id, "m1", by="test")
    engine.complete_milestone(c.contract_id, "m1", {"ok": True})
    m2_started = engine.start_milestone(c.contract_id, "m2", by="test")
    assert m2_started.status == "running"


def test_risk_engine_assessment(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import RiskEngine
    engine = RiskEngine(tmp_path)
    task = {"summary": "translate legal doc", "budget_minor": 50000,
            "data_class": "CONFIDENTIAL", "delegation_depth": 2}
    risk = engine.assess(task)
    assert 0 <= risk.overall_risk <= 1
    assert risk.recommended_approval in ("none", "auto", "conditional", "human")


def test_autopilot_modes(tmp_path):
    from aetheros_agent_economy.tokens_risk_autopilot import AutopilotEngine
    from aetheros_agent_market.flags import FeatureFlags
    from aetheros_agent_market.store import JsonStore
    
    # Use real FeatureFlags for proper behavior
    flags = FeatureFlags(tmp_path)
    flow = type("Flow", (), {
        "flags": flags,
        "optimizer": type("Opt", (), {
            "recommend": lambda self, task: {"candidates": []}
        })()
    })
    auto = AutopilotEngine(flow)
    assert auto.MODES == ("OFF", "ASSISTED", "CONDITIONAL", "AUTONOMOUS")

    # OFF mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "declined"

    # ASSISTED mode
    flags.set("remote_delegation", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "recommendation"

    # CONDITIONAL mode - requires approval for paid
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("paid_agents", True, by="test")
    flags.set("automatic_payment", False, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "pending_approval"

    # AUTONOMOUS mode
    flags._flags = JsonStore(tmp_path / "feature_flags.json")
    flags._flags._data = {}
    flags._flags.save()
    flags.set("automatic_payment", True, by="test")
    auto = AutopilotEngine(flow)
    res = auto.maybe_execute({"query": "test"})
    assert res["status"] == "executing"