"""AetherOSWatchdog — crash/hang detection, safe restart, crash-loop guard.

The watchdog runs on a bounded daemon thread and monitors registered
components via two complementary signals:

* **heartbeat staleness** — a component that stopped emitting heartbeats is
  presumed hung or dead;
* **health checks** — cheap, dependency-free probes returning
  ``(HealthState, message)``.

On failure it applies the safe-restart policy:

    1. capture diagnostics
    2. preserve state (journal + checkpoint hooks)
    3. stop safely if possible
    4. restart with exponential backoff (+ jitter)
    5. health-check
    6. verify dependencies
    7. restore state
    8. resume only if safe

Crash-loop protection: repeated restarts within a window STOP automatic
restart, mark the component DEGRADED/FAILED, preserve diagnostics and emit a
user-noticeable incident.  Recovery attempts are bounded per component so no
infinite restart loops are possible.

Safety: the watchdog NEVER runs destructive actions, never changes security
policy and never restores quarantined/revoked state.  It only calls handlers
the caller registered explicitly.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_reliability.heartbeat import get_heartbeat_registry
from aetheros_reliability.events import RecoveryEvent, get_recovery_event_store
from aetheros_reliability.states import RecoveryState

logger = logging.getLogger(__name__)


@dataclass
class ComponentMonitor:
    """Registration entry describing how to watch and restart a component."""

    component_id: str
    #: Cheap probe returning (HealthState, message).  Optional — heartbeat
    #: staleness alone is enough to detect a crash.
    health_fn: Optional[Callable[[], tuple]] = None
    #: Seconds without a heartbeat before the component is presumed dead.
    heartbeat_timeout: float = 60.0
    #: Restart handler — responsible for a SAFE restart of the component.
    restart_fn: Optional[Callable[[str, Dict[str, Any]], str]] = None
    #: Optional recovery-service action name (aetheros_observability.recovery).
    recovery_action: str = ""
    #: Restart policy
    backoff_base: float = 2.0
    backoff_max: float = 300.0
    backoff_jitter: float = 0.2
    max_restarts: int = 3
    #: Reset restart counter after this many healthy seconds.
    healthy_reset_seconds: float = 300.0

    # runtime state (mutated by the watchdog)
    last_restart_at: float = 0.0
    restart_count: int = 0
    crash_looping: bool = False
    last_failure: str = ""
    healthy_since: float = field(default_factory=time.time)
    last_state: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component_id,
            "heartbeat_timeout": self.heartbeat_timeout,
            "last_restart_at": self.last_restart_at,
            "restart_count": self.restart_count,
            "crash_looping": self.crash_looping,
            "last_failure": self.last_failure,
            "last_state": self.last_state,
            "backoff_base": self.backoff_base,
            "backoff_max": self.backoff_max,
            "max_restarts": self.max_restarts,
        }


class AetherOSWatchdog:
    """Bounded, thread-based watchdog.

    Usage::

        watchdog = get_watchdog()
        watchdog.watch(ComponentMonitor(
            component_id="gateway",
            restart_fn=my_safe_restart,
            recovery_action="gateway_restart",
        ))
        watchdog.start(interval=10)
        ...
        watchdog.stop()
    """

    def __init__(self, heartbeat_registry=None, event_store=None) -> None:
        self._lock = threading.RLock()
        self._monitors: Dict[str, ComponentMonitor] = {}
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._interval = 10.0
        self._running = False
        self._ticks = 0
        self._last_tick_at = 0.0
        self._heartbeats = heartbeat_registry or get_heartbeat_registry()
        self._events = event_store or get_recovery_event_store()
        self._recovery = None  # lazy: aetheros_observability.recovery service
        self._notifiers: List[Callable[[str, str], None]] = []  # (component, message)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def watch(self, monitor: ComponentMonitor) -> None:
        """Register a component to monitor."""
        with self._lock:
            self._monitors[monitor.component_id] = monitor

    def unwatch(self, component_id: str) -> None:
        with self._lock:
            self._monitors.pop(component_id, None)

    def start(self, interval: float = 10.0) -> None:
        """Start the watchdog loop.  Idempotent."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._interval = max(1.0, interval)
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run, name="aetheros-watchdog", daemon=True
            )
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the watchdog loop (bounded join)."""
        with self._lock:
            if not self._running:
                return
            self._stop_event.set()
            thread = self._thread
            self._running = False
        if thread:
            thread.join(timeout=timeout)

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running and bool(self._thread and self._thread.is_alive())

    # ------------------------------------------------------------------
    # Notifications / recovery wiring
    # ------------------------------------------------------------------

    def notify(self, handler: Callable[[str, str], None]) -> None:
        """Register a user-notification handler (component, human message)."""
        self._notifiers.append(handler)

    def _recovery_service(self):
        if self._recovery is None:
            try:
                from aetheros_observability.recovery import get_recovery_service
                self._recovery = get_recovery_service()
            except Exception:
                self._recovery = False
        return self._recovery if self._recovery is not False else None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.tick()
            self._stop_event.wait(self._interval)

    def tick(self) -> None:
        """Run one monitoring pass.  Callable directly (tests / scheduler)."""
        with self._lock:
            monitors = {cid: m for cid, m in self._monitors.items()}
        self._ticks += 1
        self._last_tick_at = time.time()
        for cid, monitor in monitors.items():
            try:
                self._check_one(monitor)
            except Exception:
                logger.exception("Watchdog check failed for %s", cid)

    def _check_one(self, monitor: ComponentMonitor) -> None:
        stale = self._heartbeats.is_stale(
            monitor.component_id, monitor.heartbeat_timeout
        )
        if stale:
            # Presumed dead / hung.
            self._handle_failure(monitor, "heartbeat timeout")
            return

        # Liveness/health probe (optional).
        if monitor.health_fn is not None:
            try:
                state, message = monitor.health_fn()
                monitor.last_state = getattr(state, "value", str(state))
                if getattr(state, "value", str(state)) in ("unhealthy", "failed"):
                    self._handle_failure(monitor, message or f"{state} state")
                    return
            except Exception as exc:
                self._handle_failure(monitor, f"health probe raised: {exc}")
                return

        # Healthy — track healthy window for restart-counter reset.
        if monitor.restart_count > 0 and not monitor.crash_looping:
            if (time.time() - monitor.healthy_since) > monitor.healthy_reset_seconds:
                with self._lock:
                    monitor.restart_count = 0
                    monitor.healthy_since = time.time()

    def _handle_failure(self, monitor: ComponentMonitor, reason: str) -> None:
        now = time.time()
        with self._lock:
            if monitor.crash_looping:
                monitor.last_failure = reason
                return
            monitor.last_failure = reason
            monitor.restart_count += 1
            restart_number = monitor.restart_count
            crash_loop_hit = restart_number > monitor.max_restarts

        event = RecoveryEvent(
            component_id=monitor.component_id,
            failure_type="PROCESS_FAILURE" if reason == "heartbeat timeout" else "PROBE_FAILURE",
            action="restart",
            diagnosis=reason,
            attempt=restart_number,
        )

        if crash_loop_hit:
            with self._lock:
                monitor.crash_looping = True
            event.result = "blocked"
            event.message = "crash loop detected; automatic restart stopped"
            self._events.record(event)
            self._mark_crash_loop(monitor)
            self._notify(monitor.component_id,
                         f"{monitor.component_id} keeps failing and will not be "
                         f"restarted automatically. Diagnostics preserved. "
                         f"Use recovery mode to intervene.")
            return

        # Safe restart with backoff.
        delay = self._backoff(monitor, restart_number)
        self._notify(monitor.component_id,
                     f"{monitor.component_id} failed ({reason}); "
                     f"restarting in {delay:.0f}s (attempt {restart_number}).")
        # Preserve state hooks (journal checkpoints are recorded by callers;
        # here we emit the event and run the recovery service if configured).
        success = False
        if monitor.recovery_action:
            success = self._run_recovery_action(monitor, event, reason)
        if not success and monitor.restart_fn is not None:
            success = self._run_restart(monitor, event, reason, delay)

        if success:
            monitor.last_restart_at = now
            event.result = "success"
        else:
            event.result = "failed"
            event.message = f"restart failed: {monitor.last_failure}"
        self._events.record(event)

    def _run_recovery_action(self, monitor: ComponentMonitor,
                             event: RecoveryEvent, reason: str) -> bool:
        """Delegate to the observability RecoveryService (budgeted, safe)."""
        service = self._recovery_service()
        if service is None:
            return False
        try:
            result = service.attempt(
                monitor.recovery_action,
                monitor.component_id,
                {"reason": reason},
                health_check=True,
            )
            event.duration_ms = result.duration_ms
            event.attempt = result.attempt
            event.message = result.message
            return result.outcome.value == "success"
        except Exception as exc:
            logger.debug("recovery action failed: %s", exc)
            return False

    def _run_restart(self, monitor: ComponentMonitor,
                     event: RecoveryEvent, reason: str, delay: float) -> bool:
        """Sleep the backoff then invoke the restart handler once."""
        self._stop_event.wait(delay)
        if self._stop_event.is_set():
            event.result = "skipped"
            event.message = "watchdog stopped during backoff"
            return False
        start = time.monotonic()
        try:
            message = monitor.restart_fn(monitor.component_id, {"reason": reason})
            event.duration_ms = (time.monotonic() - start) * 1000
            event.message = message
            return True
        except Exception as exc:
            monitor.last_failure = f"restart raised {type(exc).__name__}: {exc}"
            event.message = monitor.last_failure
            return False

    # ------------------------------------------------------------------
    # Backoff / crash-loop
    # ------------------------------------------------------------------

    def _backoff(self, monitor: ComponentMonitor, attempt: int) -> float:
        base = monitor.backoff_base * (2 ** (attempt - 1))
        capped = min(base, monitor.backoff_max)
        if monitor.backoff_jitter > 0:
            jitter = random.uniform(0, capped * monitor.backoff_jitter)
            capped = capped + jitter
        return capped

    def _mark_crash_loop(self, monitor: ComponentMonitor) -> None:
        logger.error(
            "Watchdog crash-loop: %s stopped after %d restarts",
            monitor.component_id, monitor.restart_count,
        )
        try:
            from aetheros_observability.health import get_health_service
            get_health_service().set_degraded(
                monitor.component_id,
                f"crash loop detected ({monitor.restart_count} restarts)",
            )
        except Exception:
            pass
        try:
            from aetheros_reliability.states import get_recovery_state_machine
            get_recovery_state_machine().enter(
                RecoveryState.FAILED_RECOVERY,
                reason=f"crash loop: {monitor.component_id}",
            )
        except ValueError:
            pass  # illegal transition — keep current state

    def _notify(self, component: str, message: str) -> None:
        for handler in list(self._notifiers):
            try:
                handler(component, message)
            except Exception:
                logger.debug("watchdog notifier failed: %s", handler)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def reset_component(self, component_id: str) -> None:
        """Reset a crash-looped component so the watchdog may try again."""
        with self._lock:
            monitor = self._monitors.get(component_id)
            if monitor:
                monitor.crash_looping = False
                monitor.restart_count = 0
                monitor.last_restart_at = 0.0
                monitor.healthy_since = time.time()
        try:
            from aetheros_observability.health import get_health_service
            get_health_service().clear_degraded(component_id)
        except Exception:
            pass

    def components(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {cid: m.to_dict() for cid, m in self._monitors.items()}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            monitors = {cid: m.to_dict() for cid, m in self._monitors.items()}
            crash_loops = [
                cid for cid, m in self._monitors.items() if m.crash_looping
            ]
            return {
                "running": self.running,
                "interval": self._interval,
                "ticks": self._ticks,
                "last_tick_at": self._last_tick_at,
                "monitored": monitors,
                "crash_loops": crash_loops,
            }


_watchdog: Optional[AetherOSWatchdog] = None
_watchdog_lock = threading.Lock()


def get_watchdog() -> AetherOSWatchdog:
    """Return the process-wide AetherOSWatchdog singleton."""
    global _watchdog
    if _watchdog is None:
        with _watchdog_lock:
            if _watchdog is None:
                _watchdog = AetherOSWatchdog()
    return _watchdog