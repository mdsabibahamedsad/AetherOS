"""AetherOS Integrations — Scheduler.

Runs jobs once, daily, weekly, monthly, by cron expression, on event, or
manually. Uses croniter for cron math. A background poll thread fires due
jobs; event-driven jobs are triggered via the EventBus. Includes a missed-job
grace window so short outages do not drop jobs.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_integrations.config import get_aetheros_dir, load_integrations_settings
from aetheros_integrations.events import EventBus
from aetheros_integrations.models import ScheduledJob
from aetheros_integrations.security import AuditLog

logger = logging.getLogger(__name__)

try:
    import croniter  # type: ignore
except ImportError:  # pragma: no cover - croniter is a hard dep via pyproject
    croniter = None  # type: ignore


class Scheduler:
    """Persistent job scheduler with cron + once + event + manual modes."""

    def __init__(self, event_bus: Optional[EventBus] = None, audit: Optional[AuditLog] = None, dirpath=None, executor: Optional[Callable[[ScheduledJob], Any]] = None):
        self._settings = load_integrations_settings()
        self._dir = dirpath or get_aetheros_dir(self._settings.data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._store_path = self._dir / "jobs.json"
        self._lock = threading.RLock()
        self._audit = audit or AuditLog(dirpath=self._dir, settings=self._settings)
        self._event_bus = event_bus or EventBus(dirpath=self._dir)
        self._executor = executor
        self._jobs: Dict[str, ScheduledJob] = {}
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._load()
        if self._event_bus:
            self._event_bus.subscribe("scheduler.trigger", self._on_event_trigger)

    # -- persistence ------------------------------------------------------

    def _load(self) -> None:
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text(encoding="utf-8"))
            for item in data:
                job = ScheduledJob(**item)
                self._jobs[job.id] = job
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load jobs: %s", exc)

    def _save(self) -> None:
        payload = [j.to_dict() for j in self._jobs.values()]
        self._store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # -- CRUD -------------------------------------------------------------

    def create(
        self,
        name: str,
        action: str,
        *,
        schedule_type: str = "once",
        cron_expr: str = "",
        run_at: Optional[float] = None,
        integration_id: str = "",
        params: Optional[Dict[str, Any]] = None,
        timezone: str = "UTC",
        event_type: str = "",
    ) -> ScheduledJob:
        if schedule_type == "cron" and croniter is not None:
            if not croniter.croniter.is_valid(cron_expr):
                raise ValueError(f"Invalid cron expression: {cron_expr}")
        job = ScheduledJob(
            name=name,
            schedule_type=schedule_type,
            cron_expr=cron_expr,
            timezone=timezone,
            integration_id=integration_id,
            action=action,
            params=params or {},
        )
        if schedule_type == "once":
            job.next_run_at = run_at or time.time() + 60
        elif schedule_type in ("daily", "weekly", "monthly"):
            job.next_run_at = self._next_natural(schedule_type, run_at)
        elif schedule_type == "cron":
            job.next_run_at = self._next_cron(cron_expr, timezone)
        elif schedule_type == "event":
            job.params["event_type"] = event_type
            job.next_run_at = 0
        with self._lock:
            self._jobs[job.id] = job
            self._save()
        self._audit.record("scheduler.job_created", target=job.id, detail={"name": name, "type": schedule_type})
        return job

    def update(self, job_id: str, **fields) -> ScheduledJob:
        job = self.get(job_id)
        for k, v in fields.items():
            if hasattr(job, k):
                setattr(job, k, v)
        if "cron_expr" in fields:
            job.next_run_at = self._next_cron(job.cron_expr, job.timezone)
        with self._lock:
            self._save()
        return job

    def remove(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                self._save()
                return True
        return False

    def get(self, job_id: str) -> ScheduledJob:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"No job {job_id}")
            return self._jobs[job_id]

    def list(self, enabled: Optional[bool] = None) -> List[ScheduledJob]:
        with self._lock:
            jobs = list(self._jobs.values())
        if enabled is not None:
            jobs = [j for j in jobs if j.enabled == enabled]
        return jobs

    # -- run --------------------------------------------------------------

    def set_executor(self, executor: Callable[[ScheduledJob], Any]) -> None:
        self._executor = executor

    def run_now(self, job_id: str) -> Any:
        job = self.get(job_id)
        job.last_run_at = time.time()
        job.run_count += 1
        job.last_status = "running"
        with self._lock:
            self._save()
        result = self._execute(job)
        return result

    def trigger_manual(self, job_id: str) -> Any:
        return self.run_now(job_id)

    def _execute(self, job: ScheduledJob) -> Any:
        if self._executor is None:
            raise RuntimeError("No executor installed on scheduler")
        try:
            result = self._executor(job)
            job.last_status = "success"
            return result
        except Exception as exc:  # noqa: BLE001
            job.last_status = f"error: {exc}"
            logger.warning("Job %s failed: %s", job.id, exc)
            raise
        finally:
            with self._lock:
                self._save()

    def _on_event_trigger(self, envelope) -> None:
        event_type = envelope.data.get("event_type") if envelope.data else None
        if not event_type:
            return
        for job in self.list(enabled=True):
            if job.schedule_type == "event" and job.params.get("event_type") == event_type:
                self.run_now(job.id)

    # -- scheduling math --------------------------------------------------

    def _next_cron(self, expr: str, timezone: str) -> float:
        if croniter is None:
            return time.time() + 3600
        try:
            import pytz

            tz = pytz.timezone(timezone) if timezone != "UTC" else None
            base = time.time()
            it = croniter.croniter(expr, base, ret_type=float)
            return it.get_next()
        except Exception:  # noqa: BLE001
            return time.time() + 3600

    def _next_natural(self, kind: str, run_at: Optional[float]) -> float:
        now = time.time()
        if run_at and run_at > now:
            return run_at
        if kind == "daily":
            return now + 86400
        if kind == "weekly":
            return now + 7 * 86400
        if kind == "monthly":
            return now + 30 * 86400
        return now + 60

    def compute_next_runs(self, now: Optional[float] = None) -> List[Dict[str, Any]]:
        now = now or time.time()
        out = []
        for job in self.list(enabled=True):
            if job.schedule_type == "event":
                out.append({"id": job.id, "name": job.name, "kind": "event", "waits_for": job.params.get("event_type", "")})
            elif job.next_run_at:
                out.append({"id": job.id, "name": job.name, "kind": job.schedule_type, "next_run_at": job.next_run_at, "in_s": round(max(0, job.next_run_at - now), 1)})
        return out

    # -- background loop --------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="aetheros-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Scheduler tick failed: %s", exc)
            self._stop.wait(self._settings.scheduler.poll_interval_s)

    def _tick(self) -> None:
        now = time.time()
        due: List[ScheduledJob] = []
        with self._lock:
            for job in self._jobs.values():
                if not job.enabled:
                    continue
                if job.schedule_type == "event":
                    continue
                if job.next_run_at and job.next_run_at <= now:
                    # missed-job grace window: still fire if within window
                    if now - job.next_run_at <= self._settings.scheduler.missed_job_window_s:
                        due.append(job)
                    # advance regardless to avoid a backlog storm
                    job.next_run_at = self._advance(job)
        for job in due:
            try:
                self.run_now(job.id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Scheduled job %s failed: %s", job.id, exc)
        if due:
            with self._lock:
                self._save()

    def _advance(self, job: ScheduledJob) -> float:
        if job.schedule_type == "once":
            return float("inf")
        if job.schedule_type == "cron":
            return self._next_cron(job.cron_expr, job.timezone)
        return self._next_natural(job.schedule_type, job.next_run_at)
