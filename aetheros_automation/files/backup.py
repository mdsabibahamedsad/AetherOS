from __future__ import annotations

import json
import logging
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from aetheros_automation.files.operations import FileOperations

logger = logging.getLogger(__name__)


def _backup_root() -> Path:
    root = Path.home() / ".aetheros" / "automation" / "backups"
    root.mkdir(parents=True, exist_ok=True)
    return root


class BackupManager:
    """Create, list, restore, and schedule file backups."""

    @staticmethod
    async def create_backup(
        paths: list[str], backup_name: str | None = None
    ) -> str:
        root = _backup_root()
        backup_id = uuid.uuid4().hex[:12]
        name = backup_name or f"backup-{backup_id}"
        dest = root / name
        dest.mkdir(parents=True, exist_ok=True)

        manifest: list[dict[str, Any]] = []
        for p in paths:
            src = Path(p).resolve()
            if not src.exists():
                logger.warning("backup: path not found, skipping %s", src)
                continue
            rel = src.name
            dst = dest / rel
            if src.is_dir():
                shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
            else:
                shutil.copy2(str(src), str(dst))
            manifest.append({
                "source": str(src),
                "destination": str(dst),
                "is_dir": src.is_dir(),
                "size": src.stat().st_size if src.is_file() else 0,
            })

        meta = {
            "id": backup_id,
            "name": name,
            "created_at": time.time(),
            "paths": paths,
            "manifest": manifest,
            "file_count": len(manifest),
        }
        (dest / "backup_meta.json").write_text(json.dumps(meta, indent=2))
        logger.info("Backup created: %s (%d files)", name, len(manifest))
        return backup_id

    @staticmethod
    async def list_backups() -> list[dict[str, Any]]:
        root = _backup_root()
        backups: list[dict[str, Any]] = []
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            meta_file = entry / "backup_meta.json"
            if meta_file.is_file():
                data = json.loads(meta_file.read_text())
                backups.append(data)
            else:
                backups.append({
                    "id": entry.name,
                    "name": entry.name,
                    "created_at": entry.stat().st_mtime,
                    "paths": [],
                    "file_count": 0,
                })
        return sorted(backups, key=lambda b: b["created_at"], reverse=True)

    @staticmethod
    async def restore_backup(
        backup_id: str, target_path: str | None = None
    ) -> None:
        root = _backup_root()
        candidates = list(root.glob(f"{backup_id}*")) + [
            d for d in root.iterdir() if d.is_dir() and d.name == backup_id
        ]
        if not candidates:
            raise FileNotFoundError(f"Backup not found: {backup_id}")
        backup_dir = candidates[0]
        meta_file = backup_dir / "backup_meta.json"
        if not meta_file.is_file():
            raise FileNotFoundError(f"Backup metadata missing: {backup_id}")

        meta = json.loads(meta_file.read_text())
        for item in meta.get("manifest", []):
            src = Path(item["destination"])
            if not src.exists():
                logger.warning("restore: missing file %s, skipping", src)
                continue
            dst = Path(target_path) / src.name if target_path else Path(item["source"])
            dst.parent.mkdir(parents=True, exist_ok=True)
            if item["is_dir"]:
                if dst.exists():
                    shutil.rmtree(str(dst))
                shutil.copytree(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))
            logger.debug("restored %s -> %s", src, dst)

        logger.info("Backup %s restored to %s", backup_id, target_path or "original locations")

    @staticmethod
    async def schedule_backup(
        paths: list[str],
        interval: str = "daily",
        max_backups: int = 10,
    ) -> None:
        """Store a backup schedule as a config file for the scheduler to pick up."""
        root = _backup_root()
        schedule_file = root / "schedule.json"
        schedules: list[dict[str, Any]] = []
        if schedule_file.exists():
            schedules = json.loads(schedule_file.read_text())

        entry = {
            "id": uuid.uuid4().hex[:12],
            "paths": paths,
            "interval": interval,
            "max_backups": max_backups,
            "created_at": time.time(),
        }
        schedules.append(entry)
        schedule_file.write_text(json.dumps(schedules, indent=2))
        logger.info("Backup scheduled: %s on %s (max %d)", entry["id"], interval, max_backups)

        # Enforce max_backups by pruning oldest
        existing = await BackupManager.list_backups()
        to_prune = len(existing) - max_backups
        if to_prune > 0:
            for old in reversed(existing[-to_prune:]):
                old_dir = root / old.get("name", old["id"])
                if old_dir.exists():
                    shutil.rmtree(str(old_dir))
                    logger.info("Pruned old backup %s", old.get("name", old["id"]))
