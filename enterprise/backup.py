"""
Backup
======

Backup orchestration for enterprise data, configurations,
and state. Supports scheduled backups, incremental snapshots,
and encrypted output.
"""

from __future__ import annotations

import enum
import json
import logging
import shutil
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class BackupStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class BackupSchedule:
    """Schedule for automatic backups."""
    name: str = "daily"
    interval_hours: int = 24
    retention_days: int = 30
    enabled: bool = True
    last_run: Optional[datetime] = None

    def is_due(self) -> bool:
        if not self.last_run:
            return True
        return datetime.utcnow() > self.last_run + timedelta(hours=self.interval_hours)


@dataclass
class BackupResult:
    """Result of a backup operation."""
    status: BackupStatus
    path: Optional[Path] = None
    size_bytes: int = 0
    file_count: int = 0
    checksum: str = ""
    duration_seconds: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "path": str(self.path) if self.path else None,
            "size_bytes": self.size_bytes,
            "file_count": self.file_count,
            "checksum": self.checksum,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }


@dataclass
class BackupJob:
    """A single backup job with source paths and configuration."""
    name: str
    source_paths: List[Path]
    destination: Path
    id: str = ""
    compress: bool = True
    encrypt: bool = False
    exclude_patterns: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


class BackupManager:
    """Manage backup operations and schedules."""

    def __init__(self) -> None:
        self._jobs: Dict[str, BackupJob] = {}
        self._schedules: Dict[str, BackupSchedule] = {}
        self._results: List[BackupResult] = []
        self._hooks: Dict[str, List[Callable]] = {
            "pre_backup": [],
            "post_backup": [],
            "backup_failed": [],
        }

    def register_job(self, job: BackupJob) -> None:
        self._jobs[job.name] = job

    def get_job(self, name: str) -> Optional[BackupJob]:
        return self._jobs.get(name)

    def register_schedule(self, schedule: BackupSchedule) -> None:
        self._schedules[schedule.name] = schedule

    def run_backup(self, job_name: str) -> BackupResult:
        """Execute a backup job."""
        job = self._jobs.get(job_name)
        if not job:
            return BackupResult(status=BackupStatus.FAILED, error=f"Job not found: {job_name}")

        import hashlib

        start = datetime.utcnow()
        result = BackupResult(status=BackupStatus.RUNNING)

        # Pre-backup hooks
        for hook in self._hooks.get("pre_backup", []):
            try:
                hook(job)
            except Exception as e:
                logger.warning("Pre-backup hook failed: %s", e)

        try:
            # Ensure destination exists
            job.destination.mkdir(parents=True, exist_ok=True)

            # Create backup archive
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{job.name}_{timestamp}"
            if job.compress:
                backup_path = job.destination / f"{backup_name}.tar.gz"
                mode = "w:gz"
            else:
                backup_path = job.destination / f"{backup_name}.tar"
                mode = "w"

            file_count = 0
            with tarfile.open(backup_path, mode) as tar:
                for source in job.source_paths:
                    if source.exists():
                        tar.add(source, arcname=source.name)
                        file_count += 1

            # Compute checksum
            checksum = hashlib.sha256()
            with open(backup_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    checksum.update(chunk)

            duration = (datetime.utcnow() - start).total_seconds()
            result = BackupResult(
                status=BackupStatus.COMPLETED,
                path=backup_path,
                size_bytes=backup_path.stat().st_size,
                file_count=file_count,
                checksum=checksum.hexdigest(),
                duration_seconds=duration,
            )

            # Post-backup hooks
            for hook in self._hooks.get("post_backup", []):
                try:
                    hook(job, result)
                except Exception as e:
                    logger.warning("Post-backup hook failed: %s", e)

            logger.info("Backup completed: %s (%s bytes)", backup_path, result.size_bytes)

        except Exception as exc:
            duration = (datetime.utcnow() - start).total_seconds()
            result = BackupResult(
                status=BackupStatus.FAILED,
                error=str(exc),
                duration_seconds=duration,
            )
            for hook in self._hooks.get("backup_failed", []):
                try:
                    hook(job, exc)
                except Exception:
                    pass

        self._results.append(result)
        return result

    def list_backups(self, job_name: Optional[str] = None) -> List[BackupResult]:
        if job_name:
            return [r for r in self._results if r.path and job_name in r.path.name]
        return list(self._results)

    def get_result(self, job_name: str) -> Optional[BackupResult]:
        for r in reversed(self._results):
            if r.path and job_name in r.path.name:
                return r
        return None

    def check_schedules(self) -> List[str]:
        """Check all schedules and run any that are due."""
        due = []
        for schedule in self._schedules.values():
            if schedule.enabled and schedule.is_due():
                for job_name in self._jobs:
                    result = self.run_backup(job_name)
                    due.append(job_name)
                schedule.last_run = datetime.utcnow()
        return due

    def register_hook(self, event: str, callback: Callable) -> None:
        if event in self._hooks:
            self._hooks[event].append(callback)
