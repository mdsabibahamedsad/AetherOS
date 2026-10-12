"""
Filesystem Security for AetherOS
================================

Strict filesystem boundaries for agents and tools (master security spec
steps 23-25):

    - allowlist / denylist path rules with canonical path validation
    - read-only vs read/write path sets
    - delete restrictions
    - symlink resolution and protection
    - path-traversal defense (``../``, ``..\\``, encoded traversal,
      device paths, alternate data streams)
    - protected paths that are never exposed to general-purpose agents
      (credentials, private keys, browser profiles, OS config, SSH dirs,
      cloud credentials, AetherOS internals)

Rules are enforced by deterministic code, never by the model. ``resolve``
always returns the canonical final path before any access is granted.

Usage::

    from aetheros_security.filesystem import (
        FilesystemSecurity, FilesystemAccess, PROTECTED_PATH_PATTERNS,
    )

    fs = FilesystemSecurity()
    fs.allow("workspace/**", access=FilesystemAccess.READ_WRITE)
    fs.deny("**/.env")
    assert fs.can_read("workspace/notes.md")
    assert not fs.can_read("/etc/passwd")
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FilesystemAccess(Enum):
    """Filesystem access mode for a path rule."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    EXECUTE = "execute"
    NONE = "none"


#: Sensitive path patterns never exposed to general-purpose agents. These
#: are matched against the canonicalized path (lowercase on Windows).
PROTECTED_PATH_PATTERNS = [
    "**/.ssh/**",
    "**/.ssh/*",
    "**/.aws/credentials",
    "**/.aws/*",
    "**/.config/gcloud/**",
    "**/.config/gcloud/*",
    "**/.azure/**",
    "**/.azure/*",
    "**/.gnupg/**",
    "**/.gnupg/*",
    "**/.kube/**",
    "**/.kube/*",
    "**/.docker/config.json",
    "**/id_rsa*",
    "**/id_dsa*",
    "**/id_ecdsa*",
    "**/id_ed25519*",
    "**/*.pem",
    "**/*.key",
    "**/*.pfx",
    "**/*.p12",
    "**/known_hosts",
    "**/authorized_keys",
    "**/.netrc",
    "**/.pgpass",
    "**/secrets.vault",
    "**/secrets_index.json",
    "**/.encryption_key",
    "**/.session_secret",
    "**/auth_accounts.json",
    "**/credentials.json",
    "**/client_secret*.json",
    "**/.aetheros/.env",
    "**/.aetheros/config.yaml",
    "**/.env",
    "**/.env.*",
    "**/history",  # shell history
    "**/.bash_history",
    "**/.zsh_history",
    "**/.git-credentials",
    "**/Cookies",
    "**/Local State",  # Chrome profile
    "**/Login Data",
]

#: Encoding bypasses and traversal fragments that must be rejected.
_TRAVERSAL_FRAGMENTS = (
    "..", "/..", "\\..", "../", "..\\", "..%2f", "..%5c", "%2e%2e",
    "%252e", "%c0%ae%c0%ae",
)

#: Device paths (Windows) — reject when a bare device name is the root.
_DEVICE_PATH_RE = re.compile(r"^(?:\\\\\?\\)?[A-Za-z]:$")

#: Alternate data stream suffix (Windows) — reject ``file:stream``.
_ADS_SUFFIX_RE = re.compile(r":([^/\\]+)$")


class FilesystemAccessError(Exception):
    """Raised when a filesystem access is denied or a path is invalid."""


@dataclass
class PathCheckResult:
    """Result of a path access check."""
    allowed: bool
    path: str
    operation: str = "read"
    reason: str = ""
    canonical: str = ""

    @property
    def ok(self) -> bool:
        return self.allowed


@dataclass
class PathRule:
    """A path access rule."""
    pattern: str
    access: FilesystemAccess = FilesystemAccess.READ_WRITE
    note: str = ""


