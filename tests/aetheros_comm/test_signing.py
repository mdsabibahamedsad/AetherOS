"""Tests for aetheros_comm.signing — HMAC signing, replay, expiry, tamper."""

from __future__ import annotations

import pytest

from aetheros_comm.envelope import AgentMessageEnvelope
from aetheros_comm.signing import MessageSigner, ReplayStore
from aetheros_comm.types import MessageType


def make_envelope(**overrides) -> AgentMessageEnvelope:
    data = {
        "messageType": MessageType.TASK_REQUEST.value,
        "senderAgentId": "orch",
        "receiverAgentId": "worker",
    }
    data.update(overrides)
    return AgentMessageEnvelope(**data)


class TestSigning:
    def test_sign_then_verify(self):
        signer = MessageSigner(key=b"test-key")
        env = make_envelope()
        signer.sign(env)
        assert env.signature
        assert signer.verify(env)

    def test_tampered_payload_fails(self):
        signer = MessageSigner(key=b"test-key")
        env = make_envelope()
        signer.sign(env)
        env.payload["evil"] = True
        assert not signer.verify(env)

    def test_tampered_sender_fails(self):
        signer = MessageSigner(key=b"test-key")
        env = make_envelope()
        signer.sign(env)
        env.senderAgentId = "attacker"
        assert not signer.verify(env)

    def test_wrong_key_fails(self):
        env = make_envelope()
        MessageSigner(key=b"key-a").sign(env)
        assert not MessageSigner(key=b"key-b").verify(env)

    def test_key_from_path_roundtrip(self, tmp_path):
        path = tmp_path / "signing.key"
        MessageSigner(key_path=path).sign(env := make_envelope())
        assert MessageSigner(key_path=path).verify(env)

    def test_unsigned_fails(self):
        signer = MessageSigner(key=b"test-key")
        assert not signer.verify(make_envelope())

    def test_removes_signature_for_recompute(self):
        signer = MessageSigner(key=b"test-key")
        env = make_envelope()
        signer.sign(env)
        first = env.signature
        signer.sign(env)
        assert env.signature == first  # deterministic


class TestReplay:
    def test_first_seen_ok_second_rejected(self):
        store = ReplayStore()
        assert store.check_and_record("orch", "msg-1")
        assert not store.check_and_record("orch", "msg-1")

    def test_same_id_different_sender_allowed(self):
        store = ReplayStore()
        assert store.check_and_record("orch", "msg-1")
        assert store.check_and_record("worker", "msg-1")

    def test_distinct_ids_allowed(self):
        store = ReplayStore()
        assert store.check_and_record("orch", "msg-1")
        assert store.check_and_record("orch", "msg-2")

    def test_ttl_prunes_old(self):
        import time
        store = ReplayStore(retention_seconds=0.001)
        assert store.check_and_record("orch", "msg-old")
        time.sleep(0.01)
        # recording another entry prunes the expired ones first.
        assert store.check_and_record("orch", "msg-new")
        assert store.check_and_record("orch", "msg-old")

    def test_len(self):
        store = ReplayStore()
        store.check_and_record("orch", "m1")
        store.check_and_record("orch", "m2")
        assert len(store) == 2


class TestExpiry:
    def test_expired_envelope_rejected_by_validator(self):
        import time
        from aetheros_comm.envelope import EnvelopeError, EnvelopeValidator
        # timestamp in the past, expiresAt shortly after timestamp and now.
        env = make_envelope(timestamp=time.time() - 5, expiresAt=time.time() - 1)
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code == "EXPIRED"

    def test_is_expired_property(self):
        import time
        assert make_envelope(expiresAt=time.time() - 1).is_expired
        assert not make_envelope(expiresAt=0).is_expired