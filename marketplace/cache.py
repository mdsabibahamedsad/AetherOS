"""
Marketplace Cache
=================

Local cache for marketplace data to reduce network requests and enable
offline operation. Uses a simple JSON file-based cache with TTL support.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from marketplace.registry import ExtensionEntry

logger = logging.getLogger(__name__)

_CACHE_DIR = Path.home() / ".aetheros" / "marketplace" / "cache"
_DEFAULT_TTL = 3600  # 1 hour


@dataclass
class CacheEntry:
    """A single cache entry."""
    key: str
    data: Any
    created_at: float = 0.0
    ttl: int = _DEFAULT_TTL

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl


class MarketplaceCache:
    """Local cache for marketplace data."""

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self._cache_dir = cache_dir or _CACHE_DIR
        self._entries: Dict[str, CacheEntry] = {}
        self._ensure_dir()
        self._load()

    def get(self, key: str) -> Optional[Any]:
        """Get a cached value. Returns None if missing or expired."""
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.is_expired:
            del self._entries[key]
            return None
        return entry.data

    def set(self, key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
        """Cache a value with a TTL."""
        self._entries[key] = CacheEntry(key=key, data=value, ttl=ttl)
        self._save()

    def invalidate(self, key: str) -> None:
        """Remove a cache entry."""
        self._entries.pop(key, None)
        self._save()

    def invalidate_all(self) -> None:
        """Clear the entire cache."""
        self._entries.clear()
        self._save()

    def get_cached_extensions(self) -> List[ExtensionEntry]:
        """Get cached extension list, or empty list."""
        data = self.get("extensions")
        if data is None:
            return []
        try:
            return [ExtensionEntry(**item) for item in data]
        except Exception:
            return []

    def set_cached_extensions(
        self, extensions: List[ExtensionEntry], ttl: int = _DEFAULT_TTL
    ) -> None:
        """Cache a list of extensions."""
        data = [
            {
                "id": e.id, "name": e.name, "version": e.version,
                "description": e.description, "publisher": e.publisher,
                "kind": e.kind, "downloads": e.downloads, "rating": e.rating,
                "categories": e.categories, "tags": e.tags,
                "source_url": e.source_url, "icon_url": e.icon_url,
                "license": e.license, "verified": e.verified,
                "updated_at": e.updated_at,
            }
            for e in extensions
        ]
        self.set("extensions", data, ttl=ttl)

    def _ensure_dir(self) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        cache_file = self._cache_dir / "cache.json"
        if not cache_file.exists():
            return
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            for entry_data in data.get("entries", []):
                entry = CacheEntry(
                    key=entry_data["key"],
                    data=entry_data["data"],
                    created_at=entry_data.get("created_at", 0),
                    ttl=entry_data.get("ttl", _DEFAULT_TTL),
                )
                if not entry.is_expired:
                    self._entries[entry.key] = entry
        except Exception as exc:
            logger.debug("Failed to load marketplace cache: %s", exc)

    def _save(self) -> None:
        cache_file = self._cache_dir / "cache.json"
        try:
            data = {
                "entries": [
                    {"key": e.key, "data": e.data, "created_at": e.created_at, "ttl": e.ttl}
                    for e in self._entries.values()
                ]
            }
            cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to save marketplace cache: %s", exc)
