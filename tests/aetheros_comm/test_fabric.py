"""Tests for aetheros_comm.fabric — the AgentCommunicationFabric facade."""

from __future__ import annotations

import threading
import time

import pytest

from aetheros_comm.authz import AuthorizationContext, ScopedPermission
from aetheros_comm.envelope import AgentMessageEnvelope
from aetheros_comm.fabric import AgentCommunicationFabric
from aetheros_comm.identity import AgentIdentity, AgentStatus
from aetheros_comm.types import MessageType, TrustZone


def make_fabric(**config_overrides) -> AgentCommunicationFabric:
    config = {"authentication": {"require_signature": True}}
    config.update(config_overrides)
    return AgentCommunicationFabric(config=config)


def register_agents(fabric, *, with_allowance=True):
    fabric.register_agent(AgentIdentity(agentId="orch", capabilities=[
        "task:request", "task:manage", "delegation:request", "comm:*"],
        trustZone="ZONE_4"))
    fabric.register_agent(AgentIdentity(agentId="worker", capabilities=[
        "task:request", "task:report", "repository_read", "comm:*"],
        trustZone="ZONE_1"))
    fabric.register_agent(AgentIdentity(agentId="specialist", capabilities=[
        "task:request", "code_analysis", "comm:*"],
        trustZone="ZONE_1"))
    fabric.register_agent(AgentIdentity(agentId="untrusted", capabilities=[
        "comm:*"],
        trustZone="ZONE_0"))
    if with_allowance:
        fabric.trust_policy.allow_cross_zone(
            TrustZone.ZONE_4, TrustZone.ZONE_1,
            capabilities=("task:request", "task:manage", "task:report",
                          "delegation:request", "comm:*"))
    fabric.connect()
    return fabric


def task_env(sender="orch", receiver="worker", **overrides):
    data = {"messageType": MessageType.TASK_REQUEST.value,
            "senderAgentId": sender, "receiverAgentId": receiver,
            "missionId": "m1", "taskId": "t1"}
    data.update(overrides)
    return AgentMessageEnvelope(**data)


class TestEndToEnd:
    def test_directed_send_delivers(self):
        fabric = register_agents(make_fabric())
        received = []
        fabric.subscribe("worker", received.append)
        result = fabric.send(task_env())
        assert result.ok
        assert len(received) == 1
        assert received[0].messageId == result.envelope.messageId

    def test_request_response(self):
        fabric = register_agents(make_fabric())

        def responder(env):
            resp = AgentMessageEnvelope(
                messageType=MessageType.TASK_RESULT.value,
                senderAgentId="worker", receiverAgentId="orch",
                missionId="m1", taskId="t1",
                correlationId=env.correlationId)
            resp.payload = {"result": "done"}
            return resp

        fabric.subscribe("worker", responder)
        result = fabric.request(task_env())
        assert result.accepted
        assert result.response is not None
        assert result.response.messageType == MessageType.TASK_RESULT.value
        assert result.response.payload == {"result": "done"}

    def test_broadcast_fans_out(self):
        fabric = register_agents(make_fabric())
        got = []
        fabric.subscribe("worker", lambda e: got.append("worker"))
        fabric.subscribe("specialist", lambda e: got.append("specialist"))
        env = AgentMessageEnvelope(messageType=MessageType.WARNING.value,
                                   senderAgentId="orch", receiverAgentId="")
        result = fabric.send(env)
        assert result.ok
        assert sorted(got) == ["specialist", "worker"]

    def test_cross_zone_denied_without_allowance(self):
        fabric = register_agents(make_fabric(), with_allowance=False)
        # untrusted (ZONE_0) -> worker (ZONE_1) requires an explicit
        # allowance; without one the message is rejected.
        result = fabric.send(task_env(sender="untrusted"))
        assert not result.accepted
        assert result.code == "CROSS_ZONE_DENIED"


class TestSecurity:
    def test_impersonation_denied(self):
        fabric = register_agents(make_fabric())
        # wire sender worker, but chain ends at orch -> forged chain.
        result = fabric.send(
            task_env(sender="worker"),
            context=AuthorizationContext(principal_chain=["orch", "worker", "orch"]))
        assert not result.accepted
        assert result.code == "CHAIN_MISMATCH"

    def test_unknown_sender_denied(self):
        fabric = register_agents(make_fabric())
        result = fabric.send(task_env(sender="ghost"))
        assert not result.accepted
        assert result.code == "UNKNOWN_SENDER"

    def test_missing_capability_denied(self):
        fabric = register_agents(make_fabric())
        # worker has no task:cancel capability.
        result = fabric.send(task_env(sender="worker",
                                      messageType=MessageType.TASK_CANCEL.value))
        assert not result.accepted
        assert result.code == "CAPABILITY_DENIED"

    def test_tampered_message_rejected_inbound(self):
        fabric = register_agents(make_fabric())
        env = task_env()
        fabric.send(env)  # signs it
        tampered = AgentMessageEnvelope.from_dict(env.to_dict())
        tampered.messageId = "fresh-tampered-id"
        tampered.payload["evil"] = True
        result = fabric.handle_inbound(tampered)
        assert not result.accepted

    def test_credential_payload_rejected(self):
        fabric = register_agents(make_fabric())
        env = task_env()
        env.payload = {"api_key": "sk-secret-1234"}
        result = fabric.send(env)
        assert not result.accepted
        assert result.code == "CREDENTIALS_REJECTED"

    def test_replayed_message_rejected(self):
        fabric = register_agents(make_fabric())
        env = task_env()
        fabric.send(env)
        replay = AgentMessageEnvelope.from_dict(env.to_dict())
        result = fabric.handle_inbound(replay)
        assert not result.accepted
        assert result.code == "REPLAY_REJECTED"

    def test_signature_failure_increments_metrics(self):
        fabric = register_agents(make_fabric())
        env = task_env()
        fabric.send(env)
        tampered = AgentMessageEnvelope.from_dict(env.to_dict())
        tampered.messageId = "signed-tamper"
        tampered.metadata["injected"] = True
        fabric.handle_inbound(tampered)
        counters = fabric.stats()["metrics"]["counters"]
        assert counters.get("signature_failures", 0) >= 1

    def test_quarantined_agent_rejected(self):
        fabric = register_agents(make_fabric())
        fabric.quarantine_agent("worker", "test quarantine")
        assert fabric.is_quarantined("worker")
        result = fabric.send(task_env())
        assert not result.accepted
        assert result.code == "RECEIVER_NOT_ACTIVE"

    def test_quarantine_requires_full_review_to_reactivate(self):
        fabric = register_agents(make_fabric())
        fabric.quarantine_agent("worker", "test")
        assert not fabric.reactivate_agent("worker", health_ok=True,
                                           identity_ok=True, config_ok=True,
                                           security_review=False)
        assert fabric.reactivate_agent("worker", health_ok=True,
                                       identity_ok=True, config_ok=True,
                                       security_review=True)
        assert not fabric.is_quarantined("worker")
        assert fabric.send(task_env()).ok


