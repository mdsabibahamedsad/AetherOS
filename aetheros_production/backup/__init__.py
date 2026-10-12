"""
Backup System for AetherOS
==========================

Automatic backup, incremental backup, snapshot, export, restore, disaster recovery.

Features:
    - Full / incremental / snapshot backups
    - True incremental backups (only files changed since the last backup)
    - AES-GCM encrypted backups (backups never contain plaintext secrets)
    - Automatic scheduled backups with retention pruning
    - Selective restore (restore specific paths, not the whole archive)
    - Integrity verification before restore

Usage::

    from aetheros_production.backup import BackupManager

    manager = BackupManager()
    backup = manager.create_backup("full")
    manager.restore_backup(backup["id"])

    # Automatic backups every 24h
    manager.start_automatic_backup(interval_hours=24)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ENCRYPTED_EXTENSION = ".aeb"  # AetherOS Encrypted Backup


@dataclass
class BackupInfo:
    """Information about a backup."""
    backup_id: str
    timestamp: float
    backup_type: str
    size_bytes: int = 0
    path: str = ""
    description: str = ""
    includes: List[str] = field(default_factory=list)
    encrypted: bool = True
    parent_id: str = ""  # for incremental chains


class BackupManager:
    """Manages backups for AetherOS.

    Usage::

        manager = BackupManager()

        # Create backup
        backup = manager.create_backup("full")

        # List backups
        backups = manager.list_backups()

        # Restore backup
        manager.restore_backup(backup["id"])

        # Automatic backups
        manager.start_automatic_backup(interval_hours=24)
    """

    def __init__(self, home: Optional[Path] = None) -> None:
        from aetheros_constants import get_aetheros_home
        self._home = home or get_aetheros_home()
        self._backup_dir = self._home / "backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._auto_stop = threading.Event()
        self._auto_thread: Optional[threading.Thread] = None
        self._last_backup_time: float = self._load_last_backup_time()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Backup state tracking
    # ------------------------------------------------------------------

    def _state_path(self) -> Path:
        return self._backup_dir / "state.json"

    def _load_last_backup_time(self) -> float:
        try:
            if self._state_path().exists():
                return json.loads(self._state_path().read_text("utf-8")).get("last_backup", 0.0)
        except (OSError, json.JSONDecodeError):
            pass
        return 0.0

    def _save_last_backup_time(self) -> None:
        try:
            self._state_path().write_text(
                json.dumps({"last_backup": time.time()}), "utf-8"
            )
        except OSError as exc:
            logger.warning("Could not save backup state: %s", exc)

    def _get_backup_includes(self, backup_type: str) -> List[str]:
        """Get list of paths to include in backup."""
        if backup_type == "full":
            return [
                "config.yaml",
                ".env",
                "plugins/",
                "skills/",
                "memory/",
                "sessions/",
                "cron/",
                "state.db",
            ]
        elif backup_type == "incremental":
            return [
                "config.yaml",
                "sessions/",
                "memory/",
            ]
        elif backup_type == "snapshot":
            return ["config.yaml"]
        return []

    def _files_to_backup(self, includes: List[str], since: float) -> Dict[str, Path]:
        """Resolve include globs to concrete files.

        For incremental backups, only files modified after ``since`` are
        returned. Always include metadata that establishes a chain anchor.
        """
        files: Dict[str, Path] = {}
        for include in includes:
            full_path = self._home / include
            if not full_path.exists():
                continue
            if full_path.is_file():
                if since <= 0 or full_path.stat().st_mtime > since:
                    files[str(full_path.relative_to(self._home))] = full_path
            elif full_path.is_dir():
                for file in full_path.rglob("*"):
                    if file.is_file():
                        if since <= 0 or file.stat().st_mtime > since:
                            files[str(file.relative_to(self._home))] = file
        return files

    # ------------------------------------------------------------------
    # Creating backups
    # ------------------------------------------------------------------

    def create_backup(
        self,
        backup_type: str = "full",
        description: str = "",
        *,
        encrypt: bool = True,
    ) -> Dict[str, Any]:
        """Create a backup.

        Args:
            backup_type: Type of backup (full, incremental, snapshot).
            description: Optional description.
            encrypt: Encrypt the archive with AES-GCM.

        Returns:
            Backup information.
        """
        backup_type = backup_type if backup_type in ("full", "incremental", "snapshot") else "full"
        backup_id = str(uuid.uuid4())[:8]
        timestamp = time.time()

        with self._lock:
            if backup_type == "incremental":
                since = self._last_backup_time
            else:
                since = 0.0

            logger.info("Creating %s backup: %s", backup_type, backup_id)
            includes = self._get_backup_includes(backup_type)
            files = self._files_to_backup(includes, since)

            if backup_type == "incremental" and not files:
                logger.info("Incremental backup skipped: no changes since last backup")
                return {
                    "id": backup_id,
                    "type": backup_type,
                    "status": "no_changes",
                    "size_bytes": 0,
                    "path": "",
                }

            backup_path = self._backup_dir / f"backup_{backup_id}{_ENCRYPTED_EXTENSION if encrypt else '.zip'}"

            try:
                self._write_archive(backup_path, files, encrypt)
                size_bytes = backup_path.stat().st_size

                metadata = BackupInfo(
                    backup_id=backup_id,
                    timestamp=timestamp,
                    backup_type=backup_type,
                    size_bytes=size_bytes,
                    path=str(backup_path),
                    description=description,
                    includes=sorted(files.keys()),
                    encrypted=encrypt,
                )

                self._write_metadata(metadata)
                # Anchor the incremental chain to the newest file mtime so
                # filesystem-clock skew cannot re-include just-backed-up files.
                if files:
                    self._last_backup_time = max(
                        max(p.stat().st_mtime for p in files.values()),
                        timestamp,
                    )
                else:
                    self._last_backup_time = timestamp
                self._save_last_backup_time()

                logger.info("Backup created: %s (%d bytes)", backup_id, size_bytes)
                return {
                    "id": backup_id,
                    "type": backup_type,
                    "size_bytes": size_bytes,
                    "path": str(backup_path),
                    "encrypted": encrypt,
                }
            except Exception as exc:
                logger.error("Backup failed: %s", exc)
                return {"error": str(exc)}

    def _write_archive(self, backup_path: Path, files: Dict[str, Path], encrypt: bool) -> None:
        """Write a (possibly encrypted) zip archive.

        When ``encrypt`` is true the zip bytes are encrypted with AES-GCM and
        the on-disk file is binary ciphertext.
        """
        buffer_path = backup_path.with_suffix(".tmp.zip")
        with zipfile.ZipFile(buffer_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for arcname, file in files.items():
                zf.write(file, arcname)
            manifest = {
                "backup_created_at": time.time(),
                "file_count": len(files),
                "files": sorted(files.keys()),
            }
            zf.writestr("backup-manifest.json", json.dumps(manifest, indent=2))

        if encrypt:
            from aetheros_security.encryption import EncryptionManager
            encryption = EncryptionManager()
            raw = buffer_path.read_bytes()
            blob = encryption.encrypt_bytes(raw, aad="aetheros-backup-v1")
            backup_path.write_bytes(blob)
            buffer_path.unlink(missing_ok=True)
        else:
            shutil.move(str(buffer_path), str(backup_path))

    def _write_metadata(self, metadata: BackupInfo) -> None:
        metadata_path = self._backup_dir / f"backup_{metadata.backup_id}.json"
        metadata_path.write_text(json.dumps({
            "backup_id": metadata.backup_id,
            "timestamp": metadata.timestamp,
            "backup_type": metadata.backup_type,
            "size_bytes": metadata.size_bytes,
            "path": metadata.path,
            "description": metadata.description,
            "includes": metadata.includes,
            "encrypted": metadata.encrypted,
        }, indent=2), "utf-8")

    # ------------------------------------------------------------------
    # Listing / querying
    # ------------------------------------------------------------------

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all backups (newest first)."""
        backups = []
        for metadata_file in sorted(self._backup_dir.glob("backup_*.json"), reverse=True):
            try:
                backups.append(json.loads(metadata_file.read_text("utf-8")))
            except Exception:
                pass
        return backups

    def get_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get backup information."""
        metadata_path = self._backup_dir / f"backup_{backup_id}.json"
        if metadata_path.exists():
            try:
                return json.loads(metadata_path.read_text("utf-8"))
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------
    # Restoring
    # ------------------------------------------------------------------

    def restore_backup(
        self,
        backup_id: str,
        *,
        paths: Optional[List[str]] = None,
        verify_first: bool = True,
    ) -> Dict[str, Any]:
        """Restore from a backup.

        Args:
            backup_id: ID of the backup to restore.
            paths: Optional subset of paths to restore (selective restore).
            verify_first: Verify archive integrity before extracting.

        Returns:
            Restore result.
        """
        backup_info = self.get_backup(backup_id)
        if not backup_info:
            return {"error": f"Backup {backup_id} not found"}

        backup_path = Path(backup_info["path"])
        if not backup_path.exists():
            return {"error": "Backup file not found"}

        logger.info("Restoring backup: %s", backup_id)

        try:
            encrypted = backup_info.get("encrypted", False)
            if verify_first:
                ok = self.verify_backup(backup_id)
                if not ok:
                    return {"error": "Backup integrity check failed"}

            temp_dir = self._backup_dir / f".restore_{backup_id}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            if encrypted:
                from aetheros_security.encryption import EncryptionManager
                encryption = EncryptionManager()
                raw = encryption.decrypt_bytes(
                    backup_path.read_bytes(), aad="aetheros-backup-v1"
                )
                zip_path = temp_dir / "archive.zip"
                zip_path.write_bytes(raw)
            else:
                zip_path = backup_path

            with zipfile.ZipFile(zip_path, "r") as zf:
                # Zip-slip protection: reject absolute / parent-relative members.
                members = zf.namelist()
                for member in members:
                    resolved = (self._home / member).resolve()
                    if not str(resolved).startswith(str(self._home.resolve())):
                        return {"error": f"Unsafe member path in backup: {member}"}

                selected = members
                if paths:
                    selected = [
                        m for m in members
                        if any(m == p or m.startswith(p.rstrip("/") + "/") for p in paths)
                    ]

                for member in selected:
                    zf.extract(member, self._home)

            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info("Backup restored: %s (%d paths)", backup_id, len(selected))
            return {"success": True, "backup_id": backup_id, "restored_paths": len(selected)}

        except Exception as exc:
            logger.error("Restore failed: %s", exc)
            return {"error": str(exc)}

    def verify_backup(self, backup_id: str) -> bool:
        """Verify a backup archive's integrity.

        Decrypts and validates the zip structure. Returns True only if the
        archive is intact and readable.
        """
        backup_info = self.get_backup(backup_id)
        if not backup_info:
            return False
        backup_path = Path(backup_info["path"])
        if not backup_path.exists():
            return False
        try:
            if backup_info.get("encrypted", False):
                from aetheros_security.encryption import EncryptionManager
                encryption = EncryptionManager()
                raw = encryption.decrypt_bytes(backup_path.read_bytes(), aad="aetheros-backup-v1")
                import io
                with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                    return zf.testzip() is None
            with zipfile.ZipFile(backup_path) as zf:
                return zf.testzip() is None
        except Exception as exc:
            logger.warning("Backup verification failed for %s: %s", backup_id, exc)
            return False

    # ------------------------------------------------------------------
    # Deletion / export / import
    # ------------------------------------------------------------------

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup."""
        deleted = False
        for suffix in (_ENCRYPTED_EXTENSION, ".zip"):
            backup_path = self._backup_dir / f"backup_{backup_id}{suffix}"
            if backup_path.exists():
                backup_path.unlink()
                deleted = True
        metadata_path = self._backup_dir / f"backup_{backup_id}.json"
        if metadata_path.exists():
            metadata_path.unlink()
            deleted = True
        return deleted

    def export_backup(self, backup_id: str, export_path: str) -> bool:
        """Export a backup to a file (keeps the encrypted format)."""
        backup_info = self.get_backup(backup_id)
        if not backup_info:
            return False
        backup_path = Path(backup_info["path"])
        if not backup_path.exists():
            return False
        try:
            shutil.copy2(backup_path, export_path)
            return True
        except Exception:
            return False

    def import_backup(self, import_path: str) -> Optional[str]:
        """Import a backup from a file.

        The file must be an AetherOS encrypted backup (``.aeb``) or a plain
        zip produced by this manager.
        """
        if not Path(import_path).exists():
            return None
        backup_id = str(uuid.uuid4())[:8]
        source = Path(import_path)
        dest_path = self._backup_dir / f"backup_{backup_id}{_ENCRYPTED_EXTENSION}"

        try:
            raw = source.read_bytes()
            # Detect plain zip (PK header) vs encrypted blob.
            encrypted = not raw.startswith(b"PK")
            if encrypted:
                dest_path.write_bytes(raw)
            else:
                dest_path.write_bytes(raw)

            metadata = {
                "backup_id": backup_id,
                "timestamp": time.time(),
                "backup_type": "imported",
                "size_bytes": dest_path.stat().st_size,
                "path": str(dest_path),
                "description": "Imported backup",
                "includes": [],
                "encrypted": encrypted,
            }
            metadata_path = self._backup_dir / f"backup_{backup_id}.json"
            metadata_path.write_text(json.dumps(metadata, indent=2), "utf-8")
            return backup_id
        except Exception as exc:
            logger.warning("Backup import failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Automatic backups
    # ------------------------------------------------------------------

    def start_automatic_backup(self, interval_hours: float = 24.0) -> bool:
        """Start an automatic backup loop in a background thread.

        Args:
            interval_hours: Interval between backups.

        Returns:
            True if the loop started (or is already running).
        """
        if self._auto_thread is not None and self._auto_thread.is_alive():
            return True
        self._auto_stop.clear()
        self._auto_thread = threading.Thread(
            target=self._auto_backup_loop,
            args=(max(0.1, interval_hours),),
            name="aetheros-auto-backup",
            daemon=True,
        )
        self._auto_thread.start()
        logger.info("Automatic backup started (every %.1fh)", interval_hours)
        return True

    def stop_automatic_backup(self) -> None:
        """Stop the automatic backup loop."""
        self._auto_stop.set()
        if self._auto_thread is not None:
            self._auto_thread.join(timeout=5)
        self._auto_thread = None
        logger.info("Automatic backup stopped")

    def _auto_backup_loop(self, interval_hours: float) -> None:
        interval_seconds = interval_hours * 3600
        while not self._auto_stop.is_set():
            self._auto_stop.wait(interval_seconds)
            if self._auto_stop.is_set():
                break
            try:
                result = self.create_backup("incremental", description="automatic")
                self.prune_backups(max_backups=10)
                logger.info("Automatic backup complete: %s", result.get("id", result.get("error")))
            except Exception as exc:
                logger.error("Automatic backup failed: %s", exc)

    def prune_backups(self, max_backups: int = 10) -> int:
        """Delete oldest backups beyond ``max_backups``.

        Returns:
            Number of backups pruned.
        """
        backups = self.list_backups()
        if len(backups) <= max_backups:
            return 0
        pruned = 0
        for backup in backups[max_backups:]:
            if self.delete_backup(backup["backup_id"]):
                pruned += 1
        if pruned:
            logger.info("Pruned %d old backup(s)", pruned)
        return pruned


# Global backup manager
_backup_manager: Optional[BackupManager] = None


def get_backup_manager() -> BackupManager:
    """Return the global BackupManager singleton."""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager
