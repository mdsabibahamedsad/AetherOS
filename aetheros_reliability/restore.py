"""RecoveryManager — safe, previewed, verifiable restore.

Restore flow (never silent):

    1. preview      — show what will change, what will be restored, what may
                      be lost, backup timestamp/version
    2. snapshot     — create a safety snapshot of CURRENT state first
    3. restore      — extract the selected backup (config / state / full)
    4. verify       — health + integrity of the restored system
    5. rollback     — on verification failure, restore the safety snapshot

The manager NEVER overwrites state without an explicit call; the CLI wraps
it in a confirmation prompt.  Restore is destructive — it is deliberately
NOT part of autonomous self-healing.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aetheros_constants import get_aetheros_home, display_aetheros_home

from aetheros_reliability.backup import BackupIntegrity, BackupStore, get_backup_store

logger = logging.getLogger(__name__)

SCOPE_CONFIG = "config"
SCOPE_STATE = "state"
SCOPE_FULL = "full"

#: Scope → relative paths under the backup archive.
_SCOPE_FILES = {
    SCOPE_CONFIG: ("config.yaml",),
    SCOPE_STATE: (
        "config.yaml", "state.db", "auth.json", "cron/jobs.json",
        "gateway_state.json", "channel_directory.json", "processes.json",
    ),
    SCOPE_FULL: None,  # everything
}

_SECRET_RESTORE_FILES = (".env", "auth.json")


@dataclass
class RestorePreview:
    backup_id: str
    created_at: float
    app_version: str
    schema_version: int
    files_in_backup: int
    files_to_restore: int
    will_overwrite: List[str]
    may_be_lost: List[str]
    scope: str
    valid: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "created_at": self.created_at,
            "app_version": self.app_version,
            "schema_version": self.schema_version,
            "files_in_backup": self.files_in_backup,
            "files_to_restore": self.files_to_restore,
            "will_overwrite": self.will_overwrite[:100],
            "may_be_lost": self.may_be_lost[:100],
            "scope": self.scope,
            "valid": self.valid,
        }


class RecoveryManager:
    """Preview + snapshot + restore + verify + rollback for backups.

    Usage::

        rm = get_recovery_manager()
        preview = rm.preview(backup_id, scope="config")
        rm.restore(backup_id, scope="config", snapshot=True)
    """

    def __init__(self, store: Optional[BackupStore] = None,
                 target: Optional[Path] = None) -> None:
        self._store = store or get_backup_store()
        self._target = Path(target) if target else get_aetheros_home()
        self._snapshot_dir = self._target / "reliability" / "restore-snapshots"

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def preview(self, backup_id: str, scope: str = SCOPE_FULL) -> RestorePreview:
        """Compute what a restore would change — never mutates anything."""
        entry = self._store.get(backup_id)
        if entry is None:
            raise ValueError(f"unknown backup id: {backup_id}")
        ok, _ = self._store.verify(backup_id)
        if not ok:
            raise ValueError(f"backup {backup_id} failed integrity verification")
        archive = Path(entry.path)
        target_files = _scope_files(scope)

        will_overwrite: List[str] = []
        may_be_lost: List[str] = []
        with zipfile.ZipFile(archive, "r") as zf:
            names = zf.namelist()
            selected = names if target_files is None else [
                n for n in names if _matches_scope(n, target_files)
            ]
            for rel in selected:
                local = self._target / rel
                if local.exists():
                    will_overwrite.append(rel)
            for rel in will_overwrite:
                if rel not in selected:
                    may_be_lost.append(rel)
        return RestorePreview(
            backup_id=backup_id,
            created_at=entry.created_at,
            app_version=entry.app_version,
            schema_version=entry.schema_version,
            files_in_backup=entry.file_count,
            files_to_restore=len(selected),
            will_overwrite=will_overwrite,
            may_be_lost=may_be_lost,
            scope=scope,
            valid=True,
        )

    # ------------------------------------------------------------------
    # Snapshot before restore
    # ------------------------------------------------------------------

    def create_restore_snapshot(self) -> str:
        """Snapshot current state so a failed restore can roll back."""
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)
        import time
        snap_id = time.strftime("%Y%m%d-%H%M%S")
        dest = self._snapshot_dir / snap_id
        dest.mkdir(parents=True, exist_ok=True)
        restored = 0
        for rel in _scope_files(SCOPE_STATE):
            src = self._target / rel
            if not src.exists():
                continue
            dst = dest / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                restored += 1
            except (OSError, PermissionError) as exc:
                logger.warning("restore snapshot failed for %s: %s", rel, exc)
        with open(dest / "snapshot.json", "w", encoding="utf-8") as f:
            json.dump({"id": snap_id, "files": _scope_files(SCOPE_STATE),
                       "restored": restored}, f, indent=2)
        return snap_id

    def list_snapshots(self) -> List[str]:
        if not self._snapshot_dir.exists():
            return []
        return sorted(
            (p.name for p in self._snapshot_dir.iterdir() if p.is_dir()),
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Restore
    # ------------------------------------------------------------------

    def restore(self, backup_id: str, *, scope: str = SCOPE_FULL,
                snapshot: bool = True) -> Dict[str, Any]:
        """Restore *backup_id* at *scope*.

        Returns ``{restored, files, snapshot, verified, error}``.  When a
        snapshot is taken first and verification fails, the snapshot is
        rolled back automatically.
        """
        entry = self._store.get(backup_id)
        if entry is None:
            return {"restored": False, "error": f"unknown backup id: {backup_id}"}
        ok, report = self._store.verify(backup_id)
        if not ok:
            return {"restored": False, "error": report.get("reason", "integrity failed")}

        snap_id = None
        if snapshot:
            snap_id = self.create_restore_snapshot()

        archive = Path(entry.path)
        target_files = _scope_files(scope)
        restored_files = []
        errors = []
        try:
            with zipfile.ZipFile(archive, "r") as zf:
                names = zf.namelist()
                selected = names if target_files is None else [
                    n for n in names if _matches_scope(n, target_files)
                ]
                for rel in selected:
                    target = self._target / rel
                    # Security: reject absolute paths and traversals.
                    try:
                        target.resolve().relative_to(self._target.resolve())
                    except ValueError:
                        errors.append(f"{rel}: path traversal blocked")
                        continue
                    try:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(rel) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        if target.name in _SECRET_RESTORE_FILES:
                            try:
                                os.chmod(target, 0o600)
                            except OSError:
                                pass
                        restored_files.append(rel)
                    except (OSError, PermissionError) as exc:
                        errors.append(f"{rel}: {exc}")
        except zipfile.BadZipFile as exc:
            return {"restored": False, "error": f"bad archive: {exc}",
                    "snapshot": snap_id}

        # Verification + rollback on failure.
        verified = self._verify_restore(scope, restored_files)
        if not verified:
            if snap_id:
                self.rollback(snap_id)
            return {
                "restored": False,
                "verified": False,
                "error": "restore verification failed; rolled back to safety snapshot",
                "files": restored_files,
                "snapshot": snap_id,
            }
        return {
            "restored": True,
            "verified": True,
            "files": restored_files,
            "file_count": len(restored_files),
            "snapshot": snap_id,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def rollback(self, snapshot_id: str) -> int:
        """Restore files from a safety snapshot.  Returns count restored."""
        snap = self._snapshot_dir / snapshot_id
        if not snap.is_dir():
            raise ValueError(f"unknown snapshot: {snapshot_id}")
        restored = 0
        for rel in _scope_files(SCOPE_STATE):
            src = snap / rel
            if not src.exists():
                continue
            dst = self._target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                restored += 1
            except (OSError, PermissionError) as exc:
                logger.error("rollback failed for %s: %s", rel, exc)
        return restored

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _verify_restore(self, scope: str, restored_files: List[str]) -> bool:
        """Cheap verification: required files present and YAML config parseable."""
        required = _scope_files(scope) or _scope_files(SCOPE_STATE)
        if scope == SCOPE_FULL:
            required = _scope_files(SCOPE_STATE)
        for rel in required:
            path = self._target / rel
            if rel.endswith("/") or rel.endswith("\\"):
                continue
            if not path.exists():
                logger.warning("restore verify: missing %s", rel)
                return False
        config_path = self._target / "config.yaml"
        if config_path.exists():
            try:
                import yaml
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    logger.warning("restore verify: config.yaml not a mapping")
                    return False
            except Exception:
                logger.warning("restore verify: config.yaml unparseable")
                return False
        return True

    def summary(self) -> Dict[str, Any]:
        return {
            "target": display_aetheros_home(),
            "snapshots": self.list_snapshots(),
            "backup_count": len(self._store.list()),
        }


def _scope_files(scope: str) -> Optional[Tuple[str, ...]]:
    if scope == SCOPE_FULL:
        return None
    return _SCOPE_FILES.get(scope, _SCOPE_FILES[SCOPE_STATE])


def _matches_scope(rel: str, scope_files: Tuple[str, ...]) -> bool:
    rel = rel.replace("\\", "/")
    for pattern in scope_files:
        pattern = pattern.replace("\\", "/")
        if rel == pattern or rel.startswith(pattern + "/"):
            return True
    return False


_manager: Optional[RecoveryManager] = None
_manager_lock = threading.Lock()


def get_recovery_manager() -> RecoveryManager:
    """Return the process-wide RecoveryManager singleton."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = RecoveryManager()
    return _manager