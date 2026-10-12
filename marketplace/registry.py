"""
Marketplace Registry
====================

Manages the extension registry — the catalog of available extensions
from one or more sources (public marketplace, private registries,
local file system).

Each registry source provides a list of ``ExtensionEntry`` objects
that describe available extensions with metadata, versions, and
download URLs.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# Default public marketplace URL
_DEFAULT_MARKETPLACE_URL = "https://marketplace.aetheros.dev/api/v1"

# Cache TTL in seconds
_CACHE_TTL = 3600  # 1 hour


class RegistrySource(Enum):
    """Source of registry data."""
    PUBLIC = "public"           # Official public marketplace
    PRIVATE = "private"         # Self-hosted / enterprise registry
    LOCAL = "local"             # Local filesystem
    FILE = "file"               # Single file (JSON/YAML)


@dataclass
class ExtensionEntry:
    """A single extension entry in the registry."""
    id: str                          # Unique ID (e.g. "publisher/name")
    name: str                        # Extension name
    version: str                     # Latest version
    description: str = ""
    publisher: str = ""
    author: str = ""
    kind: str = "standalone"
    downloads: int = 0
    rating: float = 0.0
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source_url: str = ""             # Git URL or download URL
    manifest_url: str = ""           # URL to the manifest
    icon_url: str = ""               # URL to icon
    license: str = ""
    created_at: str = ""
    updated_at: str = ""
    verified: bool = False           # Publisher verified?
    requires_env: List[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.publisher}/{self.name}" if self.publisher else self.name


@dataclass
class RegistryConfig:
    """Configuration for a registry source."""
    source: RegistrySource
    url: str = _DEFAULT_MARKETPLACE_URL
    name: str = "Official Marketplace"
    api_key: str = ""                # For private registries
    verify_ssl: bool = True
    cache_ttl: int = _CACHE_TTL
    enabled: bool = True


class MarketplaceRegistry:
    """Central registry that aggregates multiple sources.

    Usage::

        registry = MarketplaceRegistry()
        registry.add_source(RegistryConfig(source=RegistrySource.PUBLIC))
        registry.add_source(RegistryConfig(source=RegistrySource.PRIVATE, url="https://registry.mycorp.com"))

        # Discover all extensions
        all_extensions = registry.list_extensions()

        # Search
        results = registry.search("code assistant")
    """

    def __init__(self) -> None:
        self._sources: List[RegistryConfig] = []
        self._cache: Dict[str, List[ExtensionEntry]] = {}
        self._cache_timestamps: Dict[str, float] = {}

    def add_source(self, config: RegistryConfig) -> None:
        """Add a registry source."""
        self._sources.append(config)
        logger.info("Added registry source: %s (%s)", config.name, config.url)

    def remove_source(self, url: str) -> bool:
        """Remove a registry source by URL."""
        for i, src in enumerate(self._sources):
            if src.url == url:
                self._sources.pop(i)
                self._cache.pop(url, None)
                self._cache_timestamps.pop(url, None)
                return True
        return False

    def list_sources(self) -> List[RegistryConfig]:
        """Return all configured registry sources."""
        return list(self._sources)

    def list_extensions(
        self,
        source_filter: Optional[RegistrySource] = None,
    ) -> List[ExtensionEntry]:
        """List all extensions from all (or filtered) sources."""
        results: List[ExtensionEntry] = []
        for src in self._sources:
            if source_filter and src.source != source_filter:
                continue
            results.extend(self._fetch_from_source(src))
        return results

    def search(self, query: str, **filters) -> List[ExtensionEntry]:
        """Search for extensions across all sources.

        Args:
            query: Search term.
            **filters: Optional filters (kind, category, publisher, etc.).

        Returns:
            List of matching ExtensionEntry objects.
        """
        results = self.list_extensions()
        query_lower = query.lower()

        filtered = []
        for ext in results:
            # Full-text search
            if query_lower not in ext.name.lower() and \
               query_lower not in ext.description.lower() and \
               query_lower not in ext.full_name.lower():
                continue

            # Apply filters
            if "kind" in filters and ext.kind != filters["kind"]:
                continue
            if "category" in filters and filters["category"] not in ext.categories:
                continue
            if "publisher" in filters and ext.publisher != filters["publisher"]:
                continue

            filtered.append(ext)

        return filtered

    def get_extension(self, extension_id: str) -> Optional[ExtensionEntry]:
        """Get a specific extension by ID."""
        for ext in self.list_extensions():
            if ext.id == extension_id or ext.full_name == extension_id:
                return ext
        return None

    def refresh(self) -> int:
        """Force-refresh the cache from all sources.

        Returns:
            Number of extensions discovered.
        """
        self._cache.clear()
        self._cache_timestamps.clear()
        extensions = self.list_extensions()
        return len(extensions)

    def _fetch_from_source(self, config: RegistryConfig) -> List[ExtensionEntry]:
        """Fetch extensions from a source (with caching)."""
        # Check cache
        now = datetime.utcnow().timestamp()
        cache_time = self._cache_timestamps.get(config.url, 0)
        if config.url in self._cache and (now - cache_time) < config.cache_ttl:
            return self._cache[config.url]

        try:
            entries = self._do_fetch(config)
            self._cache[config.url] = entries
            self._cache_timestamps[config.url] = now
            return entries
        except Exception as exc:
            logger.warning("Failed to fetch from %s: %s", config.url, exc)
            return self._cache.get(config.url, [])

    def _do_fetch(self, config: RegistryConfig) -> List[ExtensionEntry]:
        """Actually fetch extension list from a source."""
        if config.source == RegistrySource.LOCAL:
            return self._scan_local_extensions(config.url)
        if config.source == RegistrySource.FILE:
            return self._load_from_file(config.url)
        # Remote source (PUBLIC or PRIVATE)
        return self._fetch_remote(config)

    def _scan_local_extensions(self, path_str: str) -> List[ExtensionEntry]:
        """Scan a local directory for installed extensions."""
        path = Path(path_str)
        if not path.is_dir():
            return []

        entries = []
        for child in sorted(path.iterdir()):
            if not child.is_dir():
                continue
            manifest_file = child / "plugin.yaml"
            if not manifest_file.exists():
                manifest_file = child / "manifest.yaml"
            if not manifest_file.exists():
                continue
            try:
                data = yaml.safe_load(manifest_file.read_text(encoding="utf-8")) or {}
                entries.append(ExtensionEntry(
                    id=data.get("name", child.name),
                    name=data.get("name", child.name),
                    version=str(data.get("version", "0.0.0")),
                    description=data.get("description", ""),
                    publisher=data.get("author", ""),
                    kind=data.get("kind", "standalone"),
                    source_url=str(child),
                    categories=data.get("categories", []),
                    tags=data.get("tags", []),
                ))
            except Exception as exc:
                logger.debug("Failed to parse %s: %s", manifest_file, exc)

        return entries

    def _load_from_file(self, path_str: str) -> List[ExtensionEntry]:
        """Load extension list from a JSON or YAML file."""
        path = Path(path_str)
        if not path.exists():
            return []

        try:
            raw = path.read_text(encoding="utf-8")
            if path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(raw) or []
            else:
                data = json.loads(raw)
        except Exception as exc:
            logger.warning("Failed to load %s: %s", path, exc)
            return []

        entries = []
        for item in (data if isinstance(data, list) else data.get("extensions", [])):
            if isinstance(item, dict):
                entries.append(ExtensionEntry(
                    id=item.get("id", item.get("name", "")),
                    name=item.get("name", ""),
                    version=str(item.get("version", "0.0.0")),
                    description=item.get("description", ""),
                    publisher=item.get("publisher", item.get("author", "")),
                    kind=item.get("kind", "standalone"),
                    downloads=item.get("downloads", 0),
                    rating=item.get("rating", 0.0),
                    source_url=item.get("source_url", ""),
                    icon_url=item.get("icon_url", ""),
                    categories=item.get("categories", []),
                    tags=item.get("tags", []),
                    license=item.get("license", ""),
                    verified=item.get("verified", False),
                ))
        return entries

    def _fetch_remote(self, config: RegistryConfig) -> List[ExtensionEntry]:
        """Fetch extensions from a remote registry API."""
        import urllib.request
        import json

        headers = {
            "Accept": "application/json",
            "User-Agent": f"AetherosMarketplace/1.0",
        }
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        url = config.url.rstrip("/") + "/extensions"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.warning("Failed to fetch remote registry %s: %s", url, exc)
            return []

        entries = []
        for item in (data if isinstance(data, list) else data.get("extensions", [])):
            if isinstance(item, dict):
                entries.append(ExtensionEntry(
                    id=item.get("id", item.get("name", "")),
                    name=item.get("name", ""),
                    version=str(item.get("version", "0.0.0")),
                    description=item.get("description", ""),
                    publisher=item.get("publisher", item.get("author", "")),
                    kind=item.get("kind", "standalone"),
                    downloads=item.get("downloads", 0),
                    rating=item.get("rating", 0.0),
                    source_url=item.get("source_url", ""),
                    icon_url=item.get("icon_url", ""),
                    categories=item.get("categories", []),
                    tags=item.get("tags", []),
                    license=item.get("license", ""),
                    verified=item.get("verified", False),
                    requires_env=item.get("requires_env", []),
                ))
        return entries


# Global singleton
_registry_instance: Optional[MarketplaceRegistry] = None


def get_registry() -> MarketplaceRegistry:
    """Return the global MarketplaceRegistry singleton."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = MarketplaceRegistry()
        # Add default public registry
        _registry_instance.add_source(RegistryConfig(
            source=RegistrySource.PUBLIC,
            url=_DEFAULT_MARKETPLACE_URL,
        ))
        # Add local extensions
        try:
            from aetheros_constants import get_aetheros_home
            plugins_dir = get_aetheros_home() / "plugins"
            if plugins_dir.exists():
                _registry_instance.add_source(RegistryConfig(
                    source=RegistrySource.LOCAL,
                    url=str(plugins_dir),
                    name="Local Plugins",
                ))
        except Exception:
            pass
    return _registry_instance
