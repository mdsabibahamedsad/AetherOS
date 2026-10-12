"""Execution Queue — background jobs with priority, pause, resume, retry, cancel, dependencies.

Thread-safe job queue for async execution.
"""

from __future__ import annotations

import enum
import heapq
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_runtime.queue")


class JobStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RETRYING = "retrying"


class JobPriority(enum.IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


JobFn = Callable[..., Any]


@dataclass
class Job:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    fn: Optional[JobFn] = None
    args: tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    max_retries: int = 3
    retry_count: int = 0
    depends_on: List[str] = field(default_factory=list)
    timeout: float = 300.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed_ms(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        if self.started_at:
            return (time.time() - self.started_at) * 1000
        return 0.0

    @property
    def is_done(self) -> bool:
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)


class ExecutionQueue:
    """Priority-based execution queue with full lifecycle control.

    Supports:
    - Priority ordering (critical, high, normal, low)
    - Pause/resume individual jobs
    - Retry with configurable attempts
    - Cancellation
    - Job dependencies (run after dependencies complete)
    - Concurrent worker pool
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        self._jobs: Dict[str, Job] = {}
        self._queue: List[tuple] = []
        self._running: Set[str] = set()
        self._paused: Set[str] = set()
        self._max_workers = max_workers
        self._active_workers = 0
        self._stopped = False
        self._worker_threads: List[threading.Thread] = []

    # ------------------------------------------------------------------
    # Job management
    # ------------------------------------------------------------------

    def enqueue(
        self,
        fn: JobFn,
        name: str = "",
        priority: JobPriority = JobPriority.NORMAL,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        max_retries: int = 3,
        timeout: float = 300.0,
        job_id: Optional[str] = None,
    ) -> str:
        job = Job(
            id=job_id or str(uuid.uuid4()),
            name=name or fn.__name__,
            fn=fn,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            max_retries=max_retries,
            timeout=timeout,
            depends_on=depends_on or [],
        )

        with self._cond:
            self._jobs[job.id] = job
            self._push(job)
            self._cond.notify()

        logger.info("Job enqueued: %s (%s, priority=%s)", job.name, job.id[:8], priority.name)
        return job.id

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def get_status(self, job_id: str) -> Optional[JobStatus]:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.status if job else None

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.is_done:
                return False
            job.status = JobStatus.CANCELLED
            job.completed_at = time.time()
            self._running.discard(job_id)
            return True

    def cancel_all(self) -> int:
        count = 0
        with self._lock:
            for job in self._jobs.values():
                if not job.is_done:
                    job.status = JobStatus.CANCELLED
                    job.completed_at = time.time()
                    count += 1
            self._running.clear()
            self._queue.clear()
        return count

    def pause(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status != JobStatus.PENDING:
                return False
            job.status = JobStatus.PAUSED
            self._paused.add(job_id)
            return True

    def resume(self, job_id: str) -> bool:
        with self._cond:
            job = self._jobs.get(job_id)
            if not job or job.status != JobStatus.PAUSED:
                return False
            job.status = JobStatus.PENDING
            self._paused.discard(job_id)
            self._push(job)
            self._cond.notify()
        return True

    # ------------------------------------------------------------------
    # Worker pool
    # ------------------------------------------------------------------

    def start(self, workers: Optional[int] = None) -> None:
        count = workers or self._max_workers
        with self._lock:
            self._stopped = False
        for _ in range(count):
            t = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_threads.append(t)
            t.start()
        logger.info("Execution queue started with %d workers", count)

    def stop(self, wait: bool = True) -> None:
        with self._cond:
            self._stopped = True
            self._cond.notify_all()
        if wait:
            for t in self._worker_threads:
                t.join(timeout=10)
        self._worker_threads.clear()
        logger.info("Execution queue stopped")

    def _worker_loop(self) -> None:
        while True:
            job = self._dequeue()
            if job is None:
                if self._stopped:
                    break
                continue

            try:
                self._execute_job(job)
            except Exception as exc:
                logger.exception("Worker error for job %s", job.id[:8])

    def _execute_job(self, job: Job) -> None:
        while job.retry_count <= job.max_retries:
            job.started_at = time.time()
            job.status = JobStatus.RUNNING

            try:
                if job.timeout > 0:
                    timer = threading.Timer(job.timeout, self._timeout_job, args=[job.id])
                    timer.daemon = True
                    timer.start()

                result = job.fn(*job.args, **job.kwargs)

                if job.timeout > 0:
                    timer.cancel()

                job.result = result
                job.status = JobStatus.COMPLETED
                job.completed_at = time.time()
                logger.info("Job completed: %s (%s, %.0fms)", job.name, job.id[:8], job.elapsed_ms)
                return

            except Exception as exc:
                job.retry_count += 1
                if job.retry_count <= job.max_retries:
                    job.status = JobStatus.RETRYING
                    logger.warning("Job %s retrying (%d/%d): %s", job.id[:8], job.retry_count, job.max_retries, exc)
                    time.sleep(1.0 * job.retry_count)
                else:
                    job.status = JobStatus.FAILED
                    job.error = str(exc)
                    job.completed_at = time.time()
                    logger.error("Job failed: %s (%s): %s", job.name, job.id[:8], exc)

    # ------------------------------------------------------------------
    # Queue operations
    # ------------------------------------------------------------------

    def _push(self, job: Job) -> None:
        heapq.heappush(self._queue, (-job.priority.value, job.created_at, job.id))

    def _dequeue(self) -> Optional[Job]:
        with self._cond:
            while not self._stopped:
                while self._queue:
                    _, _, job_id = heapq.heappop(self._queue)
                    job = self._jobs.get(job_id)
                    if not job or job.is_done or job.status == JobStatus.PAUSED:
                        continue
                    if not self._dependencies_met(job):
                        self._push(job)
                        continue
                    self._running.add(job_id)
                    return job
                self._cond.wait(timeout=1.0)
            return None

    def _dependencies_met(self, job: Job) -> bool:
        for dep_id in job.depends_on:
            dep = self._jobs.get(dep_id)
            if not dep or dep.status != JobStatus.COMPLETED:
                return False
        return True

    @staticmethod
    def _timeout_job(job_id: str) -> None:
        logger.warning("Job timed out: %s", job_id[:8])

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status == JobStatus.PENDING)

    def running_count(self) -> int:
        with self._lock:
            return len(self._running)

    def completed_count(self) -> int:
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status == JobStatus.COMPLETED)

    def failed_count(self) -> int:
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status == JobStatus.FAILED)

    def list_jobs(self, status: Optional[JobStatus] = None) -> List[Job]:
        with self._lock:
            if status:
                return [j for j in self._jobs.values() if j.status == status]
            return list(self._jobs.values())

    def clear_completed(self) -> int:
        count = 0
        with self._lock:
            for jid in list(self._jobs.keys()):
                job = self._jobs[jid]
                if job.status == JobStatus.COMPLETED:
                    del self._jobs[jid]
                    count += 1
        return count

    def health_check(self) -> bool:
        return not self._stopped

    def summary(self) -> str:
        return (
            f"Execution Queue: {self.pending_count()} pending, "
            f"{self.running_count()} running, {self.completed_count()} completed, "
            f"{self.failed_count()} failed"
        )