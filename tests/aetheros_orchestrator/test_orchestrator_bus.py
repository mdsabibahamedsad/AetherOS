"""Tests for aetheros_orchestrator — event bus, RPC, and daemon wiring."""

from __future__ import annotations

import asyncio

import pytest

from aetheros_orchestrator.bus.event_bus import EventBus
from aetheros_orchestrator.bus.rpc import RPCClient, RPCServer


class TestEventBus:
    @pytest.mark.asyncio
    async def test_events_dropped_before_start(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("task.created", handler)
        await bus.publish("task.created", {"id": "x"})
        assert received == []

    @pytest.mark.asyncio
    async def test_publish_delivers_to_subscribers(self):
        bus = EventBus()
        await bus.start()
        try:
            received = []

            async def handler(event):
                received.append(event)

            bus.subscribe("task.created", handler)
            await bus.publish("task.created", {"id": "t-1"})
            assert len(received) == 1
            assert received[0]["topic"] == "task.created"
            assert received[0]["data"] == {"id": "t-1"}
            assert "timestamp" in received[0]
        finally:
            await bus.stop()

    @pytest.mark.asyncio
    async def test_history_retained_and_filtered(self):
        bus = EventBus()
        await bus.start()
        try:
            await bus.publish("task.created", {"id": "a"})
            await bus.publish("task.completed", {"id": "a"})
            await bus.publish("task.created", {"id": "b"})
            assert len(bus.get_history("task.created")) == 2
            assert len(bus.get_history()) == 3
        finally:
            await bus.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_delivery(self):
        bus = EventBus()
        await bus.start()
        try:
            received = []

            async def handler(event):
                received.append(event)

            bus.subscribe("task.created", handler)
            await bus.publish("task.created", {"id": "a"})
            bus.unsubscribe("task.created", handler)
            await bus.publish("task.created", {"id": "b"})
            assert len(received) == 1
            assert bus.subscriber_count("task.created") == 0
        finally:
            await bus.stop()

    @pytest.mark.asyncio
    async def test_handler_exception_swallowed(self):
        bus = EventBus()
        await bus.start()
        try:
            async def boom(event):
                raise RuntimeError("handler failure")

            async def ok(event):
                pass

            bus.subscribe("task.created", boom)
            bus.subscribe("task.created", ok)
            await bus.publish("task.created", {"id": "a"})  # must not raise
        finally:
            await bus.stop()


class TestRPC:
    @pytest.mark.asyncio
    async def test_request_response_round_trip(self):
        bus = EventBus()
        await bus.start()
        try:
            server = RPCServer(bus, namespace="kanban")
            server.register("get", lambda id: {"id": id})

            client = RPCClient(bus)
            result = await client.call("kanban.get", {"id": "b-1"})
            assert result == {"id": "b-1"}
        finally:
            await bus.stop()

    @pytest.mark.asyncio
    async def test_error_propagates_as_runtime_error(self):
        bus = EventBus()
        await bus.start()
        try:
            server = RPCServer(bus)

            def fail():
                raise ValueError("nope")

            server.register("fail", fail)

            client = RPCClient(bus)
            with pytest.raises(RuntimeError, match="nope"):
                await client.call("fail")
        finally:
            await bus.stop()

    @pytest.mark.asyncio
    async def test_unknown_method_times_out(self):
        bus = EventBus()
        await bus.start()
        try:
            client = RPCClient(bus, timeout=0.5)
            with pytest.raises(TimeoutError, match="timed out"):
                await client.call("no.such.method")
        finally:
            await bus.stop()


class TestDaemon:
    def test_orchestrator_imports_cleanly(self):
        from aetheros_orchestrator import orchestrator as orch_mod

        assert hasattr(orch_mod, "AetherosOrchestrator")

    @pytest.mark.asyncio
    async def test_orchestrator_start_stop_emits_lifecycle_events(self):
        from unittest.mock import AsyncMock

        from aetheros_orchestrator import orchestrator as orch_mod

        cfg = {
            "daemon": {"host": "127.0.0.1", "port": 0, "log_level": "ERROR", "workers": 1},
            "orchestrator": {"startup_timeout": 2.0, "shutdown_timeout": 2.0, "healthcheck_interval": 10.0},
            "api": {"rest_enabled": True, "websocket_enabled": False},
            "subsystems": {name: {"enabled": False} for name in orch_mod.BUILTIN_SUBSYSTEMS},
        }
        orch = orch_mod.AetherosOrchestrator(cfg)
        # Avoid binding real sockets / spawning subsystems in tests.
        orch._rest_server.start = AsyncMock()
        orch._rest_server.stop = AsyncMock()
        orch._ws_server.start = AsyncMock()
        orch._ws_server.stop = AsyncMock()

        bus = orch.bus
        events = []

        async def handler(event):
            events.append(event["topic"])

        await bus.start()
        bus.subscribe("system.started", handler)
        bus.subscribe("system.stopping", handler)
        try:
            await orch.start()
            await orch.stop()
        finally:
            await bus.stop()

        assert "system.started" in events
        assert "system.stopping" in events
