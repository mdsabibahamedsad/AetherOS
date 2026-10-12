"""
Packaging Engine — builds and packages deliverables.

Handles:
  - Building distributable packages
  - Version bumping
  - Dependency resolution for packaging
  - Artifact generation
"""

from __future__ import annotations

import enum
import logging
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class PackageFormat(enum.Enum):
    """Supported package output formats."""
    WHEEL = "wheel"
    SOURCE_DIST = "sdist"
    DIRECTORY = "directory"
    DOCKER = "docker"
    ZIP = "zip"
    TAR = "tar"


@dataclass
class PackageArtifact:
    """A build artifact produced by packaging.

    Attributes:
        path: Path to the artifact file
        format: Package format
        size_bytes: File size
        checksum: SHA-256 checksum
    """
    path: str = ""
    format: PackageFormat = PackageFormat.WHEEL
    size_bytes: int = 0
    checksum: str = ""


@dataclass
class PackageManifest:
    """A package manifest describing the deliverable.

    Attributes:
        id: Unique manifest ID
        name: Package name
        version: Package version
        description: Package description
        author: Package author
        python_requires: Python version requirement
        dependencies: List of dependencies
        artifacts: Build artifacts
        built_at: When the package was built
        build_successful: Whether the build succeeded
        build_log: Build output log
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    python_requires: str = ">=3.10"
    dependencies: List[str] = field(default_factory=list)
    artifacts: List[PackageArtifact] = field(default_factory=list)
    built_at: Optional[float] = None
    build_successful: bool = False
    build_log: str = ""


class PackagingEngine:
    """Builds and packages deliverables.

    Supports multiple package formats and integrates with
    existing build systems.

    Usage:
        engine = PackagingEngine(event_bus, project_root="/path/to/project")
        manifest = engine.build_wheel()
        print(f"Built: {[a.path for a in manifest.artifacts]}")
    """

    def __init__(self, event_bus: Optional[EventBus] = None,
                 project_root: Optional[str] = None):
        self._event_bus = event_bus
        self._project_root = Path(project_root).resolve() if project_root else Path.cwd()
        self._manifests: Dict[str, PackageManifest] = {}

    def build_wheel(self, output_dir: str = "dist") -> PackageManifest:
        """Build a Python wheel package.

        Args:
            output_dir: Output directory for the built package

        Returns:
            PackageManifest with build results
        """
        manifest = PackageManifest(
            name=self._project_root.name,
        )

        output_path = self._project_root / output_dir
        output_path.mkdir(parents=True, exist_ok=True)

        cmd = ["python", "-m", "build", "--wheel",
               f"--outdir={output_path}",
               str(self._project_root)]

        manifest.build_log = f"Running: {' '.join(cmd)}\n"

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self._project_root,
            )

            manifest.build_log += result.stdout + result.stderr

            if result.returncode == 0:
                manifest.build_successful = True
                manifest.built_at = time.time()

                # Find built wheel
                for wheel in sorted(output_path.glob("*.whl")):
                    import hashlib
                    manifest.artifacts.append(PackageArtifact(
                        path=str(wheel),
                        format=PackageFormat.WHEEL,
                        size_bytes=wheel.stat().st_size,
                        checksum=hashlib.sha256(wheel.read_bytes()).hexdigest()[:16],
                    ))

                # Also find source dist
                for sdist in sorted(output_path.glob("*.tar.gz")):
                    import hashlib
                    manifest.artifacts.append(PackageArtifact(
                        path=str(sdist),
                        format=PackageFormat.SOURCE_DIST,
                        size_bytes=sdist.stat().st_size,
                        checksum=hashlib.sha256(sdist.read_bytes()).hexdigest()[:16],
                    ))

                logger.info(
                    "PackagingEngine: built %d artifacts for %s",
                    len(manifest.artifacts), manifest.name,
                )
            else:
                manifest.build_successful = False
                logger.error("PackagingEngine: build failed for %s", manifest.name)

        except FileNotFoundError:
            manifest.build_log += "Build tool not found. Install with: pip install build"
            manifest.build_successful = False
        except subprocess.TimeoutExpired:
            manifest.build_log += "Build timed out"
            manifest.build_successful = False
        except Exception as exc:
            manifest.build_log += f"Build error: {exc}"
            manifest.build_successful = False

        self._manifests[manifest.id] = manifest

        if self._event_bus:
            self._event_bus.emit_async("engineering.package_built", {
                "manifest_id": manifest.id,
                "name": manifest.name,
                "success": manifest.build_successful,
                "artifact_count": len(manifest.artifacts),
            })

        return manifest

    def bump_version(self, part: str = "patch") -> Optional[str]:
        """Bump the project version.

        Args:
            part: Version part to bump (major, minor, patch)

        Returns:
            New version string, or None if version file not found
        """
        pyproject = self._project_root / "pyproject.toml"
        if not pyproject.exists():
            logger.warning("PackagingEngine: no pyproject.toml found")
            return None

        try:
            import re

            content = pyproject.read_text(encoding="utf-8")
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if not match:
                logger.warning("PackagingEngine: no version found in pyproject.toml")
                return None

            current_version = match.group(1)
            parts = current_version.split(".")
            if len(parts) != 3:
                logger.warning("PackagingEngine: unexpected version format: %s",
                              current_version)
                return None

            major, minor, patch = parts

            if part == "major":
                new_version = f"{int(major) + 1}.0.0"
            elif part == "minor":
                new_version = f"{major}.{int(minor) + 1}.0"
            else:
                new_version = f"{major}.{minor}.{int(patch) + 1}"

            new_content = content.replace(
                f'version = "{current_version}"',
                f'version = "{new_version}"',
            )
            pyproject.write_text(new_content, encoding="utf-8")

            logger.info("PackagingEngine: version bumped %s -> %s",
                       current_version, new_version)
            return new_version

        except Exception as exc:
            logger.error("PackagingEngine: version bump failed: %s", exc)
            return None

    def get_manifest(self, manifest_id: str) -> Optional[PackageManifest]:
        """Get a package manifest by ID."""
        return self._manifests.get(manifest_id)

    def list_manifests(self) -> List[PackageManifest]:
        """List all build manifests."""
        return sorted(
            self._manifests.values(),
            key=lambda m: m.built_at or 0,
            reverse=True,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_builds": len(self._manifests),
            "successful_builds": sum(1 for m in self._manifests.values() if m.build_successful),
            "total_artifacts": sum(len(m.artifacts) for m in self._manifests.values()),
        }
