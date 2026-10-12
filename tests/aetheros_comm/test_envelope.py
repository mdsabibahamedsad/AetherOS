"""Tests for aetheros_comm.envelope — envelope validation and limits."""

from __future__ import annotations

import time

import pytest

from aetheros_comm.envelope import (AgentMessageEnvelope, EnvelopeError,
                                    EnvelopeLimits, EnvelopeValidator)
from aetheros_comm.types import ContentOrigin, MessageType


def make_envelope(**overrides) -> AgentMessageEnvelope:
    data = {
        "messageType": MessageType.TASK_REQUEST.value,
        "senderAgentId": "orch",
        "receiverAgentId": "worker",
        "missionId": "m1",
        "taskId": "t1",
    }
    data.update(overrides)
    return AgentMessageEnvelope(**data)
    def test_valid_envelope_passes(self):
        env = make_envelope()
        EnvelopeValidator().validate(env)

    def test_missing_message_id(self):
        env = make_envelope()
        env.messageId = ""
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code == "MISSING_FIELD"

    def test_missing_sender(self):
        env = make_envelope(senderAgentId="")
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code == "MISSING_FIELD"

    def test_directed_message_requires_receiver(self):
        env = make_envelope(receiverAgentId="")
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code == "MISSING_FIELD"

    def test_broadcast_capable_type_allows_empty_receiver(self):
        env = make_envelope(messageType=MessageType.WARNING.value,
                            receiverAgentId="")
        EnvelopeValidator().validate(env)


class TestProtocol:
    def test_unsupported_protocol_rejected(self):
        env = make_envelope(protocolVersion="99.9")
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code == "BAD_PROTOCOL"


class TestMessageType:
    def test_unknown_type_rejected(self):
        env = make_envelope(messageType="NOT_A_TYPE")
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code == "BAD_MESSAGE_TYPE"

    def test_message_type_property(self):
        assert make_envelope().message_type == MessageType.TASK_REQUEST


class TestTimestamps:
    def test_expired_message_rejected(self):
        import time as _time
        now = _time.time()
        env = make_envelope(timestamp=now - 100, expiresAt=now - 5)
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code == "EXPIRED"

    def test_expires_before_timestamp_rejected(self):
        env = make_envelope(timestamp=100.0, expiresAt=50.0)
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code == "BAD_EXPIRATION"

    def test_non_expiring_message_ok(self):
        env = make_envelope(expiresAt=0.0)
        EnvelopeValidator().validate(env)


class TestLimits:
    def test_oversized_payload_rejected(self):
        env = make_envelope(payload={"blob": "x" * 500_000})
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code in ("PAYLOAD_TOO_LARGE", "MESSAGE_TOO_LARGE")

    def test_too_many_capabilities_rejected(self):
        env = make_envelope(capabilities=[f"cap:{i}" for i in range(300)])
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code == "CAPABILITIES_TOO_MANY"

    def test_custom_limits_apply(self):
        limits = EnvelopeLimits(max_payload_bytes=100,
                                max_message_bytes=2048)
        env = make_envelope(payload={"x": "y" * 120})
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator(limits).validate(env)
        assert exc.value.code == "PAYLOAD_TOO_LARGE"

    def test_deep_nesting_rejected(self):
        nested = 40
        payload = current = {}
        for _ in range(nested):
            current["next"] = {}
            current = current["next"]
        env = make_envelope(payload=payload)
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code == "TOO_DEEP"

    def test_overlong_field_rejected(self):
        env = make_envelope(senderAgentId="x" * 600)
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code == "FIELD_TOO_LONG"


class TestOrigin:
    def test_valid_origin_accepted(self):
        env = make_envelope(metadata={"origin": ContentOrigin.USER.value})
        EnvelopeValidator().validate(env)

    def test_invalid_origin_rejected(self):
        env = make_envelope(metadata={"origin": "ALIEN"})
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate(env)
        assert exc.value.code == "BAD_ORIGIN"


class TestSerialization:
    def test_roundtrip(self):
        env = make_envelope(payload={"a": 1, "b": [1, 2]})
        restored = AgentMessageEnvelope.from_dict(env.to_dict())
        assert restored.messageId == env.messageId
        assert restored.payload == env.payload

    def test_json_roundtrip(self):
        env = make_envelope()
        restored = AgentMessageEnvelope.from_json(env.to_json())
        assert restored.messageId == env.messageId

    def test_non_object_json_rejected(self):
        with pytest.raises(EnvelopeError) as exc:
            AgentMessageEnvelope.from_json("[1,2,3]")
        assert exc.value.code == "NOT_OBJECT"

    def test_validate_dict_rejects_non_dict(self):
        with pytest.raises(EnvelopeError) as exc:
            EnvelopeValidator().validate_dict("not-a-dict")
        assert exc.value.code == "NOT_OBJECT"


class TestSensitive:
    def test_sensitive_types_detected(self):
        assert make_envelope(
            messageType=MessageType.TASK_REQUEST.value).is_sensitive
        assert make_envelope(
            messageType=MessageType.APPROVAL_REQUEST.value).is_sensitive

    def test_normal_types_not_sensitive(self):
        assert not make_envelope(
            messageType=MessageType.WARNING.value).is_sensitive

    def test_canonical_bytes_exclude_signature(self):
        env = make_envelope(signature="sig-a")
        bytes_a = env.canonical_bytes()
        env.signature = "sig-b"
        assert env.canonical_bytes() == bytes_a

    def test_canonical_bytes_detect_payload_change(self):
        env = make_envelope(payload={"a": 1})
        original = env.canonical_bytes()
        env.payload["a"] = 2
        assert env.canonical_bytes() != original