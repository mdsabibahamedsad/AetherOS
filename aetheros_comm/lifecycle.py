"""
Agent Communication Fabric — connection lifecycle, heartbeat, and graceful
shutdown (master spec steps 49, 50, 51, 55).

Connection state transitions are deterministic: invalid, duplicate, or stale
transitions are rejected (step 55). Heartbeats carry only necessary metadata
and drive dead / stalled / overloaded agent detection (step 50).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

from .transport import TransportState

logger = logging.getLogger(__name__)

#: Allowed transitions between connection lifecycle states (step 49/55).
_VALID_TRANSITIONS: Dict[TransportState, Set[TransportState]] = {
    TransportState.CONNECTING: {
        TransportState.AUTHENTICATING, TransportState.READY,
        TransportState.FAILED, TransportState.CLOSING},
    TransportState.AUTHENTICATING: {
        TransportState.READY, TransportState.RECONNECTING,
        TransportState.FAILED, TransportState.CLOSING},
    TransportState.READY: {
        TransportState.DEGRADED, TransportState.CLOSING,
        TransportState.RECONNECTING},
    TransportState.DEGRADED: {
        TransportState.READY, TransportState.RECONNECTING,
        TransportState.FAILED, TransportState.CLOSING},
    TransportState.RECONNECTING: {
        TransportState.AUTHENTICATING, TransportState.READY,
        TransportState.DEGRADED, TransportState.FAILED, TransportState.CLOSING},
    TransportState.CLOSING: {TransportState.CLOSED},
    TransportState.CLOSED: {TransportState.CONNECTING},
    TransportState.FAILED: {TransportState.CONNECTING, TransportState.CLOSED},
}


class ConnectionStateMachine:
    """Deterministic connection lifecycle state machine (steps 49, 55)."""

    def __init__(self, initial: TransportState = TransportState.CLOSED) -> None:
        self._state = initial
        self._lock = threading.RLock()
        self._listeners: List[Callable[[TransportState, TransportState], None]] = []

    @property
    def state(self) -> TransportState:
        with self._lock:
            return self._state

    def transition(self, next_state: TransportState,
                   *, force: bool = False) -> bool:
        """Move to ``next_state``, rejecting invalid transitions.

        Returns True on success. Raises :class:`ValueError` on an invalid,
        duplicate, or stale transition unless ``force`` is set.
        """
        with self._lock:
            if next_state == self._state:
                raise ValueError(
                    f"duplicate transition: already {next_state.value}")
            if not force and next_state not in _VALID_TRANSITIONS.get(
                    self._state, set()):
                raise ValueError(
                    f"invalid transition {self._state.value} -> "
                    f"{next_state.value}")
            previous = self._state
            self._state = next_state
        for listener in list(self._listeners):
            try:
                listener(previous, next_state)
            except Exception as exc:  # noqa: BLE001
                logger.debug("state listener failed: %s", exc)
        return True

    def on_transition(self, listener: Callable[[TransportState, TransportState],
                                               None]) -> None:
        self._listeners.append(listener)

    def assert_state(self, expected: TransportState) -> None:
        if self.state != expected:
            raise ValueError(
                f"expected state {expected.value}, got {self.state.value}")


# ---------------------------------------------------------------------------
# Heartbeat monitor (step 50)
# ---------------------------------------------------------------------------


@dataclass
class AgentPresence:
    last_seen: float = 0.0
    last_seq: int = 0
    status: str = "unknown"
    overloaded: bool = False


class HeartbeatMonitor:
    """Tracks agent liveness via HEARTBEAT messages (step 50).

    Heartbeats must contain only necessary metadata — never secrets.
    """

    def __init__(self, stale_after: float = 60.0) -> None:
        self.stale_after = stale_after
        self._presence: Dict[str, AgentPresence] = {}
        self._lock = threading.RLock()
        self._dead_callbacks: List[Callable[[str], None]] = []

    def mark_seen(self, agent_id: str, *, status: str = "alive",
                  seq: int = 0, overloaded: bool = False) -> None:
        with self._lock:
            presence = self._presence.setdefault(
                agent_id, AgentPresence())
            presence.last_seen = time.time()
            presence.status = status
            presence.last_seq = seq
            presence.overloaded = overloaded

    def is_stale(self, agent_id: str, now: Optional[float] = None) -> bool:
        now = now or time.time()
        with self._lock:
            presence = self._presence.get(agent_id)
            if presence is None:
                return True
            return (now - presence.last_seen) > self.stale_after

    def is_known(self, agent_id: str) -> bool:
        with self._lock:
            return agent_id in self._presence

    def sweep(self) -> List[str]:
        """Detect dead / stalled agents; returns freshly-dead agent ids."""
        dead = []
        now = time.time()
        with self._lock:
            for agent_id, presence in self._presence.items():
                if (now - presence.last_seen) > self.stale_after:
                    dead.append(agent_id)
        for agent_id in dead:
            for cb in list(self._dead_callbacks):
                try:
                    cb(agent_id)
                except Exception:  # noqa: BLE001
                    pass
        return dead

    def on_dead(self, callback: Callable[[str], None]) -> None:
        self._dead_callbacks.append(callback)

    def presence(self, agent_id: str) -> Optional[AgentPresence]:
        with self._lock:
            return self._presence.get(agent_id)

    def snapshot(self) -> Dict[str, Dict[str, object]]:
        with self._lock:
            return {
                agent_id: {
                    "last_seen": p.last_seen,
                    "age_seconds": time.time() - p.last_seen,
                    "last_seq": p.last_seq,
                    "status": p.status,
                    "overloaded": p.overloaded,
                }
                for agent_id, p in self._presence.items()
            }


# ---------------------------------------------------------------------------
# Graceful shutdown (step 51)
# ---------------------------------------------------------------------------


class GracefulShutdown:
    """Coordinates the graceful-disconnect sequence (step 51).

    Sequence: stop accepting new tasks -> finish safe tasks -> checkpoint
    active tasks -> notify orchestrator -> release resources -> close
    transport.
    """

    def __init__(self, on_checkpoint: Optional[Callable[[], None]] = None,
                 on_notify: Optional[Callable[[], None]] = None) -> None:
        self._accepting = True
        self._on_checkpoint = on_checkpoint
        self._on_notify = on_notify
        self._lock = threading.RLock()

    def stop_accepting(self) -> None:
        with self._lock:
            self._accepting = False

    @property
    def accepting(self) -> bool:
        with self._lock:
            return self._accepting

    def drain(self, deadline: float, active_task_count: Callable[[], int]) -> bool:
        """Wait up to ``deadline`` seconds for active tasks to finish."""
        end = time.time() + deadline
        while time.time() < end:
            if active_task_count() == 0:
                return True
            time.sleep(0.1)
        return active_task_count() == 0

    def checkpoint(self) -> None:
        if self._on_checkpoint is not None:
            self._on_checkpoint()

    def notify_orchestrator(self) -> None:
        if self._on_notify is not None:
            self._on_notify()

    def release(self) -> None:
        with self._lock:
            self._accepting = False