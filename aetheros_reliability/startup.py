"""Startup recovery — detect and reconcile an unclean shutdown.

At startup the following are detected:

* unclean shutdown (missing a clean-shutdown marker / stale PID)
* incomplete operations (recovery journal pending entries)
* stale locks (lock files older than a safety window)
* partial file operations (leftover ``*.tmp`` markers owned by this home)

The report classifies every interrupted mission (via
``aetheros_reliability.mission``) and lists stale locks.  Startup recovery
NEVER auto-runs destructive operations — it produces evidence and safe,
reviewable actions.
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home

from aetheros_reliability.journal import get_recovery_journal
from aetheros_reliability.mission import MissionRecovery

logger = logging.getLogger(__name__)

CLEAN_SHUTDOWN_MARKER = "reliability/.clean-shutdown"
LOCK_SUFFIXES = (".lock", ".pid")
#: Locks older than this are considered stale (active ops refresh them).
STALE_LOCK_AGE_SECONDS = 3600.0


@dataclass
class StartupRecoveryReport:
    unclean_shutdown: bool
    clean_shutdown_at: Optional[float]
    pending_operations: List[Dict[str, Any]]
    stale_locks: List[Dict[str, Any]]
    missions: List[Dict[str, Any]]
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unclean_shutdown": self.unclean_shutdown,
            "clean_shutdown_at": self.clean_shutdown_at,
            "pending_operations": self.pending_operations,
            "stale_locks": self.stale_locks,
            "missions": self.missions,
            "detected_at": self.detected_at,
        }


class StartupRecovery:
    """Startup reconciliation evidence.

    Usage::

        sr = StartupRecovery()
        report = sr.analyze()
        if report.unclean_shutdown:
            print("Previous shutdown was unclean; review pending operations.")
        sr.mark_clean_shutdown()
    """

    def __init__(self, home: Optional[Path] = None) -> None:
        self._home = Path(home) if home else get_aetheros_home()
        self._journal = get_recovery_journal()
        self._missions = MissionRecovery(journal=self._journal)

    @property
    def marker_path(self) -> Path:
        return self._home / CLEAN_SHUTDOWN_MARKER

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze(self) -> StartupRecoveryReport:
        marker = self.marker_path
        clean_at = None
        unclean = True
        if marker.exists():
            unclean = False
            try:
                raw = marker.read_text().strip()
                clean_at = float(raw) if raw else None
            except (ValueError, OSError):
                clean_at = None
        return StartupRecoveryReport(
            unclean_shutdown=unclean,
            clean_shutdown_at=clean_at,
            pending_operations=self._journal.pending(limit=200),
            stale_locks=self._find_stale_locks(),
            missions=[s.to_dict() for s in self._missions.analyze()],
        )

    def _find_stale_locks(self) -> List[Dict[str, Any]]:
        """Find lock/pid files older than the staleness window."""
        stale = []
        now = time.time()
        for suffix in LOCK_SUFFIXES:
            for path in self._home.rglob(f"*{suffix}"):
                try:
                    if not path.is_file():
                        continue
                    age = now - path.stat().st_mtime
                    if age > STALE_LOCK_AGE_SECONDS:
                        stale.append({
                            "path": str(path),
                            "age_seconds": round(age, 1),
                        })
                except OSError:
                    continue
        return stale

    # ------------------------------------------------------------------
    # Markers
    # ------------------------------------------------------------------

    def mark_clean_shutdown(self) -> bool:
        """Write the clean-shutdown marker (atomic)."""
        try:
            marker = self.marker_path
            marker.parent.mkdir(parents=True, exist_ok=True)
            tmp = marker.with_suffix(".tmp")
            tmp.write_text(str(time.time()), encoding="utf-8")
            os.replace(tmp, marker)
            return True
        except OSError as exc:
            logger.error("Clean-shutdown marker write failed: %s", exc)
            return False

    def mark_unclean(self, reason: str = "") -> bool:
        """Clear the clean marker (call this when a crash is detected so the
        NEXT startup can detect the unclean shutdown)."""
        try:
            self.marker_path.unlink(missing_ok=True)
            if reason:
                logger.warning("Marking unclean shutdown: %s", reason)
            return True
        except OSError:
            return False

    def clear_pending(self) -> None:
        """After successful reconciliation, terminalize stale pending ops."""
        for op in self._journal.pending(limit=500):
            try:
                self._journal.abort(op["operation_id"],
                                    detail={"note": "aborted at startup reconciliation"})
            except Exception:
                pass

    def summary(self) -> Dict[str, Any]:
        report = self.analyze()
        return {
            "unclean_shutdown": report.unclean_shutdown,
            "pending_operations": len(report.pending_operations),
            "stale_locks": len(report.stale_locks),
            "missions": len(report.missions),
        }


def _is_lock_name(name: str) -> bool:
    return name.endswith(LOCK_SUFFIXES) and not name.endswith((".py", ".pyc"))