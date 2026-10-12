"""Circuit breaker for provider/tool failure storms (P46).

CLOSED → OPEN after `threshold` consecutive failures; OPEN refuses calls for
`cooldown_seconds`, then HALF_OPEN lets a single probe through. Success in
half-open closes the circuit; failure re-opens with growing cooldown.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Generic, TypeVar


class BreakerOpen(RuntimeError):
    """Raised while the circuit is open (fail fast, no upstream call)."""


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


T = TypeVar("T")


@dataclass
class BreakerPolicy:
    threshold: int = 3                 # consecutive failures -> open
    cooldown_seconds: float = 5.0      # initial open window
    max_cooldown_seconds: float = 60.0


@dataclass
class _State(Generic[T]):
    state: State = State.CLOSED
    consecutive_failures: int = 0
    opened_at: float = 0.0
    cooldown: float = 0.0
    last_error: str = ""
    probes_in_flight: int = 0


class CircuitBreaker:
    def __init__(self, key: str, policy: Optional[BreakerPolicy] = None):
        self.key = key
        self.policy = policy or BreakerPolicy()
        self._s: _State[None] = _State()

    # -- inspection ------------------------------------------------------------

    @property
    def state(self) -> State:
        self._refresh()
        return self._s.state

    @property
    def last_error(self) -> str:
        return self._s.last_error

    def _refresh(self) -> None:
        s = self._s
        if s.state is State.OPEN and \
                time.time() - s.opened_at >= s.cooldown:
            s.state = State.HALF_OPEN
            s.probes_in_flight = 0

    # -- execution ---------------------------------------------------------------

    def call(self, fn: Callable[[], T]) -> T:
        """Run fn under breaker discipline."""
        self._refresh()
        s = self._s
        if s.state is State.OPEN:
            raise BreakerOpen(f"circuit {self.key} open "
                              f"(retry in {max(0.0, s.cooldown - (time.time() - s.opened_at)):.1f}s)")
        if s.state is State.HALF_OPEN and s.probes_in_flight > 0:
            raise BreakerOpen(f"circuit {self.key} half-open: probe in flight")
        if s.state is State.HALF_OPEN:
            s.probes_in_flight += 1
            try:
                result = fn()
            except Exception as exc:
                s.probes_in_flight -= 1
                self._trip(exc)
                raise
            s.probes_in_flight -= 1
            self._record_success()
            return result

        try:
            result = fn()
        except Exception as exc:
            self._record_failure(exc)
            raise
        self._record_success()
        return result

    # -- transitions ----------------------------------------------------------------

    def _record_success(self) -> None:
        s = self._s
        s.consecutive_failures = 0
        s.state = State.CLOSED
        s.cooldown = 0.0

    def _record_failure(self, exc: Exception) -> None:
        s = self._s
        s.consecutive_failures += 1
        s.last_error = f"{type(exc).__name__}: {exc}"
        if s.consecutive_failures >= self.policy.threshold:
            self._trip(exc)

    def _trip(self, exc: Exception) -> None:
        s = self._s
        was_closed = s.state is State.CLOSED
        s.state = State.OPEN
        s.opened_at = time.time()
        # first trip uses the base window; re-trips grow it (bounded)
        s.cooldown = (
            self.policy.cooldown_seconds if was_closed or not s.cooldown
            else min(self.policy.max_cooldown_seconds, s.cooldown * 2)
        )
        s.last_error = f"{type(exc).__name__}: {exc}"
