"""Stress and cascading-failure tests for the aetheros_comm fabric."""

from __future__ import annotations

import threading
import time

import pytest

from aetheros_comm.authz import AuthorizationContext
from aetheros_comm.envelope import AgentMessageEnvelope
from aetheros_comm.fabric import AgentCommunicationFabric
from aetheros_comm.identity import AgentIdentity
from aetheros_comm.types import MessageType, TrustZone


def build(n_agents: int) -> AgentCommunicationFabric:
    fabric = AgentCommunicationFabric()
    fabric.register_agent(AgentIdentity(agentId="orch", capabilities=[
        "task:request", "comm:*"], trustZone="ZONE_4"))
    for i in range(n_agents):
        fabric.register_agent(AgentIdentity(agentId=f"w{i}", capabilities=[
            "task:request", "task:report", "comm:*"], trustZone="ZONE_1"))
    fabric.trust_policy.allow_cross_zone(
        TrustZone.ZONE_4, TrustZone.ZONE_1,
        capabilities=("task:request", "comm:*"))
    fabric.connect()
    return fabric


def ctx_for(sender: str):
    return AuthorizationContext(principal_chain=["orch", sender],
                                mission_id="m", task_id="t")


class TestMultiAgent:
    def test_one_agent_roundtrip(self):
        fabric = build(1)
        received = []
        fabric.subscribe("w0", received.append)
        env = AgentMessageEnvelope(messageType=MessageType.TASK_REQUEST.value,
                                   senderAgentId="orch", receiverAgentId="w0",
                                   missionId="m", taskId="t")
        assert fabric.send(env).ok
        assert len(received) == 1

    def test_five_agents_deliver_all(self):
        fabric = build(5)
        received = []
        for i in range(5):
            fabric.subscribe(f"w{i}", lambda e, i=i: received.append((i, e)))
        for i in range(5):
            env = AgentMessageEnvelope(messageType=MessageType.TASK_REQUEST.value,
                                       senderAgentId="orch", receiverAgentId=f"w{i}",
                                       missionId="m", taskId="t")
            assert fabric.send(env).ok
        assert len(received) == 5
        assert {i for i, _ in received} == set(range(5))

    def test_ten_agents_concurrent_sends(self):
        fabric = build(10)
        received = []
        for i in range(10):
            fabric.subscribe(f"w{i}", lambda e, i=i: received.append((i, e)))
        threads = []
        errors = []

        def send(i):
            try:
                env = AgentMessageEnvelope(
                    messageType=MessageType.TASK_REQUEST.value,
                    senderAgentId="orch", receiverAgentId=f"w{i}",
                    missionId="m", taskId="t")
                if not fabric.send(env).ok:
                    errors.append(f"send failed for w{i}")
            except Exception as exc:
                errors.append(str(exc))

        for i in range(10):
            t = threading.Thread(target=send, args=(i,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        assert not errors
        assert len(received) == 10

    def test_concurrent_requests_distinct_correlations(self):
        fabric = build(5)
        results = {}

        def responder(env):
            resp = AgentMessageEnvelope(
                messageType=MessageType.TASK_RESULT.value,
                senderAgentId=env.receiverAgentId, receiverAgentId="orch",
                correlationId=env.correlationId)
            return resp

        fabric.subscribe("orch", lambda e: None)  # ensure orch handlers exist
        for i in range(5):
            fabric.subscribe(f"w{i}", responder)
        threads = []
        for i in range(5):
            t = threading.Thread(target=lambda i=i: results.update(
                {i: fabric.request(
                    AgentMessageEnvelope(
                        messageType=MessageType.TASK_REQUEST.value,
                        senderAgentId="orch", receiverAgentId=f"w{i}",
                        missionId="m", taskId="t"))}))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        corr_ids = {r.response.correlationId for r in results.values()
                    if r.response}
        assert len(corr_ids) == 5


class TestCascadingFailure:
    def test_quarantine_isolates_faulty_agent(self):
        fabric = build(3)
        # worker 0 misbehaves: malformed messages trip quarantine.
        for _ in range(6):
            env = AgentMessageEnvelope(messageType="NOT_A_TYPE",
                                       senderAgentId="w0",
                                       receiverAgentId="w1")
            fabric.handle_inbound(env)
        assert fabric.is_quarantined("w0")
        # Other agents still communicate.
        env = AgentMessageEnvelope(messageType=MessageType.TASK_REQUEST.value,
                                   senderAgentId="orch", receiverAgentId="w1",
                                   missionId="m", taskId="t")
        assert fabric.send(env).ok

    def test_circuit_breaker_opens_on_failures(self):
        fabric = build(1)
        # 'dead' is registered with the authorizer but never attaches to the
        # local bus, so every delivery fails and the breaker opens.
        fabric.registry.register(AgentIdentity(agentId="dead", capabilities=[
            "comm:*"], trustZone="ZONE_1"))
        fabric.trust_policy.allow_cross_zone(
            TrustZone.ZONE_4, TrustZone.ZONE_1,
            capabilities=("comm:*",))
        breaker = fabric._get_breaker("dead")
        for _ in range(breaker.failure_threshold):
            env = AgentMessageEnvelope(messageType=MessageType.WARNING.value,
                                       senderAgentId="orch", receiverAgentId="dead")
            fabric.send(env)
        assert breaker.state == "OPEN"
        env = AgentMessageEnvelope(messageType=MessageType.WARNING.value,
                                   senderAgentId="orch", receiverAgentId="dead")
        result = fabric.send(env)
        assert not result.accepted
        assert result.code == "UNAVAILABLE"

    def test_healthy_agent_isolated_from_faulty_metric(self):
        fabric = build(3)
        for i in range(3):
            env = AgentMessageEnvelope(messageType=MessageType.TASK_REQUEST.value,
                                       senderAgentId="orch", receiverAgentId=f"w{i}",
                                       missionId="m", taskId="t")
            assert fabric.send(env).ok
        stats = fabric.stats()
        assert stats["metrics"]["counters"]["messages_sent"] == 3
        assert stats["metrics"]["counters"]["messages_received"] == 3