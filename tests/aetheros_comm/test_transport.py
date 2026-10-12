"""Tests for aetheros_comm.transport — LocalAgentBus and adapters."""

from __future__ import annotations

import threading
import time

import pytest

from aetheros_comm.envelope import AgentMessageEnvelope
from aetheros_comm.transport import (ClusterTransport, KernelBusTransport,
                                     LocalAgentBus, OrchestratorBusTransport,
                                     SendReceipt, SwarmBusTransport,
                                     TransportState)
from aetheros_comm.types import MessageType


def make_env(sender="orch", receiver="worker", message_type=MessageType.HELLO.value):
    return AgentMessageEnvelope(messageType=message_type,
                                senderAgentId=sender,
                                receiverAgentId=receiver)


class TestLocalBusLifecycle:
    def test_not_ready_before_connect(self):
        bus = LocalAgentBus()
        receipt = bus.send(make_env())
        assert not receipt.delivered

    def test_connect_sets_ready(self):
        bus = LocalAgentBus()
        bus.connect()
        assert bus.state == TransportState.READY

    def test_disconnect_clears(self):
        bus = LocalAgentBus()
        bus.connect()
        bus.disconnect()
        assert bus.state == TransportState.CLOSED


class TestLocalBusDelivery:
    def test_directed_delivery(self):
        bus = LocalAgentBus()
        bus.connect()
        bus.register_agent("worker")
        bus.register_agent("orch")
        received = []
        bus.subscribe("worker", received.append)
        receipt = bus.send(make_env())
        assert receipt.delivered
        assert len(received) == 1
        assert received[0].receiverAgentId == "worker"

    def test_unknown_recipient_dead_letter(self):
        bus = LocalAgentBus()
        bus.connect()
        bus.register_agent("orch")
        receipt = bus.send(make_env(receiver="ghost"))
        assert not receipt.delivered
        assert "no such agent" in receipt.error

    def test_no_subscriber_dead_letter(self):
        bus = LocalAgentBus()
        bus.connect()
        bus.register_agent("worker")
        bus.register_agent("orch")
        receipt = bus.send(make_env())
        assert not receipt.delivered

    def test_unsubscribe_stops_delivery(self):
        bus = LocalAgentBus()
        bus.connect()
        bus.register_agent("worker")
        bus.register_agent("orch")
        received = []
        unsub = bus.subscribe("worker", received.append)
        unsub()
        bus.send(make_env())
        assert received == []

    def test_broadcast_delivers_to_all(self):
        bus = LocalAgentBus()
        bus.connect()
        bus.register_agent("a")
        bus.register_agent("b")
        bus.register_agent("c")
        got = []
        bus.subscribe("a", lambda e: got.append("a"))
        bus.subscribe("b", lambda e: got.append("b"))
        env = AgentMessageEnvelope(messageType=MessageType.HELLO.value,
                                   senderAgentId="c", receiverAgentId="")
        receipt = bus.send(env)
        assert receipt.delivered
        assert sorted(got) == ["a", "b"]


class TestLocalBusRequestResponse:
    def test_request_response_correlation(self):
        bus = LocalAgentBus()
        bus.connect()
        bus.register_agent("worker")
        bus.register_agent("orch")

        def responder(env):
            return AgentMessageEnvelope(
                messageType=MessageType.TASK_RESULT.value,
                senderAgentId="worker", receiverAgentId="orch",
                correlationId=env.correlationId)

        bus.subscribe("worker", responder)
        response = bus.request(make_env(message_type=MessageType.TASK_REQUEST.value))
        assert response is not None
        assert response.messageType == MessageType.TASK_RESULT.value
        assert response.correlationId

    def test_request_timeout_returns_none(self):
        bus = LocalAgentBus()
        bus.connect()
        bus.register_agent("worker")
        bus.register_agent("orch")
        bus.subscribe("worker", lambda env: None)  # never responds
        response = bus.request(make_env(), timeout=0.1)
        assert response is None

    def test_parallel_requests_distinct(self):
        bus = LocalAgentBus()
        bus.connect()
        bus.register_agent("worker")
        bus.register_agent("orch")

        def responder(env):
            time.sleep(0.01)
            return AgentMessageEnvelope(
                messageType=MessageType.TASK_RESULT.value,
                senderAgentId="worker", receiverAgentId="orch",
                correlationId=env.correlationId)

        bus.subscribe("worker", responder)
        results = []
        threads = []
        for _ in range(5):
            t = threading.Thread(target=lambda: results.append(
                bus.request(make_env(message_type=MessageType.TASK_REQUEST.value),
                            timeout=5.0)))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        assert len(results) == 5
        assert all(r is not None for r in results)
        ids = {r.correlationId for r in results}
        assert len(ids) == 5


class TestTransportHealth:
    def test_health_ready(self):
        bus = LocalAgentBus()
        bus.connect()
        bus.register_agent("a")
        health = bus.health()
        assert health.ready
        assert health.agents_connected == 1

    def test_health_not_ready_when_closed(self):
        bus = LocalAgentBus()
        assert not bus.health().ready


class TestAdapters:
    def test_kernel_adapter_connects(self):
        transport = KernelBusTransport()
        try:
            transport.connect()
            assert transport.state == TransportState.READY
            assert transport.is_ready
        finally:
            transport.disconnect()

    def test_swarm_adapter_connects(self):
        transport = SwarmBusTransport()
        try:
            transport.connect()
            assert transport.state == TransportState.READY
        finally:
            transport.disconnect()

    def test_orchestrator_adapter_connects(self):
        transport = OrchestratorBusTransport()
        try:
            transport.connect()
            assert transport.state == TransportState.READY
        finally:
            transport.disconnect()

    def test_cluster_transport_send_before_ready(self):
        transport = ClusterTransport()
        receipt = transport.send(make_env())
        assert not receipt.delivered
        assert receipt.error == "not ready"

    def test_send_receipt_to_dict(self):
        receipt = SendReceipt("m1", True)
        assert receipt.to_dict()["delivered"] is True