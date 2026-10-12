from __future__ import annotations

import asyncio
import json
import uuid
import time
from typing import Any, Callable

from aetheros_orchestrator.bus.event_bus import EventBus


class RPCServer:
    def __init__(self, bus: EventBus, namespace: str = ""):
        self._bus = bus
        self._namespace = namespace
        self._handlers: dict[str, Callable] = {}

    def register(self, method: str, handler: Callable):
        full = f"{self._namespace}.{method}" if self._namespace else method
        self._handlers[full] = handler
        self._bus.subscribe(f"rpc.request.{full}", self._handle)

    async def _handle(self, event: dict):
        method = event["data"]["method"]
        handler = self._handlers.get(method)
        if handler is None:
            return

        request_id = event["data"]["request_id"]
        params = event["data"].get("params", {})

        try:
            result = handler(**params)
            if asyncio.iscoroutine(result):
                result = await result
            await self._bus.publish(
                f"rpc.response.{request_id}",
                {"request_id": request_id, "result": result, "method": method},
            )
        except Exception as e:
            await self._bus.publish(
                f"rpc.response.{request_id}",
                {"request_id": request_id, "result": None, "method": method, "error": str(e)},
            )


class RPCClient:
    def __init__(self, bus: EventBus, timeout: float = 30.0):
        self._bus = bus
        self._timeout = timeout
        self._pending: dict[str, asyncio.Future] = {}

    async def call(self, method: str, params: dict = None, timeout: float | None = None) -> Any:
        request_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        def cleanup(event: dict | None = None):
            self._pending.pop(request_id, None)

        self._bus.subscribe(f"rpc.response.{request_id}", lambda e: self._resolve(e, request_id))

        await self._bus.publish(
            "rpc.request." + method,
            {"method": method, "params": params or {}, "request_id": request_id},
        )

        try:
            result = await asyncio.wait_for(future, timeout or self._timeout)
            self._bus.unsubscribe(f"rpc.response.{request_id}", lambda e: None)
            return result
        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            raise TimeoutError(f"RPC call to {method} timed out")

    def _resolve(self, event: dict, request_id: str):
        future = self._pending.get(request_id)
        if future is None or future.done():
            return
        data = event["data"]
        if "error" in data and data["error"]:
            future.set_exception(RuntimeError(data["error"]))
        else:
            future.set_result(data["result"])
