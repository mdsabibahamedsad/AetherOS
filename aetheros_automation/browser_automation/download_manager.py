from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Download:
    id: str
    url: str
    filename: str
    destination: str
    total_size: int = 0
    downloaded_size: int = 0
    status: str = "pending"
    mime_type: str = ""
    source_url: str = ""
    error_message: str = ""
    created_at: str = ""
    completed_at: str = ""
    security_scan_status: str = "pending"


class DownloadManager:
    def __init__(self):
        self._downloads: dict[str, Download] = {}
        self._path = get_aetheros_home() / "automation" / "downloads.json"
        self._load()

    def _load(self):
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for d in data:
                    dl = Download(**d)
                    self._downloads[dl.id] = dl
        except Exception as e:
            logger.warning("Failed to load downloads: %s", e)

    def _save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(d) for d in self._downloads.values()]
            self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save downloads: %s", e)

    def add_download(
        self, url: str, filename: str, destination: str, mime_type: str = "", source_url: str = ""
    ) -> Download:
        dl = Download(
            id=str(uuid.uuid4()),
            url=url,
            filename=filename,
            destination=destination,
            mime_type=mime_type,
            source_url=source_url or url,
            status="pending",
            created_at=datetime.utcnow().isoformat(),
        )
        self._downloads[dl.id] = dl
        self._save()
        return dl

    def update_progress(self, download_id: str, downloaded_size: int, total_size: int = 0):
        dl = self._downloads.get(download_id)
        if dl is None:
            return
        dl.downloaded_size = downloaded_size
        if total_size:
            dl.total_size = total_size
        dl.status = "downloading"
        self._save()

    def complete_download(self, download_id: str):
        dl = self._downloads.get(download_id)
        if dl is None:
            return
        dl.status = "completed"
        dl.completed_at = datetime.utcnow().isoformat()
        dl.security_scan_status = "completed"
        self._save()

    def fail_download(self, download_id: str, error: str):
        dl = self._downloads.get(download_id)
        if dl is None:
            return
        dl.status = "failed"
        dl.error_message = error
        dl.completed_at = datetime.utcnow().isoformat()
        self._save()

    def cancel_download(self, download_id: str) -> bool:
        dl = self._downloads.get(download_id)
        if dl is None:
            return False
        dl.status = "cancelled"
        dl.completed_at = datetime.utcnow().isoformat()
        self._save()
        return True

    def pause_download(self, download_id: str) -> bool:
        dl = self._downloads.get(download_id)
        if dl is None or dl.status != "downloading":
            return False
        dl.status = "paused"
        self._save()
        return True

    def resume_download(self, download_id: str) -> bool:
        dl = self._downloads.get(download_id)
        if dl is None or dl.status != "paused":
            return False
        dl.status = "pending"
        self._save()
        return True

    def get_download(self, download_id: str) -> Download | None:
        return self._downloads.get(download_id)

    def list_downloads(self, status: str | None = None) -> list[Download]:
        if status:
            return [d for d in self._downloads.values() if d.status == status]
        return list(self._downloads.values())

    def get_active_downloads(self) -> list[Download]:
        return [d for d in self._downloads.values() if d.status in ("pending", "downloading", "paused")]

    def remove_download(self, download_id: str) -> bool:
        if download_id in self._downloads:
            del self._downloads[download_id]
            self._save()
            return True
        return False

    def clear_completed(self):
        self._downloads = {k: v for k, v in self._downloads.items() if v.status != "completed"}
        self._save()

    def set_security_scan(self, download_id: str, status: str):
        dl = self._downloads.get(download_id)
        if dl:
            dl.security_scan_status = status
            self._save()

    def count(self) -> int:
        return len(self._downloads)
