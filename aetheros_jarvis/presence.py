"""Jarvis Mode — presence detection.

Tracks user activity to determine presence state (active / idle / away /
locked / sleeping). Proactive behavior pauses when the user is away, locked
out, or asleep. Presence is derived from real signals: input activity
heartbeats, idle timers, and system lock/sleep events where available.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_jarvis.models import PresenceState

logger = logging.getLogger(__name__)


class PresenceDetector:
    """Detects the user's presence state from activity signals.

    The detector is clock-based and thread-safe. Call :meth:`mark_activity`
    whenever the user interacts (keyboard, mouse, voice); the state machine
    derives idle/away from configurable timeouts. System lock/sleep can be
    reported explicitly via :meth:`report_lock` / :meth:`report_sleep` when
    the platform provides those signals.
    """

    def __init__(self, idle_after_seconds: float = 120.0, away_after_seconds: float = 900.0) -> None:
        self._idle_after = idle_after_seconds
        self._away_after = away_after_seconds
        self._lock = threading.RLock()
        self._last_activity: float = time.time()
        self._explicit: Optional[PresenceState] = None
        self._listeners: List[Callable[[PresenceState, PresenceState], None]] = []
        self._state: PresenceState = PresenceState.ACTIVE

    # ------------------------------------------------------------------
    # Input signals
    # ------------------------------------------------------------------

    def mark_activity(self) -> None:
        """Record user activity (keyboard, mouse, voice, touch)."""
        with self._lock:
            self._last_activity = time.time()

    def report_lock(self) -> None:
        """Report that the screen locked."""
        with self._lock:
            self._explicit = PresenceState.LOCKED
            self._transition(PresenceState.LOCKED)

    def report_unlock(self) -> None:
        with self._lock:
            self._explicit = None
            self._last_activity = time.time()
            self._transition(PresenceState.ACTIVE)

    def report_sleep(self) -> None:
        with self._lock:
            self._explicit = PresenceState.SLEEPING
            self._transition(PresenceState.SLEEPING)

    def report_wake(self) -> None:
        with self._lock:
            self._explicit = None
            self._last_activity = time.time()
            self._transition(PresenceState.ACTIVE)

    def report_away(self, away: bool = True) -> None:
        with self._lock:
            self._explicit = PresenceState.AWAY if away else None
            if away:
                self._transition(PresenceState.AWAY)
            else:
                self._last_activity = time.time()
                self._transition(PresenceState.ACTIVE)

    # ------------------------------------------------------------------
    # State derivation
    # ------------------------------------------------------------------

    def current(self) -> PresenceState:
        with self._lock:
            if self._explicit is not None:
                state = self._explicit
            else:
                idle_seconds = time.time() - self._last_activity
                if idle_seconds >= self._away_after:
                    state = PresenceState.AWAY
                elif idle_seconds >= self._idle_after:
                    state = PresenceState.IDLE
                else:
                    state = PresenceState.ACTIVE
            return self._transition(state)

    def _transition(self, state: PresenceState) -> PresenceState:
        """Update state and notify listeners when it actually changed."""
        if state != self._state:
            old = self._state
            self._state = state
            self._notify(old, state)
        return state

    @property
    def state(self) -> PresenceState:
        return self.current()

    @property
    def idle_seconds(self) -> float:
        with self._lock:
            return time.time() - self._last_activity

    def is_available(self) -> bool:
        """True when proactive behavior is appropriate."""
        state = self.current()
        return state in (PresenceState.ACTIVE, PresenceState.IDLE)

    def is_fully_present(self) -> bool:
        return self.current() == PresenceState.ACTIVE

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_change(self, callback: Callable[[PresenceState, PresenceState], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def _notify(self, old: PresenceState, new: PresenceState) -> None:
        for cb in self._listeners:
            try:
                cb(old, new)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Presence listener error: %s", exc)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "state": self.current().value,
            "idle_seconds": round(self.idle_seconds, 1),
            "idle_after": self._idle_after,
            "away_after": self._away_after,
            "available": self.is_available(),
        }
