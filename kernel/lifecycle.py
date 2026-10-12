"""
Lifecycle Manager — component and service lifecycle for the AetherOS Kernel.

Manages the startup, health-check, and shutdown of all kernel components.
Components register with a name and optional dependencies; the lifecycle
manager resolves the startup order and handles graceful shutdown.

States:
    STOPPED → INITIALIZING → RUNNING → STOPPING → STOPPED
                                ↓
                            FAILED (on error)
"""

from __future__ import annotations

import enum
import logging
import signal
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus, EventTopics

logger = logging.getLogger(__name__)


class ComponentState(enum.Enum):
    """Lifecycle state of a kernel component."""
    UNKNOWN = "unknown"
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass
class ServiceRegistration:
    """Registration metadata for a kernel service/component.

    Attributes:
        name: Unique component name
        version: Component version string
        description: Human-readable description
        dependencies: List of component names this depends on
        init_fn: Callable(ServiceRegistration) -> bool, called during startup
        start_fn: Callable(ServiceRegistration) -> bool, called after init
        stop_fn: Callable(ServiceRegistration) -> None, called during shutdown
        health_fn: Optional callable() -> bool for health checks
        timeout_seconds: Max time to wait for init/start
    """
    name: str
    version: str = "0.1.0"
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    init_fn: Optional[Callable[["ServiceRegistration"], bool]] = None
    start_fn: Optional[Callable[["ServiceRegistration"], bool]] = None
    stop_fn: Optional[Callable[["ServiceRegistration"], None]] = None
    health_fn: Optional[Callable[[], bool]] = None
    timeout_seconds: float = 30.0

    # Runtime state
    state: ComponentState = ComponentState.STOPPED
    started_at: Optional[float] = None
    error: Optional[str] = None


