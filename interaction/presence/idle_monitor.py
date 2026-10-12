"""
Idle Monitor — Detects user idle periods for presence awareness.

Monitors user activity (keyboard, mouse, system) to detect idle periods
that can trigger configurable automation or notifications.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class IdleEvent(enum.Enum):
    """Events emitted by the idle monitor."""
    MONITORING_STARTED = "idle.monitoring_started"
    MONITORING_STOPPED = "idle.monitoring_stopped"
    USER_BECAME_IDLE = "idle.user_became_idle"
    USER_RETURNED = "idle.user_returned"
    IDLE_WARNING = "idle.warning"
    AUTO_PAUSE = "idle.auto_pause"


class IdleState(enum.Enum):
    """Idle monitor states."""
    ACTIVE = "active"
    IDLE = "idle"
    LONG_IDLE = "long_idle"
    AWAY = "away"


@dataclass
class IdleConfig:
    """Configuration for idle monitoring.

    Attributes:
        idle_threshold: Seconds before user is considered idle
        long_idle_threshold: Seconds before user is long idle
        away_threshold: Seconds before user is considered away
        check_interval: Poll interval in seconds
        auto_pause_workflows: Pause workflows on long idle
        auto_notify: Send notification on idle
    """
    idle_threshold: float = 120.0
    long_idle_threshold: float = 600.0
    away_threshold: float = 1800.0
    check_interval: float = 10.0
    auto_pause_workflows: bool = False
    auto_notify: bool = False


class IdleMonitor:
    """Monitors user idle time and emits events on idle transitions.

    Tracks the time since last user activity and transitions through
    idle states. Supports configurable thresholds for different levels
    of idle.

    Usage:
        config = IdleConfig(idle_threshold=120, long_idle_threshold=600)
        monitor = IdleMonitor(config)
        monitor.set_activity_adapter(lambda: get_last_input_time())
        monitor.start()
    """

    def __init__(self, config: Optional[IdleConfig] = None):
        self.config = config or IdleConfig()
        self._lock = threading.RLock()
        self._state = IdleState.ACTIVE
        self._idle_since: float = 0.0
        self._last_activity_time: float = time.time()
        self._idle_duration: float = 0.0
        self._running = False
        self._poll_thread: Optional[threading.Thread] = None
        self._subscribers: List[Callable[[IdleEvent, Dict[str, Any]], None]] = []
        self._activity_adapter: Optional[Callable[[], float]] = None

    def set_activity_adapter(self, adapter: Callable[[], float]) -> None:
        """Set the adapter for checking last user activity.

        The adapter should return seconds since last user input
        (keyboard or mouse).

        Args:
            adapter: Callable returning idle seconds
        """
        self._activity_adapter = adapter

    def start(self) -> None:
        """Start idle monitoring."""
        if self._running:
            return
        self._running = True

        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="idle-monitor",
        )
        self._poll_thread.start()

        self._notify(IdleEvent.MONITORING_STARTED, {
            "idle_threshold": self.config.idle_threshold,
        })
        logger.info("IdleMonitor: started (idle=%ds, long=%ds, away=%ds)",
                     self.config.idle_threshold,
                     self.config.long_idle_threshold,
                     self.config.away_threshold)

    def stop(self) -> None:
        """Stop idle monitoring."""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2)
            self._poll_thread = None

        self._notify(IdleEvent.MONITORING_STOPPED, {})
        logger.info("IdleMonitor: stopped")

    def _poll_loop(self) -> None:
        """Background polling loop."""
        while self._running:
            try:
                self._check_idle()
            except Exception as exc:
                logger.debug("IdleMonitor: poll error: %s", exc)
            time.sleep(self.config.check_interval)

    def _check_idle(self) -> None:
        """Check idle state and emit events on transitions."""
        now = time.time()

        # Get idle time from adapter or track locally
        if self._activity_adapter:
            try:
                idle_seconds = self._activity_adapter()
            except Exception:
                idle_seconds = now - self._last_activity_time
        else:
            idle_seconds = now - self._last_activity_time

        self._idle_duration = idle_seconds
        new_state = self._classify_idle(idle_seconds)

        with self._lock:
            prev_state = self._state
            if new_state != prev_state:
                self._state = new_state
                if new_state == IdleState.IDLE:
                    self._idle_since = now
                    self._notify(IdleEvent.USER_BECAME_IDLE, {
                        "idle_seconds": idle_seconds,
                        "state": new_state.value,
                    })
                elif prev_state != IdleState.ACTIVE and new_state == IdleState.ACTIVE:
                    self._idle_since = 0.0
                    self._notify(IdleEvent.USER_RETURNED, {
                        "idle_duration": idle_seconds,
                        "previous_state": prev_state.value,
                    })

    def _classify_idle(self, idle_seconds: float) -> IdleState:
        """Classify idle duration into a state.

        Args:
            idle_seconds: Seconds since last activity

        Returns:
            Corresponding IdleState
        """
        if idle_seconds >= self.config.away_threshold:
            return IdleState.AWAY
        if idle_seconds >= self.config.long_idle_threshold:
            return IdleState.LONG_IDLE
        if idle_seconds >= self.config.idle_threshold:
            return IdleState.IDLE
        return IdleState.ACTIVE

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def touch(self) -> None:
        """Manually reset the idle timer (user is active)."""
        self._last_activity_time = time.time()

    @property
    def idle_duration(self) -> float:
        """Get current idle duration in seconds."""
        return self._idle_duration

    @property
    def state(self) -> IdleState:
        """Get current idle state."""
        with self._lock:
            return self._state

    def is_idle(self) -> bool:
        """Check if user is currently idle.

        Returns:
            True if idle (includes long_idle and away)
        """
        with self._lock:
            return self._state != IdleState.ACTIVE

    def subscribe(self, callback: Callable[[IdleEvent, Dict[str, Any]], None]) -> Callable:
        """Subscribe to idle events.

        Args:
            callback: Receives (event, data)

        Returns:
            Unsubscribe function
        """
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe():
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    def _notify(self, event: IdleEvent, data: Dict[str, Any]) -> None:
        """Notify subscribers.

        Args:
            event: Event type
            data: Event data
        """
        with self._lock:
            subscribers = list(self._subscribers)
        for cb in subscribers:
            try:
                cb(event, data)
            except Exception as exc:
                logger.debug("IdleMonitor: subscriber failed: %s", exc)

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        with self._lock:
            return {
                "state": self._state.value,
                "idle_duration": self._idle_duration,
                "monitoring": self._running,
                "has_adapter": self._activity_adapter is not None,
            }
