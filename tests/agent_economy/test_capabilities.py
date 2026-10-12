"""Unit tests for capability model + composition + verification + pricing + capacity."""

import pytest

from aetheros_agent_economy.capabilities import CapabilityDefinition, CapabilityRegistry
from aetheros_agent_economy.composition import CapabilityCompositionEngine, CapabilityGraph
from aetheros_agent_economy.capverify import CapabilityVerificationEngine
from aetheros_agent_economy.pricing import PriceEstimate, FxTable, normalize_price, _apply_tiers
from aetheros_agent_economy.capacity import CapacityRegistry, route_load_aware


def test_capability_register_and_get(tmp_path):
    reg = CapabilityRegistry(tmp_path)
    cap = CapabilityDefinition(
        capability_id="ocr.document", namespace="ocr", name="Document OCR",
        version="1", description="Extract text from PDFs",
        input_schema={"type": "object", "properties": {"file": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"text": {"type": "string"}}},
        modalities=["text"], domains=["documents"],
        prerequisites=[], security_level="standard",
        data_requirements=[], compute_requirements={}, network_requirements={},
        verification_methods=["schema", "hash"], providers=[], consumers=[],
        status="active")
    reg.register(cap)
    got = reg.get("ocr.document")
    assert got is not None and got.capability_id == "ocr.document"
    assert got.version == "1"


def test_capability_revocation_creates_new_version(tmp_path):
    reg = CapabilityRegistry(tmp_path)
    cap = CapabilityDefinition(
        capability_id="test.cap", namespace="test", name="Test",
        version="1", description="", status="active")
    reg.register(cap)
    revoked = reg.revoke("test.cap", "security issue")
    assert revoked.status == "revoked"
    assert revoked.version == "1+revoked"


def test_composition_rejects_cycles(tmp_path):
    from aetheros_agent_economy.capabilities import CapabilityRegistry
    from aetheros_agent_economy.composition import CapabilityCompositionEngine
    reg = CapabilityRegistry(tmp_path)
    for cid in ["a", "b"]:
        cap = CapabilityDefinition(capability_id=cid, namespace="x", name=cid,
                                   version="1", description="", prerequisites=[])
        reg.register(cap)
    engine = CapabilityCompositionEngine(tmp_path, reg)
    with pytest.raises(ValueError, match="cycle"):
        engine.compose("bad", ["a", "b"], extra_edges=[["a", "b"], ["b", "a"]])


def test_composition_valid_dag(tmp_path):
    from aetheros_agent_economy.capabilities import CapabilityRegistry
    from aetheros_agent_economy.composition import CapabilityCompositionEngine
    reg = CapabilityRegistry(tmp_path)
    for cid in ["a", "b", "c"]:
        cap = CapabilityDefinition(capability_id=cid, namespace="x", name=cid,
                                   version="1", description="",
                                   prerequisites=["a"] if cid == "b" else (["b"] if cid == "c" else []))
        reg.register(cap)
    engine = CapabilityCompositionEngine(tmp_path, reg)
    comp = engine.compose("chain", ["a", "b", "c"])
    assert comp.topo_order == ["a", "b", "c"]


def test_verification_requires_evidence(tmp_path):
    from aetheros_agent_economy.capverify import CapabilityVerificationEngine
    from aetheros_agent_economy.flow import MarketplaceFlow
    flow = MarketplaceFlow(tmp_path, gateway_factory=lambda: None)
    ver = CapabilityVerificationEngine(tmp_path, flow)
    # DECLARED without evidence
    att = ver.advertise("agent-1", {"capabilities": [{"capability_id": "test.cap"}]})
    assert ver.status("agent-1", "test.cap").status == "DECLARED"
    # VERIFIED requires strong evidence
    with pytest.raises(ValueError, match="VERIFIED requires"):
        ver.verify("agent-1", "test.cap", sources=["advertisement"])


