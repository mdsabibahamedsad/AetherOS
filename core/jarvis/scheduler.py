from __future__ import annotations

import os
import json
import time
import uuid
import logging
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    INTERVAL = "interval"
    CRON = "cron"
    ONESHOT = "oneshot"
    DAILY = "daily"
    HOURLY = "hourly"


@dataclass
class ScheduledJob:
    id: str
    name: str
    type: ScheduleType
    interval_seconds: float = 0
    cron_expression: str = ""
    enabled: bool = True
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    run_count: int = 0
    created_at: float = 0.0
    metadata: dict = field(default_factory=dict)
    handler: Optional[Callable] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if self.next_run is None and self.enabled:
            self._calculate_next()


class BackgroundScheduler:
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path.home() / ".aetheros" / "jarvis" / "scheduler.json"
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, ScheduledJob] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tick_interval = 5.0
        self._load()

    def _load(self):
        try:
            if self._storage_path.exists():
                data = json.loads(self._storage_path.read_text())
                for job_data in data:
                    if "type" in job_data:
                        job_data["type"] = ScheduleType(job_data["type"])
                    job = ScheduledJob(**job_data)
                    self._jobs[job.id] = job
        except Exception as e:
            logger.debug(f"Could not load scheduler jobs: {e}")

    def _save(self):
        try:
            data = []
            for job in self._jobs.values():
                job_dict = {
                    "id": job.id, "name": job.name,
                    "type": job.type.value, "interval_seconds": job.interval_seconds,
                    "cron_expression": job.cron_expression, "enabled": job.enabled,
                    "last_run": job.last_run, "next_run": job.next_run,
                    "run_count": job.run_count, "created_at": job.created_at,
                    "metadata": job.metadata,
                }
                data.append(job_dict)
            self._storage_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug(f"Could not save scheduler jobs: {e}")

    def schedule(self, name: str, type: ScheduleType | str,
                 interval_seconds: float = 0,
                 handler: Optional[Callable] = None,
                 metadata: Optional[dict] = None) -> ScheduledJob:
        if isinstance(type, str):
            type = ScheduleType(type)
        job = ScheduledJob(
            id=f"job-{uuid.uuid4().hex[:12]}",
            name=name,
            type=type,
            interval_seconds=interval_seconds,
            handler=handler,
            metadata=metadata or {},
        )
        with self._lock:
            self._jobs[job.id] = job
            self._save()
        return job

    def unschedule(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                self._save()
                return True
            return False

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            return job

    def get_all_jobs(self) -> list[ScheduledJob]:
        with self._lock:
            return list(self._jobs.values())

    def enable_job(self, job_id: str, enabled: bool) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.enabled = enabled
                self._save()
                return True
            return False

    def run_job_now(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.handler:
                try:
                    job.handler()
                    job.last_run = time.time()
                    job.run_count += 1
                    self._save()
                    return True
                except Exception as e:
                    logger.error(f"Job {job_id} failed: {e}")
            return False

    def _tick(self):
        while self._running:
            try:
                now = time.time()
                with self._lock:
                    for job in self._jobs.values():
                        if not job.enabled:
                            continue
                        if job.next_run and now >= job.next_run:
                            if job.handler:
                                try:
                                    job.handler()
                                except Exception as e:
                                    logger.error(f"Job {job.id} failed: {e}")
                            job.last_run = now
                            job.run_count += 1
                            job._calculate_next()
                    self._save()
            except Exception as e:
                logger.debug(f"Scheduler tick error: {e}")
            time.sleep(self._tick_interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._tick, daemon=True, name="jarvis-scheduler")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _calculate_next(self):
        pass


def _calculate_next(self):
    now = time.time()
    if self.type == ScheduleType.INTERVAL and self.interval_seconds > 0:
        self.next_run = (self.last_run or now) + self.interval_seconds
    elif self.type == ScheduleType.HOURLY:
        self.next_run = (now // 3600 + 1) * 3600
    elif self.type == ScheduleType.DAILY:
        self.next_run = (now // 86400 + 1) * 86400
    elif self.type == ScheduleType.ONESHOT:
        self.next_run = None
    else:
        self.next_run = now + 300

ScheduledJob._calculate_next = _calculate_next
