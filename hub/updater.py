"""Auto-update manager — check, download, and apply updates with rollback support."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from aetheros_constants import get_aetheros_home
from hub.store import HubStore

logger = logging.getLogger(__name__)


class AutoUpdater:
    def __init__(self, store: Optional[HubStore] = None):
        self.store = store or HubStore()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def check_for_updates(self, category: str = None) -> list[dict]:
        """Check all installed items against the marketplace for newer versions."""
        from hub.marketplace import HubMarketplace
        mp = HubMarketplace(self.store)
        installed = self.store.get_installed(category)
        updates = []
        for item in installed:
            mp_item = mp.get_item(item["id"])
            if mp_item and mp_item.version > item.get("version", "0.0.0"):
                updates.append({
                    "item_id": item["id"],
                    "name": item.get("name", item["id"]),
                    "category": item.get("category", ""),
                    "current_version": item.get("version", "0.0.0"),
                    "available_version": mp_item.version,
                    "changelog": mp_item.changelog[-1].changelog if mp_item.changelog else "",
                })
        return updates

    def apply_update(self, item_id: str, backup_first: bool = True) -> dict:
        """Apply an update with rollback capability."""
        from hub.marketplace import HubMarketplace
        mp = HubMarketplace(self.store)
        item = self.store.get_installed_item(item_id)
        if not item:
            return {"success": False, "error": f"{item_id} not installed"}
        if backup_first:
            from hub.backup import BackupManager
            bm = BackupManager(self.store)
            bm.create_backup(name=f"pre-update-{item_id}")

        mp_item = mp.get_item(item_id)
        if not mp_item:
            return {"success": False, "error": f"{item_id} not found in marketplace"}
        try:
            result = mp.install(item_id)
            if result.get("success"):
                self.store.set_setting(f"update_{item_id}_applied",
                                       datetime.utcnow().isoformat() + "Z")
            return result
        except Exception as e:
            if backup_first:
                self._rollback(item_id)
            return {"success": False, "error": str(e)}

    def _rollback(self, item_id: str) -> dict:
        from hub.backup import BackupManager
        bm = BackupManager(self.store)
        backups = bm.list_backups()
        pre_update = [b for b in backups if f"pre-update-{item_id}" in b.get("name", "")]
        if pre_update:
            return bm.restore(pre_update[0]["id"])
        return {"success": False, "error": "No rollback available"}

    def rollback_update(self, item_id: str) -> dict:
        return self._rollback(item_id)

    def check_all(self) -> list[dict]:
        return self.check_for_updates()

    def start_background_checker(self, interval_hours: int = 24) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._background_loop,
            args=(interval_hours,),
            daemon=True,
        )
        self._thread.start()
        logger.info("Background update checker started (every %dh)", interval_hours)

    def stop_background_checker(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _background_loop(self, interval_hours: int) -> None:
        while self._running:
            try:
                last_check = self.store.get_setting("last_update_check", "")
                if last_check:
                    last = datetime.fromisoformat(last_check.replace("Z", "+00:00"))
                    if datetime.utcnow() - last.replace(tzinfo=None) < timedelta(hours=interval_hours):
                        time.sleep(3600)
                        continue
                updates = self.check_all()
                if updates:
                    logger.info("Background check: %d updates available", len(updates))
                    self.store.set_setting("pending_updates",
                                           json.dumps([u["item_id"] for u in updates]))
                self.store.set_setting("last_update_check",
                                       datetime.utcnow().isoformat() + "Z")
            except Exception as e:
                logger.error("Background update check failed: %s", e)
            time.sleep(interval_hours * 3600)

    def get_pending_updates(self) -> list[dict]:
        pending = self.store.get_setting("pending_updates", "[]")
        try:
            item_ids = json.loads(pending)
            return [u for u in self.check_all()
                    if u["item_id"] in item_ids]
        except (json.JSONDecodeError, TypeError):
            return []

    def apply_all_pending(self) -> list[dict]:
        pending = self.get_pending_updates()
        results = []
        for update in pending:
            result = self.apply_update(update["item_id"])
            results.append(result)
        self.store.set_setting("pending_updates", "[]")
        return results
