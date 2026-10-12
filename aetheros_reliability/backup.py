"""Versioned, integrity-checked, atomic, rotated backups.

Builds on the existing ``aetheros_cli.backup`` exclusion/safe-copy rules but
adds the reliability contract every backup must satisfy:

* **versioning** — each backup has backupId, createdAt, schemaVersion,
  appVersion, platform and an integrity manifest (per-file checksums);
* **atomicity** — a backup is written to a temp file, verified, then renamed;
  a partially written backup is never exposed as valid;
* **integrity** — a backup is only "valid" after read + schema + checksum +
  required-file + metadata verification;
* **rotation** — retention honors configuration; the only known valid backup
  is never deleted.

Secrets (``.env``, ``auth.json``) are backed up as-is because restoring them
is required for real recovery, but the manifest marks them ``secret: true``
and the registry never echoes their contents.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import shutil
import sqlite3
import tempfile
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)

BACKUP_SCHEMA_VERSION = 1
MANIFEST_NAME = "reliability-manifest.json"
REQUIRED_FILES = ("config.yaml", "state.db")
_SECRET_FILENAMES = (".env", "auth.json")

#: Registry of backups (index metadata) — lives alongside the archives.
REGISTRY_NAME = "backups.json"


@dataclass
class BackupEntry:
    backup_id: str
    created_at: float
    schema_version: int
    app_version: str
    platform: str
    integrity_ok: bool
    file_count: int
    total_size: int
    path: str
    checksum_sha256: str = ""
    valid: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
            "app_version": self.app_version,
            "platform": self.platform,
            "integrity_ok": self.integrity_ok,
            "valid": self.valid,
            "file_count": self.file_count,
            "total_size": self.total_size,
            "checksum_sha256": self.checksum_sha256,
            "path": self.path,
        }


class BackupIntegrity:
    """Verifies a backup archive's read/schema/checksum/required-files."""

    @staticmethod
    def verify(archive: Path) -> Tuple[bool, Dict[str, Any]]:
        """Return ``(ok, report)``.  A backup is valid only when every check
        passes.  Raises ``FileNotFoundError`` for missing archives."""
        if not archive.exists():
            raise FileNotFoundError(str(archive))
        report: Dict[str, Any] = {"checks": {}}
        if not zipfile.is_zipfile(archive):
            report["checks"]["zip"] = False
            report["ok"] = False
            report["reason"] = "not a zip archive"
            return False, report

        try:
            with zipfile.ZipFile(archive, "r") as zf:
                bad = zf.testzip()
                report["checks"]["zip"] = bad is None
                names = set(zf.namelist())
                report["file_count"] = len(names)

                manifest = None
                if MANIFEST_NAME in names:
                    try:
                        manifest = json.loads(zf.read(MANIFEST_NAME))
                        report["checks"]["manifest"] = True
                    except (json.JSONDecodeError, KeyError):
                        report["checks"]["manifest"] = False
                        report["reason"] = "manifest corrupt"
                        report["ok"] = False
                        return False, report
                else:
                    report["checks"]["manifest"] = False
                    report["reason"] = "missing reliability manifest"
                    report["ok"] = False
                    return False, report

                # schema check
                schema = manifest.get("schema_version", 0)
                report["checks"]["schema"] = schema == BACKUP_SCHEMA_VERSION
                if not report["checks"]["schema"]:
                    report["reason"] = f"unsupported schema {schema}"
                    report["ok"] = False
                    return False, report

                # required files
                missing = [f for f in REQUIRED_FILES if f not in names]
                report["checks"]["required_files"] = not missing
                report["missing"] = missing
                if missing:
                    report["reason"] = f"missing required files: {missing}"
                    report["ok"] = False
                    return False, report

                # per-file checksums (when manifest declares them)
                files = manifest.get("files", {})
                verified = 0
                mismatches = []
                for rel, meta in files.items():
                    checksum = meta.get("sha256") if isinstance(meta, dict) else None
                    if not checksum:
                        continue
                    if rel not in names:
                        mismatches.append(f"{rel}:missing")
                        continue
                    actual = _sha256_bytes(zf.read(rel))
                    if actual != checksum:
                        mismatches.append(f"{rel}:checksum")
                    else:
                        verified += 1
                report["checks"]["checksums"] = not mismatches
                report["checksum_mismatches"] = mismatches
                report["checksums_verified"] = verified

                # metadata
                report["backup_id"] = manifest.get("backup_id")
                report["created_at"] = manifest.get("created_at")
                report["app_version"] = manifest.get("app_version")
                report["platform"] = manifest.get("platform")

                ok = all(report["checks"].values())
                report["ok"] = ok
                if not ok:
                    report["reason"] = "integrity check failed"
                return ok, report
        except (zipfile.BadZipFile, KeyError) as exc:
            report["ok"] = False
            report["reason"] = f"archive error: {exc}"
            return False, report


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()


def _exclude_backup_rule(rel: Path) -> bool:
    """Reuse the existing backup exclusion rules from ``aetheros_cli.backup``."""
    try:
        from aetheros_cli.backup import _should_exclude
        return _should_exclude(rel)
    except Exception:
        return rel.parts and rel.parts[0] in ("backups", "state-snapshots")


