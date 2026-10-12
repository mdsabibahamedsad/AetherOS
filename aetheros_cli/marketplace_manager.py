"""
Marketplace manager — plugin marketplace lifecycle for AetherOS.
Handles catalog management, plugin installation/update/removal,
version tracking, dependency resolution, and permissions.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


class Permission(Enum):
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    INTERNET = "internet"
    BROWSER = "browser"
    TERMINAL = "terminal"
    DOCKER = "docker"
    PYTHON_EXEC = "python.exec"
    CLIPBOARD = "clipboard"
    NOTIFICATIONS = "notifications"
    MICROPHONE = "microphone"
    CAMERA = "camera"
    WORKSPACE_READ = "workspace.read"
    WORKSPACE_WRITE = "workspace.write"
    SECRETS_READ = "secrets.read"
    SETTINGS_READ = "settings.read"
    SETTINGS_WRITE = "settings.write"
    MCP_ACCESS = "mcp.access"
    MEMORY_ACCESS = "memory.access"
    NETWORK_LISTEN = "network.listen"


class Category(Enum):
    AI = "ai"
    CODING = "coding"
    PRODUCTIVITY = "productivity"
    AUTOMATION = "automation"
    RESEARCH = "research"
    DEVTOOLS = "devtools"
    SECURITY = "security"
    COMMUNICATION = "communication"
    DATA = "data"
    FUN = "fun"
    UTILITY = "utility"
    INTEGRATION = "integration"
    WORKFLOW = "workflow"
    UI = "ui"
    KNOWLEDGE = "knowledge"
    MCP = "mcp"


@dataclass
class PluginPermission:
    resource: str
    actions: List[str] = field(default_factory=lambda: ["read"])
    effect: str = "allow"

    def to_dict(self) -> Dict[str, Any]:
        return {"resource": self.resource, "actions": self.actions, "effect": self.effect}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PluginPermission:
        return cls(
            resource=data["resource"],
            actions=data.get("actions", ["read"]),
            effect=data.get("effect", "allow"),
        )


@dataclass
class PluginVersion:
    version: str
    changelog: str = ""
    published: str = ""
    checksum: str = ""
    dependencies: Dict[str, str] = field(default_factory=dict)
    min_engine_version: str = "0.16.0"
    permissions: List[PluginPermission] = field(default_factory=list)
    download_url: str = ""
    file_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "changelog": self.changelog,
            "published": self.published,
            "checksum": self.checksum,
            "dependencies": self.dependencies,
            "min_engine_version": self.min_engine_version,
            "permissions": [p.to_dict() for p in self.permissions],
            "download_url": self.download_url,
            "file_size": self.file_size,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PluginVersion:
        return cls(
            version=data["version"],
            changelog=data.get("changelog", ""),
            published=data.get("published", ""),
            checksum=data.get("checksum", ""),
            dependencies=data.get("dependencies", {}),
            min_engine_version=data.get("min_engine_version", "0.16.0"),
            permissions=[PluginPermission.from_dict(p) for p in data.get("permissions", [])],
            download_url=data.get("download_url", ""),
            file_size=data.get("file_size", 0),
        )


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    documentation: str = ""
    categories: List[Category] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    permissions: List[PluginPermission] = field(default_factory=list)
    signature: str = ""
    checksum: str = ""
    min_engine_version: str = "0.16.0"
    icon: str = ""
    screenshots: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    versions: Dict[str, PluginVersion] = field(default_factory=dict)
    entry_point: str = "plugin.py"
    type: str = "plugin"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "homepage": self.homepage,
            "repository": self.repository,
            "documentation": self.documentation,
            "categories": [c.value for c in self.categories],
            "dependencies": self.dependencies,
            "permissions": [p.to_dict() for p in self.permissions],
            "signature": self.signature,
            "checksum": self.checksum,
            "min_engine_version": self.min_engine_version,
            "icon": self.icon,
            "screenshots": self.screenshots,
            "tags": self.tags,
            "versions": {k: v.to_dict() for k, v in self.versions.items()},
            "entry_point": self.entry_point,
            "type": self.type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PluginManifest:
        categories = []
        for c in data.get("categories", []):
            try:
                categories.append(Category(c))
            except ValueError:
                pass
        versions = {}
        for k, v in data.get("versions", {}).items():
            versions[k] = PluginVersion.from_dict(v) if isinstance(v, dict) else v
        return cls(
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            author=data.get("author", ""),
            license=data.get("license", "MIT"),
            homepage=data.get("homepage", ""),
            repository=data.get("repository", ""),
            documentation=data.get("documentation", ""),
            categories=categories,
            dependencies=data.get("dependencies", {}),
            permissions=[PluginPermission.from_dict(p) for p in data.get("permissions", [])],
            signature=data.get("signature", ""),
            checksum=data.get("checksum", ""),
            min_engine_version=data.get("min_engine_version", "0.16.0"),
            icon=data.get("icon", ""),
            screenshots=data.get("screenshots", []),
            tags=data.get("tags", []),
            versions=versions,
            entry_point=data.get("entry_point", "plugin.py"),
            type=data.get("type", "plugin"),
        )


@dataclass
class PluginInstallation:
    plugin_name: str
    version: str
    path: Path
    enabled: bool = True
    permissions: List[PluginPermission] = field(default_factory=list)
    installed_at: str = ""
    updated_at: str = ""
    source: str = "marketplace"
    manifest: Optional[PluginManifest] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_name": self.plugin_name,
            "version": self.version,
            "path": str(self.path),
            "enabled": self.enabled,
            "permissions": [p.to_dict() for p in self.permissions],
            "installed_at": self.installed_at,
            "updated_at": self.updated_at,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PluginInstallation:
        return cls(
            plugin_name=data["plugin_name"],
            version=data["version"],
            path=Path(data["path"]),
            enabled=data.get("enabled", True),
            permissions=[PluginPermission.from_dict(p) for p in data.get("permissions", [])],
            installed_at=data.get("installed_at", ""),
            updated_at=data.get("updated_at", ""),
            source=data.get("source", "marketplace"),
        )


@dataclass
class PluginRating:
    plugin: str
    user: str
    score: int
    review: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin": self.plugin,
            "user": self.user,
            "score": self.score,
            "review": self.review,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PluginRating:
        return cls(
            plugin=data["plugin"],
            user=data["user"],
            score=data["score"],
            review=data.get("review", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class TrustScore:
    plugin: str
    score: float
    downloads: int = 0
    ratings_count: int = 0
    average_rating: float = 0.0
    verified_publisher: bool = False
    signature_verified: bool = False
    last_reviewed: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin": self.plugin,
            "score": self.score,
            "downloads": self.downloads,
            "ratings_count": self.ratings_count,
            "average_rating": self.average_rating,
            "verified_publisher": self.verified_publisher,
            "signature_verified": self.signature_verified,
            "last_reviewed": self.last_reviewed,
        }


class DependencyResolutionError(Exception):
    pass


class PluginInstallError(Exception):
    pass


class MarketplaceManager:
    def __init__(self, catalog_sources: Optional[List[str]] = None):
        self._home = get_aetheros_home()
        self._plugins_dir = self._home / "plugins"
        self._marketplace_dir = self._home / "marketplace"
        self._registry_path = self._marketplace_dir / "registry.json"
        self._ratings_path = self._marketplace_dir / "ratings.json"
        self._audit_log_path = self._marketplace_dir / "audit.log"
        self._trust_scores_path = self._marketplace_dir / "trust.json"
        self._catalog_sources = catalog_sources or [
            "local",
            "https://marketplace.aetheros.dev/api/v1",
        ]
        self._registry: Dict[str, PluginManifest] = {}
        self._installations: Dict[str, PluginInstallation] = {}
        self._ratings: List[PluginRating] = []
        self._trust_scores: Dict[str, TrustScore] = {}
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self._marketplace_dir.mkdir(parents=True, exist_ok=True)
        self._plugins_dir.mkdir(parents=True, exist_ok=True)

    def _load_registry(self) -> Dict[str, PluginManifest]:
        if self._registry_path.exists():
            try:
                data = json.loads(self._registry_path.read_text(encoding="utf-8"))
                return {k: PluginManifest.from_dict(v) for k, v in data.items()}
            except Exception as e:
                logger.warning("Failed to load registry: %s", e)
        return {}

    def _save_registry(self) -> None:
        data = {k: v.to_dict() for k, v in self._registry.items()}
        self._registry_path.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )

    def _load_installations(self) -> Dict[str, PluginInstallation]:
        path = self._marketplace_dir / "installations.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return {k: PluginInstallation.from_dict(v) for k, v in data.items()}
            except Exception as e:
                logger.warning("Failed to load installations: %s", e)
        return {}

    def _save_installations(self) -> None:
        path = self._marketplace_dir / "installations.json"
        path.write_text(
            json.dumps(
                {k: v.to_dict() for k, v in self._installations.items()},
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    def _load_ratings(self) -> List[PluginRating]:
        if self._ratings_path.exists():
            try:
                data = json.loads(self._ratings_path.read_text(encoding="utf-8"))
                return [PluginRating.from_dict(r) for r in data]
            except Exception as e:
                logger.warning("Failed to load ratings: %s", e)
        return []

    def _save_ratings(self) -> None:
        self._ratings_path.write_text(
            json.dumps([r.to_dict() for r in self._ratings], indent=2, default=str),
            encoding="utf-8",
        )

    def _load_trust_scores(self) -> Dict[str, TrustScore]:
        if self._trust_scores_path.exists():
            try:
                data = json.loads(self._trust_scores_path.read_text(encoding="utf-8"))
                return {k: TrustScore(**v) for k, v in data.items()}
            except Exception as e:
                logger.warning("Failed to load trust scores: %s", e)
        return {}

    def _save_trust_scores(self) -> None:
        self._trust_scores_path.write_text(
            json.dumps(
                {k: v.to_dict() for k, v in self._trust_scores.items()},
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    def _audit_log(self, action: str, detail: str = "") -> None:
        timestamp = datetime.utcnow().isoformat()
        entry = f"[{timestamp}] {action}"
        if detail:
            entry += f": {detail}"
        try:
            with open(self._audit_log_path, "a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except Exception as e:
            logger.warning("Audit log write failed: %s", e)
        logger.info("Audit: %s", entry)

    def _compute_checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        if path.is_file():
            h.update(path.read_bytes())
        elif path.is_dir():
            for p in sorted(path.rglob("*")):
                if p.is_file():
                    h.update(p.read_bytes())
        return h.hexdigest()

    def resolve_dependencies(
        self, plugin_name: str, version: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        resolved: List[Tuple[str, str]] = []
        visited: Set[str] = set()

        def _resolve(name: str, ver: Optional[str]) -> None:
            if name in visited:
                return
            visited.add(name)
            manifest = self._registry.get(name)
            if not manifest:
                raise DependencyResolutionError(f"Plugin '{name}' not found in registry")
            target_ver = ver or manifest.version
            version_data = manifest.versions.get(target_ver)
            if not version_data:
                raise DependencyResolutionError(
                    f"Version '{target_ver}' not found for plugin '{name}'"
                )
            resolved.append((name, target_ver))
            for dep_name, dep_ver in version_data.dependencies.items():
                _resolve(dep_name, dep_ver)

        _resolve(plugin_name, version)
        return resolved

    def install_plugin(
        self,
        name: str,
        version: Optional[str] = None,
        source: Optional[str] = None,
        verify_signature: bool = True,
    ) -> PluginInstallation:
        manifest = self._registry.get(name)
        if not manifest:
            raise PluginInstallError(f"Plugin '{name}' not found in registry")

        target_version = version or manifest.version
        version_data = manifest.versions.get(target_version)
        if not version_data:
            raise PluginInstallError(
                f"Version '{target_version}' not available for '{name}'"
            )

        deps = self.resolve_dependencies(name, target_version)
        for dep_name, dep_ver in deps:
            existing = self._installations.get(dep_name)
            if not existing or existing.version != dep_ver:
                self.install_plugin(dep_name, dep_ver, source, verify_signature=False)

        plugin_dir = self._plugins_dir / name
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)
        plugin_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = plugin_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2), encoding="utf-8"
        )

        checksum = self._compute_checksum(plugin_dir)

        now = datetime.utcnow().isoformat()
        installation = PluginInstallation(
            plugin_name=name,
            version=target_version,
            path=plugin_dir,
            enabled=True,
            permissions=version_data.permissions or manifest.permissions,
            installed_at=now,
            updated_at=now,
            source=source or "marketplace",
            manifest=manifest,
        )

        self._installations[name] = installation
        self._save_installations()

        ts = self._trust_scores.get(name, TrustScore(plugin=name, score=0.0))
        ts.downloads += 1
        self._trust_scores[name] = ts
        self._save_trust_scores()

        self._audit_log("install", f"{name}@{target_version}")
        return installation

    def uninstall_plugin(self, name: str, remove_deps: bool = False) -> bool:
        installation = self._installations.get(name)
        if not installation:
            logger.warning("Plugin '%s' is not installed", name)
            return False

        dependents = [
            pn
            for pn, pi in self._installations.items()
            if pi.manifest
            and name in pi.manifest.dependencies
            and pn != name
        ]
        if dependents:
            raise PluginInstallError(
                f"Cannot uninstall '{name}': depends on by {dependents}"
            )

        plugin_dir = installation.path
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)

        del self._installations[name]
        self._save_installations()
        self._audit_log("uninstall", name)

        if remove_deps and installation.manifest:
            for dep_name in installation.manifest.dependencies:
                if dep_name in self._installations:
                    self.uninstall_plugin(dep_name, remove_deps=True)
        return True

    def update_plugin(
        self, name: str, target_version: Optional[str] = None
    ) -> PluginInstallation:
        existing = self._installations.get(name)
        if not existing:
            raise PluginInstallError(f"Plugin '{name}' is not installed")

        manifest = self._registry.get(name)
        if not manifest:
            raise PluginInstallError(f"Plugin '{name}' not found in registry")

        new_version = target_version or manifest.version
        if new_version == existing.version:
            logger.info("Plugin '%s' is already at version %s", name, new_version)
            return existing

        self.backup_plugin(name)
        installation = self.install_plugin(name, new_version)
        self._audit_log("update", f"{name}: {existing.version} -> {new_version}")
        return installation

    def rollback_plugin(self, name: str, target_version: str) -> PluginInstallation:
        backup_dir = self._marketplace_dir / "backups" / name
        if not backup_dir.exists():
            raise PluginInstallError(f"No backup found for '{name}'")

        manifest = self._registry.get(name)
        if not manifest or target_version not in manifest.versions:
            raise PluginInstallError(
                f"Version '{target_version}' not found for '{name}'"
            )

        installation = self.install_plugin(name, target_version)
        self._audit_log("rollback", f"{name} -> {target_version}")
        return installation

    def backup_plugin(self, name: str) -> Path:
        installation = self._installations.get(name)
        if not installation:
            raise PluginInstallError(f"Plugin '{name}' is not installed")

        backup_dir = self._marketplace_dir / "backups" / name
        backup_dir.mkdir(parents=True, exist_ok=True)

        version_dir = backup_dir / installation.version
        if version_dir.exists():
            shutil.rmtree(version_dir)

        shutil.copytree(installation.path, version_dir)
        self._audit_log("backup", f"{name}@{installation.version}")
        return version_dir

    def enable_plugin(self, name: str) -> bool:
        installation = self._installations.get(name)
        if not installation:
            logger.warning("Plugin '%s' is not installed", name)
            return False
        installation.enabled = True
        self._save_installations()
        self._audit_log("enable", name)
        return True

    def disable_plugin(self, name: str) -> bool:
        installation = self._installations.get(name)
        if not installation:
            logger.warning("Plugin '%s' is not installed", name)
            return False
        installation.enabled = False
        self._save_installations()
        self._audit_log("disable", name)
        return True

    def list_plugins(
        self,
        category: Optional[Category] = None,
        enabled_only: bool = False,
    ) -> List[PluginInstallation]:
        results = list(self._installations.values())
        if category:
            results = [
                p
                for p in results
                if p.manifest and category in p.manifest.categories
            ]
        if enabled_only:
            results = [p for p in results if p.enabled]
        return results

    def get_plugin(self, name: str) -> Optional[PluginInstallation]:
        return self._installations.get(name)

    def search_plugins(
        self,
        query: str = "",
        category: Optional[Category] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        sort_by: str = "name",
        sort_desc: bool = False,
    ) -> List[PluginManifest]:
        results = list(self._registry.values())

        if query:
            q = query.lower()
            results = [
                m
                for m in results
                if q in m.name.lower()
                or q in m.description.lower()
                or q in m.author.lower()
            ]

        if category:
            results = [m for m in results if category in m.categories]

        if tags:
            results = [
                m for m in results if any(t in m.tags for t in tags)
            ]

        if author:
            results = [m for m in results if author.lower() in m.author.lower()]

        if sort_by == "name":
            results.sort(key=lambda m: m.name.lower(), reverse=sort_desc)
        elif sort_by == "version":
            results.sort(key=lambda m: m.version, reverse=sort_desc)
        elif sort_by == "downloads":
            results.sort(
                key=lambda m: self._trust_scores.get(m.name, TrustScore(m.name, 0)).downloads,
                reverse=not sort_desc,
            )
        elif sort_by == "rating":
            results.sort(
                key=lambda m: self._trust_scores.get(m.name, TrustScore(m.name, 0)).average_rating,
                reverse=not sort_desc,
            )

        return results

    def get_updates(self) -> List[Tuple[str, str, str]]:
        updates: List[Tuple[str, str, str]] = []
        for name, installation in self._installations.items():
            manifest = self._registry.get(name)
            if manifest and manifest.version != installation.version:
                updates.append((name, installation.version, manifest.version))
        return updates

    def get_categories(self) -> Dict[Category, int]:
        counts: Dict[Category, int] = {}
        for manifest in self._registry.values():
            for cat in manifest.categories:
                counts[cat] = counts.get(cat, 0) + 1
        return counts

    def get_permissions(self, name: str) -> List[PluginPermission]:
        installation = self._installations.get(name)
        if installation:
            return installation.permissions
        manifest = self._registry.get(name)
        if manifest:
            return manifest.permissions
        return []

    def rate_plugin(
        self, plugin: str, user: str, score: int, review: str = ""
    ) -> PluginRating:
        if plugin not in self._registry and plugin not in self._installations:
            raise ValueError(f"Plugin '{plugin}' not found")
        if score < 1 or score > 5:
            raise ValueError("Score must be between 1 and 5")

        rating = PluginRating(
            plugin=plugin,
            user=user,
            score=score,
            review=review,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        for i, r in enumerate(self._ratings):
            if r.plugin == plugin and r.user == user:
                rating.created_at = r.created_at
                self._ratings[i] = rating
                break
        else:
            self._ratings.append(rating)

        self._save_ratings()
        self._update_trust_score(plugin)
        self._audit_log("rate", f"{plugin} <- {score} by {user}")
        return rating

    def get_ratings(self, plugin: str) -> List[PluginRating]:
        return [r for r in self._ratings if r.plugin == plugin]

    def _update_trust_score(self, plugin: str) -> None:
        plugin_ratings = self.get_ratings(plugin)
        avg = 0.0
        count = len(plugin_ratings)
        if count > 0:
            avg = sum(r.score for r in plugin_ratings) / count

        ts = self._trust_scores.get(
            plugin,
            TrustScore(plugin=plugin, score=0.0),
        )
        ts.average_rating = avg
        ts.ratings_count = count

        base = (avg / 5.0) * 60.0
        download_bonus = min(20.0, ts.downloads / 100.0 * 5.0)
        verified_bonus = 15.0 if ts.verified_publisher else 0.0
        sig_bonus = 5.0 if ts.signature_verified else 0.0
        ts.score = min(100.0, base + download_bonus + verified_bonus + sig_bonus)

        self._trust_scores[plugin] = ts
        self._save_trust_scores()

    def verify_signature(self, name: str) -> bool:
        manifest = self._registry.get(name)
        if not manifest or not manifest.signature:
            return False
        expected = self._compute_checksum(self._plugins_dir / name)
        if manifest.checksum and manifest.checksum != expected:
            logger.warning("Checksum mismatch for '%s'", name)
            return False

        ts = self._trust_scores.get(name, TrustScore(plugin=name, score=0.0))
        ts.signature_verified = True
        self._trust_scores[name] = ts
        self._save_trust_scores()
        return True

    def refresh_catalog(self, source: Optional[str] = None) -> int:
        count = 0
        self._registry = self._load_registry()
        from aetheros_cli.plugins import discover_plugins

        installed = discover_plugins()
        for plugin_name, plugin_info in installed.items():
            if hasattr(plugin_info, "manifest"):
                try:
                    m = plugin_info.manifest
                    manifest = PluginManifest(
                        name=m.get("name", plugin_name),
                        version=m.get("version", "0.1.0"),
                        description=m.get("description", ""),
                        author=m.get("author", ""),
                        license=m.get("license", "MIT"),
                        categories=[
                            Category(c) for c in m.get("categories", [])
                            if c in [e.value for e in Category]
                        ],
                        tags=m.get("tags", []),
                    )
                    if plugin_name not in self._registry:
                        self._registry[plugin_name] = manifest
                        count += 1
                except Exception as e:
                    logger.debug("Skipping plugin '%s': %s", plugin_name, e)

        self._save_registry()
        self._audit_log("refresh_catalog", f"loaded {count} plugins")
        return count

    def get_audit_log(self, limit: int = 100) -> List[str]:
        if not self._audit_log_path.exists():
            return []
        lines = self._audit_log_path.read_text(encoding="utf-8").strip().split("\n")
        return lines[-limit:]

    def add_manifest(self, manifest: PluginManifest) -> None:
        self._registry[manifest.name] = manifest
        self._save_registry()
        self._audit_log("add_manifest", f"{manifest.name}@{manifest.version}")

    def remove_manifest(self, name: str) -> bool:
        if name in self._registry:
            del self._registry[name]
            self._save_registry()
            self._audit_log("remove_manifest", name)
            return True
        return False

    @property
    def registry(self) -> Dict[str, PluginManifest]:
        return dict(self._registry)

    @property
    def installations(self) -> Dict[str, PluginInstallation]:
        return dict(self._installations)
