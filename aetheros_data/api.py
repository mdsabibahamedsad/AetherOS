"""Typed API surface for storage/backup/restore/sync/recovery (section 108).

Every operation returns a dict with ok/result or raises a typed error;
mutating operations append audit entries and support cancellation via the
``cancelled`` callback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_data import engine as _engine_mod
from aetheros_data.engine import StorageEngine


def _eng(db_path: Optional[Path] = None) -> StorageEngine:
    if db_path is not None:
        return StorageEngine(db_path=db_path)
    return _engine_mod.get_engine()


def storage_status(db_path: Optional[Path] = None) -> Dict[str, Any]:
    e = _eng(db_path)
    from aetheros_data.services import startup_health_check, METRICS
    health = startup_health_check(e)
    return {"ok": True, "stats": e.stats(), "health": health,
            "metrics": METRICS.snapshot()}


def backup_create(scope: str = "critical", kind: str = "FULL",
                  include_secrets: bool = False,
                  encryption_key: Optional[bytes] = None,
                  db_path: Optional[Path] = None) -> Dict[str, Any]:
    from aetheros_data.backup import BackupManager
    e = _eng(db_path)
    r = BackupManager(e).create(scope=scope, kind=kind,
                                include_secrets=include_secrets,
                                encryption_key=encryption_key)
    return {"ok": True, "backup_id": r.backup_id, "path": r.path,
            "content_hash": r.content_hash, "size": r.size, "files": r.files,
            "encryption": r.encryption}


def backup_list(db_path: Optional[Path] = None) -> Dict[str, Any]:
    from aetheros_data.backup import BackupManager
    return {"ok": True, "backups": BackupManager(_eng(db_path)).list()}


def backup_verify(backup_id: str, encryption_key: Optional[bytes] = None,
                  db_path: Optional[Path] = None) -> Dict[str, Any]:
    from aetheros_data.backup import BackupManager
    return BackupManager(_eng(db_path)).verify(backup_id, encryption_key)


def backup_restore(backup_id: str, mode: str = "FULL_RESTORE",
                   domains: Optional[List[str]] = None,
                   encryption_key: Optional[bytes] = None,
                   assume_yes: bool = False,
                   db_path: Optional[Path] = None) -> Dict[str, Any]:
    from aetheros_data.restore import RestoreManager
    return RestoreManager(_eng(db_path)).restore(
        backup_id, mode=mode, domains=domains,
        encryption_key=encryption_key, assume_yes=assume_yes)


def recovery_status(db_path: Optional[Path] = None) -> Dict[str, Any]:
    from aetheros_data.recovery import CrashRecoveryManager
    return {"ok": True, "recovery": CrashRecoveryManager(_eng(db_path)).startup_scan()}


def sync_status(db_path: Optional[Path] = None) -> Dict[str, Any]:
    from aetheros_data.sync import SyncEngine
    return {"ok": True, "sync": SyncEngine(_eng(db_path)).status()}


def integrity_check(db_path: Optional[Path] = None) -> Dict[str, Any]:
    from aetheros_data.services import ConsistencyChecker
    e = _eng(db_path)
    return {"ok": True, "pragma": e.integrity_check(),
            "consistency": ConsistencyChecker(e).check()}


def data_export(dest: str, scope: str = "user",
                db_path: Optional[Path] = None) -> Dict[str, Any]:
    from aetheros_data.portability import PortabilityManager
    return {"ok": True, **PortabilityManager(_eng(db_path)).export(Path(dest), scope=scope)}


def data_import(path: str, actor: str = "", authorize: bool = False,
                db_path: Optional[Path] = None) -> Dict[str, Any]:
    from aetheros_data.portability import PortabilityManager
    return PortabilityManager(_eng(db_path)).import_data(Path(path), actor=actor,
                                                         authorize=authorize)
