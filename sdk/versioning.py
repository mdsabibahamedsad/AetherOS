"""
Semantic Versioning Utilities
=============================

Implements semantic version (SemVer 2.0) parsing, comparison, and range
matching. Used by the compatibility layer to determine whether an
extension is compatible with the current AetherOS/SDK version.

Supports:
    - Version parsing (``1.2.3``, ``1.2.3-alpha.1``)
    - Version comparison (``<``, ``<=``, ``==``, ``>=``, ``>``, ``!=``)
    - Version range matching (``>=1.0.0,<2.0.0``)
    - Breaking change detection
    - Migration warning generation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# Regex for semver 2.0: major.minor.patch[-prerelease][+build]
_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)"
    r"\.(?P<minor>0|[1-9]\d*)"
    r"\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


class Version:
    """A semantic version (SemVer 2.0)."""

    def __init__(self, version_string: str) -> None:
        m = _SEMVER_RE.match(version_string.strip())
        if not m:
            raise ValueError(
                f"Invalid version string: '{version_string}'. "
                f"Expected SemVer format (e.g., '1.2.3' or '1.2.3-alpha.1')."
            )
        self._major = int(m.group("major"))
        self._minor = int(m.group("minor"))
        self._patch = int(m.group("patch"))
        self._prerelease = m.group("prerelease") or ""
        self._build = m.group("build") or ""
        self._string = version_string.strip()

    @property
    def major(self) -> int:
        return self._major

    @property
    def minor(self) -> int:
        return self._minor

    @property
    def patch(self) -> int:
        return self._patch

    @property
    def prerelease(self) -> str:
        return self._prerelease

    @property
    def is_prerelease(self) -> bool:
        return bool(self._prerelease)

    def __str__(self) -> str:
        return self._string

    def __repr__(self) -> str:
        return f"Version('{self._string}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (
            self._major == other._major
            and self._minor == other._minor
            and self._patch == other._patch
            and self._prerelease == other._prerelease
        )

    def __lt__(self, other: "Version") -> bool:
        if self._major != other._major:
            return self._major < other._major
        if self._minor != other._minor:
            return self._minor < other._minor
        if self._patch != other._patch:
            return self._patch < other._patch
        # Prerelease versions have lower precedence
        if self._prerelease and not other._prerelease:
            return True
        if not self._prerelease and other._prerelease:
            return False
        if self._prerelease and other._prerelease:
            return self._prerelease < other._prerelease
        return False

    def __le__(self, other: "Version") -> bool:
        return self == other or self < other

    def __gt__(self, other: "Version") -> bool:
        return not (self <= other)

    def __ge__(self, other: "Version") -> bool:
        return not (self < other)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self._major, self._minor, self._patch, self._prerelease))


@dataclass
class VersionRange:
    """A range of acceptable versions.

    Format: ``>=1.0.0,<2.0.0`` means "at least 1.0.0 but less than 2.0.0".
    """

    min_version: Optional[Version] = None
    max_version: Optional[Version] = None
    include_min: bool = True
    include_max: bool = False

    @classmethod
    def parse(cls, range_string: str) -> "VersionRange":
        """Parse a version range string.

        Supported formats:
            ``>=1.0.0``          — at least 1.0.0
            ``>=1.0.0,<2.0.0``   — between 1.0.0 (inclusive) and 2.0.0 (exclusive)
            ``==1.0.0``          — exactly 1.0.0
            ``>=1.0.0,<=2.0.0``  — between 1.0.0 and 2.0.0 (both inclusive)
            ``*``                — any version
        """
        range_string = range_string.strip()
        if range_string == "*":
            return cls()

        parts = [p.strip() for p in range_string.split(",")]
        vr = cls()

        for part in parts:
            if part.startswith(">="):
                vr.min_version = Version(part[2:].strip())
                vr.include_min = True
            elif part.startswith(">"):
                vr.min_version = Version(part[1:].strip())
                vr.include_min = False
            elif part.startswith("<="):
                vr.max_version = Version(part[2:].strip())
                vr.include_max = True
            elif part.startswith("<"):
                vr.max_version = Version(part[1:].strip())
                vr.include_max = False
            elif part.startswith("=="):
                v = Version(part[2:].strip())
                vr.min_version = v
                vr.max_version = v
                vr.include_min = True
                vr.include_max = True
            elif part.startswith("!="):
                # Not-equal: handled separately — we don't encode it in the range
                raise ValueError("Range '!=' is not supported; use '==' for exact match")
            else:
                vr.min_version = Version(part)
                vr.include_min = True
                vr.include_max = False

        return vr

    def contains(self, version: Version) -> bool:
        """Check if *version* falls within this range."""
        if self.min_version is not None:
            if self.include_min:
                if version < self.min_version:
                    return False
            else:
                if version <= self.min_version:
                    return False
        if self.max_version is not None:
            if self.include_max:
                if version > self.max_version:
                    return False
            else:
                if version >= self.max_version:
                    return False
        return True

    def __str__(self) -> str:
        parts = []
        if self.min_version is not None:
            op = ">=" if self.include_min else ">"
            parts.append(f"{op}{self.min_version}")
        if self.max_version is not None:
            op = "<=" if self.include_max else "<"
            parts.append(f"{op}{self.max_version}")
        return ",".join(parts) if parts else "*"

    def __repr__(self) -> str:
        return f"VersionRange('{self}')"


@dataclass
class BreakingChange:
    """A record of a breaking change between versions."""
    version: str
    description: str
    migration_guide: str = ""
    affected_apis: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"[{self.version}] {self.description}"


@dataclass
class MigrationWarning:
    """A non-breaking deprecation warning."""
    version: str
    message: str
    api: str = ""
    alternative: str = ""

    def __str__(self) -> str:
        return f"[{self.version}] {self.api}: {self.message}"


# Registry of known breaking changes (populated by the SDK version)
_BREAKING_CHANGES: List[BreakingChange] = []

_MIGRATION_WARNINGS: List[MigrationWarning] = []


def register_breaking_change(change: BreakingChange) -> None:
    """Register a breaking change for SDK version tracking."""
    _BREAKING_CHANGES.append(change)


def register_migration_warning(warning: MigrationWarning) -> None:
    """Register a migration warning for deprecation notices."""
    _MIGRATION_WARNINGS.append(warning)


def get_breaking_changes(since_version: Optional[str] = None) -> List[BreakingChange]:
    """Return breaking changes, optionally filtered since a version."""
    if since_version is None:
        return list(_BREAKING_CHANGES)
    since = Version(since_version)
    return [c for c in _BREAKING_CHANGES if Version(c.version) > since]


def get_migration_warnings(current_version: str) -> List[MigrationWarning]:
    """Return migration warnings for APIs used by a specific version."""
    current = Version(current_version)
    return [w for w in _MIGRATION_WARNINGS if Version(w.version) <= current]
