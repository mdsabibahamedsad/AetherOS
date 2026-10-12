from __future__ import annotations

import asyncio
import json
from typing import Any

from aetheros_orchestrator.bus.event_bus import EventBus
from aetheros_orchestrator.logging.setup import get_logger


class RESTServer:
    def __init__(self, bus: EventBus, host: str = "127.0.0.1", port: int = 8765):
        self._bus = bus
        self._host = host
        self._port = port
        self._logger = get_logger("api.rest")
        self._routes: dict[str, dict[str, Any]] = {}
        self._server: asyncio.AbstractServer | None = None

    def route(self, method: str, path: str, handler: Any = None):
        self._routes.setdefault(method, {})[path] = handler

    async def start(self):
        self._logger.info("REST server starting on %s:%s", self._host, self._port)
        import json as _json
        handler = await asyncio.start_server(
            self._handle_connection, self._host, self._port,
        )
        self._server = handler
        self._logger.info("REST server ready on %s:%s", self._host, self._port)

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._logger.info("REST server stopped")

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            data = await asyncio.wait_for(reader.read(65536), timeout=30)
            request = json.loads(data.decode())
            response = await self._dispatch(request)
            writer.write(json.dumps(response).encode())
            await writer.drain()
        except Exception as e:
            writer.write(json.dumps({"error": str(e)}).encode())
            await writer.drain()
        finally:
            writer.close()

    async def _dispatch(self, request: dict) -> dict:
        method = request.get("method", "GET")
        path = request.get("path", "/")
        route_handler = self._routes.get(method, {}).get(path)
        if route_handler:
            try:
                result = route_handler(request.get("params", {}))
                if asyncio.iscoroutine(result):
                    result = await result
                return {"result": result}
            except Exception as e:
                return {"error": str(e)}
        return {"error": f"no route: {method} {path}"}


def create_default_rest(bus: EventBus, host: str = "127.0.0.1", port: int = 8765) -> RESTServer:
    server = RESTServer(bus, host=host, port=port)
    from aetheros_orchestrator.lifecycle.health import HealthStatus
    server.route("GET", "/health", lambda p: {"status": "ok", "subsystems": {}})
    server.route("GET", "/version", lambda p: {"version": "0.1.0", "name": "AetherOS"})
    server.route("POST", "/event", lambda p: bus.publish(p.get("topic", ""), p.get("data"), p.get("source", "api")))
    server.route("GET", "/events", lambda p: bus.get_history(p.get("topic"), p.get("limit", 50)))
    return server
