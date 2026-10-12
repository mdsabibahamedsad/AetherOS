"""
Release Management for AetherOS
===============================

Release candidate, stable v1.0, LTS, Enterprise/Community editions.

Usage::

    from aetheros_production.release import ReleaseManager

    manager = ReleaseManager()
    info = manager.get_version_info()
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VersionInfo:
    """Version information."""
    version: str
    channel: str
    edition: str
    release_date: str
    changelog: str = ""
    known_issues: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    migration_notes: str = ""


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ReleaseManager:
    """Manages releases for AetherOS.

    Usage::

        manager = ReleaseManager()

        # Get version info
        info = manager.get_version_info()

        # Generate release notes
        notes = manager.generate_release_notes()

        # Produce a release manifest with artifact checksums
        manifest = manager.create_release_manifest()
    """

    def __init__(self) -> None:
        from aetheros_constants import get_aetheros_home
        from aetheros_production import get_version
        self._home = get_aetheros_home()
        self._current_version = get_version()
        self._edition = "community"

    def get_version_info(self) -> Dict[str, Any]:
        """Get version information."""
        return {
            "version": self._current_version,
            "channel": "stable",
            "edition": self._edition,
            "release_date": self._release_date(),
            "python_version": self._get_python_version(),
            "platform": self._get_platform(),
        }

    def _release_date(self) -> str:
        """Return today's date as the release date."""
        return time.strftime("%Y-%m-%d")

    def _get_python_version(self) -> str:
        """Get Python version."""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _get_platform(self) -> str:
        """Get platform information."""
        import platform
        return f"{platform.system()} {platform.release()}"

    def create_release_manifest(
        self,
        output_dir: Optional[Path] = None,
        channel: str = "stable",
        changelog: str = "",
        known_issues: Optional[List[str]] = None,
        breaking_changes: Optional[List[str]] = None,
        migration_notes: str = "",
        artifacts: Optional[List[Path]] = None,
    ) -> Dict[str, Any]:
        """Create a release manifest with artifact checksums.

        Produces a JSON document containing the release metadata plus a
        ``checksums`` map (SHA-256) for every supplied artifact. The
        manifest is also written to ``<output_dir>/release.json`` when an
        output directory is given.
        """
        output_dir = Path(output_dir) if output_dir else self._home / "releases"
        output_dir.mkdir(parents=True, exist_ok=True)

        checksums: Dict[str, str] = {}
        if artifacts:
            for artifact in artifacts:
                artifact = Path(artifact)
                if artifact.exists() and artifact.is_file():
                    checksums[artifact.name] = _sha256_file(artifact)

        manifest = {
            "schema_version": 1,
            "version": self._current_version,
            "channel": channel,
            "edition": self._edition,
            "release_date": self._release_date(),
            "changelog": changelog or self.get_changelog(),
            "known_issues": known_issues if known_issues is not None else self.get_known_issues(),
            "breaking_changes": breaking_changes if breaking_changes is not None else self.get_breaking_changes(),
            "migration_notes": migration_notes or self.get_migration_guide(),
            "artifacts": [Path(a).name for a in (artifacts or []) if Path(a).exists()],
            "checksums": checksums,
        }

        manifest_path = output_dir / "release.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        return manifest

    def get_breaking_changes(self) -> List[str]:
        """Get breaking changes."""
        return [
            "Plugin API v2 requires updating custom plugins",
            "MCP server configuration format updated",
        ]

    def generate_release_notes(self) -> str:
        """Generate release notes."""
        return f"""# AetherOS v{self._current_version} Release Notes

## What's New

- Complete Developer Platform with SDK ecosystem
- Plugin system with sandboxing and permissions
- MCP server support
- Workflow engine
- Voice interaction
- Knowledge management
- Multi-language SDK support (Python, TypeScript, JavaScript, Go, Rust, C#, Java)
- Marketplace for extensions
- Theme engine
- Enterprise features

## Improvements

- Performance optimizations
- Security hardening
- Documentation improvements
- Bug fixes

## Known Issues

- Some advanced features require additional configuration
- Voice engine may need calibration on some systems

## Migration Guide

See MIGRATION.md for upgrade instructions.

## Support

- Documentation: https://docs.aetheros.dev
- Issues: https://github.com/aetheros/aetheros/issues
- Community: https://discord.gg/aetheros
"""

    def get_changelog(self) -> str:
        """Get changelog."""
        changelog_path = Path("CHANGELOG.md")
        if changelog_path.exists():
            return changelog_path.read_text(encoding="utf-8")
        return "# Changelog\n\nNo changelog available."

    def get_known_issues(self) -> List[str]:
        """Get known issues."""
        return [
            "Voice engine calibration may be needed on some systems",
            "Some enterprise features require additional configuration",
            "Docker deployment may need network configuration",
        ]

    def get_migration_guide(self) -> str:
        """Get migration guide."""
        return """# Migration Guide

## Upgrading from Previous Versions

### Step 1: Backup

```bash
aetheros backup
```

### Step 2: Update

```bash
aetheros update
```

### Step 3: Verify

```bash
aetheros doctor
```

## Breaking Changes

- Plugin API v2 requires updating custom plugins
- MCP server configuration format updated

## Rollback

If you encounter issues:

```bash
aetheros rollback --to-version 1.0.0
```
"""

    def get_support_matrix(self) -> Dict[str, Any]:
        """Get support matrix."""
        return {
            "platforms": {
                "Windows": {"min_version": "10", "status": "supported"},
                "macOS": {"min_version": "12", "status": "supported"},
                "Linux": {"min_version": "Ubuntu 20.04", "status": "supported"},
                "WSL": {"min_version": "2", "status": "supported"},
                "Docker": {"min_version": "20.10", "status": "supported"},
            },
            "python_versions": ["3.9", "3.10", "3.11", "3.12"],
            "editions": ["community", "enterprise"],
        }

    def get_license_summary(self) -> Dict[str, Any]:
        """Get license summary."""
        return {
            "aetheros": "MIT License",
            "dependencies": {
                "openai": "MIT License",
                "anthropic": "MIT License",
                "litellm": "MIT License",
                "fastapi": "MIT License",
                "pydantic": "MIT License",
            },
        }


# Global release manager
_release_manager: Optional[ReleaseManager] = None


def get_release_manager() -> ReleaseManager:
    """Return the global ReleaseManager singleton."""
    global _release_manager
    if _release_manager is None:
        _release_manager = ReleaseManager()
    return _release_manager
