"""Jarvis Mode — runtime lifecycle.

The central orchestrator. Owns initialization, sleep, wake, pause, resume,
and shutdown of every Jarvis subsystem, plus health monitoring, diagnostics,
and recovery. The runtime delegates actual behavior to the individual
managers (wake word, voice, presence, proactive, briefing, mission, etc.)
while guaranteeing they start/stop in a safe order.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_jarvis.models import JarvisConfig, JarvisState

logger = logging.getLogger(__name__)


class JarvisRuntime:
    """Lifecycle manager for the Jarvis runtime.

    States: ``STOPPED -> INITIALIZING -> RUNNING -> (SLEEPING | PAUSED) ->
    SHUTDOWN``. ``ERROR``/``RECOVERING`` handle failures. Each transition
    calls the corresponding hook on every registered subsystem.
    """

    def __init__(self, config: Optional[JarvisConfig] = None) -> None:
        self._lock = threading.RLock()
        self._config = config or JarvisConfig()
        self._state = JarvisState.STOPPED
        self._subsystems: List[Any] = []
        self._listeners: List[Callable[[JarvisState, JarvisState], None]] = []
        self._started_at: float = 0.0
        self._error: str = ""
        self._health: Dict[str, bool] = {}
        self._wake_sources: List[str] = []

    # ------------------------------------------------------------------
    # Subsystem registration
    # ------------------------------------------------------------------

    def register(self, subsystem: Any, *, wake_source: bool = False) -> None:
        """Register a subsystem. Subsystems expose lifecycle hooks
        (``initialize``, ``sleep``, ``wake``, ``pause``, ``resume``,
        ``shutdown``, ``health_check``) when implemented."""
        with self._lock:
            if subsystem not in self._subsystems:
                self._subsystems.append(subsystem)
            if wake_source:
                self._wake_sources.append(getattr(subsystem, "name", str(subsystem.__class__.__name__)))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        with self._lock:
            if self._state != JarvisState.STOPPED:
                return False
            self._state = JarvisState.INITIALIZING
        self._notify(JarvisState.STOPPED, JarvisState.INITIALIZING)
        self._started_at = time.time()

        with self._lock:
            subsystems = list(self._subsystems)
        for sub in subsystems:
            self._call_hook(sub, "initialize")

        self._set_state(JarvisState.RUNNING)
        logger.info("Jarvis runtime initialized (%d subsystems)", len(subsystems))
        return True

    def start(self) -> bool:
        if self._state == JarvisState.RUNNING:
            return True
        return self.initialize()

    def sleep(self) -> bool:
        """Enter sleep: proactive + wake listening pause; voice stays off."""
        with self._lock:
            if self._state != JarvisState.RUNNING:
                return False
        for sub in self._subsystems:
            self._call_hook(sub, "sleep")
        self._set_state(JarvisState.SLEEPING)
        logger.info("Jarvis runtime sleeping")
        return True

    def wake(self) -> bool:
        """Wake from sleep: re-enable proactive + wake listening."""
        with self._lock:
            if self._state != JarvisState.SLEEPING:
                return False
        for sub in self._subsystems:
            self._call_hook(sub, "wake")
        self._set_state(JarvisState.RUNNING)
        logger.info("Jarvis runtime awake")
        return True

    def pause(self) -> bool:
        with self._lock:
            if self._state != JarvisState.RUNNING:
                return False
        for sub in self._subsystems:
            self._call_hook(sub, "pause")
        self._set_state(JarvisState.PAUSED)
        logger.info("Jarvis runtime paused")
        return True

    def resume(self) -> bool:
        with self._lock:
            if self._state != JarvisState.PAUSED:
                return False
        for sub in self._subsystems:
            self._call_hook(sub, "resume")
        self._set_state(JarvisState.RUNNING)
        logger.info("Jarvis runtime resumed")
        return True

    def shutdown(self) -> bool:
        with self._lock:
            if self._state in (JarvisState.STOPPED, JarvisState.SHUTDOWN):
                return False
        for sub in reversed(self._subsystems):
            self._call_hook(sub, "shutdown")
        self._set_state(JarvisState.SHUTDOWN)
        logger.info("Jarvis runtime shut down")
        return True

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def check_health(self) -> Dict[str, bool]:
        health: Dict[str, bool] = {}
        for sub in self._subsystems:
            name = self._subsystem_name(sub)
            health[name] = self._call_hook_bool(sub, "health_check", default=True)
        with self._lock:
            self._health = health
            if any(not v for v in health.values()) and self._state == JarvisState.RUNNING:
                self._state = JarvisState.ERROR
                self._error = "One or more subsystems unhealthy"
        return health

    @property
    def healthy(self) -> bool:
        with self._lock:
            return all(self._health.values()) if self._health else True

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            subs = list(self._subsystems)
        return {
            "state": self._state.value,
            "uptime_seconds": round(time.time() - self._started_at, 2) if self._started_at else 0.0,
            "healthy": self.healthy,
            "error": self._error,
            "subsystems": [self._subsystem_name(s) for s in subs],
            "wake_sources": list(self._wake_sources),
            "health": dict(self._health),
        }

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def recover(self) -> bool:
        """Attempt to re-initialize failed subsystems and return to RUNNING."""
        previous = self._state
        with self._lock:
            self._state = JarvisState.RECOVERING
        self._notify(previous, JarvisState.RECOVERING)
        logger.info("Jarvis runtime recovery starting")

        ok = True
        for sub in self._subsystems:
            if self._call_hook_bool(sub, "health_check", default=True):
                continue
            try:
                self._call_hook(sub, "shutdown")
                self._call_hook(sub, "initialize")
                recovered = self._call_hook_bool(sub, "health_check", default=True)
                ok = ok and recovered
                logger.info("Recovered subsystem %s: %s", self._subsystem_name(sub), recovered)
            except Exception as exc:
                logger.warning("Recovery failed for %s: %s", self._subsystem_name(sub), exc)
                ok = False

        self._set_state(JarvisState.RUNNING if ok else JarvisState.ERROR)
        if not ok:
            self._error = "Recovery incomplete"
        return ok

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def state(self) -> JarvisState:
        with self._lock:
            return self._state

    @property
    def is_running(self) -> bool:
        return self.state == JarvisState.RUNNING

    @property
    def config(self) -> JarvisConfig:
        return self._config

    def on_state_change(self, callback: Callable[[JarvisState, JarvisState], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def _set_state(self, state: JarvisState) -> None:
        with self._lock:
            old = self._state
            self._state = state
            if state != JarvisState.ERROR:
                self._error = ""
        self._notify(old, state)

    def _notify(self, old: JarvisState, new: JarvisState) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(old, new)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("State listener error: %s", exc)

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def _subsystem_name(self, sub: Any) -> str:
        name = getattr(sub, "name", None)
        if name:
            return str(name)
        return sub.__class__.__name__

    def _call_hook(self, sub: Any, hook: str) -> None:
        method = getattr(sub, hook, None)
        if method is None:
            return
        try:
            result = method()
            if hasattr(result, "__await__"):
                import asyncio
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    asyncio.run(result)
                else:
                    # A running loop exists; fire-and-forget would risk the
                    # loop, so we warn instead of silently dropping.
                    logger.debug("Async hook %s skipped on running loop for %s", hook, self._subsystem_name(sub))
        except Exception as exc:
            logger.warning("Hook %s failed for %s: %s", hook, self._subsystem_name(sub), exc)

    def _call_hook_bool(self, sub: Any, hook: str, default: bool = True) -> bool:
        method = getattr(sub, hook, None)
        if method is None:
            return default
        try:
            return bool(method())
        except Exception as exc:
            logger.debug("Hook %s errored for %s: %s", hook, self._subsystem_name(sub), exc)
            return False
