from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class SubsystemState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass
class SubsystemHandle:
    name: str
    state: SubsystemState = SubsystemState.STOPPED
    startup: Callable | None = None
    shutdown: Callable | None = None
    restart: Callable | None = None
    config: dict = field(default_factory=dict)
    started_at: float = 0.0
    error: str = ""


class LifecycleManager:
    def __init__(self, startup_timeout: float = 30.0, shutdown_timeout: float = 15.0):
        self._subsystems: dict[str, SubsystemHandle] = {}
        self._startup_timeout = startup_timeout
        self._shutdown_timeout = shutdown_timeout
        self._start_order: list[str] = []
        self._running = False

    def register(self, name: str, startup: Callable | None = None, shutdown: Callable | None = None,
                 restart: Callable | None = None, config: dict | None = None):
        self._subsystems[name] = SubsystemHandle(
            name=name, startup=startup, shutdown=shutdown,
            restart=restart, config=config or {},
        )

    def set_start_order(self, order: list[str]):
        known = {s.name for s in self._subsystems.values()}
        self._start_order = [n for n in order if n in known]

    async def start_all(self) -> dict[str, SubsystemState]:
        self._running = True
        results: dict[str, SubsystemState] = {}

        for name in self._start_order:
            handle = self._subsystems.get(name)
            if handle is None:
                continue
            state = await self._start_subsystem(name)
            results[name] = state

        for name, handle in self._subsystems.items():
            if name not in results:
                state = await self._start_subsystem(name)
                results[name] = state

        return results

    async def _start_subsystem(self, name: str) -> SubsystemState:
        handle = self._subsystems[name]
        if handle.state != SubsystemState.STOPPED:
            return handle.state

        handle.state = SubsystemState.STARTING
        handle.error = ""

        if handle.startup:
            try:
                result = handle.startup(handle.config)
                if asyncio.iscoroutine(result):
                    await asyncio.wait_for(result, timeout=self._startup_timeout)
                handle.state = SubsystemState.RUNNING
                handle.started_at = time.time()
            except asyncio.TimeoutError:
                handle.state = SubsystemState.FAILED
                handle.error = f"startup timed out after {self._startup_timeout}s"
            except Exception as e:
                handle.state = SubsystemState.FAILED
                handle.error = str(e)
        else:
            handle.state = SubsystemState.RUNNING
            handle.started_at = time.time()

        return handle.state

    async def stop_all(self) -> dict[str, SubsystemState]:
        results: dict[str, SubsystemState] = {}
        for name in reversed(self._start_order):
            handle = self._subsystems.get(name)
            if handle is None:
                continue
            results[name] = await self._stop_subsystem(name)

        for name, handle in self._subsystems.items():
            if name not in results:
                results[name] = await self._stop_subsystem(name)

        self._running = False
        return results

    async def _stop_subsystem(self, name: str) -> SubsystemState:
        handle = self._subsystems[name]
        if handle.state in (SubsystemState.STOPPED, SubsystemState.FAILED):
            return handle.state

        handle.state = SubsystemState.STOPPING
        if handle.shutdown:
            try:
                result = handle.shutdown(handle.config)
                if asyncio.iscoroutine(result):
                    await asyncio.wait_for(result, timeout=self._shutdown_timeout)
            except Exception as e:
                handle.error = str(e)
        handle.state = SubsystemState.STOPPED
        return handle.state

    async def restart(self, name: str) -> SubsystemState:
        await self._stop_subsystem(name)
        return await self._start_subsystem(name)

    async def restart_all(self) -> dict[str, SubsystemState]:
        await self.stop_all()
        return await self.start_all()

    def get_state(self, name: str) -> SubsystemState | None:
        handle = self._subsystems.get(name)
        return handle.state if handle else None

    def get_handle(self, name: str) -> SubsystemHandle | None:
        return self._subsystems.get(name)

    def is_running(self) -> bool:
        return self._running
