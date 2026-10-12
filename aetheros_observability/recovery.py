"""Self-healing / recovery service.

Only performs safe, reversible recovery automatically.  Every recovery
action must define a policy (action, trigger, precondition, risk,
rollback, maxAttempts, cooldown, auditEvent).  A recovery budget and
cooldowns prevent infinite recovery loops; crash-loop detection stops
endless restart of a component that repeatedly crashes.

NEVER automatically: delete user data, delete memory, rotate credentials
without authorization, change security policy, disable security controls,
execute destructive shell commands, modify arbitrary files, or change
system configuration dangerously.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_observability.health import HealthState, get_health_service

logger = logging.getLogger(__name__)


class RecoveryOutcome(str, enum.Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"
    BLOCKED = "blocked"
    EXHAUSTED = "exhausted"


@dataclass
class RecoveryPolicy:
    """Contract every recovery action must satisfy (Step 42)."""

    action: str                 # e.g. "reconnect_gateway"
    trigger: str                # e.g. "gateway.connection_dropped"
    precondition: str = ""      # description of what must hold before acting
    risk: str = "low"           # low | medium | high
    rollback: str = ""          # how to undo
    max_attempts: int = 3
    cooldown_seconds: float = 60.0
    audit_event: str = "recovery.executed"


@dataclass
class RecoveryResult:
    action: str
    component: str
    outcome: RecoveryOutcome
    attempt: int = 0
    message: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: float = field(default_factory=time.time)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "component": self.component,
            "outcome": self.outcome.value,
            "attempt": self.attempt,
            "message": self.message,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": round(self.duration_ms, 2),
        }


RecoveryHandler = Callable[[str, Dict[str, Any]], str]


#: Recovery actions that must never be executed automatically.
_FORBIDDEN_ACTIONS = (
    "delete",
    "drop",
    "truncate",
    "rm ",
    "rm -",
    "unlink",
    "wipe",
    "rotate_credentials",
    "disable_security",
    "change_policy",
    "kill -9",
)


class RecoveryService:
    """Safe, reversible, budgeted self-healing (Step 40).

    Usage::

        rs = get_recovery_service()

        def _reconnect(component, ctx):
            # ... safe reconnect logic ...
            return "ok"

        rs.register(
            "reconnect",
            RecoveryPolicy(action="reconnect", trigger="connection_dropped"),
            _reconnect,
        )
        result = rs.attempt("reconnect", "gateway")
    """

    def __init__(self, health_service=None) -> None:
        self._lock = threading.RLock()
        self._policies: Dict[str, RecoveryPolicy] = {}
        self._handlers: Dict[str, RecoveryHandler] = {}
        self._attempts: Dict[str, int] = defaultdict(int)
        self._cooldown_until: Dict[str, float] = {}
        self._last_results: Dict[str, RecoveryResult] = {}
        self._history: List[RecoveryResult] = []
        self._crash_loops: Dict[str, Dict[str, Any]] = {}
        self._health_service = health_service
        self._audit_log: List[Dict[str, Any]] = []
        self._max_history = 200

    @property
    def health(self):
        if self._health_service is None:
            return get_health_service()
        return self._health_service

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, action: str, policy: RecoveryPolicy,
                 handler: RecoveryHandler) -> None:
        """Register a recovery action with its policy and handler."""
        if any(forbidden in action.lower() for forbidden in _FORBIDDEN_ACTIONS):
            raise ValueError(f"recovery action rejected (unsafe): {action}")
        with self._lock:
            self._policies[action] = policy
            self._handlers[action] = handler

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def attempt(self, action: str, component: str,
                context: Optional[Dict[str, Any]] = None,
                *, health_check: bool = True) -> RecoveryResult:
        """Attempt a recovery action for *component*.

        Honors the recovery budget (max attempts + cooldown) and, when
        *health_check* is true, only acts when the component is not
        currently healthy.  Never runs destructive actions.
        """
        with self._lock:
            policy = self._policies.get(action)
            handler = self._handlers.get(action)
        if policy is None or handler is None:
            return self._finish(RecoveryResult(
                action=action, component=component, outcome=RecoveryOutcome.BLOCKED,
                message="no policy/handler registered",
            ))

        now = time.time()
        with self._lock:
            attempts = self._attempts[action]
            cooldown_until = self._cooldown_until.get(action, 0.0)

        if attempts >= policy.max_attempts:
            self._mark_crash_loop(action, component)
            result = RecoveryResult(
                action=action, component=component,
                outcome=RecoveryOutcome.EXHAUSTED, attempt=attempts,
                message=f"recovery budget exhausted ({policy.max_attempts})",
            )
            return self._finish(result)

        if now < cooldown_until:
            return self._finish(RecoveryResult(
                action=action, component=component,
                outcome=RecoveryOutcome.SKIPPED, attempt=attempts,
                message=f"in cooldown ({cooldown_until - now:.0f}s left)",
            ))

        if health_check:
            current = self.health.get_result(component)
            if current is not None and current.is_healthy:
                return self._finish(RecoveryResult(
                    action=action, component=component,
                    outcome=RecoveryOutcome.SKIPPED, attempt=attempts,
                    message="component already healthy",
                ))

        started = time.time()
        try:
            message = handler(component, context or {})
            with self._lock:
                self._attempts[action] += 1
            outcome = RecoveryOutcome.SUCCESS
        except Exception as exc:
            with self._lock:
                self._attempts[action] += 1
            outcome = RecoveryOutcome.FAILED
            message = f"{type(exc).__name__}: {exc}"

        result = RecoveryResult(
            action=action, component=component, outcome=outcome,
            attempt=self._attempts[action], message=message,
            started_at=started, finished_at=time.time(),
            duration_ms=(time.time() - started) * 1000,
        )

        if outcome == RecoveryOutcome.SUCCESS:
            with self._lock:
                self._attempts.pop(action, None)
                self._cooldown_until.pop(action, None)
                self._crash_loops.pop(action, None)
            self._audit(action, component, "success", message)
        else:
            with self._lock:
                self._cooldown_until[action] = time.time() + policy.cooldown_seconds
            self._audit(action, component, outcome.value, message)

        return self._finish(result)

    def can_recover(self, action: str) -> bool:
        """Return True when a recovery action may still run (budget/cooldown)."""
        with self._lock:
            policy = self._policies.get(action)
            if policy is None:
                return False
            attempts = self._attempts.get(action, 0)
            cooldown_until = self._cooldown_until.get(action, 0.0)
        if attempts >= policy.max_attempts:
            return False
        if time.time() < cooldown_until:
            return False
        return True

    # ------------------------------------------------------------------
    # Crash-loop detection
    # ------------------------------------------------------------------

    def _mark_crash_loop(self, action: str, component: str) -> None:
        now = time.time()
        with self._lock:
            entry = self._crash_loops.setdefault(action, {
                "component": component,
                "detected_at": now,
                "attempts": self._attempts.get(action, 0),
                "notified": False,
            })
            entry["last_seen"] = now
            entry["attempts"] = self._attempts.get(action, 0)
        health = self.health
        try:
            health.set_degraded(component, f"crash loop detected for action {action}")
        except Exception:
            pass
        logger.error("Crash loop detected: action=%s component=%s", action, component)

    def crash_loops(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self._crash_loops.items()}

    def is_crash_loop(self, action: str) -> bool:
        with self._lock:
            return action in self._crash_loops

    # ------------------------------------------------------------------
    # Status / audit
    # ------------------------------------------------------------------

    def get_status(self, action: str) -> Optional[RecoveryResult]:
        with self._lock:
            return self._last_results.get(action)

    def history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._history[-limit:]]

    def audit_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._audit_log[-limit:])

    def reset(self, action: str) -> None:
        with self._lock:
            self._attempts.pop(action, None)
            self._cooldown_until.pop(action, None)
            self._crash_loops.pop(action, None)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _finish(self, result: RecoveryResult) -> RecoveryResult:
        with self._lock:
            self._last_results[result.action] = result
            self._history.append(result)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        return result

    def _audit(self, action: str, component: str, outcome: str, message: str) -> None:
        policy = self._policies.get(action)
        event = {
            "audit_event": policy.audit_event if policy else "recovery.executed",
            "action": action,
            "component": component,
            "outcome": outcome,
            "message": message,
            "timestamp": time.time(),
        }
        with self._lock:
            self._audit_log.append(event)
            if len(self._audit_log) > 500:
                self._audit_log = self._audit_log[-500:]
        # Surface to the standard error log for triage.
        if outcome == "failed" or outcome == "exhausted":
            logger.error("Recovery %s for %s: %s", outcome, component, message)


from collections import defaultdict  # noqa: E402


_recovery_service: Optional[RecoveryService] = None


def get_recovery_service() -> RecoveryService:
    """Return the process-wide RecoveryService singleton."""
    global _recovery_service
    if _recovery_service is None:
        _recovery_service = RecoveryService()
    return _recovery_service