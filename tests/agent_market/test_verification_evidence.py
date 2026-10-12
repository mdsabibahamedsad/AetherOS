"""Unit: verification strategies, evidence store, events."""

import pytest

from aetheros_agent_market import schemas as S
from aetheros_agent_market.events import EventBus
from aetheros_agent_market.evidence import EvidenceStore
from aetheros_agent_market.verification import ResultVerificationEngine


def test_schema_strategy():
    eng = ResultVerificationEngine()
    v = eng.verify({"answer": 42}, ["schema"],
                   {"output_schema": {"required": ["answer"]}})
    assert v.passed is True
    v2 = eng.verify({"nope": 1}, ["schema"],
                    {"output_schema": {"required": ["answer"]}})
    assert v2.passed is False


def test_unknown_strategy_fails_closed():
    eng = ResultVerificationEngine()
    v = eng.verify({}, ["telepathy"])
    assert v.passed is False


def test_artifact_hash_strategy(tmp_path):
    target = tmp_path / "out.txt"
    target.write_bytes(b"hello")
    import hashlib
    digest = hashlib.sha256(b"hello").hexdigest()
    eng = ResultVerificationEngine()
    v = eng.verify({}, ["artifact_hash"],
                   {"artifact_hashes": {str(target): digest}})
    assert v.passed is True
    v2 = eng.verify({}, ["artifact_hash"],
                    {"artifact_hashes": {str(target): "00" * 32}})
    assert v2.passed is False


def test_expected_output_fragments():
    eng = ResultVerificationEngine()
    v = eng.verify("revenue was $12m in Q3", ["expected_output"],
                   {"must_contain": ["$12m", "Q3"]})
    assert v.passed is True
    v2 = eng.verify("revenue was great", ["expected_output"],
                    {"must_contain": ["$12m"]})
    assert v2.passed is False


def test_citation_strategy():
    eng = ResultVerificationEngine()
    v = eng.verify("see https://example.com/a and https://example.com/b",
                   ["citation_presence"], {"min_citations": 2})
    assert v.passed is True
    v2 = eng.verify("trust me", ["citation_presence"], {"min_citations": 1})
    assert v2.passed is False


def test_evidence_roundtrip_and_integrity(home):
    store = EvidenceStore(home)
    ev = store.put("output", b"result bytes", delegation_id="d1",
                   actor="agent-x", summary="ok")
    assert ev.sha256.startswith("sha256:")
    assert store.verify_blob(ev) is True
    assert store.get(ev.evidence_id).evidence_id == ev.evidence_id
    assert len(store.chain("d1")) == 1


def test_evidence_refuses_secrets(home):
    store = EvidenceStore(home)
    with pytest.raises(PermissionError, match="secret"):
        store.put("input", b"api_key = ABCDEF1234567890XYZABC",
                  delegation_id="d1", actor="user")


def test_evidence_size_cap(home):
    store = EvidenceStore(home)
    with pytest.raises(ValueError, match="50MB"):
        store.put("output", b"x" * (51 * 1024 * 1024), actor="a")


def test_evidence_tamper_detected(home):
    store = EvidenceStore(home)
    ev = store.put("output", b"original", actor="a")
    blob = home / ev.ref
    blob.write_bytes(b"tampered")
    assert store.verify_blob(ev) is False


def test_events_typed_deduped_correlated(home):
    bus = EventBus(home)
    e1 = bus.emit("ContractCreated", actor="local", contract_id="ct-1",
                  correlation_id="corr-1")
    with pytest.raises(ValueError):
        bus.emit("SomethingHappened")
    # Replay with same id returns original (dedupe).
    e2 = bus.emit("ContractCreated", actor="local", contract_id="ct-1",
                  correlation_id="corr-1", event_id=e1["event_id"])
    assert e2["event_id"] == e1["event_id"]
    assert len(bus.list()) == 1
    assert bus.list(kind="ContractCreated")[0]["correlation_id"] == "corr-1"