def test_drift_detection(tmp_path):
    from aetheros_agent_economy.capverify import CapabilityVerificationEngine
    ver = CapabilityVerificationEngine(tmp_path, None)
    # First snapshot
    snap1 = {"capabilities": ["a", "b"], "version": "1",
             "endpoint": "https://x.com/", "security_scopes": ["read"]}
    r1 = ver.detect_drift("agent-1", snap1)
    assert r1["reverify_required"] is False
    # Changed endpoint
    snap2 = {"capabilities": ["a", "b"], "version": "1",
             "endpoint": "https://y.com/", "security_scopes": ["read"]}
    r2 = ver.detect_drift("agent-1", snap2)
    assert r2["reverify_required"] is True
    assert any(d["field"] == "endpoint" for d in r2["drift"])


def test_pricing_fixed_and_rate_based():
    from aetheros_agent_economy.pricing import normalize_price, FxTable, _apply_tiers

    est = normalize_price({"model": "FIXED", "currency": "USD", "amount_minor": 500})
    assert est.amount_minor == 500 and est.model == "FIXED"

    est = normalize_price({"model": "PER_REQUEST", "currency": "USD",
                           "unit_minor": 50}, usage={"requests": 10})
    assert est.amount_minor == 500 and est.model == "PER_REQUEST"

    est = normalize_price({"model": "PER_TOKEN", "currency": "USD",
                           "unit_minor": 10}, usage={"tokens": 1500})
    assert est.amount_minor == 15000
    assert "estimated" in est.warnings[0].lower()

    est = normalize_price({"model": "TIERED", "currency": "USD",
                           "tiers": [{"up_to": 10, "unit_minor": 100},
                                     {"up_to": 100, "unit_minor": 50}]},
                          usage={"units": 15})
    # 10 @ 100 + 5 @ 50 = 1250
    assert est.amount_minor == 1250


def test_tiers_boundary(tmp_path):
    assert _apply_tiers([{"up_to": 10, "unit_minor": 100}], 5) == 500
    assert _apply_tiers([{"up_to": 10, "unit_minor": 100},
                         {"up_to": None, "unit_minor": 50}], 15) == 1250


def test_fx_refuses_missing_rate():
    fx = FxTable("USD", {"EUR": 0.9})
    assert fx.to_base_minor(1000, "USD") == 1000
    assert fx.to_base_minor(900, "EUR") == 1000
    with pytest.raises(ValueError, match="no FX rate"):
        fx.to_base_minor(100, "JPY")


def test_capacity_registry_expiry(tmp_path):
    from aetheros_agent_economy.capacity import CapacityRegistry
    cap = CapacityRegistry(tmp_path, max_age_s=1.0)
    assert cap.get("a") is None
    from aetheros_agent_economy.capacity import CapacitySnapshot
    snap = CapacitySnapshot(agent_id="a", concurrency_used=5,
                            concurrency_max=10, availability="available",
                            health="online", provenance="advertised")
    cap.report(snap)
    assert cap.get("a") is not None
    # Wait for expiry
    import time as _t
    _t.sleep(1.1)
    assert cap.get("a") is None


def test_route_load_aware_prefers_healthy():
    from aetheros_agent_economy.capacity import CapacityRegistry, route_load_aware
    cap = CapacityRegistry(None)
    # primary overloaded
    class FakeCap:
        def get(self, aid):
            if aid == "primary":
                from aetheros_agent_economy.capacity import CapacitySnapshot
                return CapacitySnapshot(agent_id="primary", concurrency_used=9,
                                        concurrency_max=10, availability="available",
                                        health="online")
            if aid == "alt":
                from aetheros_agent_economy.capacity import CapacitySnapshot
                return CapacitySnapshot(agent_id="alt", concurrency_used=1,
                                        concurrency_max=10, availability="available",
                                        health="online")
            return None
        def overloaded(self, aid):
            if aid == "primary": return True
            if aid == "alt": return False
            return None
    cap = FakeCap()
    def gate(cand):
        return True, "ok"
    res = route_load_aware("primary", ["alt"], cap, gate, min_trust_rank=0)
    assert res["selected"] == "alt"
    assert res["rerouted"] is True