class TestDelegation:
    def test_delegated_send_with_scoped_perms(self):
        fabric = register_agents(make_fabric())
        ctx = AuthorizationContext(principal_chain=["user", "orch", "worker"],
                                   scoped_permissions=[
                                       ScopedPermission("task:cancel", "*", "read")],
                                   mission_id="m1", task_id="t1")
        received = []
        fabric.subscribe("specialist", received.append)
        result = fabric.send(
            task_env(sender="worker", receiver="specialist",
                     messageType=MessageType.TASK_CANCEL.value),
            context=ctx)
        assert result.ok
        assert len(received) == 1

    def test_delegation_without_scope_denied(self):
        fabric = register_agents(make_fabric())
        ctx = AuthorizationContext(principal_chain=["user", "orch", "worker"],
                                   mission_id="m1", task_id="t1")
        result = fabric.send(
            task_env(sender="worker", messageType=MessageType.TASK_CANCEL.value),
            context=ctx)
        assert not result.accepted
        assert result.code == "CAPABILITY_DENIED"


class TestIdempotency:
    def test_idempotent_replay_returns_cached(self):
        fabric = register_agents(make_fabric())
        received = []
        fabric.subscribe("worker", received.append)
        env = task_env()
        first = fabric.send(env, idempotency_key="op-1")
        assert first.ok
        replay = task_env()
        second = fabric.send(replay, idempotency_key="op-1")
        assert second.accepted
        assert second.code == "IDEMPOTENT"
        assert len(received) == 1  # executed once

    def test_different_keys_both_execute(self):
        fabric = register_agents(make_fabric())
        received = []
        fabric.subscribe("worker", received.append)
        assert fabric.send(task_env(), idempotency_key="k1").ok
        assert fabric.send(task_env(), idempotency_key="k2").ok
        assert len(received) == 2


class TestProtocolNegotiation:
    def test_negotiates_common(self):
        fabric = register_agents(make_fabric())
        assert fabric.negotiate(["1.0"]) == "1.0"

    def test_incompatible_raises(self):
        fabric = register_agents(make_fabric())
        with pytest.raises(Exception):
            fabric.negotiate(["0.5"])


class TestRouting:
    def test_routes_by_capability(self):
        fabric = register_agents(make_fabric())
        agent = fabric.route(["code_analysis"],
                             requester_agent_id="orch",
                             requester_zone=TrustZone.ZONE_4)
        assert agent == "specialist"

    def test_fallback_chain_ordered(self):
        fabric = register_agents(make_fabric())
        chain = fabric.fallback_chain(["task:request", "comm:*"],
                                      requester_agent_id="orch",
                                      requester_zone=TrustZone.ZONE_4)
        assert "worker" in chain
        assert "specialist" in chain

    def test_route_respects_quarantine(self):
        fabric = register_agents(make_fabric())
        fabric.quarantine_agent("specialist", "down")
        agent = fabric.route(["code_analysis"],
                             requester_agent_id="orch",
                             requester_zone=TrustZone.ZONE_4)
        assert agent is None


class TestHeartbeat:
    def test_heartbeat_marks_liveness(self):
        fabric = register_agents(make_fabric())
        # worker sends a heartbeat to specialist (same zone); inbound marks
        # worker alive.
        result = fabric.send_heartbeat(sender="worker", receiver="specialist", seq=1)
        assert result.ok
        assert fabric.heartbeats.is_stale("worker") is False

    def test_stale_heartbeat_detected(self):
        fabric = register_agents(make_fabric())
        fabric.heartbeats.mark_seen("worker", seq=1)
        fabric.heartbeats._presence["worker"].last_seen = time.time() - 999
        assert fabric.heartbeats.is_stale("worker")

    def test_unknown_agent_is_stale(self):
        fabric = register_agents(make_fabric())
        assert fabric.heartbeats.is_stale("ghost")


class TestLifecycle:
    def test_connect_close(self):
        fabric = make_fabric()
        fabric.register_agent(AgentIdentity(agentId="a", capabilities=["comm:*"]))
        fabric.connect()
        assert fabric.stats()["transport_state"] == "READY"
        fabric.close()
        assert fabric.stats()["transport_state"] == "CLOSED"

    def test_stats_shape(self):
        fabric = register_agents(make_fabric())
        stats = fabric.stats()
        assert set(stats) >= {"protocol_version", "transport", "registry",
                              "metrics", "graph", "quarantine"}
        assert stats["protocol_version"] == "1.0"