class FilesystemSecurity:
    """Enforces filesystem access boundaries.

    Rules:
        - Protected-path patterns are always denied first (highest priority).
        - Explicit deny rules next.
        - Explicit allow rules gate access; without any allow rule,
          everything is denied (zero-trust default).
    """

    def __init__(self) -> None:
        self._allow_rules: List[PathRule] = []
        self._deny_rules: List[PathRule] = []
        self._protected_patterns: List[str] = list(PROTECTED_PATH_PATTERNS)
        self._resolve_symlinks = True

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def allow(self, pattern: str, access: FilesystemAccess = FilesystemAccess.READ_WRITE,
              note: str = "") -> None:
        if isinstance(access, str):
            try:
                access = FilesystemAccess(access)
            except ValueError:
                access = FilesystemAccess.NONE
        self._allow_rules.append(PathRule(pattern, access, note))

    def deny(self, pattern: str, note: str = "") -> None:
        self._deny_rules.append(PathRule(pattern, FilesystemAccess.NONE, note))

    def add_protected(self, pattern: str) -> None:
        self._protected_patterns.append(pattern)

    def set_symlink_resolution(self, enabled: bool) -> None:
        self._resolve_symlinks = enabled

    # ------------------------------------------------------------------
    # Canonicalization (step 25)
    # ------------------------------------------------------------------

    def resolve(self, path: str) -> str:
        """Canonicalize a path, rejecting traversal and other bypasses.

        Raises:
            FilesystemAccessError: If the path contains traversal fragments,
                device paths, or alternate data streams.
        """
        if not path:
            raise FilesystemAccessError("Empty path")
        if isinstance(path, os.PathLike):
            path = os.fspath(path)
        if path.startswith(("\\\\", "//")) and not path.startswith(("\\\\?\\", "//?/")):
            raise FilesystemAccessError(f"UNC path rejected: {path}")
        if _ADS_SUFFIX_RE.search(path):
            raise FilesystemAccessError(f"Alternate data stream rejected: {path}")

        # Reject traversal fragments before normalization (double-encoding
        # and raw forms).
        lowered = path.lower()
        for frag in _TRAVERSAL_FRAGMENTS:
            if frag in lowered:
                raise FilesystemAccessError(f"Path traversal rejected: {path}")

        try:
            resolved = str(Path(path).resolve())
        except (OSError, RuntimeError) as exc:
            raise FilesystemAccessError(f"Cannot resolve path: {path}: {exc}") from exc

        # After resolution, check for device-root and trailing separators.
        if _DEVICE_PATH_RE.match(resolved):
            raise FilesystemAccessError(f"Device path rejected: {resolved}")
        return resolved

    def safe_resolve(self, path: str) -> Tuple[bool, str]:
        """Non-raising variant of :meth:`resolve`.

        Returns:
            (ok, canonical_or_error_message)
        """
        try:
            return True, self.resolve(path)
        except FilesystemAccessError as exc:
            return False, str(exc)

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def _match(self, pattern: str, path: str) -> bool:
        """Glob match a pattern against a canonical path.

        A relative pattern (e.g. ``workspace/**``) is matched against both
        the full canonical path and the tail of the path, so it works no
        matter where the workspace is mounted. An absolute pattern matches
        only against the full path.
        """
        import fnmatch
        norm_pattern = pattern.replace("\\", "/")
        norm_path = path.replace("\\", "/")
        is_absolute = norm_pattern.startswith("/") or (
            len(norm_pattern) >= 2 and norm_pattern[1] == ":"
        )

        def _glob(norm_pattern: str, norm_path: str) -> bool:
            # ``**`` alone matches everything.
            if norm_pattern == "**":
                return True
            # ``**/rest`` matches ``rest`` at any depth (also at the root).
            if norm_pattern.startswith("**/"):
                rest = norm_pattern[3:]
                parts = norm_path.split("/")
                for i in range(len(parts)):
                    tail = "/".join(parts[i:])
                    if _glob(rest, tail):
                        return True
                return False
            if norm_pattern.endswith("/**"):
                prefix = norm_pattern[:-3]
                if prefix == "":
                    return True
                return (norm_path == prefix.rstrip("/")
                        or norm_path.startswith(prefix.rstrip("/") + "/"))
            return fnmatch.fnmatch(norm_path, norm_pattern) or \
                fnmatch.fnmatch(norm_path, norm_pattern + "/**")

        if is_absolute:
            return _glob(norm_pattern, norm_path)
        # Relative pattern: try the full path and every suffix tail.
        if _glob(norm_pattern, norm_path):
            return True
        segments = norm_path.split("/")
        for i in range(1, len(segments)):
            tail = "/".join(segments[i:])
            if _glob(norm_pattern, tail):
                return True
        return False

    def _is_protected(self, path: str) -> bool:
        lowered = path.lower().replace("\\", "/")
        for pattern in self._protected_patterns:
            pat = pattern.replace("\\", "/").lower()
            if self._match(pat, lowered):
                return True
        return False

    def check(self, path: str, operation: str = "read") -> PathCheckResult:
        """Check whether ``operation`` is allowed on a canonical path.

        Operation: read | write | delete | execute. Writes imply read;
        deletes require read + write.
        """
        try:
            canonical = self.resolve(path)
        except FilesystemAccessError as exc:
            return PathCheckResult(False, path, operation, str(exc))

        # Protected paths first.
        if self._is_protected(canonical):
            return PathCheckResult(False, path, operation,
                                   "path is protected", canonical)

        # Explicit denies.
        for rule in self._deny_rules:
            if self._match(rule.pattern, canonical):
                return PathCheckResult(False, path, operation,
                                       rule.note or "path denied", canonical)

        # Allow rules gate everything.
        allowed = False
        max_access = None
        for rule in self._allow_rules:
            if self._match(rule.pattern, canonical):
                allowed = True
                if max_access is None or _access_rank(rule.access) > _access_rank(max_access):
                    max_access = rule.access

        if not allowed or max_access is None:
            return PathCheckResult(False, path, operation, "no matching allow rule",
                                   canonical)
        if max_access == FilesystemAccess.NONE:
            return PathCheckResult(False, path, operation, "access none", canonical)
        if max_access == FilesystemAccess.READ_ONLY and operation != "read":
            return PathCheckResult(False, path, operation, "read-only path", canonical)
        if max_access == FilesystemAccess.EXECUTE and operation not in ("execute", "read"):
            return PathCheckResult(False, path, operation, "execute-only path", canonical)
        return PathCheckResult(True, path, operation, "", canonical)

    def can_read(self, path: str) -> bool:
        return self.check(path, "read").allowed

    def can_write(self, path: str) -> bool:
        return self.check(path, "write").allowed

    def can_delete(self, path: str) -> bool:
        return self.check(path, "delete").allowed

    def can_execute(self, path: str) -> bool:
        return self.check(path, "execute").allowed

    def get_stats(self) -> Dict[str, Any]:
        return {
            "allow_rules": len(self._allow_rules),
            "deny_rules": len(self._deny_rules),
            "protected_patterns": len(self._protected_patterns),
            "symlink_resolution": self._resolve_symlinks,
        }


def _access_rank(access: FilesystemAccess) -> int:
    return {
        FilesystemAccess.NONE: 0,
        FilesystemAccess.READ_ONLY: 1,
        FilesystemAccess.EXECUTE: 2,
        FilesystemAccess.READ_WRITE: 3,
    }.get(access, 0)


# Global filesystem security
_filesystem_security: FilesystemSecurity | None = None


def get_filesystem_security() -> FilesystemSecurity:
    """Return the global FilesystemSecurity singleton."""
    global _filesystem_security
    if _filesystem_security is None:
        _filesystem_security = FilesystemSecurity()
    return _filesystem_security