class BackupStore:
    """Versioned, atomic, integrity-verified, rotated backup store.

    Usage::

        store = get_backup_store()
        entry = store.create(label="pre-update")
        ok, report = store.verify(entry.backup_id)
        for e in store.list(): ...
        store.prune(keep=5)
    """

    def __init__(self, root: Optional[Path] = None,
                 source: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._root = Path(root) if root else (
            get_aetheros_home() / "reliability" / "backups"
        )
        self._source = Path(source) if source else get_aetheros_home()
        self._registry_path = self._root / REGISTRY_NAME

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(self, label: str = "") -> Optional[BackupEntry]:
        """Create a versioned, atomic backup of the source home.

        Writes to a temp archive, verifies it, then atomically renames into
        place and records it in the registry.  Returns None on failure.
        """
        self._root.mkdir(parents=True, exist_ok=True)
        backup_id = _new_backup_id()
        archive = self._root / f"backup-{backup_id}.zip"
        tmp = self._root / f".backup-{backup_id}.tmp"

        try:
            files = self._collect_files()
            if not files:
                logger.warning("Backup: no files found under %s", self._source)
                return None
            manifest = self._build_manifest(backup_id, label, files)
            ok, report = self._write_archive(tmp, files, manifest)
            if not ok:
                logger.error("Backup write failed: %s", report.get("reason"))
                return None
            # Verify the staged archive BEFORE exposing it.
            vok, vreport = BackupIntegrity.verify(tmp)
            if not vok:
                logger.error("Backup verification failed: %s", vreport.get("reason"))
                tmp.unlink(missing_ok=True)
                return None
            os.replace(tmp, archive)
        except (OSError, sqlite3.Error) as exc:
            logger.error("Backup failed: %s", exc)
            tmp.unlink(missing_ok=True)
            return None

        entry = BackupEntry(
            backup_id=backup_id,
            created_at=manifest["created_at"],
            schema_version=manifest["schema_version"],
            app_version=manifest["app_version"],
            platform=manifest["platform"],
            integrity_ok=True,
            file_count=manifest["file_count"],
            total_size=manifest["total_size"],
            checksum_sha256=_sha256_file(archive),
            path=str(archive),
            metadata={"label": label},
        )
        self._record(entry)
        return entry

    # ------------------------------------------------------------------
    # Listing / registry
    # ------------------------------------------------------------------

    def list(self) -> List[BackupEntry]:
        """List backups (registry order, newest first).  Lazily verifies the
        ``valid`` flag for display but never blocks on full checksums."""
        with self._lock:
            entries = self._load_registry()
        out = []
        for e in sorted(entries, key=lambda x: x.created_at, reverse=True):
            path = Path(e.path)
            if not path.exists():
                e.valid = False
                e.integrity_ok = False
            out.append(e)
        return out

    def get(self, backup_id: str) -> Optional[BackupEntry]:
        for e in self.list():
            if e.backup_id == backup_id:
                return e
        return None

    def latest(self) -> Optional[BackupEntry]:
        entries = self.list()
        return entries[0] if entries else None

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------

    def verify(self, backup_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Full integrity verification of a stored backup."""
        entry = self.get(backup_id)
        if entry is None:
            return False, {"reason": "unknown backup id", "checks": {}}
        ok, report = BackupIntegrity.verify(Path(entry.path))
        report["backup_id"] = backup_id
        return ok, report

    def verify_all(self) -> Dict[str, Any]:
        results = {}
        for entry in self.list():
            if entry.valid:
                ok, _ = self.verify(entry.backup_id)
            else:
                ok = False
            results[entry.backup_id] = ok
        return results

    # ------------------------------------------------------------------
    # Rotation
    # ------------------------------------------------------------------

    def prune(self, keep: int = 5) -> List[str]:
        """Delete oldest backups beyond *keep*.

        Never deletes the ONLY valid backup: if every candidate for removal
        is the sole intact archive, pruning is skipped.
        """
        if keep < 1:
            keep = 1
        entries = self.list()
        valid = [e for e in entries if e.valid and e.integrity_ok]
        removed = []
        for e in entries[keep:]:
            if e in valid and len(valid) == 1:
                logger.warning("Refusing to delete the only valid backup %s", e.backup_id)
                continue
            try:
                Path(e.path).unlink(missing_ok=True)
                removed.append(e.backup_id)
            except OSError as exc:
                logger.warning("Failed to prune backup %s: %s", e.backup_id, exc)
        if removed:
            self._drop_from_registry(removed)
        return removed

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _collect_files(self) -> List[Tuple[Path, Path]]:
        """Collect (abs_path, rel_path) honoring existing exclusion rules."""
        files: List[Tuple[Path, Path]] = []
        if not self._source.is_dir():
            return files
        for dirpath, dirnames, filenames in os.walk(self._source, followlinks=False):
            dp = Path(dirpath)
            dirnames[:] = [
                d for d in dirnames if not _exclude_backup_rule(Path(d))
            ]
            for fname in filenames:
                fpath = dp / fname
                try:
                    rel = fpath.relative_to(self._source)
                except ValueError:
                    continue
                if _exclude_backup_rule(rel):
                    continue
                if fpath.is_symlink():
                    continue
                if fpath.resolve() == self._root.resolve():
                    continue
                files.append((fpath, rel))
        return files

    def _build_manifest(self, backup_id: str, label: str,
                        files: List[Tuple[Path, Path]]) -> Dict[str, Any]:
        manifest: Dict[str, Any] = {
            "backup_id": backup_id,
            "created_at": time.time(),
            "schema_version": BACKUP_SCHEMA_VERSION,
            "app_version": _app_version(),
            "platform": f"{platform.system()}-{platform.machine()}",
            "label": label,
            "file_count": len(files),
            "total_size": 0,
            "source": str(self._source),
            "files": {},
        }
        for abs_path, rel in files:
            rel_s = rel.as_posix()
            manifest["files"][rel_s] = {
                "size": abs_path.stat().st_size,
                "secret": rel_s in _SECRET_FILENAMES,
            }
        return manifest

    def _write_archive(self, out_path: Path,
                       files: List[Tuple[Path, Path]],
                       manifest: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Write the archive.  SQLite DBs are snapshotted safely; file
        checksums are computed over the bytes written to the archive."""
        total = 0
        try:
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED,
                                 compresslevel=6) as zf:
                for abs_path, rel in files:
                    rel_s = rel.as_posix()
                    if abs_path.suffix == ".db":
                        data, corrupt = _safe_db_bytes(abs_path)
                        zf.writestr(rel_s, data)
                        if corrupt:
                            manifest["files"][rel_s]["corrupt"] = True
                    else:
                        zf.write(abs_path, arcname=rel_s)
                        data = abs_path.read_bytes()
                    manifest["files"][rel_s]["sha256"] = _sha256_bytes(data)
                    total += len(data)
                manifest["total_size"] = total
                zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2).encode("utf-8"))
        except OSError as exc:
            return False, {"reason": str(exc)}
        return True, {}

    def _record(self, entry: BackupEntry) -> None:
        with self._lock:
            entries = self._load_registry()
            entries = [e for e in entries if e.backup_id != entry.backup_id]
            entries.append(entry)
            self._save_registry(entries)

    def _load_registry(self) -> List[BackupEntry]:
        if not self._registry_path.exists():
            return []
        try:
            with open(self._registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            out = []
            for item in data if isinstance(data, list) else []:
                try:
                    out.append(BackupEntry(
                        backup_id=item["backup_id"],
                        created_at=item["created_at"],
                        schema_version=item.get("schema_version", 1),
                        app_version=item.get("app_version", ""),
                        platform=item.get("platform", ""),
                        integrity_ok=bool(item.get("integrity_ok", True)),
                        file_count=item.get("file_count", 0),
                        total_size=item.get("total_size", 0),
                        path=item.get("path", ""),
                        checksum_sha256=item.get("checksum_sha256", ""),
                        valid=bool(item.get("valid", True)),
                        metadata=item.get("metadata", {}),
                    ))
                except (KeyError, TypeError):
                    continue
            return out
        except (OSError, json.JSONDecodeError):
            return []

    def _save_registry(self, entries: List[BackupEntry]) -> None:
        payload = [e.to_dict() for e in entries]
        tmp = self._registry_path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.flush()
        os.replace(tmp, self._registry_path)

    def _drop_from_registry(self, backup_ids: List[str]) -> None:
        with self._lock:
            entries = [e for e in self._load_registry() if e.backup_id not in backup_ids]
            self._save_registry(entries)


def _new_backup_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def _app_version() -> str:
    try:
        from aetheros_cli import __version__
        return str(__version__)
    except Exception:
        try:
            from aetheros_production import get_version
            return str(get_version())
        except Exception:
            return "unknown"


def _safe_db_bytes(src: Path) -> Tuple[bytes, bool]:
    """Snapshot a SQLite DB via the backup() API and return its bytes.

    Returns ``(data, corrupt)``.  When the DB cannot be opened (e.g. it is a
    real but corrupt file), the raw bytes are preserved and ``corrupt=True``
    is set so the backup can complete while flagging the corruption —
    evidence is never silently dropped and no single bad DB aborts all
    backups.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        try:
            dst = sqlite3.connect(str(tmp_path))
            try:
                conn.backup(dst)
            finally:
                dst.close()
        finally:
            conn.close()
        return tmp_path.read_bytes(), False
    except sqlite3.Error:
        logger.warning("DB %s could not be snapshotted via SQLite backup; "
                       "preserving raw bytes (corrupt flag set)", src)
        return src.read_bytes(), True
    finally:
        tmp_path.unlink(missing_ok=True)


_store: Optional[BackupStore] = None
_store_lock = threading.Lock()


def get_backup_store() -> BackupStore:
    """Return the process-wide BackupStore singleton."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = BackupStore()
    return _store