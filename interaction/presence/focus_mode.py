"""
Focus Mode — Manages focus sessions and deep work periods.

Supports configurable focus sessions with notification muting,
workspace isolation, and automation triggers for long-running workflows.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class FocusEvent(enum.Enum):
    """Events emitted by focus mode."""
    FOCUS_STARTED = "focus.started"
    FOCUS_ENDED = "focus.ended"
    FOCUS_INTERRUPTED = "focus.interrupted"
    FOCUS_EXTENDED = "focus.extended"
    SESSION_REMINDER = "focus.reminder"
    BLOCKER_DETECTED = "focus.blocker_detected"


class FocusState(enum.Enum):
    """Focus mode states."""
    INACTIVE = "inactive"
    FOCUSING = "focusing"
    PAUSED = "paused"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


@dataclass
class FocusConfig:
    """Configuration for focus sessions.

    Attributes:
        default_duration: Default focus duration in minutes
        max_duration: Maximum focus duration
        mute_notifications: Mute notifications during focus
        block_distractions: Block distracting applications/websites
        auto_start_after_idle: Auto-start focus after idle period
        break_reminder_interval: Break reminder interval in minutes
        allow_pause: Allow pausing focus sessions
    """
    default_duration: int = 25
    max_duration: int = 120
    mute_notifications: bool = True
    block_distractions: bool = False
    auto_start_after_idle: bool = False
    break_reminder_interval: int = 0
    allow_pause: bool = True


@dataclass
class FocusSession:
    """A focus session instance.

    Attributes:
        id: Unique session identifier
        state: Current session state
        duration_minutes: Target duration
        started_at: When the session started
        paused_at: When the session was paused
        total_paused: Total paused duration in seconds
        completed: Whether the session completed naturally
        task: Optional focus task description
        metadata: Additional session metadata
    """
    id: str = ""
    state: FocusState = FocusState.FOCUSING
    duration_minutes: int = 25
    started_at: float = 0.0
    paused_at: Optional[float] = None
    total_paused: float = 0.0
    completed: bool = False
    task: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class FocusMode:
    """Manages focus sessions for deep work.

    Supports creating, pausing, extending, and completing focus sessions.
    Integrates with the notification system to mute during focus.

    Usage:
        config = FocusConfig(default_duration=25, mute_notifications=True)
        focus = FocusMode(config)
        focus.initialize()

        session = focus.start_focus(task="Implement Phase 9")
        focus.end_focus(session.id)
    """

    def __init__(self, config: Optional[FocusConfig] = None):
        self.config = config or FocusConfig()
        self._lock = threading.RLock()
        self._enabled = False
        self._active_session: Optional[FocusSession] = None
        self._session_history: List[FocusSession] = []
        self._max_history: int = 100
        self._subscribers: List[Callable[[FocusEvent, Dict[str, Any]], None]] = []
        self._timer_thread: Optional[threading.Thread] = None
        self._running = False
        self._break_callbacks: List[Callable] = []

    def initialize(self) -> None:
        """Initialize focus mode."""
        self._enabled = True
        logger.info("FocusMode: initialized (default=%dmin, mute=%s)",
                     self.config.default_duration,
                     self.config.mute_notifications)

    def shutdown(self) -> None:
        """Shut down focus mode."""
        self._running = False
        if self._timer_thread:
            self._timer_thread.join(timeout=2)
        self._enabled = False
        logger.info("FocusMode: shut down")

    @property
    def enabled(self) -> bool:
        """Whether focus mode is enabled."""
        return self._enabled

    @property
    def active_session(self) -> Optional[FocusSession]:
        """Get the currently active session."""
        with self._lock:
            return self._active_session

    @property
    def is_focusing(self) -> bool:
        """Whether a focus session is currently active."""
        with self._lock:
            return self._active_session is not None

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def start_focus(
        self,
        duration_minutes: Optional[int] = None,
        task: str = "",
    ) -> FocusSession:
        """Start a focus session.

        Args:
            duration_minutes: Duration in minutes (default from config)
            task: Optional task description

        Returns:
            Created FocusSession
        """
        session = FocusSession(
            id=uuid.uuid4().hex[:12],
            state=FocusState.FOCUSING,
            duration_minutes=duration_minutes or self.config.default_duration,
            started_at=time.time(),
            task=task,
        )

        with self._lock:
            self._active_session = session

        # Start timer thread for session monitoring
        self._start_timer()

        self._notify(FocusEvent.FOCUS_STARTED, {
            "session_id": session.id,
            "duration_minutes": session.duration_minutes,
            "task": task,
        })

        logger.info("FocusMode: focus started (%d min, task=%s)",
                     session.duration_minutes, task or "(none)")
        return session

    def end_focus(self, session_id: str, completed: bool = True) -> bool:
        """End a focus session.

        Args:
            session_id: Session to end
            completed: Whether the session completed naturally

        Returns:
            True if ended
        """
        with self._lock:
            if self._active_session is None or self._active_session.id != session_id:
                return False
            self._active_session.state = FocusState.COMPLETED if completed else FocusState.INTERRUPTED
            self._active_session.completed = completed
            session = self._active_session
            self._session_history.append(session)
            if len(self._session_history) > self._max_history:
                self._session_history = self._session_history[-self._max_history:]
            self._active_session = None

        self._stop_timer()

        self._notify(
            FocusEvent.FOCUS_ENDED if completed else FocusEvent.FOCUS_INTERRUPTED,
            {
                "session_id": session_id,
                "duration_seconds": time.time() - session.started_at,
                "task": session.task,
            },
        )

        logger.info("FocusMode: focus ended (%s, duration=%ds)",
                     "completed" if completed else "interrupted",
                     time.time() - session.started_at)
        return True

    def pause_focus(self) -> bool:
        """Pause the active focus session.

        Returns:
            True if paused
        """
        with self._lock:
            if self._active_session is None:
                return False
            if self._active_session.state != FocusState.FOCUSING:
                return False
            self._active_session.state = FocusState.PAUSED
            self._active_session.paused_at = time.time()
        return True

    def resume_focus(self) -> bool:
        """Resume a paused focus session.

        Returns:
            True if resumed
        """
        with self._lock:
            if self._active_session is None:
                return False
            if self._active_session.state != FocusState.PAUSED:
                return False
            if self._active_session.paused_at:
                self._active_session.total_paused += time.time() - self._active_session.paused_at
            self._active_session.state = FocusState.FOCUSING
            self._active_session.paused_at = None
        return True

    def extend_focus(self, extra_minutes: int) -> bool:
        """Extend the active focus session.

        Args:
            extra_minutes: Extra minutes to add

        Returns:
            True if extended
        """
        with self._lock:
            if self._active_session is None:
                return False
            new_duration = self._active_session.duration_minutes + extra_minutes
            if new_duration > self.config.max_duration:
                return False
            self._active_session.duration_minutes = new_duration

        self._notify(FocusEvent.FOCUS_EXTENDED, {
            "extra_minutes": extra_minutes,
            "new_duration": new_duration,
        })
        return True

    # ------------------------------------------------------------------
    # Timer
    # ------------------------------------------------------------------

    def _start_timer(self) -> None:
        """Start the focus session timer thread."""
        self._running = True
        self._timer_thread = threading.Thread(
            target=self._timer_loop,
            daemon=True,
            name="focus-timer",
        )
        self._timer_thread.start()

    def _stop_timer(self) -> None:
        """Stop the timer thread."""
        self._running = False
        if self._timer_thread:
            self._timer_thread.join(timeout=2)
            self._timer_thread = None

    def _timer_loop(self) -> None:
        """Background timer loop for session management."""
        while self._running and self._active_session:
            with self._lock:
                session = self._active_session
                if session is None:
                    break

                elapsed = time.time() - session.started_at - session.total_paused
                remaining = (session.duration_minutes * 60) - elapsed

                if remaining <= 0:
                    # Session time's up
                    self.end_focus(session.id, completed=True)
                    break

            time.sleep(5)

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    def subscribe(self, callback: Callable[[FocusEvent, Dict[str, Any]], None]) -> Callable:
        """Subscribe to focus events.

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

    def add_break_callback(self, callback: Callable) -> Callable:
        """Register a callback for break reminders.

        Args:
            callback: Break reminder callback

        Returns:
            Unsubscribe function
        """
        self._break_callbacks.append(callback)

        def unsubscribe():
            if callback in self._break_callbacks:
                self._break_callbacks.remove(callback)

        return unsubscribe

    def _notify(self, event: FocusEvent, data: Dict[str, Any]) -> None:
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
                logger.debug("FocusMode: subscriber failed: %s", exc)

    def get_stats(self) -> Dict[str, Any]:
        """Get focus mode statistics."""
        with self._lock:
            active = self._active_session
            return {
                "enabled": self._enabled,
                "focusing": active is not None,
                "active_session": active.id if active else None,
                "sessions_completed": sum(1 for s in self._session_history if s.completed),
                "sessions_interrupted": sum(1 for s in self._session_history if not s.completed),
                "total_sessions": len(self._session_history),
            }
