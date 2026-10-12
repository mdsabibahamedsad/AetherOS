"""Dependency Injection Service Container for AetherOS.

Provides a lightweight, typed dependency injection container.
Services register themselves with a lifecycle and are resolved on demand.

Usage::

    container = ServiceContainer()
    container.register("logger", lambda c: logging.getLogger(), ServiceLifecycle.SINGLETON)
    container.register("gateway", lambda c: Gateway(c.resolve("logger")), ServiceLifecycle.SINGLETON)

    gateway = container.resolve("gateway")
"""

from __future__ import annotations

import enum
import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger("aetheros_arch.container")


class ServiceLifecycle(enum.Enum):
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


ServiceFactory = Callable[["ServiceContainer"], Any]


class ServiceRegistration:
    def __init__(
        self,
        name: str,
        factory: ServiceFactory,
        lifecycle: ServiceLifecycle = ServiceLifecycle.SINGLETON,
        description: str = "",
    ) -> None:
        self.name = name
        self.factory = factory
        self.lifecycle = lifecycle
        self.description = description
        self.instance: Any = None
        self._lock = threading.Lock()

    def resolve(self, container: "ServiceContainer") -> Any:
        if self.lifecycle == ServiceLifecycle.TRANSIENT:
            return self.factory(container)

        if self.lifecycle == ServiceLifecycle.SINGLETON:
            if self.instance is None:
                with self._lock:
                    if self.instance is None:
                        self.instance = self.factory(container)
            return self.instance

        if self.lifecycle == ServiceLifecycle.SCOPED:
            raise RuntimeError(
                f"Service '{self.name}' is scoped; "
                f"use resolve_scoped() with a scope context"
            )

        return self.factory(container)


class ServiceContainer:
    """Dependency injection container.

    Thread-safe. Supports singleton, transient, and scoped lifecycles.
    """

    def __init__(self) -> None:
        self._registrations: Dict[str, ServiceRegistration] = {}
        self._lock = threading.RLock()
        self._scoped_instances: Dict[str, Dict[str, Any]] = {}
        self._started: List[str] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        factory: ServiceFactory,
        lifecycle: ServiceLifecycle = ServiceLifecycle.SINGLETON,
        description: str = "",
    ) -> None:
        """Register a service."""
        with self._lock:
            self._registrations[name] = ServiceRegistration(
                name=name,
                factory=factory,
                lifecycle=lifecycle,
                description=description,
            )

    def register_instance(self, name: str, instance: Any, description: str = "") -> None:
        """Register an already-created instance as a singleton."""
        with self._lock:
            reg = ServiceRegistration(
                name=name,
                factory=lambda c: instance,
                lifecycle=ServiceLifecycle.SINGLETON,
                description=description,
            )
            reg.instance = instance
            self._registrations[name] = reg

    def register_type(
        self,
        name: str,
        cls: Type,
        lifecycle: ServiceLifecycle = ServiceLifecycle.SINGLETON,
        description: str = "",
    ) -> None:
        """Register a class type for auto-instantiation."""

        def factory(container: ServiceContainer) -> Any:
            sig = __import__("inspect").signature(cls.__init__)
            params = {}
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                if param_name == "container":
                    params[param_name] = container
                elif param.default is not param.empty:
                    if param.default is None and container.has(param_name):
                        params[param_name] = container.resolve(param_name)
                elif container.has(param_name):
                    params[param_name] = container.resolve(param_name)
            return cls(**params)

        self.register(name, factory, lifecycle, description)

    def has(self, name: str) -> bool:
        return name in self._registrations

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(self, name: str) -> Any:
        """Resolve a service by name."""
        with self._lock:
            reg = self._registrations.get(name)
            if reg is None:
                raise KeyError(f"Service '{name}' not registered")
            return reg.resolve(self)

    def resolve_scoped(self, name: str, scope: str) -> Any:
        """Resolve a scoped service within a scope context."""
        with self._lock:
            reg = self._registrations.get(name)
            if reg is None:
                raise KeyError(f"Service '{name}' not registered")

            if reg.lifecycle != ServiceLifecycle.SCOPED:
                return reg.resolve(self)

            if scope not in self._scoped_instances:
                self._scoped_instances[scope] = {}
            scope_dict = self._scoped_instances[scope]

            if name not in scope_dict:
                scope_dict[name] = reg.factory(self)
            return scope_dict[name]

    def try_resolve(self, name: str, default: Any = None) -> Any:
        """Resolve a service, returning *default* if not registered."""
        try:
            return self.resolve(name)
        except KeyError:
            return default

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    def start(self, name: str) -> bool:
        """Start (initialize) a registered service.

        Calls the factory eagerly so the singleton is created now.
        Returns True if the service was started, False if already running.
        """
        with self._lock:
            if name in self._started:
                return False
            reg = self._registrations.get(name)
            if reg is None:
                logger.warning("Cannot start unknown service: %s", name)
                return False
            if reg.lifecycle == ServiceLifecycle.SINGLETON and reg.instance is None:
                reg.resolve(self)
            self._started.append(name)
            logger.info("Service started: %s", name)
            return True

    def start_all(self) -> List[str]:
        """Start all registered singleton services."""
        started = []
        with self._lock:
            for name in list(self._registrations.keys()):
                if name not in self._started:
                    self.start(name)
                    started.append(name)
        return started

    def stop(self, name: str) -> bool:
        """Stop a service (mark as not started)."""
        with self._lock:
            if name in self._started:
                self._started.remove(name)
                logger.info("Service stopped: %s", name)
                return True
            return False

    def stop_all(self) -> None:
        """Stop all started services."""
        with self._lock:
            names = list(self._started)
            self._started.clear()
            self._scoped_instances.clear()
            for name in names:
                reg = self._registrations.get(name)
                if reg and reg.lifecycle == ServiceLifecycle.SINGLETON:
                    reg.instance = None

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    @property
    def registered_services(self) -> List[str]:
        return list(self._registrations.keys())

    @property
    def started_services(self) -> List[str]:
        return list(self._started)

    def get_description(self, name: str) -> str:
        reg = self._registrations.get(name)
        return reg.description if reg else ""