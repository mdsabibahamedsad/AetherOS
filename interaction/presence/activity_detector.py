"""
Activity Detector — Detects user activity states.

Monitors user activity (active work, idle periods, focus sessions,
long-running workflows) and emits structured events that can trigger
configurable automation.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ActivityType(enum.Enum):
    """Types of user activity."""
    ACTIVE = "active"
    IDLE = "idle"
    AWAY = "away"
    FOCUS = "focus"
    WORKING = "working"
    MEETING = "meeting"
    PRESENTING = "presenting"
    BREAK = "break"
    UNKNOWN = "unknown"


class ActivityState(enum.Enum):
    """Activity detector states."""
    STOPPED = "stopped"
    MONITORING = "monitoring"
    PAUSED = "paused"


class ActivityEvent(enum.Enum):
    """Events emitted by the activity detector."""
    MONITORING_STARTED = "activity.monitoring_started"
    MONITORING_STOPPED = "activity.monitoring_stopped"
    ACTIVITY_CHANGED = "activity.changed"
    IDLE_STARTED = "activity.idle_started"
    IDLE_ENDED = "activity.idle_ended"
    FOCUS_STARTED = "activity.focus_started"
    FOCUS_ENDED = "activity.focus_ended"
    WORKFLOW_DETECTED = "activity.workflow_detected"


@dataclass
class ActivitySnapshot:
    """A snapshot of user activity at a point in time.

    Attributes:
        timestamp: When the snapshot was taken
        activity_type: Current activity type
        active_duration: Duration of current activity (seconds)
        input_activity: Keyboard/mouse activity level
        cpu_usage: CPU usage indicator
        active_window: Title of active window
        sources: Which sources contributed to this detection
    """
    timestamp: float = 0.0
    activity_type: ActivityType = ActivityType.UNKNOWN
    active_duration: float = 0.0
    input_activity: float = 0.0
    cpu_usage: float = 0.0
    active_window: str = ""
    sources: List[str] = field(default_factory=list)


class ActivityDetector:
    """Detects and monitors user activity states.

    Combines multiple signals (input device activity, CPU usage,
    window focus, calendar) to determine the user's current activity
    state. Emits events on state transitions.

    Usage:
        detector = ActivityDetector()
        detector.start_monitoring()

        state = detector.get_current_activity()
        print(f"User state: {state.activity_type}")

        detector.subscribe(lambda event, data: handle_activity_change(event, data))
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._state = ActivityState.STOPPED
        self._current_activity: ActivityType = ActivityType.UNKNOWN
        self._activity_start: float = 0.0
        self._subscribers: List[Callable[[ActivityEvent, Dict[str, Any]], None]] = []
        self._history: List[ActivitySnapshot] = []
        self._max_history: int = 1000
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_interval: float = 5.0
        self._running = False

        # Activity source adapters
        self._input_adapter: Optional[Callable[[], float]] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_monitoring(self, interval: float = 5.0) -> None:
        """Start activity monitoring.

        Args:
            interval: Poll interval in seconds
        """
        with self._lock:
            if self._state == ActivityState.MONITORING:
                return
            self._state = ActivityState.MONITORING
            self._running = True
            self._poll_interval = interval
            self._activity_start = time.time()

        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="activity-detector",
        )
        self._poll_thread.start()

        self._notify(ActivityEvent.MONITORING_STARTED, {
            "interval": interval,
        })
        logger.info("ActivityDetector: monitoring started (interval=%.1fs)", interval)

    def stop_monitoring(self) -> None:
        """Stop activity monitoring."""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2)
            self._poll_thread = None

        with self._lock:
            self._state = ActivityState.STOPPED

        self._notify(ActivityEvent.MONITORING_STOPPED, {})
        logger.info("ActivityDetector: monitoring stopped")

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        """Background polling loop."""
        while self._running:
            try:
                self._check_activity()
            except Exception as exc:
                logger.debug("ActivityDetector: poll error: %s", exc)
            time.sleep(self._poll_interval)

    def _check_activity(self) -> None:
        """Check current activity and update state."""
        # Determine activity from input adapter
        input_level = 0.0
        if self._input_adapter:
            try:
                input_level = self._input_adapter()
            except Exception as exc:
                logger.debug("ActivityDetector: input adapter failed: %s", exc)

        # Classify activity type
        new_type = ActivityType.UNKNOWN
        if input_level > 0.5:
            new_type = ActivityType.ACTIVE
        elif input_level > 0.1:
            new_type = ActivityType.WORKING
        elif input_level <= 0.1:
            # Check if we've been inactive long enough to be idle
            elapsed = time.time() - self._activity_start
            if elapsed > 300:  # 5 minutes
                new_type = ActivityType.AWAY
            elif elapsed > 60:  # 1 minute
                new_type = ActivityType.IDLE
            else:
                new_type = ActivityType.ACTIVE

        # Update state if changed
        with self._lock:
            if new_type != self._current_activity:
                prev = self._current_activity
                self._current_activity = new_type
                self._activity_start = time.time()

                self._notify(ActivityEvent.ACTIVITY_CHANGED, {
                    "previous": prev.value,
                    "current": new_type.value,
                })

                if new_type in (ActivityType.IDLE, ActivityType.AWAY):
                    self._notify(ActivityEvent.IDLE_STARTED, {
                        "type": new_type.value,
                    })

            # Record snapshot
            snapshot = ActivitySnapshot(
                timestamp=time.time(),
                activity_type=self._current_activity,
                active_duration=time.time() - self._activity_start,
                input_activity=input_level,
            )
            self._history.append(snapshot)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def set_input_adapter(self, adapter: Callable[[], float]) -> None:
        """Set the input activity detection adapter.

        The adapter should return a float 0.0 (inactive) to 1.0 (very active).

        Args:
            adapter: Input activity callback
        """
        self._input_adapter = adapter

    def get_current_activity(self) -> ActivitySnapshot:
        """Get the current activity state.

        Returns:
            ActivitySnapshot for current state
        """
        with self._lock:
            return ActivitySnapshot(
                timestamp=time.time(),
                activity_type=self._current_activity,
                active_duration=time.time() - self._activity_start,
            )

    def subscribe(self, callback: Callable[[ActivityEvent, Dict[str, Any]], None]) -> Callable:
        """Subscribe to activity events.

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

    def _notify(self, event: ActivityEvent, data: Dict[str, Any]) -> None:
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
                logger.debug("ActivityDetector: subscriber failed: %s", exc)

    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        with self._lock:
            return {
                "state": self._state.value,
                "current_activity": self._current_activity.value,
                "history_size": len(self._history),
                "monitoring": self._running,
                "has_input_adapter": self._input_adapter is not None,
            }
