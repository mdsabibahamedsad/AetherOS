"""AetherOS Vision — performance.

Image caching, lazy loading, and batch processing primitives shared across
the vision runtime. Keeps repeated OCR/analysis of the same bytes cheap and
lets callers process many images without blowing memory.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

from aetheros_vision.config import VisionSettings, get_aetheros_dir, load_vision_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


class VisionCache:
    """On-disk cache keyed by content hash with a size limit."""

    def __init__(self, namespace: str = "vision", settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()
        self._dir = get_aetheros_dir(f"{self._settings.cache_dir}/{namespace}")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def _key_path(self, key: str) -> Path:
        return self._dir / f"{key}.bin"

    def get(self, key: str) -> Optional[bytes]:
        with self._lock:
            path = self._key_path(key)
            if path.exists():
                try:
                    self._hits += 1
                    return path.read_bytes()
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Cache read failed: %s", exc)
            self._misses += 1
            return None

    def put(self, key: str, data: bytes) -> None:
        if not self._settings.cache_enabled:
            return
        with self._lock:
            try:
                path = self._key_path(key)
                path.write_bytes(data)
                self._prune()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Cache write failed: %s", exc)

    def cached_bytes(self, path: str, loader: Callable[[], bytes]) -> bytes:
        key = sha256_file(path)
        hit = self.get(key)
        if hit is not None:
            return hit
        data = loader()
        self.put(key, data)
        return data

    def _prune(self) -> None:
        if not self._dir.exists():
            return
        try:
            files = [(p, p.stat().st_size) for p in self._dir.iterdir() if p.is_file()]
            total = sum(sz for _, sz in files)
            limit = 256 * 1024 * 1024  # 256 MB default cache budget
            if total <= limit:
                return
            files.sort(key=lambda fs: fs[0].stat().st_mtime)
            for p, sz in files:
                if total <= limit:
                    break
                p.unlink(missing_ok=True)
                total -= sz
        except Exception as exc:  # noqa: BLE001
            logger.debug("Cache prune failed: %s", exc)

    def stats(self) -> Dict[str, Any]:
        return {"hits": self._hits, "misses": self._misses}

    def clear(self) -> int:
        removed = 0
        if self._dir.exists():
            for p in self._dir.iterdir():
                if p.is_file():
                    p.unlink(missing_ok=True)
                    removed += 1
        return removed


class BatchProcessor:
    """Process many items in bounded batches to keep peak memory low."""

    def __init__(self, batch_size: int = 4, delay_s: float = 0.0):
        self._batch_size = max(1, batch_size)
        self._delay_s = max(0.0, delay_s)

    def process(self, items: List[T], fn: Callable[[T], Any]) -> List[Any]:
        results: List[Any] = []
        for i in range(0, len(items), self._batch_size):
            batch = items[i:i + self._batch_size]
            for item in batch:
                results.append(fn(item))
            if self._delay_s and i + self._batch_size < len(items):
                time.sleep(self._delay_s)
        return results


def lazy_import(module: str, attribute: str, fallback: Any = None) -> Any:
    """Import ``module.attribute`` on first use; return fallback on failure."""
    try:
        mod = __import__(module, fromlist=[attribute])
        return getattr(mod, attribute)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Lazy import %s.%s failed: %s", module, attribute, exc)
        return fallback
