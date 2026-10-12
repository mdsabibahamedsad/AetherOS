"""
Kernel Scheduler — wraps the existing cron scheduler with a kernel-aware interface.

Provides:
  - Background job scheduling (wrapping the existing cron/scheduler.py)
  - Periodic job management
  - Deferred execution
  - Priority queues
  - Integration with the kernel event bus

The kernel scheduler delegates to the existing Aetheros cron infrastructure
for execution, adding event emission and kernel lifecycle hooks.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus, EventTopics

logger = logging.getLogger(__name__)


class JobPriority(Enum):
    """Priority levels for scheduled jobs."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class ScheduledJob:
    """A job registered with the kernel scheduler.

    Attributes:
        id: Unique job ID
        name: Human-readable name
        job_type: Type of job (cron, interval, oneshot, deferred)
        callback: Callable to execute
        interval_seconds: For interval jobs, how often to run
        cron_expr: For cron jobs, the cron expression
        run_at: For oneshot/deferred jobs, the timestamp to run at
        priority: Job priority
        max_runs: Maximum number of executions (None = unlimited)
        run_count: Current execution count
        enabled: Whether the job is active
        created_at: Creation timestamp
        last_run_at: Last execution timestamp
        metadata: Arbitrary metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    job_type: str = "interval"  # cron, interval, oneshot, deferred
    callback: Optional[Callable] = None
    interval_seconds: float = 300.0
    cron_expr: str = ""
    run_at: Optional[float] = None
    priority: JobPriority = JobPriority.NORMAL
    max_runs: Optional[int] = None
    run_count: int = 0
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    last_run_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class KernelScheduler:
    """Kernel-level scheduler wrapping the existing cron system.

    Usage:
        scheduler = KernelScheduler(event_bus)

        # Add a periodic job
        job = scheduler.add_interval("health-check", 60, my_health_check_fn)

        # Schedule a one-shot job
        scheduler.add_oneshot("send-report", time.time() + 3600, send_report)

        # Wrap an existing cron job
        scheduler.add_cron_job(existing_cron_job_dict)

        scheduler.start()
        # ... later ...
        scheduler.stop()
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._tick_thread: Optional[threading.Thread] = None
        self._shutdown_flag = False

    # ------------------------------------------------------------------
    # Job registration
    # ------------------------------------------------------------------

    def add_interval(self, name: str, interval_seconds: float,
                     callback: Callable, priority: JobPriority = JobPriority.NORMAL,
                     max_runs: int = None) -> ScheduledJob:
        """Add a recurring interval job."""
        job = ScheduledJob(
            name=name,
            job_type="interval",
            callback=callback,
            interval_seconds=interval_seconds,
            priority=priority,
            max_runs=max_runs,
        )
        self._register(job)
        return job

    def add_oneshot(self, name: str, run_at: float,
                    callback: Callable) -> ScheduledJob:
        """Add a one-shot job that runs once at a specific time."""
        job = ScheduledJob(
            name=name,
            job_type="oneshot",
            callback=callback,
            run_at=run_at,
            max_runs=1,
        )
        self._register(job)
        return job

    def add_deferred(self, name: str, delay_seconds: float,
                     callback: Callable) -> ScheduledJob:
        """Add a deferred job that runs once after a delay."""
        return self.add_oneshot(name, time.time() + delay_seconds, callback)

    def add_cron(self, name: str, cron_expr: str,
                 callback: Callable) -> ScheduledJob:
        """Add a cron-expression-based job."""
        job = ScheduledJob(
            name=name,
            job_type="cron",
            callback=callback,
            cron_expr=cron_expr,
        )
        self._register(job)
        return job

    def _register(self, job: ScheduledJob) -> None:
        """Register a job (internal)."""
        with self._lock:
            self._jobs[job.id] = job
        logger.info(
            "Scheduler: registered job '%s' (type=%s, interval=%s)",
            job.name, job.job_type,
            job.interval_seconds if job.job_type == "interval" else "N/A",
        )

    # ------------------------------------------------------------------
    # Job management
    # ------------------------------------------------------------------

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, enabled_only: bool = True) -> List[ScheduledJob]:
        """List all scheduled jobs."""
        with self._lock:
            jobs = list(self._jobs.values())
        if enabled_only:
            jobs = [j for j in jobs if j.enabled]
        jobs.sort(key=lambda j: (j.priority.value, j.name))
        return jobs

    def pause_job(self, job_id: str) -> bool:
        """Pause a job (disable without removing)."""
        job = self.get_job(job_id)
        if job is None:
            return False
        job.enabled = False
        logger.info("Scheduler: paused job '%s'", job.name)
        return True

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        job = self.get_job(job_id)
        if job is None:
            return False
        job.enabled = True
        logger.info("Scheduler: resumed job '%s'", job.name)
        return True

    def remove_job(self, job_id: str) -> bool:
        """Remove a job from the scheduler."""
        with self._lock:
            job = self._jobs.pop(job_id, None)
        if job:
            logger.info("Scheduler: removed job '%s'", job.name)
            return True
        return False

    def trigger_job(self, job_id: str) -> bool:
        """Manually trigger a job's execution immediately."""
        job = self.get_job(job_id)
        if job is None or job.callback is None:
            return False
        try:
            job.callback()
            job.last_run_at = time.time()
            job.run_count += 1
            if self._event_bus:
                self._event_bus.emit_async("scheduler.job_triggered", {
                    "job_id": job.id, "job_name": job.name,
                })
            return True
        except Exception as exc:
            logger.error("Scheduler: job '%s' trigger failed: %s", job.name, exc)
            return False

    # ------------------------------------------------------------------
    # Integration with existing cron system
    # ------------------------------------------------------------------

    def add_existing_cron_jobs(self) -> int:
        """Import jobs from the existing cron system into the kernel scheduler.

        Reads from ~/.aetheros/cron/jobs.json via cron.jobs API.
        Returns the number of jobs imported.
        """
        try:
            from cron.jobs import load_jobs

            existing_jobs = load_jobs()
            count = 0
            for j in existing_jobs:
                job_id = j.get("id", str(uuid.uuid4().hex[:12]))
                name = j.get("name", j.get("prompt", f"cron-{job_id}"))

                # Register as a passive job (actual execution still happens
                # through the existing cron/scheduler.py)
                job = ScheduledJob(
                    id=job_id,
                    name=name[:60],
                    job_type="cron",
                    cron_expr=str(j.get("schedule", {})),
                    enabled=j.get("enabled", True),
                    metadata={
                        "original": j,
                        "managed_by_existing": True,
                    },
                )
                with self._lock:
                    self._jobs[job.id] = job
                count += 1

            logger.info("Scheduler: imported %d existing cron jobs", count)
            return count
        except Exception as exc:
            logger.warning("Scheduler: failed to import existing cron jobs: %s", exc)
            return 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the scheduler tick thread."""
        if self._running:
            return
        self._running = True
        self._shutdown_flag = False
        self._tick_thread = threading.Thread(
            target=self._tick_loop,
            daemon=True,
            name="kernel-scheduler",
        )
        self._tick_thread.start()
        logger.info("Scheduler: started tick loop")

    def stop(self) -> None:
        """Stop the scheduler tick thread."""
        self._shutdown_flag = True
        self._running = False
        if self._tick_thread:
            self._tick_thread.join(timeout=5)
            self._tick_thread = None
        logger.info("Scheduler: stopped")

    def _tick_loop(self) -> None:
        """Main tick loop — checks and executes due jobs."""
        while not self._shutdown_flag:
            try:
                self._tick()
            except Exception as exc:
                logger.error("Scheduler: tick error: %s", exc)
            time.sleep(5)  # Tick every 5 seconds

    def _tick(self) -> None:
        """Check for due jobs and execute them."""
        now = time.time()
        with self._lock:
            jobs = list(self._jobs.values())

        for job in jobs:
            if not job.enabled or job.callback is None:
                continue
            if job.max_runs and job.run_count >= job.max_runs:
                continue

            should_run = False
            if job.job_type == "interval":
                if job.last_run_at is None:
                    should_run = True
                elif now - job.last_run_at >= job.interval_seconds:
                    should_run = True
            elif job.job_type == "oneshot":
                if job.run_at and now >= job.run_at:
                    should_run = True
            elif job.job_type == "cron":
                # Cron is managed by the existing system — skip here
                continue

            if should_run:
                self._execute_job(job)

    def _execute_job(self, job: ScheduledJob) -> None:
        """Execute a single job with error handling."""
        if self._event_bus:
            self._event_bus.emit_async("scheduler.job_started", {
                "job_id": job.id, "job_name": job.name,
            })

        try:
            job.callback()
            job.last_run_at = time.time()
            job.run_count += 1
            logger.debug("Scheduler: executed job '%s' (run %d)", job.name, job.run_count)

            if self._event_bus:
                self._event_bus.emit_async("scheduler.job_completed", {
                    "job_id": job.id, "job_name": job.name,
                })
        except Exception as exc:
            logger.error("Scheduler: job '%s' failed: %s", job.name, exc)
            if self._event_bus:
                self._event_bus.emit_async("scheduler.job_failed", {
                    "job_id": job.id, "job_name": job.name, "error": str(exc),
                })

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return scheduler statistics."""
        jobs = self.list_jobs(enabled_only=False)
        enabled = sum(1 for j in jobs if j.enabled)
        return {
            "running": self._running,
            "total_jobs": len(jobs),
            "enabled_jobs": enabled,
            "disabled_jobs": len(jobs) - enabled,
            "by_type": {
                t: sum(1 for j in jobs if j.job_type == t)
                for t in set(j.job_type for j in jobs)
            },
        }

    def is_healthy(self) -> bool:
        """Health check — returns True if the tick thread is alive."""
        return self._running and (
            self._tick_thread is None or self._tick_thread.is_alive()
        )
