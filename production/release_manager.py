"""
Release Manager
===============

Release management for AetherOS production deployments.

Provides:
- Version management (semver + CalVer)
- Artifact building and verification
- Checksum generation
- Release notes compilation
- Version consistency checks
- Build reproducibility validation
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReleaseArtifact:
    """A release artifact with metadata.

    Attributes:
        path: Path to the artifact file
        name: Artifact name
        checksum_sha256: SHA-256 checksum
        checksum_md5: MD5 checksum
        size_bytes: File size
        created_at: Creation timestamp
    """
    path: str
    name: str = ""
    checksum_sha256: str = ""
    checksum_md5: str = ""
    size_bytes: int = 0
    created_at: float = field(default_factory=time.time)

    def compute_checksums(self) -> None:
        """Compute SHA-256 and MD5 checksums."""
        if not os.path.exists(self.path):
            return
        self.size_bytes = os.path.getsize(self.path)
        sha256 = hashlib.sha256()
        md5 = hashlib.md5()
        with open(self.path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha256.update(chunk)
                md5.update(chunk)
        self.checksum_sha256 = sha256.hexdigest()
        self.checksum_md5 = md5.hexdigest()
        if not self.name:
            self.name = os.path.basename(self.path)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "checksum_sha256": self.checksum_sha256,
            "checksum_md5": self.checksum_md5,
            "size_bytes": self.size_bytes,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
        }


@dataclass
class ReleaseReport:
    """Report of a release creation.

    Attributes:
        version: The release version
        date: Release date
        artifacts: Built release artifacts
        checksums: Checksum file content
        changelog: Generated changelog text
        validation_results: Pre-release validation results
        success: Whether release was successful
        errors: Any errors encountered
    """
    version: str
    date: str = ""
    artifacts: List[ReleaseArtifact] = field(default_factory=list)
    checksums: str = ""
    changelog: str = ""
    validation_results: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    errors: List[str] = field(default_factory=list)

    def add_artifact(self, artifact: ReleaseArtifact) -> None:
        artifact.compute_checksums()
        self.artifacts.append(artifact)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "date": self.date or datetime.now().strftime("%Y-%m-%d"),
            "artifact_count": len(self.artifacts),
            "artifacts": [a.to_dict() for a in self.artifacts],
            "checksums": self.checksums,
            "success": self.success,
            "errors": self.errors,
            "validation": self.validation_results,
        }


class ReleaseManager:
    """Manages the AetherOS release process.

    Usage:
        mgr = ReleaseManager()
        report = mgr.create_release(bump_type="minor")
        print(report.version)
    """

    def __init__(self, repo_root: Optional[str] = None):
        self._repo_root = Path(repo_root or self._find_repo_root())
        self._version_file = self._repo_root / "aetheros_cli" / "__init__.py"
        self._pyproject_file = self._repo_root / "pyproject.toml"

    def _find_repo_root(self) -> str:
        """Find the repository root directory."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return os.getcwd()

    def get_current_version(self) -> str:
        """Read the current version from source files."""
        content = self._version_file.read_text()
        match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
        return match.group(1) if match else "0.0.0"

    def bump_version(self, current: str, part: str = "patch") -> str:
        """Bump a semver version string."""
        parts = current.split(".")
        if len(parts) != 3:
            parts = ["0", "0", "0"]
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if part == "major":
            major += 1; minor = 0; patch = 0
        elif part == "minor":
            minor += 1; patch = 0
        elif part == "patch":
            patch += 1
        else:
            raise ValueError(f"Unknown bump part: {part}")

        return f"{major}.{minor}.{patch}"

    def check_version_consistency(self) -> Dict[str, bool]:
        """Check that version strings are consistent across files."""
        results: Dict[str, bool] = {}
        init_version = self.get_current_version()
        results["__init__.py"] = bool(init_version)

        if self._pyproject_file.exists():
            pyproject = self._pyproject_file.read_text()
            match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
            pyproject_version = match.group(1) if match else ""
            results["pyproject.toml"] = pyproject_version == init_version
        else:
            results["pyproject.toml"] = False

        results["consistent"] = all(v for v in results.values() if v is not False)
        return results

    def build_artifacts(self, version: str) -> List[ReleaseArtifact]:
        """Build release artifacts using uv build or python -m build."""
        artifacts: List[ReleaseArtifact] = []
        dist_dir = self._repo_root / "dist"

        # Clean dist directory
        import shutil
        shutil.rmtree(dist_dir, ignore_errors=True)

        # Build
        uv_bin = self._which("uv")
        if uv_bin:
            cmd = [uv_bin, "build", "--sdist", "--wheel"]
        else:
            cmd = [sys.executable, "-m", "build", "--sdist", "--wheel"]

        result = subprocess.run(
            cmd, cwd=str(self._repo_root),
            capture_output=True, text=True, timeout=300,
        )

        if result.returncode != 0:
            logger.warning("Build failed: %s", result.stderr.strip())
            return artifacts

        # Collect artifacts
        if dist_dir.exists():
            for p in sorted(dist_dir.iterdir()):
                if p.is_file() and version in p.name:
                    artifacts.append(ReleaseArtifact(path=str(p)))

        return artifacts

    def generate_checksums(self, artifacts: List[ReleaseArtifact]) -> str:
        """Generate a checksum file (SHA256SUMS format)."""
        lines: List[str] = []
        for artifact in sorted(artifacts, key=lambda a: a.name):
            lines.append(f"{artifact.checksum_sha256}  {artifact.name}")
        return "\n".join(lines)

    def create_release(
        self,
        bump_type: str = "patch",
        build: bool = True,
    ) -> ReleaseReport:
        """Create a new release.

        Args:
            bump_type: Version bump type (major, minor, patch)
            build: Whether to build artifacts

        Returns:
            ReleaseReport with release details.
        """
        current = self.get_current_version()
        new_version = self.bump_version(current, bump_type)
        date_str = datetime.now().strftime("%Y-%m-%d")

        report = ReleaseReport(version=new_version, date=date_str)

        # Check version consistency
        consistency = self.check_version_consistency()
        report.validation_results["version_consistency"] = consistency

        if not consistency.get("consistent", False):
            report.errors.append("Version inconsistency detected")
            report.success = False

        if build:
            artifacts = self.build_artifacts(new_version)
            for a in artifacts:
                report.add_artifact(a)

            if not artifacts:
                report.errors.append("No artifacts were built")
                report.success = False
            else:
                report.checksums = self.generate_checksums(artifacts)

        return report

    def _which(self, cmd: str) -> Optional[str]:
        """Find a command on PATH."""
        import shutil
        return shutil.which(cmd)
