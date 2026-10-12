"""Data models for the AetherOS Hub — plugins, MCP servers, skills, themes, extensions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class HubCategory(str, Enum):
    PLUGINS = "plugins"
    MCP_SERVERS = "mcp_servers"
    SKILLS = "skills"
    EXTENSIONS = "extensions"
    THEMES = "themes"
    WORKFLOWS = "workflows"
    AI_AGENTS = "ai_agents"
    TOOL_PACKS = "tool_packs"
    LANGUAGE_PACKS = "language_packs"
    MODELS = "models"
    ICON_PACKS = "icon_packs"


class InstallStatus(str, Enum):
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"
    UPDATING = "updating"
    BROKEN = "broken"
    DISABLED = "disabled"
    UNINSTALLING = "uninstalling"


class Permission(str, Enum):
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    TERMINAL = "terminal"
    GIT = "git"
    DOCKER = "docker"
    CLIPBOARD = "clipboard"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    NOTIFICATIONS = "notifications"
    BROWSER = "browser"
    EMAIL = "email"
    CALENDAR = "calendar"
    MEMORY = "memory"
    MCP = "mcp"
    AI_PROVIDERS = "ai_providers"
    AUDIO = "audio"
    SCREENSHOT = "screenshot"
    KEYCHAIN = "keychain"
    USB = "usb"
    BLUETOOTH = "bluetooth"


class SandboxRuntime(str, Enum):
    PYTHON = "python"
    NODE = "node"
    RUST = "rust"
    GO = "go"
    WASM = "wasm"


class PublisherVerification(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    OFFICIAL = "official"
    COMMUNITY = "community"


@dataclass
class HubAuthor:
    name: str
    email: str = ""
    url: str = ""
    github: str = ""
    verified: PublisherVerification = PublisherVerification.UNVERIFIED


@dataclass
class HubDependency:
    package_id: str
    version: str
    optional: bool = False


@dataclass
class HubVersion:
    version: str
    changelog: str = ""
    released_at: str = ""
    min_engine_version: str = ""
    max_engine_version: str = ""


@dataclass
class HubReview:
    id: str = ""
    user: str = ""
    rating: int = 5
    title: str = ""
    body: str = ""
    created_at: str = ""
    verified_purchase: bool = False


@dataclass
class HubItem:
    id: str
    name: str
    description: str
    category: HubCategory
    author: HubAuthor
    version: str = "1.0.0"
    license: str = "MIT"
    homepage: str = ""
    github: str = ""
    tags: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    changelog: list[HubVersion] = field(default_factory=list)
    dependencies: list[HubDependency] = field(default_factory=list)
    permissions: list[Permission] = field(default_factory=list)
    sandbox_runtime: SandboxRuntime = SandboxRuntime.PYTHON
    rating: float = 0.0
    downloads: int = 0
    reviews: list[HubReview] = field(default_factory=list)
    last_updated: str = ""
    created_at: str = ""
    featured: bool = False
    trending: bool = False
    editors_choice: bool = False
    verified: bool = False
    official: bool = False
    community: bool = True
    new: bool = False
    recently_updated: bool = False
    icon_url: str = ""
    readme: str = ""
    install_path: str = ""
    manifest: dict = field(default_factory=dict)
    config_schema: dict = field(default_factory=dict)
    signature: str = ""
    publisher_key: str = ""
    checksum: str = ""
    size_bytes: int = 0
    install_status: InstallStatus = InstallStatus.NOT_INSTALLED
    installed_version: str = ""
    enabled: bool = True
    compatible: bool = True
    categories: list[str] = field(default_factory=list)
    screenshots_count: int = 0
    review_count: int = 0

    @property
    def display_category(self) -> str:
        return self.category.value.replace("_", " ").title()

    @property
    def author_name(self) -> str:
        return self.author.name if self.author else "Unknown"

    @property
    def author_verified(self) -> bool:
        return self.author.verified in (PublisherVerification.VERIFIED,
                                        PublisherVerification.OFFICIAL)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "category": self.category.value, "version": self.version,
            "author": {"name": self.author.name, "email": self.author.email,
                       "url": self.author.url, "github": self.author.github,
                       "verified": self.author.verified.value},
            "license": self.license, "homepage": self.homepage,
            "github": self.github, "tags": self.tags,
            "screenshots": self.screenshots, "rating": self.rating,
            "downloads": self.downloads, "last_updated": self.last_updated,
            "created_at": self.created_at, "featured": self.featured,
            "trending": self.trending, "editors_choice": self.editors_choice,
            "verified": self.verified, "official": self.official,
            "community": self.community, "new": self.new,
            "recently_updated": self.recently_updated, "icon_url": self.icon_url,
            "permissions": [p.value for p in self.permissions],
            "dependencies": [{"package_id": d.package_id, "version": d.version,
                              "optional": d.optional} for d in self.dependencies],
            "install_status": self.install_status.value,
            "installed_version": self.installed_version,
            "enabled": self.enabled, "compatible": self.compatible,
            "size_bytes": self.size_bytes, "review_count": self.review_count,
        }


@dataclass
class InstallRecord:
    item_id: str
    category: HubCategory
    version: str
    installed_at: str = ""
    updated_at: str = ""
    enabled: bool = True
    checksum: str = ""
    manifest: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = "MIT"
    entrypoint: str = ""
    permissions: list[str] = field(default_factory=list)
    dependencies: list[dict] = field(default_factory=list)
    min_engine_version: str = "1.0.0"
    homepage: str = ""
    repository: str = ""
    tags: list[str] = field(default_factory=list)
    icons: dict = field(default_factory=dict)
    sandbox: str = "python"
    hooks: list[str] = field(default_factory=list)
    config_schema: dict = field(default_factory=dict)


@dataclass
class BackupManifest:
    version: str = "1.0"
    created_at: str = ""
    items: list[dict] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    settings: dict = field(default_factory=dict)


@dataclass
class SDKProject:
    project_type: str
    name: str
    language: str
    path: str
    manifest: PluginManifest = field(default_factory=PluginManifest)
