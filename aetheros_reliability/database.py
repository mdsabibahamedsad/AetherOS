"""Database health, corruption detection and safe recovery.

Detects (without destroying evidence):

* invalid schema (user_version vs expected)
* malformed records / broken indexes (SQLite ``integrity_check``)
* unrecoverable connection states

Safe recovery actions:

* bounded connection retry with backoff
* WAL checkpoint + reopen
* integrity verification
* quarantine of a corrupted DB (renamed, never deleted) so the caller can
  restore from backup or last-known-good.

This extends — and never replaces — the existing SQLite session store
(``aetheros_state.py``) and cron job store.  It only verifies and, when
safe, reopens.
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


@dataclass
class DatabaseHealth:
    path: str
    ok: bool
    integrity: str = ""          # "ok" | message
    user_version: int = 0
    expected_version: int = 0
    schema_matches: bool = True
    size_bytes: int = 0
    message: str = ""
    checked_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "ok": self.ok,
            "integrity": self.integrity,
            "user_version": self.user_version,
            "expected_version": self.expected_version,
            "schema_matches": self.schema_matches,
            "size_bytes": self.size_bytes,
            "message": self.message,
            "checked_at": self.checked_at,
        }


class DatabaseRecovery:
    """Verify and safely reopen SQLite stores.

    Usage::

        dr = get_database_recovery()
        health = dr.check("state", expected_version=5)
        ok = dr.recover("state")            # retry → reopen → integrity
        quarantine = dr.quarantine("state") # corrupt DB preserved, not deleted
    """

    #: Known AetherOS SQLite databases (relative to AETHEROS_HOME).
    DEFAULT_DATABASES = {
        "state": ("state.db", 0),          # SessionDB (schema version ignored)
        "cron": ("cron/jobs.db", 0),
        "kanban": ("kanban/board.db", 0),
    }

    def __init__(self, home: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._home = Path(home) if home else get_aetheros_home()
        self._quarantine_dir = self._home / "reliability" / "quarantine"
        self._cache: Dict[str, DatabaseHealth] = {}

    def _db_path(self, name: str) -> Optional[Path]:
        if name in self.DEFAULT_DATABASES:
            rel, _ = self.DEFAULT_DATABASES[name]
            return self._home / rel
        return self._home / f"{name}.db"

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def check(self, name: str, expected_version: int = 0) -> DatabaseHealth:
        """Verify a database's integrity and schema."""
        path = self._db_path(name)
        if path is None or not path.exists():
            health = DatabaseHealth(
                path=str(path or self._home / f"{name}.db"), ok=False,
                message="database missing",
            )
            self._cache[name] = health
            return health
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
            try:
                cur = conn.execute("PRAGMA quick_check")
                quick = cur.fetchone()
                integrity_ok = bool(quick and quick[0] == "ok")
                try:
                    cur = conn.execute("PRAGMA user_version")
                    user_version = int(cur.fetchone()[0])
                except Exception:
                    user_version = 0
                health = DatabaseHealth(
                    path=str(path),
                    ok=integrity_ok,
                    integrity=quick[0] if quick else "unknown",
                    user_version=user_version,
                    expected_version=expected_version,
                    schema_matches=(not expected_version) or user_version == expected_version,
                    size_bytes=path.stat().st_size,
                )
            finally:
                conn.close()
        except sqlite3.Error as exc:
            health = DatabaseHealth(
                path=str(path), ok=False, message=f"open failed: {exc}",
            )
        self._cache[name] = health
        return health

    def check_all(self) -> Dict[str, DatabaseHealth]:
        results = {}
        for name in self.DEFAULT_DATABASES:
            rel, expected = self.DEFAULT_DATABASES[name]
            results[name] = self.check(name, expected_version=expected)
        return results

    def get_health(self, name: str) -> Optional[DatabaseHealth]:
        return self._cache.get(name)

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def recover(self, name: str, *, retries: int = 3,
                retry_delay: float = 1.0) -> DatabaseHealth:
        """Bounded retry → WAL checkpoint → reopen → integrity check.

        Returns final health.  Never destroys data.
        """
        health = self.check(name)
        if health.ok:
            return health
        for attempt in range(1, retries + 1):
            if attempt > 1:
                time.sleep(retry_delay * (2 ** (attempt - 1)))
            self._reopen(name)
            health = self.check(name)
            if health.ok:
                health.message = f"recovered on attempt {attempt}"
                return health
        health.message = f"recovery exhausted after {retries} attempts"
        return health

    def _reopen(self, name: str) -> None:
        path = self._db_path(name)
        if path is None or not path.exists():
            return
        try:
            conn = sqlite3.connect(str(path), timeout=10)
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            finally:
                conn.close()
        except sqlite3.Error:
            pass

    # ------------------------------------------------------------------
    # Quarantine (preserve evidence)
    # ------------------------------------------------------------------

    def quarantine(self, name: str) -> Optional[Path]:
        """Rename a corrupted database to the quarantine dir — never deletes.

        Returns the quarantine path, or None if nothing was quarantined.
        """
        path = self._db_path(name)
        if path is None or not path.exists():
            return None
        self._quarantine_dir.mkdir(parents=True, exist_ok=True)
        import uuid
        dest = self._quarantine_dir / f"{name}-{uuid.uuid4().hex[:8]}{path.suffix}"
        try:
            shutil.move(str(path), str(dest))
            logger.warning("Quarantined corrupted database %s → %s", path, dest)
            return dest
        except OSError as exc:
            logger.error("Quarantine failed for %s: %s", path, exc)
            return None

    def quarantined(self) -> List[Dict[str, Any]]:
        if not self._quarantine_dir.exists():
            return []
        out = []
        for p in sorted(self._quarantine_dir.iterdir()):
            if p.is_file():
                out.append({
                    "path": str(p),
                    "size": p.stat().st_size,
                    "name": p.name,
                })
        return out

    def summary(self) -> Dict[str, Any]:
        return {
            "databases": {
                n: h.to_dict() for n, h in self.check_all().items()
            },
            "quarantined": self.quarantined(),
        }


_db_recovery: Optional[DatabaseRecovery] = None
_db_recovery_lock = threading.Lock()


def get_database_recovery() -> DatabaseRecovery:
    """Return the process-wide DatabaseRecovery singleton."""
    global _db_recovery
    if _db_recovery is None:
        with _db_recovery_lock:
            if _db_recovery is None:
                _db_recovery = DatabaseRecovery()
    return _db_recovery