from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

from aetheros_orchestrator.bus.event_bus import EventBus
from aetheros_orchestrator.logging.setup import get_logger


class WebSocketServer:
    def __init__(self, bus: EventBus, host: str = "127.0.0.1", port: int = 8766):
        self._bus = bus
        self._host = host
        self._port = port
        self._logger = get_logger("api.ws")
        self._clients: set[asyncio.StreamWriter] = set()
        self._subscriptions: dict[str, set[asyncio.StreamWriter]] = {}
        self._server: asyncio.AbstractServer | None = None

    async def start(self):
        self._logger.info("WebSocket server starting on %s:%s", self._host, self._port)
        self._bus.subscribe("*", self._broadcast_event)
        self._server = await asyncio.start_server(
            self._handle_connection, self._host, self._port,
        )
        self._logger.info("WebSocket server ready on %s:%s", self._host, self._port)

    async def stop(self):
        self._bus.unsubscribe("*", self._broadcast_event)
        for client in self._clients:
            try:
                client.close()
            except Exception:
                pass
        self._clients.clear()
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._clients.add(writer)
        try:
            while True:
                data = await asyncio.wait_for(reader.read(65536), timeout=3600)
                if not data:
                    break
                msg = json.loads(data.decode())
                await self._handle_message(writer, msg)
        except (asyncio.TimeoutError, ConnectionResetError, EOFError):
            pass
        finally:
            self._clients.discard(writer)
            for subs in self._subscriptions.values():
                subs.discard(writer)
            try:
                writer.close()
            except Exception:
                pass

    async def _handle_message(self, writer: asyncio.StreamWriter, msg: dict):
        action = msg.get("action", "")
        if action == "subscribe":
            topic = msg.get("topic", "")
            self._subscriptions.setdefault(topic, set()).add(writer)
        elif action == "unsubscribe":
            topic = msg.get("topic", "")
            self._subscriptions.get(topic, set()).discard(writer)
        elif action == "publish":
            await self._bus.publish(msg.get("topic", ""), msg.get("data"), "ws")

    async def _broadcast_event(self, event: dict):
        topic = event["topic"]
        payload = json.dumps(event).encode()
        targets = set(self._clients)
        if topic in self._subscriptions:
            targets |= self._subscriptions[topic]
        for client in targets:
            try:
                client.write(payload + b"\n")
                await client.drain()
            except Exception:
                self._clients.discard(client)
