"""Integration tests for the full economy flow."""

import pytest
import time
from pathlib import Path

from aetheros_agent_economy.flow import MarketplaceFlow
from aetheros_agent_economy.capabilities import CapabilityDefinition, CapabilityRegistry
from aetheros_agent_economy.composition import CapabilityCompositionEngine
from aetheros_agent_economy.capverify import CapabilityVerificationEngine
from aetheros_agent_economy.pricing import normalize_price
from aetheros_agent_economy.capacity import CapacityRegistry
from aetheros_agent_economy.auction import AuctionRound
from aetheros_agent_economy.planner import PlanOptimizer, PlanSimulator
from aetheros_agent_economy.reputation import PerformanceProfiler, DiscoveryLearner
from aetheros_agent_economy.capverify import CapabilityVerificationEngine
from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
from aetheros_agent_economy.tokens_risk_autopilot import RiskEngine, AutopilotEngine
from aetheros_agent_economy.governance import AnomalyDetector, CollusionDetector, MarketplaceHealthEngine, MarketplaceGovernanceEngine

from aetheros_agent_economy.flow import MarketplaceFlow
from tests.agent_market.conftest import StubGateway, seed_service


def _enable(flow):
    flow.flags.set("marketplace", True, by="test")
    flow.flags.set("remote_delegation", True, by="test")


def _task(**kw):
    base = {"summary": "t", "capabilities": [], "data_class": "INTERNAL",
            "verification_requirements": ["schema"],
            "payment_provider": "none", "requester": "test"}
    base.update(kw)
    return base


def test_end_to_end_capability_lifecycle(tmp_path):
    """Full lifecycle: register -> compose -> advertise -> verify -> compose -> price -> auction."""
    flow = MarketplaceFlow(tmp_path, gateway_factory=StubGateway)
    flow.flags.set("marketplace", True, by="test")
    flow.flags.set("remote_delegation", True, by="test")
    flow.flags.set("paid_agents", True, by="test")
    flow.flags.set("automatic_payment", True, by="test")

    # 1. Register capabilities
    reg = CapabilityRegistry(flow.home)
    for cid in ["ocr.document", "translation.text", "analysis.financial"]:
        cap = CapabilityDefinition(capability_id=cid, namespace="econ", name=cid,
                                   version="1", description="",
                                   prerequisites=[])
        reg.register(cap)

    # 2. Compose
    engine = CapabilityCompositionEngine(tmp_path, reg)
    comp = engine.compose("doc_pipeline", ["ocr.document", "translation.text", "analysis.financial"])
    assert comp.topo_order == ["ocr.document", "translation.text", "analysis.financial"]

    # 3. Advertise + verify
    ver = CapabilityVerificationEngine(tmp_path, flow)
    ad = ver.advertise("agent-x", {"capabilities": [{"capability_id": "ocr.document"}]})
    assert ver.status("agent-x", "ocr.document").status == "DECLARED"
    att = ver.grade_from_history("agent-x", "ocr.document")
    assert att.status in ("DECLARED", "OBSERVED", "VERIFIED")

    # 4. Price
    est = normalize_price({"model": "PER_REQUEST", "currency": "USD", "unit_minor": 100},
                          usage={"requests": 5})
    assert est.amount_minor == 500

    # 4. Auction
    round_obj = AuctionRound(tmp_path, "ocr.document", rule="lowest_price")
    round_obj.submit(type("Bid", (), {"bid_id": "", "round_id": "", "agent_id": "a1",
        "service_id": "s1", "price_minor": 100, "currency": "USD", "capacity": {},
        "sla": {}, "availability": "available", "execution_estimate_s": 1.0,
        "quote_id": "", "offer_id": ""})())
    round_obj.submit(type("Bid", (), {"bid_id": "", "round_id": "", "agent_id": "a2",
        "service_id": "s1", "price_minor": 50, "currency": "USD", "capacity": {},
        "sla": {}, "availability": "available", "execution_estimate_s": 1.0,
        "quote_id": "", "offer_id": ""})())
    ranked = round_obj.rank()
    assert ranked[0]["bid"]["agent_id"] == "a2"

    print("Full capability lifecycle test passed")


def test_marketplace_automation_integration(tmp_path):
    """Automation engine executing marketplace delegations."""
    flow = MarketplaceFlow(tmp_path, gateway_factory=StubGateway)
    _enable(flow)
    _ident, svc = seed_service(flow, pricing="per_task", price_minor=400)
    flow.flags.set("paid_agents", True, by="test")
    flow.flags.set("automatic_payment", True, by="test")
    flow.budgets.set_budget(type("S", (), {"Budget": S.Budget})(
        budget_id="b", scope="user", currency="USD",
        daily_limit_minor=100000, per_task_limit_minor=10000,
        approval_threshold_minor=5000, auto_approve_limit_minor=1000))
    from aetheros_agent_market import schemas as S
    flow.flags.set("automatic_payment", True, by="test")
    from aetheros_agent_economy.integrations import scheduled_delegation_spec, run_scheduled
    spec = scheduled_delegation_spec(
        {"summary": "weekly report", "verification_requirements": ["schema"],
         "payment_provider": "credits"},
        {"service_id": svc.service_id, "agent_id": svc.agent_id})
    out = run_scheduled(flow, spec)
    assert out["status"] == "running"


