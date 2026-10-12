"""
Maintenance Engine
==================

Automated system maintenance for AetherOS production deployments.

Performs:
- Cache and temporary file cleanup
- Log rotation and archival
- Database optimization (VACUUM, checkpoint)
- Stale session cleanup
- State file integrity checks
- Backup creation
- Resource reclamation
- Configuration validation
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MaintenanceSeverity(Enum):
    """Severity levels for maintenance tasks."""
    CRITICAL = "critical"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class MaintenanceCategory(Enum):
    """Categories of maintenance tasks."""
    CLEANUP = "cleanup"
    OPTIMIZATION = "optimization"
    BACKUP = "backup"
    VALIDATION = "validation"
    RECOVERY = "recovery"
    HOUSEKEEPING = "housekeeping"


@dataclass
class MaintenanceTask:
    """A single maintenance task configuration and result.

    Attributes:
        name: Task name
        category: Task category
        description: Description of what the task does
        severity: Severity/importance
        automated: Whether this can run automatically
        run_if: Optional predicate function to determine if task should run
        action: Callable to perform the maintenance
        result: Result message after execution
        success: Whether the task completed successfully
        duration_ms: How long the task took
        freed_bytes: Bytes freed/cleaned (if applicable)
    """
    name: str
    category: MaintenanceCategory = MaintenanceCategory.HOUSEKEEPING
    description: str = ""
    severity: MaintenanceSeverity = MaintenanceSeverity.OPTIONAL
    automated: bool = True
    run_if: Optional[Callable[[], bool]] = None
    action: Optional[Callable[[], str]] = None

    # Runtime state
    result: str = ""
    success: bool = False
    duration_ms: float = 0.0
    freed_bytes: int = 0


@dataclass
class MaintenanceReport:
    """Report from a maintenance run.

    Attributes:
        timestamp: When maintenance ran
        tasks: Tasks that were executed
        total_duration_ms: Total time spent
        completed: Number of tasks completed
        failed: Number of tasks failed
        skipped: Number of tasks skipped
        total_freed_bytes: Total bytes reclaimed
    """
    timestamp: float = field(default_factory=time.time)
    tasks: List[MaintenanceTask] = field(default_factory=list)
    total_duration_ms: float = 0.0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    total_freed_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "total_duration_ms": self.total_duration_ms,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "total_freed_bytes": self.total_freed_bytes,
            "total_freed_mb": self.total_freed_bytes / (1024 * 1024),
            "tasks": [
                {
                    "name": t.name,
                    "category": t.category.value,
                    "success": t.success,
                    "duration_ms": t.duration_ms,
                    "result": t.result,
                    "freed_bytes": t.freed_bytes,
                }
                for t in self.tasks
            ],
        }


class MaintenanceEngine:
    """Orchestrates system maintenance tasks.

    Usage:
        engine = MaintenanceEngine()
        report = engine.run_all()
        print(f"Freed {report.total_freed_mb:.1f} MB")
    """

    def __init__(self):
        self._tasks: List[MaintenanceTask] = []
        self._register_default_tasks()

    def _register_default_tasks(self) -> None:
        """Register default maintenance tasks."""
        self.register_task(MaintenanceTask(
            name="clean_temp_files",
            category=MaintenanceCategory.CLEANUP,
            description="Remove temporary files and caches",
            severity=MaintenanceSeverity.RECOMMENDED,
            action=self._clean_temp_files,
        ))
        self.register_task(MaintenanceTask(
            name="checkpoint_wal",
            category=MaintenanceCategory.OPTIMIZATION,
            description="Checkpoint SQLite WAL file to reduce size",
            severity=MaintenanceSeverity.RECOMMENDED,
            action=self._checkpoint_wal,
        ))
        self.register_task(MaintenanceTask(
            name="vacuum_state_db",
            category=MaintenanceCategory.OPTIMIZATION,
            description="VACUUM the state database to reclaim space",
            severity=MaintenanceSeverity.RECOMMENDED,
            action=self._vacuum_state_db,
        ))
        self.register_task(MaintenanceTask(
            name="rotate_logs",
            category=MaintenanceCategory.HOUSEKEEPING,
            description="Rotate and compress old log files",
            severity=MaintenanceSeverity.OPTIONAL,
            action=self._rotate_logs,
        ))
        self.register_task(MaintenanceTask(
            name="clean_stale_sessions",
            category=MaintenanceCategory.CLEANUP,
            description="Remove stale session data",
            severity=MaintenanceSeverity.OPTIONAL,
            action=self._clean_stale_sessions,
        ))
        self.register_task(MaintenanceTask(
            name="validate_state_files",
            category=MaintenanceCategory.VALIDATION,
            description="Check integrity of state files",
            severity=MaintenanceSeverity.RECOMMENDED,
            action=self._validate_state_files,
        ))

    def register_task(self, task: MaintenanceTask) -> None:
        """Register a maintenance task."""
        self._tasks.append(task)

    def run_all(self) -> MaintenanceReport:
        """Run all maintenance tasks that meet their preconditions."""
        report = MaintenanceReport()
        start = time.perf_counter()

        for task in self._tasks:
            task_start = time.perf_counter()

            # Check precondition
            if task.run_if is not None and not task.run_if():
                task.success = True  # Not a failure, just skipped
                task.result = "Skipped (precondition not met)"
                task.duration_ms = (time.perf_counter() - task_start) * 1000
                report.skipped += 1
                report.tasks.append(task)
                continue

            # Run the task
            try:
                if task.action:
                    task.result = task.action()
                task.success = True
                report.completed += 1
            except Exception as exc:
                task.result = f"Failed: {exc}"
                task.success = False
                report.failed += 1
                logger.warning("Maintenance task '%s' failed: %s", task.name, exc)

            task.duration_ms = (time.perf_counter() - task_start) * 1000
            report.total_freed_bytes += task.freed_bytes
            report.tasks.append(task)

        report.total_duration_ms = (time.perf_counter() - start) * 1000
        return report

    def run_task(self, task_name: str) -> Optional[MaintenanceTask]:
        """Run a specific maintenance task by name."""
        for task in self._tasks:
            if task.name == task_name:
                task_start = time.perf_counter()
                try:
                    if task.action:
                        task.result = task.action()
                    task.success = True
                except Exception as exc:
                    task.result = f"Failed: {exc}"
                    task.success = False
                task.duration_ms = (time.perf_counter() - task_start) * 1000
                return task
        return None

    # ------------------------------------------------------------------
    # Default task implementations
    # ------------------------------------------------------------------

    def _clean_temp_files(self) -> str:
        """Clean temporary files from known temp directories."""
        freed = 0
        count = 0

        # Clean /tmp/aetheros-* files
        tmp_dir = Path("/tmp")
        for p in tmp_dir.glob("aetheros-*"):
            try:
                if p.is_file():
                    freed += p.stat().st_size
                    p.unlink()
                    count += 1
                elif p.is_dir():
                    size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                    freed += size
                    shutil.rmtree(p)
                    count += 1
            except OSError:
                pass

        # Clean benchmark output files
        bench_dir = Path("/tmp/aetheros-benchmarks")
        if bench_dir.exists():
            try:
                for p in bench_dir.glob("*.json"):
                    freed += p.stat().st_size
                    p.unlink()
                    count += 1
            except OSError:
                pass

        self._report_freed("clean_temp_files", freed)
        return f"Cleaned {count} temp files/folders, freed {freed / 1024:.1f} KB"

    def _checkpoint_wal(self) -> str:
        """Checkpoint SQLite WAL files."""
        try:
            from aetheros_constants import get_aetheros_home
            state_db = get_aetheros_home() / "state.db"

            if not state_db.exists():
                return "No state.db found"

            import sqlite3
            conn = sqlite3.connect(str(state_db))
            wal_path = get_aetheros_home() / "state.db-wal"
            wal_before = wal_path.stat().st_size if wal_path.exists() else 0

            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()

            wal_after = 0
            if wal_path.exists():
                wal_after = wal_path.stat().st_size

            freed = wal_before - wal_after
            self._report_freed("checkpoint_wal", freed)
            return f"WAL checkpointed: {wal_before // 1024}K → {wal_after // 1024}K"
        except Exception as exc:
            return f"WAL checkpoint failed: {exc}"

    def _vacuum_state_db(self) -> str:
        """VACUUM the SQLite state database."""
        try:
            from aetheros_constants import get_aetheros_home
            state_db = get_aetheros_home() / "state.db"

            if not state_db.exists():
                return "No state.db found"

            before = state_db.stat().st_size
            import sqlite3
            conn = sqlite3.connect(str(state_db))
            conn.execute("VACUUM")
            conn.close()
            after = state_db.stat().st_size

            freed = before - after
            self._report_freed("vacuum_state_db", freed)
            return f"VACUUM: {before // 1024}K → {after // 1024}K (freed {freed // 1024}K)"
        except Exception as exc:
            return f"VACUUM failed: {exc}"

    def _rotate_logs(self) -> str:
        """Rotate and compress old log files."""
        try:
            from aetheros_constants import get_aetheros_home
            log_dir = get_aetheros_home() / "logs"

            if not log_dir.exists():
                return "No logs directory found"

            rotated = 0
            freed = 0
            for log_file in log_dir.glob("*.log"):
                if log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB
                    import gzip
                    rotated_name = log_file.with_suffix(f".log.{int(time.time())}.gz")
                    with open(log_file, "rb") as f_in:
                        with gzip.open(rotated_name, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    freed += log_file.stat().st_size
                    log_file.write_text("")  # Truncate
                    rotated += 1
                    self._report_freed("rotate_logs", freed)

            if rotated > 0:
                return f"Rotated {rotated} log files"
            return "No logs needed rotation"
        except Exception as exc:
            return f"Log rotation failed: {exc}"

    def _clean_stale_sessions(self) -> str:
        """Clean stale session data."""
        try:
            from aetheros_constants import get_aetheros_home
            sessions_dir = get_aetheros_home() / "sessions"
            removed = 0

            if sessions_dir.exists():
                for f in sessions_dir.iterdir():
                    if f.is_file():
                        age = time.time() - f.stat().st_mtime
                        if age > 7 * 24 * 3600:  # Older than 7 days
                            f.unlink()
                            removed += 1

            return f"Removed {removed} stale session files"
        except Exception as exc:
            return f"Session cleanup failed: {exc}"

    def _validate_state_files(self) -> str:
        """Validate integrity of state files."""
        from aetheros_constants import get_aetheros_home
        issues: List[str] = []
        home = get_aetheros_home()

        # Check state.db
        state_db = home / "state.db"
        if state_db.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(state_db))
                conn.execute("SELECT COUNT(*) FROM sqlite_master")
                conn.close()
            except Exception as exc:
                issues.append(f"state.db: {exc}")

        # Check config
        config = home / "config.yaml"
        if not config.exists():
            issues.append("config.yaml not found")

        # Check .env
        env_file = home / ".env"
        if not env_file.exists():
            issues.append(".env file not found")

        if issues:
            return f"Found {len(issues)} issue(s): {'; '.join(issues)}"
        return "All state files validated"

    def _report_freed(self, task_name: str, bytes_freed: int) -> None:
        """Update a task's freed_bytes."""
        for task in self._tasks:
            if task.name == task_name:
                task.freed_bytes = bytes_freed
                break


def run_maintenance() -> MaintenanceReport:
    """Quick-start convenience function to run all maintenance tasks.

    Returns:
        A complete MaintenanceReport.
    """
    engine = MaintenanceEngine()
    return engine.run_all()
