"""API routes — route registry and dashboard API aggregator."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class RouteRegistry:
    def __init__(self):
        self._routes: dict[tuple[str, str], Callable] = {}

    def register(self, method: str, path: str, handler: Callable):
        self._routes[(method.upper(), path.rstrip("/") or "/")] = handler

    def get(self, path: str, handler: Callable):
        self.register("GET", path, handler)

    def post(self, path: str, handler: Callable):
        self.register("POST", path, handler)

    def put(self, path: str, handler: Callable):
        self.register("PUT", path, handler)

    def delete(self, path: str, handler: Callable):
        self.register("DELETE", path, handler)

    def match(self, method: str, path: str) -> Optional[Callable]:
        return self._routes.get((method.upper(), path.rstrip("/") or "/"))

    def list_routes(self) -> list[dict]:
        return [
            {"method": m, "path": p}
            for (m, p) in self._routes
        ]


class DashboardAPI:
    def __init__(self):
        self.routes = RouteRegistry()
        self._data_providers: dict[str, Callable] = {}

    def register_data(self, key: str, provider: Callable):
        self._data_providers[key] = provider

    def get_data(self, key: str, **kwargs) -> Any:
        provider = self._data_providers.get(key)
        if provider:
            return provider(**kwargs)
        return None

    def register_default_routes(self):
        self.routes.get("/api/health", self._health)
        self.routes.get("/api/status", self._status)
        self.routes.post("/api/data", self._get_data)
        self.routes.get("/api/routes", self._list_routes)
        self.routes.get("/api/info", self._info)

    async def _health(self, body, params, headers, writer):
        return {"status": "ok", "timestamp": __import__(
            'datetime').datetime.utcnow().isoformat() + "Z"}

    async def _status(self, body, params, headers, writer):
        return {
            "status": "running",
            "version": "1.0.0",
            "uptime": 0,
            "plugins": [],
            "services": [],
        }

    async def _get_data(self, body, params, headers, writer):
        key = body.get("key", "")
        kwargs = body.get("params", {})
        data = self.get_data(key, **kwargs)
        return {"key": key, "data": data}

    async def _list_routes(self, body, params, headers, writer):
        return {"routes": self.routes.list_routes()}

    async def _info(self, body, params, headers, writer):
        return {
            "name": "AetherOS Dashboard",
            "version": "1.0.0",
            "data_providers": list(self._data_providers.keys()),
            "routes": len(self.routes.list_routes()),
        }

    def shutdown(self):
        pass