def test_multi_provider_contract_flow(tmp_path):
    """Full composite contract: OCR -> Translate -> Verify."""
    flow = MarketplaceFlow(tmp_path, gateway_factory=StubGateway)
    _enable(flow)
    flow.flags.set("paid_agents", True, by="test")
    flow.flags.set("automatic_payment", True, by="test")
    flow.budgets.set_budget(type("S", (), {"Budget": S.Budget})(
        budget_id="b", scope="user", currency="USD",
        daily_limit_minor=100000, per_task_limit_minor=10000,
        approval_threshold_minor=5000, auto_approve_limit_minor=1000))

    # Seed services
    _, ocr = seed_service(flow, agent_id="agent-ocr", org="ocr-corp",
                          pricing="per_task", price_minor=200)
    _, trans = seed_service(flow, agent_id="agent-trans", org="trans-corp",
                            pricing="per_task", price_minor=150)
    _, verif = seed_service(flow, agent_id="agent-verif", org="verif-corp",
                            pricing="per_task", price_minor=100)

    from aetheros_agent_economy.contracts2 import CompositeContractEngine, Milestone, CompositeContract
    engine = CompositeContractEngine(tmp_path)
    c = CompositeContract(contract_id="ct-1", total_budget_minor=500,
                          currency="USD", allow_fallback=True)
    engine.create(c)
    m1 = Milestone(milestone_id="m1", contract_id="ct-1", sequence=1,
                   provider_agent_id="agent-ocr", description="OCR extract")
    m2 = Milestone(milestone_id="m2", contract_id="ct-1", sequence=2,
                   provider_agent_id="agent-trans", description="Translate",
                   depends_on=["m1"])
    m3 = Milestone(milestone_id="m3", contract_id="ct-1", sequence=3,
                   provider_agent_id="agent-verif", description="Verify",
                   depends_on=["m2"])
    engine.add_milestone(c.contract_id, m1)
    engine.add_milestone(c.contract_id, m2)
    engine.add_milestone(c.contract_id, m3)
    engine.propose(c.contract_id)
    engine.approve(c.contract_id, by="user")
    engine.activate(c.contract_id)
    m1_started = engine.start_milestone(c.contract_id, "m1")
    assert m1_started.status == "running"
    m1_done = engine.complete_milestone(c.contract_id, "m1", {"text": "extracted"})
    assert m1_done.status == "completed"
    m2_started = engine.start_milestone(c.contract_id, "m2")
    assert m2_started.status == "running"
    m2_done = engine.complete_milestone(c.contract_id, "m2", {"text": "translated"})
    assert m2_done.status == "completed"
    m3_started = engine.start_milestone(c.contract_id, "m3")
    assert m3_started.status == "running"
    m3_done = engine.complete_milestone(c.contract_id, "m3", {"verified": True})
    assert m3_done.status == "completed"
    final = engine.get("ct-1")
    assert final.status == "completed"


def test_risk_aware_routing(tmp_path):
    """High-risk task routes to higher-trust provider."""
    flow = MarketplaceFlow(tmp_path, gateway_factory=StubGateway)
    _enable(flow)
    from aetheros_agent_economy.capacity import CapacityRegistry, route_load_aware
    cap = CapacityRegistry(tmp_path)
    cap.report(type("Cap", (), {"agent_id": "trusted", "concurrency_used": 1,
                                "concurrency_max": 10, "availability": "available",
                                "health": "online", "provenance": "observed"})())
    cap.report(type("Cap", (), {"agent_id": "untrusted", "concurrency_used": 1,
                                "concurrency_max": 10, "availability": "available",
                                "health": "online", "provenance": "observed"})())
    def gate(cand):
        return True, "ok"
    res = route_load_aware("untrusted", ["trusted"], cap, gate, min_trust_rank=0)
    assert res["selected"] == "trusted"


def test_anomaly_detection_in_flow(tmp_path):
    flow = MarketplaceFlow(tmp_path, gateway_factory=StubGateway)
    det = AnomalyDetector(tmp_path, flow)
    anom = det.check_price_spike("agent-x", 5000, 1000, threshold=3.0)
    assert anom is not None and anom.kind == "price_spike"


def test_governance_in_flow(tmp_path):
    flow = MarketplaceFlow(tmp_path)
    gov = MarketplaceGovernanceEngine(tmp_path, flow)
    gov.set_policy("deny_private", {"if": {"dataClass": "PRIVATE",
                                            "providerTrust": "unverified"},
                                    "then": "DENY"}, by="admin")
    res = gov.evaluate({"dataClass": "PRIVATE", "providerTrust": "unverified"})
    assert len(res["decisions"]) == 1
    assert res["decisions"][0]["action"] == "DENY"