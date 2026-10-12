"""Fuzz tests for aetheros_comm.envelope — malformed input rejection."""

from __future__ import annotations

import json
import random

import pytest

from aetheros_comm.envelope import (AgentMessageEnvelope, EnvelopeError,
                                    EnvelopeValidator)


class TestFuzz:
    def test_garbage_inputs_rejected_cleanly(self):
        validator = EnvelopeValidator()
        garbage = [
            None, 42, "hello", [], (1, 2), {1: 2}, {"messageId": 5},
            {"senderAgentId": None}, "null", "true", "{", "[]",
            '{"messageId": "x", "senderAgentId": 7}',
        ]
        for data in garbage:
            with pytest.raises(EnvelopeError):
                validator.validate_dict(data)

    def test_random_mutations_never_crash(self):
        validator = EnvelopeValidator()
        base = AgentMessageEnvelope(
            messageType="TASK_REQUEST", senderAgentId="orch",
            receiverAgentId="worker", missionId="m", taskId="t")
        base_dict = base.to_dict()
        rng = random.Random(42)
        field_names = list(base_dict.keys())
        for _ in range(200):
            mutated = json.loads(json.dumps(base_dict))
            field = rng.choice(field_names)
            mutations = [
                None, 12345, [], {}, "x" * 700, {"nested": {"deep": True}},
            ]
            mutated[field] = rng.choice(mutations)
            try:
                validator.validate_dict(mutated)
            except EnvelopeError:
                pass  # expected for malformed input
            except Exception:  # pragma: no cover
                pytest.fail(f"unexpected exception on {field}={mutated[field]!r}")

    def test_random_payload_types_never_crash(self):
        validator = EnvelopeValidator()
        rng = random.Random(7)
        for _ in range(100):
            env = AgentMessageEnvelope(
                messageType="TASK_REQUEST", senderAgentId="orch",
                receiverAgentId="worker")
            env.payload = rng.choice([None, 1, "str", [1, 2], {"a": [{"b": 1}]}])
            try:
                validator.validate(env)
            except EnvelopeError:
                pass
            except Exception:  # pragma: no cover
                pytest.fail("unexpected exception for payload")

    def test_deep_recursion_bounded(self):
        validator = EnvelopeValidator()
        env = AgentMessageEnvelope(senderAgentId="orch",
                                   receiverAgentId="worker")
        node = env.payload
        for _ in range(5000):
            node["n"] = {}
            node = node["n"]
        with pytest.raises(EnvelopeError) as exc:
            validator.validate(env)
        assert exc.value.code in ("TOO_DEEP", "PAYLOAD_TOO_LARGE")

    def test_json_type_confusion(self):
        validator = EnvelopeValidator()
        # field type confusion must not be silently interpreted.
        cases = [
            {"messageType": "TASK_REQUEST", "senderAgentId": "a",
             "receiverAgentId": "b", "priority": "urgent"},
            {"messageType": "TASK_REQUEST", "senderAgentId": "a",
             "receiverAgentId": "b", "timestamp": "now"},
            {"messageType": "TASK_REQUEST", "senderAgentId": "a",
             "receiverAgentId": "b", "capabilities": "read"},
        ]
        for data in cases:
            with pytest.raises(EnvelopeError):
                validator.validate_dict(data)