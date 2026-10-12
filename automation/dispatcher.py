"""
Event dispatcher: bridges the automation event bus to scheduled executions
(Master 13 Phases 9, 17, 77-80).

Matching an event to an automation does NOT spawn a second execution system.
Dispatch simply stamps ``next_run_at = now`` on the automation (the same
mechanism ``trigger_job`` uses), so the regular cron tick picks it up through
every existing guard: prompt-injection scanning, toolset denylists, worker
pools, delivery routing, breaker accounting, resource limits.

Boundaries enforced here:

- global emergency stop blocks all dispatch
- per-automation cooldown (trigger.cooldown_seconds, default from config)
- global sliding-window rate cap (triggers.max_dispatches_per_minute)
- breaker/quarantine gate (same gate the scheduler uses)
- external events only match automations that opted in via allow_untrusted

A single daemon thread owns the pump: it polls FileWatcher roots, publishes
their changes onto the bus, and consumes bus events. It starts lazily on the
first scheduler tick only when there is something to watch or trigger.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_SECONDS = 60


def _cfg() -> Dict[str, Any]:
    try:
        from aetheros_cli.config import load_config

        return load_config() or {}
    except Exception:
        return {}


def _settings(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    section = cfg.get("automation", {}) if isinstance(cfg, dict) else {}
    trig = section.get("triggers", {}) if isinstance(section.get("triggers"), dict) else {}
    try:
        rate = int(trig.get("max_dispatches_per_minute", 30))
    except (TypeError, ValueError):
        rate = 30
    return {
        "enabled": bool(trig.get("enabled", True)),
        "max_dispatches_per_minute": max(1, rate),
    }


class Dispatcher:
    """Owns watcher polling and event→automation stamping."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_lock = threading.Lock()
        self._dispatch_times: deque = deque()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Matching + dispatch
    # ------------------------------------------------------------------

    def event_automations(self) -> List[Dict[str, Any]]:
        from cron.jobs import load_jobs

        result = []
        for job in load_jobs():
            trigger = job.get("trigger")
            if isinstance(trigger, dict) and trigger.get("kind") == "event":
                result.append(job)
        return result

    def has_work(self) -> bool:
        if not _settings().get("enabled", True):
            return False
        if self.event_automations():
            return True
        return bool(_file_watcher_settings().get("allowed_roots"))

    def dispatch(self, event_dict: Dict[str, Any]) -> int:
        """Stamp due next_run_at on every matching automation. Returns count."""
        cfg = _cfg()
        if not _settings(cfg).get("enabled", True):
            return 0
        try:
            from automation.guard import estop_active

            if estop_active() is not None:
                logger.info("Event dispatch skipped: emergency stop active")
                return 0
        except Exception:
            pass
        if not self._rate_allows():
            logger.warning(
                "Event dispatch rate cap reached (%s/min); dropping %s",
                _settings(cfg)["max_dispatches_per_minute"],
                event_dict.get("event_type"),
            )
            return 0

        from automation.triggers import event_matches

        dispatched = 0
        try:
            from datetime import datetime, timezone

            now_iso = datetime.now(timezone.utc).isoformat()
        except Exception:
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%S")

        event_id_ref = str(event_dict.get("payload", {}).get("automation_id") or "")

        for job in self.event_automations():
            trigger = job.get("trigger") or {}
            # Phase 95 loop defense: lifecycle events emitted by an
            # automation never re-arm that same automation.
            if (
                str(event_dict.get("event_type")) in ("automation.completed", "automation.failed")
                and event_id_ref
                and event_id_ref == str(job.get("id"))
            ):
                continue
            if not event_matches(trigger, event_dict):
                continue
            cooldown = trigger.get("cooldown_seconds")
            if cooldown is None:
                cooldown = DEFAULT_COOLDOWN_SECONDS
            last = _parse_ts(job.get("last_triggered_at"))
            if last is not None and (time.time() - last) < float(cooldown):
                logger.debug(
                    "Automation '%s' in trigger cooldown (%ss)",
                    job.get("name"), cooldown,
                )
                continue
            try:
                from automation.guard import gate_job
                from cron.jobs import update_job

                allowed, reason, _half_open = gate_job(job, cfg=cfg)
                if not allowed:
                    logger.info(
                        "Automation '%s' gated (%s); event dropped",
                        job.get("name"), reason,
                    )
                    continue
                updated = update_job(job["id"], {"next_run_at": now_iso})
                if updated is None:
                    continue
                from cron.jobs import apply_job_field_updates

                apply_job_field_updates(
                    job["id"], {"last_triggered_at": now_iso}
                )
                dispatched += 1
                from automation.events import publish_internal

                publish_internal(
                    "automation.dispatched",
                    {
                        "automation_id": job["id"],
                        "name": job.get("name"),
                        "by_event": event_dict.get("event_id"),
                        "event_type": event_dict.get("event_type"),
                    },
                    source="dispatcher",
                )
            except Exception:
                logger.exception(
                    "Event dispatch failed for automation %s", job.get("id")
                )
        return dispatched

    def _rate_allows(self) -> bool:
        window = 60.0
        now = time.time()
        with self._lock:
            while self._dispatch_times and (now - self._dispatch_times[0]) > window:
                self._dispatch_times.popleft()
            cap = _settings()["max_dispatches_per_minute"]
            if len(self._dispatch_times) >= cap:
                return False
            self._dispatch_times.append(now)
            return True

    # ------------------------------------------------------------------
    # Pump thread
    # ------------------------------------------------------------------

    def ensure_started(self) -> bool:
        """Idempotently start the pump when there is anything to serve."""
        if self._thread is not None and self._thread.is_alive():
            return True
        try:
            if not self.has_work():
                return False
        except Exception:
            return False
        with self._start_lock:
            if self._thread is not None and self._thread.is_alive():
                return True
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run, name="automation-events", daemon=True
            )
            self._thread.start()
            logger.info("Automation event dispatcher started")
            return True

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)

    def _run(self) -> None:
        from automation.events import get_bus

        bus = get_bus()
        poll_interval = _file_watcher_settings().get("poll_interval_seconds", 5.0)
        queue: "deque" = deque()
        bus.subscribe(lambda evt: queue.append(evt))
        watcher = None
        try:
            # Phase 72: prune terminal workflow-run records once per process.
            import automation.runs as run_store

            from automation.notifications import retention_days

            removed = run_store.prune_runs(retention_days())
            if removed:
                logger.info("Pruned %d expired workflow run record(s)", removed)
        except Exception:
            logger.debug("Run-record pruning failed", exc_info=True)
        while not self._stop.wait(timeout=float(poll_interval)):
            try:
                _sweep_approval_timeouts()
            except Exception:
                logger.debug("Approval expiry sweep failed", exc_info=True)
            try:
                if watcher is None:
                    roots = [
                        t.get("root")
                        for t in self._declared_watch_roots()
                    ]
                    if roots:
                        from automation.file_watcher import FileWatcher

                        watcher = FileWatcher(roots)
                if watcher is not None:
                    watcher.poll()
                    from automation.file_watcher import emit_changes

                    emit_changes(watcher.flush_ready())
            except Exception:
                logger.exception("File watcher cycle failed")
            try:
                while queue:
                    event = queue.popleft()
                    self.dispatch(event.to_dict())
            except Exception:
                logger.exception("Event dispatch cycle failed")

    def _declared_watch_roots(self) -> List[Dict[str, Any]]:
        """Roots referenced by event triggers with file.* types, intersected
        with configured allowed_roots."""
        settings = _file_watcher_settings()
        allowed = set(settings.get("allowed_roots") or [])
        wanted: Dict[str, Dict[str, Any]] = {}
        try:
            for job in self.event_automations():
                trigger = job.get("trigger") or {}
                types = trigger.get("event_types") or []
                if not any(str(t).startswith("file.") for t in types):
                    continue
                for flt in trigger.get("filters") or []:
                    if str(flt.get("path")) == "payload.root" and flt.get("op") == "eq":
                        root = str(flt.get("value") or "")
                        expanded = str(Path(root).expanduser())
                        resolved = _safe_resolve(expanded)
                        if resolved and (
                            expanded in allowed
                            or resolved in allowed
                            or any(resolved.startswith(a + os.sep) for a in allowed)
                        ):
                            wanted[resolved] = {"root": resolved}
        except Exception:
            logger.debug("Watch-root derivation failed", exc_info=True)
        return list(wanted.values())


