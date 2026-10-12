"""
Agent Communication Fabric — reliability primitives
(master spec steps 29, 33, 34, 35, 36, 38).

Provides failure classification, retry policy, circuit breakers, backpressure
(flow control), and ordered fallback chains. These are transport-agnostic and
used by the fabric's send/request pipeline.
"""

from __future__ import annotations

import enum
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

from .types import FailureClass


class CircuitState(str, enum.Enum):
    """Circuit breaker states (master spec step 35)."""

    CLOSED = "CLOSED"       # requests flow
    OPEN = "OPEN"           # dependency is failing; reject fast
    HALF_OPEN = "HALF_OPEN" # probing with a single trial


# ---------------------------------------------------------------------------
# Failure classification (step 34)
# ---------------------------------------------------------------------------


def classify_error(exc: BaseException) -> FailureClass:
    """Map an exception to a failure class for the retry policy."""
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    if name in ("timeouterror", "asyncio_timeouterror", "timeout"):
        return FailureClass.TIMEOUT
    if any(k in name for k in ("auth", "authoriz", "permission",
                               "accessdenied", "forbidden")):
        return FailureClass.AUTHORIZATION
    if any(k in name for k in ("signature", "replay", "security", "tamper")):
        return FailureClass.SECURITY
    if any(k in name for k in ("ratelimit", "ratelimited", "throttl")):
        return FailureClass.RATE_LIMIT
    if any(k in text for k in ("rate limit", "too many requests", "429")):
        return FailureClass.RATE_LIMIT
    if any(k in name for k in ("unavailable", "connection", "connect",
                               "serviceunavailable", "503", "502")):
        return FailureClass.UNAVAILABLE
    if any(k in name for k in ("invalid", "valueerror", "schema", "envelope",
                               "protocol")):
        return FailureClass.INVALID_REQUEST
    return FailureClass.TRANSIENT


# ---------------------------------------------------------------------------
# Retry policy (step 34)
# ---------------------------------------------------------------------------


@dataclass
class RetryPolicy:
    """Policy deciding when and how to retry a failed send."""

    max_attempts: int = 3
    base_delay: float = 0.2
    max_delay: float = 5.0
    backoff_factor: float = 2.0
    jitter: float = 0.1
    retryable: tuple = (
        FailureClass.TRANSIENT,
        FailureClass.TIMEOUT,
        FailureClass.RATE_LIMIT,
        FailureClass.UNAVAILABLE,
    )

    def should_retry(self, failure_class: FailureClass,
                     attempt: int) -> bool:
        """Whether attempt ``attempt`` (0-based) may be retried."""
        if attempt + 1 >= self.max_attempts:
            return False
        return failure_class in self.retryable

    def delay_for(self, attempt: int) -> float:
        """Backoff delay for a retry at 0-based ``attempt``."""
        delay = min(self.base_delay * (self.backoff_factor ** attempt),
                    self.max_delay)
        if self.jitter > 0:
            delay = delay * (1.0 + random.uniform(-self.jitter, self.jitter))
        return max(0.0, delay)


# ---------------------------------------------------------------------------
# Circuit breaker (step 35)
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """Protects a dependency from cascading failures (step 35).

    CLOSED -> OPEN after ``failure_threshold`` consecutive failures;
    OPEN -> HALF_OPEN after ``open_timeout``; HALF_OPEN -> CLOSED after one
    successful probe, or back to OPEN on failure.
    """

    def __init__(self, name: str = "",
                 failure_threshold: int = 5,
                 open_timeout: float = 10.0) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.open_timeout = open_timeout
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at = 0.0
        self._lock = threading.RLock()
        self._trips = 0

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if (self._state == CircuitState.OPEN
                    and time.time() - self._opened_at >= self.open_timeout):
                self._state = CircuitState.HALF_OPEN
            return self._state

    def allow_request(self) -> bool:
        """Whether a request may proceed right now."""
        return self.state == CircuitState.CLOSED or self.state == CircuitState.HALF_OPEN

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._opened_at = time.time()
                self._trips += 1
            elif (self._state == CircuitState.CLOSED
                    and self._consecutive_failures >= self.failure_threshold):
                self._state = CircuitState.OPEN
                self._opened_at = time.time()
                self._trips += 1

    def reset(self) -> None:
        with self._lock:
            self._state = CircuitState.CLOSED
            self._consecutive_failures = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "state": self.state.value,
            "consecutive_failures": self._consecutive_failures,
            "trips": self._trips,
        }


# ---------------------------------------------------------------------------
# Backpressure (step 36)
# ---------------------------------------------------------------------------


class Backpressure:
    """Bounds the in-flight work to a dependency (step 36).

    When the per-agent in-flight limit is reached, new sends are rejected
    (load shedding) instead of piling up. The fabric surfaces this as a
    ``RATE_LIMIT`` / ``UNAVAILABLE`` condition and may reroute to a fallback.
    """

    def __init__(self, max_in_flight: int = 32,
                 queue_limit: int = 512) -> None:
        self.max_in_flight = max_in_flight
        self.queue_limit = queue_limit
        self._in_flight: Dict[str, int] = {}
        self._queued: Dict[str, int] = {}
        self._lock = threading.RLock()

    def acquire(self, agent_id: str) -> bool:
        """Reserve one in-flight slot for ``agent_id``.

        Returns False when the dependency is overloaded.
        """
        with self._lock:
            inflight = self._in_flight.get(agent_id, 0)
            queued = self._queued.get(agent_id, 0)
            if inflight >= self.max_in_flight:
                if queued >= self.queue_limit:
                    return False
                self._queued[agent_id] = queued + 1
                return True
            self._in_flight[agent_id] = inflight + 1
            return True

    def release(self, agent_id: str) -> None:
        with self._lock:
            if self._queued.get(agent_id, 0) > 0:
                self._queued[agent_id] -= 1
            else:
                self._in_flight[agent_id] = max(
                    0, self._in_flight.get(agent_id, 0) - 1)

    def is_overloaded(self, agent_id: str) -> bool:
        with self._lock:
            return self._in_flight.get(agent_id, 0) >= self.max_in_flight

    def snapshot(self) -> Dict[str, Dict[str, int]]:
        with self._lock:
            return {
                "in_flight": dict(self._in_flight),
                "queued": dict(self._queued),
            }


# ---------------------------------------------------------------------------
# Fallback chains (step 38)
# ---------------------------------------------------------------------------


@dataclass
class FallbackChain:
    """Ordered fallback candidates for a task (step 38).

    The chain respects capabilities, status, and trust-zone policy (validated
    at construction / by the caller). The terminal step (degraded mode or
    human approval) is the caller's responsibility.
    """

    task_description: str = ""
    candidates: List[str] = field(default_factory=list)
    _cursor: int = 0

    def next_candidate(self) -> Optional[str]:
        """Return the next candidate, or None when exhausted."""
        if self._cursor >= len(self.candidates):
            return None
        candidate = self.candidates[self._cursor]
        self._cursor += 1
        return candidate

    def reset(self) -> None:
        self._cursor = 0

    def remaining(self) -> List[str]:
        return self.candidates[self._cursor:]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_description": self.task_description,
            "candidates": list(self.candidates),
            "remaining": self.remaining(),
        }