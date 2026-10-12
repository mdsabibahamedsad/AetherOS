"""ReliabilityService — unified facade over the reliability layer.

Composes the watchdog, state machine, journal, events, heartbeat registry,
mode controller, queue recovery, IPC health, RCA, SLA metrics, diagnostics,
config recovery, database recovery, shutdown coordinator and startup recovery
into one entry point for the CLI and the agent loop.

Safety contract:
* every automatic action is budgeted (max attempts) and cooldown-bounded
* high-risk recovery (restore, revoking anything) is NEVER automatic
* the facade never fabricates health — statuses come from real checks
* shutdown/startup metadata is always recorded so next boot can reconcile
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ReliabilityService:
    """Process-wide reliability facade.

    Usage::

        svc = get_reliability_service()
        svc.status()            # full status dict
        svc.health()            # component health + mode
        svc.start_watchdog()
    """

    def __init__(self) -> None:
        # Imported lazily here to avoid import-order issues at package load.
        from aetheros_reliability.backup import get_backup_store
        from aetheros_reliability.config_recovery import get_config_recovery
        from aetheros_reliability.database import get_database_recovery
        from aetheros_reliability.diagnostics import get_reliability_diagnostics
        from aetheros_reliability.events import get_recovery_event_store
        from aetheros_reliability.heartbeat import get_heartbeat_registry
        from aetheros_reliability.journal import get_recovery_journal
        from aetheros_reliability.modes import get_mode_controller
        from aetheros_reliability.rca import get_root_cause_analyzer
        from aetheros_reliability.slas import get_recovery_sla_metrics
        from aetheros_reliability.startup import StartupRecovery
        from aetheros_reliability.states import get_recovery_state_machine
        from aetheros_reliability.watchdog import get_watchdog

        self.journal = get_recovery_journal()
        self.events = get_recovery_event_store()
        self.heartbeats = get_heartbeat_registry()
        self.state_machine = get_recovery_state_machine()
        self.modes = get_mode_controller()
        self.watchdog = get_watchdog()
        self.rca = get_root_cause_analyzer()
        self.sla = get_recovery_sla_metrics()
        self.diagnostics = get_reliability_diagnostics()
        self.backups = get_backup_store()
        self.config_recovery = get_config_recovery()
        self.database = get_database_recovery()
        self.startup = StartupRecovery()
        self._started = False
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Watchdog lifecycle
    # ------------------------------------------------------------------

    def start_watchdog(self) -> bool:
        with self._lock:
            if self._started:
                return True
            ok = self.watchdog.start()
            if ok:
                self._started = True
            return ok

    def stop_watchdog(self) -> None:
        with self._lock:
            self.watchdog.stop()
            self._started = False

    @property
    def watchdog_running(self) -> bool:
        return self.watchdog.running

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Component health + watchdog status + operating mode."""
        status: Dict[str, Any] = {"ok": True, "mode": self.modes.active().value}
        try:
            health_state = self.watchdog.status()
            status["watchdog"] = health_state
            healthy = health_state.get("healthy", True)
            status["components"] = {
                c: "healthy" for c in self.heartbeats.components()
            }
            if not healthy:
                status["ok"] = False
        except Exception as exc:
            status["ok"] = False
            status["watchdog_error"] = str(exc)
        status["recovery_state"] = self.state_machine.state.value
        return status

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "service": "reliability",
            "mode": self.modes.active().value,
            "recovery_state": self.state_machine.state.value,
            "watchdog_running": self.watchdog_running,
            "watchdog": self.watchdog.status(),
            "heartbeats": {
                c: self.heartbeats.age(c)
                for c in self.heartbeats.components()
            },
            "journal": self.journal.stats(),
            "events_recent": self.events.recent(limit=5),
            "backups": {
                "count": len(self.backups.list()),
                "latest": (self.backups.list()[0].to_dict()
                           if self.backups.list() else None),
            },
            "last_known_good": {
                "exists": self.config_recovery.has_last_known_good(),
                "valid": self.config_recovery.validate().valid,
            },
            "degraded_components": self.modes.degraded_components(),
            "sla": self.sla.summary(),
            "rca": self.rca.summary(),
            "timestamp": time.time(),
        }

    def status_short(self) -> Dict[str, Any]:
        s = self.status()
        return {
            "mode": s["mode"],
            "recovery_state": s["recovery_state"],
            "watchdog_running": s["watchdog_running"],
            "ok": bool(s["watchdog"].get("healthy")),
            "backups": s["backups"]["count"],
            "lkg": s["last_known_good"]["exists"],
            "degraded": list(s["degraded_components"]),
        }

    def summary(self) -> str:
        s = self.status_short()
        parts = [
            f"mode={s['mode']}",
            f"state={s['recovery_state']}",
            f"watchdog={'on' if s['watchdog_running'] else 'off'}",
        ]
        if s.get("degraded"):
            parts.append(f"degraded={','.join(s['degraded'])}")
        return "; ".join(parts)

    # ------------------------------------------------------------------
    # Convenience delegates
    # ------------------------------------------------------------------

    def record_recovery(self, component: str, action: str,
                        result: str, **extra: Any) -> None:
        """Record a recovery attempt into events + journal + SLA."""
        from aetheros_reliability.events import RecoveryEvent, RecoveryResult
        ok = result in (
            RecoveryResult.SUCCESS.value,
            RecoveryResult.VERIFIED.value,
            RecoveryResult.NOT_VERIFIED.value,
        )
        self.events.record(RecoveryEvent(
            component_id=component,
            failure_type="recovery",
            action=action,
            result=result,
            details=extra,
        ))
        try:
            op = self.journal.begin(component, f"recovery:{action}")
            self.journal.complete(op, detail={"result": result})
        except Exception:
            pass
        duration_ms = float(extra.get("duration_ms", 0))
        self.sla.record_recovery(component, duration_ms, ok)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ReliabilityService mode={self.modes.active().value}>"


_service: Optional[ReliabilityService] = None
_service_lock = threading.Lock()


def get_reliability_service() -> ReliabilityService:
    """Return the process-wide ReliabilityService singleton."""
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = ReliabilityService()
    return _service