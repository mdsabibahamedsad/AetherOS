"""Runtime Manager — initialize, start, stop, restart, health, diagnostics, recovery.

Owns the complete lifecycle of the AI Runtime subsystem.
Every component registers here; the manager orchestrates startup/shutdown order.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_runtime.manager")


class RuntimeState(enum.Enum):
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    ERROR = "error"
    RECOVERING = "recovering"
    RESTARTING = "restarting"


@dataclass
class RuntimeConfig:
    auto_start: bool = False
    health_check_interval: float = 30.0
    recovery_max_attempts: int = 3
    recovery_delay: float = 5.0
    shutdown_timeout: float = 10.0
    diagnostics_enabled: bool = True
    performance_tracking: bool = True


class ComponentState:
    def __init__(self, name: str) -> None:
        self.name = name
        self.running = False
        self.healthy = True
        self.error: Optional[str] = None
        self.started_at: float = 0.0
        self.restart_count: int = 0

    def start(self) -> None:
        self.running = True
        self.started_at = time.time()

    def stop(self) -> None:
        self.running = False

    def fail(self, error: str) -> None:
        self.running = False
        self.healthy = False
        self.error = error


ComponentFactory = Callable[[], Any]


class RuntimeManager:
    """Central lifecycle manager for the AI Runtime.

    Every subsystem (conversations, streaming, agents, tools, etc.)
    registers here. The manager controls:
    - Startup sequencing (dependency-aware)
    - Health checks with configurable intervals
    - Automatic recovery on failure
    - Graceful shutdown
    - Full diagnostics
    """

    def __init__(self, config: Optional[RuntimeConfig] = None) -> None:
        self._lock = threading.RLock()
        self._config = config or RuntimeConfig()
        self._state = RuntimeState.STOPPED
        self._components: Dict[str, ComponentState] = {}
        self._factories: Dict[str, ComponentFactory] = {}
        self._instances: Dict[str, Any] = {}
        self._dependencies: Dict[str, List[str]] = {}
        self._start_order: List[str] = []
        self._health_thread: Optional[threading.Thread] = None
        self._health_stop = threading.Event()
        self._listeners: List[Callable[[RuntimeState, RuntimeState], None]] = []
        self._start_time: float = 0.0

    # ------------------------------------------------------------------
    # Component registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        factory: ComponentFactory,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        with self._lock:
            self._factories[name] = factory
            self._components[name] = ComponentState(name)
            if dependencies:
                self._dependencies[name] = dependencies
            logger.info("Runtime component registered: %s", name)

    def get_component(self, name: str) -> Optional[Any]:
        with self._lock:
            return self._instances.get(name)

    def get_component_state(self, name: str) -> Optional[ComponentState]:
        with self._lock:
            return self._components.get(name)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        with self._lock:
            if self._state != RuntimeState.STOPPED:
                return False
            self._state = RuntimeState.INITIALIZING
        self._notify(RuntimeState.STOPPED, RuntimeState.INITIALIZING)
        logger.info("Runtime initializing...")

        with self._lock:
            self._resolve_start_order()

        for name in self._start_order:
            try:
                factory = self._factories.get(name)
                if factory:
                    instance = factory()
                    with self._lock:
                        self._instances[name] = instance
                        self._components[name].start()
                    logger.info("Component initialized: %s", name)
            except Exception as exc:
                logger.error("Component %s failed to initialize: %s", name, exc)
                with self._lock:
                    self._components[name].fail(str(exc))
                    self._state = RuntimeState.ERROR
                self._notify(RuntimeState.INITIALIZING, RuntimeState.ERROR)
                return False

        self._start_time = time.time()
        with self._lock:
            self._state = RuntimeState.RUNNING
        self._notify(RuntimeState.INITIALIZING, RuntimeState.RUNNING)
        logger.info("Runtime initialized successfully (%d components)", len(self._instances))

        if self._config.health_check_interval > 0:
            self._start_health_checks()

        return True

    def start(self) -> bool:
        if self._state == RuntimeState.RUNNING:
            return True
        return self.initialize()

    def stop(self) -> bool:
        with self._lock:
            if self._state == RuntimeState.STOPPED:
                return True
            self._state = RuntimeState.STOPPED
        self._notify(self._state, RuntimeState.STOPPED)
        self._stop_health_checks()

        for name in reversed(self._start_order):
            try:
                instance = self._instances.get(name)
                if hasattr(instance, "shutdown"):
                    instance.shutdown()
                with self._lock:
                    self._components[name].stop()
                logger.info("Component stopped: %s", name)
            except Exception as exc:
                logger.warning("Component %s shutdown error: %s", name, exc)

        with self._lock:
            self._instances.clear()
        logger.info("Runtime stopped")
        return True

    def restart(self) -> bool:
        old_state = self._state
        with self._lock:
            self._state = RuntimeState.RESTARTING
        self._notify(old_state, RuntimeState.RESTARTING)
        logger.info("Runtime restarting...")

        self.stop()
        return self.start()

    def is_running(self) -> bool:
        return self._state == RuntimeState.RUNNING

    def is_healthy(self) -> bool:
        if self._state != RuntimeState.RUNNING:
            return False
        with self._lock:
            return all(c.healthy for c in self._components.values())

    @property
    def state(self) -> RuntimeState:
        return self._state

    @property
    def uptime(self) -> float:
        if self._start_time == 0:
            return 0.0
        return time.time() - self._start_time

    # ------------------------------------------------------------------
    # Health checks
    # ------------------------------------------------------------------

    def _start_health_checks(self) -> None:
        self._health_stop.clear()
        self._health_thread = threading.Thread(
            target=self._health_loop, daemon=True,
            name="runtime-health",
        )
        self._health_thread.start()

    def _stop_health_checks(self) -> None:
        self._health_stop.set()
        if self._health_thread:
            self._health_thread.join(timeout=5)

    def _health_loop(self) -> None:
        while not self._health_stop.is_set():
            self.check_health()
            self._health_stop.wait(self._config.health_check_interval)

    def check_health(self) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        with self._lock:
            names = list(self._components.keys())

        for name in names:
            component = self.get_component(name)
            healthy = True
            if component and hasattr(component, "health_check"):
                try:
                    healthy = bool(component.health_check())
                except Exception as exc:
                    logger.warning("Health check failed for %s: %s", name, exc)
                    healthy = False

            with self._lock:
                comp = self._components.get(name)
                if comp:
                    comp.healthy = healthy
                    if not healthy:
                        comp.error = "Health check failed"

            results[name] = healthy

        all_healthy = all(results.values())
        with self._lock:
            if not all_healthy and self._state == RuntimeState.RUNNING:
                self._state = RuntimeState.DEGRADED
                self._notify(RuntimeState.RUNNING, RuntimeState.DEGRADED)

        return results

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def recover(self, component_name: Optional[str] = None) -> bool:
        old_state = self._state
        with self._lock:
            self._state = RuntimeState.RECOVERING
        self._notify(old_state, RuntimeState.RECOVERING)
        logger.info("Runtime recovery starting...")

        targets = [component_name] if component_name else list(self._factories.keys())

        success = True
        for name in targets:
            for attempt in range(self._config.recovery_max_attempts):
                try:
                    factory = self._factories.get(name)
                    if not factory:
                        continue
                    instance = factory()
                    with self._lock:
                        self._instances[name] = instance
                        comp = self._components.get(name)
                        if comp:
                            comp.start()
                            comp.healthy = True
                            comp.error = None
                            comp.restart_count += 1
                    logger.info("Recovered component: %s (attempt %d)", name, attempt + 1)
                    break
                except Exception as exc:
                    logger.error("Recovery attempt %d for %s failed: %s", attempt + 1, name, exc)
                    if attempt == self._config.recovery_max_attempts - 1:
                        success = False

        with self._lock:
            self._state = RuntimeState.RUNNING if success else RuntimeState.ERROR
        self._notify(RuntimeState.RECOVERING, self._state)
        return success

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "state": self._state.value,
                "uptime_seconds": self.uptime,
                "component_count": len(self._components),
                "instance_count": len(self._instances),
                "healthy": all(c.healthy for c in self._components.values()),
                "components": {
                    name: {
                        "running": c.running,
                        "healthy": c.healthy,
                        "error": c.error,
                        "started_at": c.started_at,
                        "restart_count": c.restart_count,
                    }
                    for name, c in self._components.items()
                },
                "config": {
                    "health_check_interval": self._config.health_check_interval,
                    "recovery_max_attempts": self._config.recovery_max_attempts,
                },
            }

    def summary(self) -> str:
        info = self.diagnostics()
        lines = [
            f"Runtime Manager: {info['state'].upper()}",
            f"  Uptime: {info['uptime_seconds']:.0f}s",
            f"  Components: {info['component_count']} registered, {info['instance_count']} running",
            f"  Healthy: {info['healthy']}",
        ]
        for name, c in info["components"].items():
            icon = "✓" if c["healthy"] else "✗"
            lines.append(f"    {icon} {name} (restarts: {c['restart_count']})")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_state_change(self, callback: Callable[[RuntimeState, RuntimeState], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def _notify(self, old: RuntimeState, new: RuntimeState) -> None:
        for cb in self._listeners:
            try:
                cb(old, new)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _resolve_start_order(self) -> None:
        visited: Set[str] = set()
        result: List[str] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            for dep in self._dependencies.get(name, []):
                visit(dep)
            result.append(name)

        for name in self._factories:
            visit(name)

        self._start_order = result