def _sweep_approval_timeouts() -> None:
    """Phase 23: expired approvals deny themselves — never execute silently."""
    from automation import approvals, workflow_engine

    for request in approvals.sweep_expired():
        logger.warning(
            "Approval for automation '%s' expired — run %s marked failed",
            request.get("name"), request.get("run_id"),
        )
        try:
            from cron.jobs import apply_job_field_updates

            apply_job_field_updates(
                str(request.get("automation_id")),
                {"state": "paused", "paused_reason": "approval expired"},
            )
        except Exception:
            pass
        workflow_engine.expire_pending_run(request)


def _safe_resolve(path: str) -> Optional[str]:
    try:
        from pathlib import Path

        p = Path(path).expanduser()
        if not p.exists():
            return None
        return str(p.resolve())
    except OSError:
        return None


def _parse_ts(value: Any) -> Optional[float]:
    if not value:
        return None
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.astimezone()
        return dt.timestamp()
    except (TypeError, ValueError):
        return None


def _file_watcher_settings() -> Dict[str, Any]:
    from automation.file_watcher import watcher_settings

    return watcher_settings()


_dispatcher: Optional[Dispatcher] = None
_dispatch_lock = threading.Lock()


def get_dispatcher() -> Dispatcher:
    global _dispatcher
    with _dispatch_lock:
        if _dispatcher is None:
            _dispatcher = Dispatcher()
        return _dispatcher


def ensure_dispatcher_running() -> bool:
    """Called from the scheduler tick; starts the pump lazily."""
    try:
        return get_dispatcher().ensure_started()
    except Exception:
        logger.debug("Dispatcher start failed", exc_info=True)
        return False


import atexit as _atexit


@_atexit.register
def _shutdown_dispatcher() -> None:
    try:
        if _dispatcher is not None:
            _dispatcher.stop(timeout=2.0)
    except Exception:
        pass
