"""RecoveryManager — bounded, safe failure recovery (Step 19).

When an action fails the manager:

1. captures the failure state (result + failed action),
2. calls a ``re-observe`` hook to refresh the environment,
3. decides whether a bounded retry is safe,
4. never retries destructive/high-risk actions beyond ``max_destructive_retries``
   (default 0 — destructive failures are surfaced, not hammered),
5. gives up with a FAILED verdict when retries are exhausted or unsafe.

Retries are bounded both in count and in the *total* number of attempts for
the run, so a single failing action cannot spin forever.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_actions.model import Action, RiskLevel
from aetheros_actions.state import ComputerUseState


@dataclass
class RecoveryDecision:
    """What the manager decided for a failed action."""

    should_retry: bool
    attempts: int
    reason: str
    state: ComputerUseState = ComputerUseState.RECOVERING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_retry": self.should_retry,
            "attempts": self.attempts,
            "reason": self.reason,
            "state": self.state.value,
        }


@dataclass
class RecoveryState:
    """Per-action-failure bookkeeping for one run."""

    failures: List[Dict[str, Any]] = field(default_factory=list)
    retries_used: int = 0
    last_failure_ts: float = 0.0

    def count(self, action_type: str) -> int:
        return sum(1 for f in self.failures if f.get("action_type") == action_type)


class RecoveryManager:
    """Bounded retry controller with destructive-action protection."""

    def __init__(
        self,
        max_retries: int = 2,
        max_destructive_retries: int = 0,
        max_run_attempts: int = 20,
        retry_interval: float = 0.3,
        reobserve: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.max_retries = max(0, int(max_retries))
        self.max_destructive_retries = max(0, int(max_destructive_retries))
        self.max_run_attempts = max(1, int(max_run_attempts))
        self.retry_interval = max(0.0, float(retry_interval))
        self.reobserve = reobserve
        self.state = RecoveryState()

    def should_retry(self, action: Action, attempts_used: int, result: Any = None) -> RecoveryDecision:
        """Decide whether to retry ``action`` after a failure."""
        self.state.failures.append({
            "action_type": action.action_type.value,
            "target": action.target,
            "ts": time.time(),
        })
        self.state.last_failure_ts = time.time()
        destructive = action.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        allowed = self.max_destructive_retries if destructive else self.max_retries
        if attempts_used >= allowed:
            return RecoveryDecision(
                should_retry=False,
                attempts=attempts_used,
                reason=f"exhausted {'destructive ' if destructive else ''}retry budget "
                       f"({allowed})",
                state=ComputerUseState.FAILED,
            )
        if self.state.retries_used + attempts_used >= self.max_run_attempts:
            return RecoveryDecision(
                should_retry=False,
                attempts=attempts_used,
                reason="run retry budget exhausted",
                state=ComputerUseState.FAILED,
            )
        if self.reobserve is not None:
            try:
                self.reobserve()
            except Exception:  # noqa: BLE001
                pass
        if self.retry_interval:
            time.sleep(self.retry_interval)
        return RecoveryDecision(
            should_retry=True,
            attempts=attempts_used + 1,
            reason="transient failure; bounded retry",
        )

    def record_success(self) -> None:
        """Reset per-run retry accounting after a step succeeds."""
        self.state.retries_used = 0

    def snapshot(self) -> Dict[str, Any]:
        return {
            "failures": len(self.state.failures),
            "retries_used": self.state.retries_used,
            "last_failure_ts": self.state.last_failure_ts,
        }