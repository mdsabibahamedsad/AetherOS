"""
Tool Permission Manifests for AetherOS
======================================

Every tool declares a permission manifest describing exactly what it can
touch (master security spec steps 9-11):

    - filesystem operations (read/write/delete/execute) with path scopes
    - network access (allowed/denied hosts, ports)
    - shell execution
    - resource scopes (workspace/projectA/**, email:read, database:reports)

Operations are separated by class (READ / WRITE / DELETE / EXECUTE / SEND /
PUBLISH / ADMIN). Reading a file does NOT grant deleting it; reading email
does NOT grant sending email; reading a database does NOT grant modifying it.

Manifests are enforced by the authorization engine before a tool call
executes. A tool without a manifest gets deny-by-default unless a policy
rule explicitly allows it.

Usage::

    from aetheros_security.manifest import (
        ToolManifest, ManifestRegistry, PermissionOperation,
    )

    manifest = ToolManifest(
        tool_id="file.read",
        filesystem={"read": ["workspace/**"]},
    )
    registry = ManifestRegistry()
    registry.register(manifest)
    assert registry.allows("file.read", "read", "workspace/notes.md")
    assert not registry.allows("file.read", "delete", "workspace/notes.md")
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PermissionOperation(Enum):
    """Permission operation classes (read/write separation)."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    SEND = "send"
    PUBLISH = "publish"
    ADMIN = "admin"


