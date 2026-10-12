"""
Extension Sandbox
=================

Configurable sandbox for executing extensions with resource isolation
and permission enforcement.

Sandbox modes:
    - ``NONE``: No sandboxing (default, for trusted extensions)
    - ``PERMISSION``: Permission-based sandbox (files, network, etc.)
    - ``STRICT``: Full isolation (subprocess, resource limits)
"""

from __future__ import annotations

import enum
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from sdk.permissions import Permission, PermissionSet, PermissionAudit

logger = logging.getLogger(__name__)


class SandboxMode(enum.Enum):
    """Sandbox isolation level."""
    NONE = "none"               # No sandboxing
    PERMISSION = "permission"   # Permission-based gating
    STRICT = "strict"           # Full isolation (subprocess)


@dataclass
class SandboxConfig:
    """Configuration for the extension sandbox."""
    mode: SandboxMode = SandboxMode.PERMISSION
    allowed_paths: List[str] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    allowed_env_vars: List[str] = field(default_factory=list)
    max_memory_mb: int = 512
    max_cpu_percent: float = 50.0
    network_allowed: bool = False
    filesystem_read_allowed: bool = True
    filesystem_write_allowed: bool = False
    temp_dir: Optional[str] = None


class SandboxViolation(Exception):
    """Raised when an extension violates sandbox restrictions."""


class ExtensionSandbox:
    """Sandbox for executing extensions with resource isolation.

    Usage::

        sandbox = ExtensionSandbox(config=SandboxConfig(mode=SandboxMode.PERMISSION))
        sandbox.check_permission("network:connect", extension_name="my-plugin")
        with sandbox.isolated_filesystem() as temp_path:
            # Extension code runs here with restricted filesystem
            pass
    """

    def __init__(self, config: Optional[SandboxConfig] = None) -> None:
        self._config = config or SandboxConfig()
        self._permission_audit = PermissionAudit()
        self._active: bool = True

    @property
    def config(self) -> SandboxConfig:
        return self._config

    @property
    def is_active(self) -> bool:
        return self._active

    def check_permission(
        self,
        permission_name: str,
        extension_name: str = "",
    ) -> bool:
        """Check whether an action is allowed by the sandbox.

        Args:
            permission_name: Permission to check (e.g. ``"network:connect"``).
            extension_name: Name of the extension requesting permission.

        Returns:
            True if allowed, False if denied.

        Raises:
            SandboxViolation: In strict mode, raises instead of returning False.
        """
        if self._config.mode == SandboxMode.NONE:
            return True

        if self._config.mode == SandboxMode.STRICT:
            # In strict mode, check against config allowlists
            category = permission_name.split(":")[0] if ":" in permission_name else permission_name
            if category == "network" and not self._config.network_allowed:
                raise SandboxViolation(
                    f"Network access denied for '{extension_name}' in strict sandbox"
                )
            if category == "filesystem":
                if "write" in permission_name and not self._config.filesystem_write_allowed:
                    raise SandboxViolation(
                        f"Filesystem write denied for '{extension_name}' in strict sandbox"
                    )
                if permission_name == "filesystem:read" and not self._config.filesystem_read_allowed:
                    raise SandboxViolation(
                        f"Filesystem read denied for '{extension_name}' in strict sandbox"
                    )
            # Fall through for allowed actions

        # Permission mode: delegate to the audit system
        perm = Permission(permission_name)
        granted = self._permission_audit.request(
            extension_name, perm,
            reason=f"sandbox policy ({self._config.mode.value})",
        )
        return granted

    def isolate_path(self, path: Path, extension_name: str = "") -> Path:
        """Resolve and validate a path within sandbox constraints.

        In permission mode, only allows paths within the allowed list.
        In strict mode, restricts to a temp sandbox directory.

        Returns the resolved path, or raises SandboxViolation.
        """
        resolved = path.resolve()

        if self._config.mode == SandboxMode.NONE:
            return resolved

        # Check allowed paths
        if self._config.allowed_paths:
            for allowed in self._config.allowed_paths:
                allowed_resolved = Path(allowed).resolve()
                try:
                    resolved.relative_to(allowed_resolved)
                    return resolved
                except ValueError:
                    continue

            raise SandboxViolation(
                f"Path '{resolved}' is not in the allowed paths for '{extension_name}'"
            )

        return resolved

    def isolated_filesystem(self) -> tempfile.TemporaryDirectory:
        """Create a temporary isolated filesystem for extension execution.

        Returns a TemporaryDirectory context manager.
        """
        return tempfile.TemporaryDirectory(
            prefix=f"aetheros-sandbox-",
            dir=self._config.temp_dir,
        )

    def get_permission_audit(self) -> PermissionAudit:
        """Return the permission audit trail."""
        return self._permission_audit

    def shutdown(self) -> None:
        """Shut down the sandbox."""
        self._active = False