class LifecycleManager:
    """Manages component lifecycle across the kernel.

    Usage:
        mgr = LifecycleManager(event_bus)
        mgr.register(ServiceRegistration(name="scheduler", ...))
        mgr.start()  # Starts all in dependency order
        # ... run ...
        mgr.shutdown()  # Graceful stop in reverse order
    """

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._services: Dict[str, ServiceRegistration] = {}
        self._start_order: List[str] = []
        self._shutdown_flag = False
        self._health_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, service: ServiceRegistration) -> ServiceRegistration:
        """Register a component/service with the lifecycle manager.

        Raises ValueError if a service with the same name already exists.
        """
        with self._lock:
            if service.name in self._services:
                raise ValueError(f"Service '{service.name}' already registered")
            self._services[service.name] = service
        logger.info(
            "Lifecycle: registered service '%s' (v%s)",
            service.name, service.version,
        )
        return service

    def get(self, name: str) -> Optional[ServiceRegistration]:
        """Get a registered service by name."""
        with self._lock:
            return self._services.get(name)

    def get_state(self, name: str) -> Optional[ComponentState]:
        """Get the current state of a service."""
        svc = self.get(name)
        return svc.state if svc else None

    def get_all(self) -> Dict[str, ServiceRegistration]:
        """Return a snapshot of all registered services."""
        with self._lock:
            return dict(self._services)

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """Start all registered components in dependency order.

        Returns True if all components started successfully.
        """
        self._event_bus.emit(EventTopics.LIFECYCLE_STARTING, source="lifecycle")

        with self._lock:
            services = dict(self._services)
        ordered = self._resolve_dependency_order(services)

        self._start_order = ordered
        success = True

        for name in ordered:
            svc = services[name]
            try:
                self._start_single(svc)
            except Exception as exc:
                svc.state = ComponentState.FAILED
                svc.error = str(exc)
                logger.error(
                    "Lifecycle: service '%s' failed to start: %s",
                    name, exc,
                )
                success = False
                self._event_bus.emit(EventTopics.SYSTEM_ERROR, {
                    "component": name, "error": str(exc),
                })
                # Continue starting other services so we don't cascade failures

        if success:
            logger.info("Lifecycle: all %d components started", len(ordered))
        else:
            logger.warning(
                "Lifecycle: %d/%d components started with errors",
                sum(1 for n in ordered if services[n].state == ComponentState.RUNNING),
                len(ordered),
            )

        self._event_bus.emit(EventTopics.LIFECYCLE_STARTED, {
            "success": success,
            "count": len(ordered),
        })

        # Start background health checker
        self._start_health_checker()

        return success

    def _start_single(self, svc: ServiceRegistration) -> None:
        """Initialize and start a single service."""
        svc.state = ComponentState.INITIALIZING
        logger.debug("Lifecycle: initializing '%s'...", svc.name)

        if svc.init_fn:
            start = time.time()
            result = svc.init_fn(svc)
            elapsed = time.time() - start
            if not result:
                raise RuntimeError(f"init_fn returned False ({elapsed:.1f}s)")

        svc.state = ComponentState.RUNNING
        svc.started_at = time.time()

        if svc.start_fn:
            start = time.time()
            svc.start_fn(svc)
            elapsed = time.time() - start
            logger.debug("Lifecycle: '%s' start_fn completed in %.1fs", svc.name, elapsed)

        logger.info("Lifecycle: '%s' is RUNNING", svc.name)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Shut down all components in reverse dependency order."""
        self._shutdown_flag = True
        self._event_bus.emit(EventTopics.LIFECYCLE_STOPPING, source="lifecycle")

        if self._health_thread:
            self._health_thread.join(timeout=5)

        with self._lock:
            services = dict(self._services)

        # Reverse order for shutdown
        for name in reversed(self._start_order):
            svc = services.get(name)
            if svc is None or svc.state != ComponentState.RUNNING:
                continue
            try:
                svc.state = ComponentState.STOPPING
                if svc.stop_fn:
                    svc.stop_fn(svc)
                svc.state = ComponentState.STOPPED
                logger.info("Lifecycle: '%s' stopped", name)
            except Exception as exc:
                svc.state = ComponentState.FAILED
                svc.error = str(exc)
                logger.error("Lifecycle: '%s' stopped with error: %s", name, exc)

        self._event_bus.emit(EventTopics.LIFECYCLE_STOPPED, source="lifecycle")
        logger.info("Lifecycle: shutdown complete")

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def _start_health_checker(self) -> None:
        """Start background thread that periodically checks component health."""
        if self._health_thread is not None:
            return

        def _check_health():
            while not self._shutdown_flag:
                time.sleep(30)
                for name, svc in list(self.get_all().items()):
                    if svc.state != ComponentState.RUNNING:
                        continue
                    if svc.health_fn:
                        try:
                            healthy = svc.health_fn()
                            if not healthy:
                                logger.warning(
                                    "Lifecycle: health check failed for '%s'",
                                    name,
                                )
                                self._event_bus.emit(EventTopics.LIFECYCLE_HEALTH, {
                                    "component": name, "healthy": False,
                                })
                        except Exception as exc:
                            logger.warning(
                                "Lifecycle: health check error for '%s': %s",
                                name, exc,
                            )

        self._health_thread = threading.Thread(
            target=_check_health,
            daemon=True,
            name="kernel-health",
        )
        self._health_thread.start()

    def health_summary(self) -> Dict[str, Any]:
        """Return a summary of all component health states."""
        summary = {"healthy": 0, "degraded": 0, "failed": 0, "components": {}}
        for name, svc in self.get_all().items():
            entry = {
                "state": svc.state.value,
                "version": svc.version,
                "error": svc.error,
            }
            if svc.health_fn:
                try:
                    entry["healthy"] = svc.health_fn()
                except Exception as exc:
                    entry["healthy"] = False
                    entry["health_error"] = str(exc)
            summary["components"][name] = entry
            if svc.state == ComponentState.FAILED:
                summary["failed"] += 1
            elif svc.state == ComponentState.RUNNING:
                summary["healthy"] += 1
            else:
                summary["degraded"] += 1
        return summary

    # ------------------------------------------------------------------
    # Dependency resolution
    # ------------------------------------------------------------------

    def _resolve_dependency_order(
        self, services: Dict[str, ServiceRegistration]
    ) -> List[str]:
        """Topological sort of services by dependencies.

        Raises ValueError on circular dependencies.
        """
        visited: set = set()
        in_progress: set = set()
        result: List[str] = []

        def _visit(name: str, chain: List[str]):
            if name in visited:
                return
            if name in in_progress:
                cycle = " -> ".join(chain + [name])
                raise ValueError(f"Circular dependency: {cycle}")

            svc = services.get(name)
            if svc is None:
                return

            in_progress.add(name)
            for dep in svc.dependencies:
                _visit(dep, chain + [name])
            in_progress.discard(name)
            visited.add(name)
            result.append(name)

        for name in services:
            _visit(name, [])

        return result

    # ------------------------------------------------------------------
    # Signal handling
    # ------------------------------------------------------------------

    def install_signal_handlers(self) -> None:
        """Install SIGINT/SIGTERM handlers that trigger graceful shutdown."""
        def _handle_signal(signum, frame):
            sig_name = signal.Signals(signum).name
            logger.info("Lifecycle: received %s, shutting down...", sig_name)
            self.shutdown()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)