class FilesystemAccess(Enum):
    """Filesystem access modes."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    EXECUTE = "execute"
    NONE = "none"


@dataclass
class NetworkManifest:
    """Network permissions for a tool."""
    allowed_hosts: List[str] = field(default_factory=list)
    denied_hosts: List[str] = field(default_factory=list)
    allowed_ports: List[int] = field(default_factory=list)
    outbound: bool = False
    block_private: bool = True


@dataclass
class FilesystemManifest:
    """Filesystem permissions with explicit path scopes."""
    read: List[str] = field(default_factory=list)
    write: List[str] = field(default_factory=list)
    delete: List[str] = field(default_factory=list)
    execute: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)

    def allows(self, operation: PermissionOperation, path: str) -> bool:
        scopes = getattr(self, operation.value, [])
        for pattern in self.denied_paths:
            if _path_match(pattern, path):
                return False
        if not scopes:
            return False
        return any(_path_match(pattern, path) for pattern in scopes)


@dataclass
class ToolManifest:
    """The permission manifest for a single tool.

    Attributes:
        tool_id: Canonical tool id (e.g. ``file.read``).
        version: Manifest/tool version.
        filesystem: Filesystem permissions.
        network: Network permissions.
        shell: Whether the tool may execute shell commands.
        shell_patterns: Allowlisted shell command patterns when shell is True.
        resources: Resource-scope allow patterns (e.g. ``database:reports``).
        risk: Default risk level for the tool.
    """
    tool_id: str
    version: str = "1.0.0"
    filesystem: FilesystemManifest = field(default_factory=FilesystemManifest)
    network: NetworkManifest = field(default_factory=NetworkManifest)
    shell: bool = False
    shell_patterns: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    risk: str = "medium"

    def can_read(self, path: str) -> bool:
        return self.filesystem.allows(PermissionOperation.READ, path)

    def can_write(self, path: str) -> bool:
        return self.filesystem.allows(PermissionOperation.WRITE, path)

    def can_delete(self, path: str) -> bool:
        return self.filesystem.allows(PermissionOperation.DELETE, path)

    def can_execute(self, path: str) -> bool:
        return self.filesystem.allows(PermissionOperation.EXECUTE, path)

    def allows_resource(self, resource: str) -> bool:
        return any(_path_match(pattern, resource) for pattern in self.resources)

    def allows_host(self, host: str) -> bool:
        host = (host or "").lower()
        if host in [h.lower() for h in self.network.denied_hosts]:
            return False
        if not self.network.allowed_hosts:
            return self.network.outbound
        return any(_host_match(pattern, host)
                   for pattern in self.network.allowed_hosts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "version": self.version,
            "filesystem": {
                "read": list(self.filesystem.read),
                "write": list(self.filesystem.write),
                "delete": list(self.filesystem.delete),
                "execute": list(self.filesystem.execute),
                "denied_paths": list(self.filesystem.denied_paths),
            },
            "network": {
                "allowed_hosts": list(self.network.allowed_hosts),
                "denied_hosts": list(self.network.denied_hosts),
                "allowed_ports": list(self.network.allowed_ports),
                "outbound": self.network.outbound,
            },
            "shell": self.shell,
            "shell_patterns": list(self.shell_patterns),
            "resources": list(self.resources),
            "risk": self.risk,
        }


def _path_match(pattern: str, value: str) -> bool:
    """Glob match a path pattern against a value (case-insensitive on win32)."""
    import os
    value = value or ""
    pattern = pattern or ""
    if pattern == "**":
        return True
    if pattern.startswith("**/"):
        rest = pattern[3:]
        parts = value.replace("\\", "/").split("/")
        for i in range(len(parts)):
            tail = "/".join(parts[i:])
            if _path_match(rest, tail):
                return True
        return False
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        if prefix == "":
            return True
        return value == prefix.rstrip("/") or value.startswith(prefix.rstrip("/") + "/")
    if os.name == "nt":
        value = value.replace("\\", "/")
        pattern = pattern.replace("\\", "/")
        value = value.lower()
        pattern = pattern.lower()
    return fnmatch.fnmatch(value, pattern)


def _host_match(pattern: str, host: str) -> bool:
    pattern = (pattern or "").lower()
    if pattern.startswith("*.") and host.endswith(pattern[1:]):
        return True
    return pattern == host


class ManifestError(Exception):
    """Raised for invalid manifests."""


class ManifestRegistry:
    """Registry of tool permission manifests.

    Enforced deterministically before tool execution. Deny-by-default: a
    tool with no manifest grants nothing.
    """

    def __init__(self) -> None:
        self._manifests: Dict[str, ToolManifest] = {}

    def register(self, manifest: ToolManifest) -> ToolManifest:
        if not manifest.tool_id:
            raise ManifestError("Tool manifest requires a tool_id")
        self._manifests[manifest.tool_id] = manifest
        logger.debug("Tool manifest registered: %s v%s", manifest.tool_id,
                     manifest.version)
        return manifest

    def get(self, tool_id: str) -> Optional[ToolManifest]:
        return self._manifests.get(tool_id)

    def unregister(self, tool_id: str) -> bool:
        return self._manifests.pop(tool_id, None) is not None

    def allows(self, tool_id: str, operation: str, value: str = "") -> bool:
        """Check a single operation against a manifest.

        For filesystem operations ``value`` is the path; for network it is
        the host; for resources it is the resource id.
        """
        manifest = self._manifests.get(tool_id)
        if manifest is None:
            return False
        op = operation.lower()
        if op in ("read", "write", "delete", "execute"):
            return manifest.filesystem.allows(PermissionOperation(op), value)
        if op == "network" or op == "connect":
            return manifest.allows_host(value)
        if op == "resource":
            return manifest.allows_resource(value)
        if op == "shell":
            return manifest.shell
        return False

    def grants(self, tool_id: str, operation: str, value: str = "") -> bool:
        """Alias for :meth:`allows`."""
        return self.allows(tool_id, operation, value)

    def list_manifests(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._manifests.values()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_manifests": len(self._manifests),
            "shell_allowed": sum(1 for m in self._manifests.values() if m.shell),
            "network_allowed": sum(1 for m in self._manifests.values()
                                   if m.network.outbound),
        }


# Global manifest registry
_manifest_registry: ManifestRegistry | None = None


def get_manifest_registry() -> ManifestRegistry:
    """Return the global ManifestRegistry singleton."""
    global _manifest_registry
    if _manifest_registry is None:
        _manifest_registry = ManifestRegistry()
    return _manifest_registry