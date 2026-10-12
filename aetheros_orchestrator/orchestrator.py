from __future__ import annotations

import asyncio
from typing import Any

from aetheros_orchestrator.bus.event_bus import EventBus
from aetheros_orchestrator.bus.rpc import RPCServer, RPCClient
from aetheros_orchestrator.graph.resolver import DependencyGraph, BUILTIN_SUBSYSTEMS
from aetheros_orchestrator.lifecycle.manager import LifecycleManager
from aetheros_orchestrator.lifecycle.health import HealthChecker
from aetheros_orchestrator.logging.setup import setup_logging, get_logger
from aetheros_orchestrator.logging.telemetry import get_tracer, get_metrics
from aetheros_orchestrator.api.rest import create_default_rest
from aetheros_orchestrator.api.websocket import WebSocketServer


class AetherosOrchestrator:
    def __init__(self, config: dict):
        self._config = config
        self._logger = get_logger("orchestrator")
        self._running = False

        self.bus = EventBus()
        self.rpc_server = RPCServer(self.bus, "orchestrator")
        self.rpc_client = RPCClient(self.bus)
        self.health = HealthChecker(config.get("orchestrator", {}).get("healthcheck_interval", 10.0))
        self.lifecycle = LifecycleManager(
            startup_timeout=config.get("orchestrator", {}).get("startup_timeout", 30.0),
            shutdown_timeout=config.get("orchestrator", {}).get("shutdown_timeout", 15.0),
        )
        self.tracer = get_tracer()
        self.metrics = get_metrics()
        self.graph = DependencyGraph(BUILTIN_SUBSYSTEMS)

        self._rest_server = create_default_rest(self.bus, config["daemon"]["host"], config["daemon"]["port"])
        self._ws_server = WebSocketServer(self.bus)

    async def start(self):
        self._logger.info("Starting AetherOS subsystems...")
        setup_logging(self._config["daemon"])
        await self.bus.start()
        self._register_rpcs()

        enabled = self._get_enabled_subsystems()
        resolution = self.graph.resolve(enabled)
        self._logger.info("Start order: %s", resolution.order)
        if resolution.cycles:
            self._logger.warning("Dependency cycles: %s", resolution.cycles)
        if resolution.omitted:
            self._logger.warning("Omitted (unresolved): %s", resolution.omitted)

        self._register_subsystem_handles(resolution.order)
        self.lifecycle.set_start_order(resolution.order)

        results = await self.lifecycle.start_all()
        for name, state in results.items():
            self._logger.info("Subsystem %s: %s", name, state.value)
            self.health.record_health(name, state.value if state.value != "failed" else "unhealthy")

        self.health.register_check("orchestrator", lambda: True)
        await self.health.start()

        await self._rest_server.start()
        if self._config.get("api", {}).get("websocket_enabled", True):
            await self._ws_server.start()

        self._running = True
        await self.bus.publish("system.started", {"config": self._config["daemon"]}, "orchestrator")
        self._logger.info("All subsystems started. API on %s:%s", self._config["daemon"]["host"], self._config["daemon"]["port"])

    async def stop(self):
        self._running = False
        self._logger.info("Shutting down...")
        await self.bus.publish("system.stopping", {}, "orchestrator")
        await self._ws_server.stop()
        await self._rest_server.stop()
        await self.health.stop()
        await self.lifecycle.stop_all()
        await self.bus.stop()
        self._logger.info("All subsystems stopped")

    async def restart(self, subsystem: str | None = None):
        if subsystem:
            await self.lifecycle.restart(subsystem)
            self._logger.info("Restarted subsystem: %s", subsystem)
        else:
            await self.lifecycle.restart_all()
            self._logger.info("All subsystems restarted")

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "subsystems": {
                name: {
                    "state": self.lifecycle.get_state(name).value if self.lifecycle.get_state(name) else "unknown",
                    "health": self.health.get_status(name).status if self.health.get_status(name) else "unknown",
                }
                for name in BUILTIN_SUBSYSTEMS
            },
            "metrics": self.metrics.snapshot(),
            "uptime": 0,
        }

    def _get_enabled_subsystems(self) -> set[str]:
        subsys_cfg = self._config.get("subsystems", {})
        enabled = set()
        for name in BUILTIN_SUBSYSTEMS:
            cfg = subsys_cfg.get(name, {})
            if cfg.get("enabled", True):
                enabled.add(name)
        return enabled

    def _register_rpcs(self):
        self.rpc_server.register("status", lambda **kw: self.get_status())
        self.rpc_server.register("restart", lambda subsystem=None, **kw: self.restart(subsystem))
        self.rpc_server.register("stop", lambda **kw: self.stop())
        self.rpc_server.register("health", lambda **kw: {n: s.status for n, s in self.health.all_statuses().items()})

    def _register_subsystem_handles(self, order: list[str]):
        self.lifecycle.register("logging", startup=lambda c: setup_logging(self._config["daemon"]))
        self.lifecycle.register("config", startup=lambda c: self._config)
        self.lifecycle.register("bus", startup=lambda c: self.bus.start(), shutdown=lambda c: self.bus.stop())
        self.lifecycle.register("api", startup=lambda c: self._rest_server.start(), shutdown=lambda c: self._rest_server.stop())
        self.lifecycle.register("mcp", startup=self._start_mcp, shutdown=self._stop_mcp)
        self.lifecycle.register("reasoning", startup=self._start_reasoning, shutdown=self._stop_reasoning)
        self.lifecycle.register("skills", startup=self._start_skills, shutdown=self._stop_skills)
        self.lifecycle.register("platform", startup=self._start_platform, shutdown=self._stop_platform)
        self.lifecycle.register("knowledge", startup=self._start_knowledge, shutdown=self._stop_knowledge)
        self.lifecycle.register("ui", startup=self._start_ui, shutdown=self._stop_ui)
        self.lifecycle.register("desktop", startup=self._start_desktop, shutdown=self._stop_desktop)

    async def _start_mcp(self, config: dict):
        try:
            from aetheros_mcp_hub import AetherosMCPHub
            hub = AetherosMCPHub()
            await hub.start()
            self._mcp_hub = hub
            self._logger.info("MCP Hub started")
        except ImportError:
            self._logger.warning("MCP Hub not available")

    async def _stop_mcp(self, config: dict):
        if hasattr(self, "_mcp_hub"):
            await self._mcp_hub.stop()

    async def _start_reasoning(self, config: dict):
        try:
            from aetheros_reasoning import ReasoningEngine
            engine = ReasoningEngine()
            self._reasoning = engine
            self._logger.info("Reasoning engine started")
        except ImportError:
            self._logger.warning("Reasoning engine not available")

    async def _stop_reasoning(self, config: dict):
        pass

    async def _start_skills(self, config: dict):
        try:
            from aetheros_skills import SkillsRegistry
            registry = SkillsRegistry()
            await registry.load_all()
            self._skills = registry
            self._logger.info("Skills registry loaded")
        except ImportError:
            self._logger.warning("Skills system not available")

    async def _stop_skills(self, config: dict):
        pass

    async def _start_platform(self, config: dict):
        try:
            from aetheros_platform import AetherosPlatform
            platform = AetherosPlatform(self._config)
            await platform.start()
            self._platform = platform
            self._logger.info("Platform layer started")
        except ImportError:
            self._logger.warning("Platform layer not available")

    async def _stop_platform(self, config: dict):
        if hasattr(self, "_platform"):
            await self._platform.stop()

    async def _start_knowledge(self, config: dict):
        try:
            from aetheros_knowledge import init_knowledge
            self._knowledge = init_knowledge(self._config.get("knowledge", {}))
            self._logger.info("Knowledge OS initialized")
        except ImportError:
            self._logger.warning("Knowledge OS not available")

    async def _stop_knowledge(self, config: dict):
        pass

    async def _start_ui(self, config: dict):
        self._logger.info("UI layer ready")

    async def _stop_ui(self, config: dict):
        pass

    async def _start_desktop(self, config: dict):
        self._logger.info("Desktop bridge ready")

    async def _stop_desktop(self, config: dict):
        pass
