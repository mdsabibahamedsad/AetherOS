"""
Dependency Manager — manages project dependencies and dependency graphs.

Handles:
  - Dependency discovery and analysis
  - Dependency graph construction
  - Version conflict detection
  - Vulnerability checking integration
  - Dependency update tracking
"""

from __future__ import annotations

import enum
import logging
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class DependencyStatus(enum.Enum):
    """Status of a dependency entry."""
    CURRENT = "current"
    OUTDATED = "outdated"
    VULNERABLE = "vulnerable"
    CONFLICTING = "conflicting"
    UNUSED = "unused"
    MISSING = "missing"


@dataclass
class DependencyVulnerability:
    """A known vulnerability in a dependency.

    Attributes:
        id: Vulnerability ID (CVE or similar)
        severity: Severity description
        description: Vulnerability description
        fixed_in: Version where this is fixed
        cvss_score: CVSS score if available
    """
    id: str = ""
    severity: str = "medium"
    description: str = ""
    fixed_in: str = ""
    cvss_score: float = 0.0


@dataclass
class DependencyEntry:
    """A single dependency entry.

    Attributes:
        name: Dependency name
        version: Current version
        latest_version: Latest available version
        required_version: Version constraint from config
        type: Dependency type (production, development, optional)
        status: Dependency status
        vulnerabilities: Known vulnerabilities
        used_by: Files that use this dependency
        source: How this dependency was discovered
        updated_at: When this entry was last checked
    """
    name: str = ""
    version: str = ""
    latest_version: str = ""
    required_version: str = ""
    type: str = "production"
    status: DependencyStatus = DependencyStatus.CURRENT
    vulnerabilities: List[DependencyVulnerability] = field(default_factory=list)
    used_by: List[str] = field(default_factory=list)
    source: str = ""
    updated_at: float = field(default_factory=time.time)


class DependencyManager:
    """Manages project dependencies.

    Provides dependency discovery, graph construction, version checking,
    and vulnerability scanning integration.

    Usage:
        mgr = DependencyManager(event_bus, project_root="/path/to/project")
        deps = mgr.discover()
        for dep in deps:
            print(f"{dep.name}: {dep.version}")
    """

    def __init__(self, event_bus: Optional[EventBus] = None,
                 project_root: Optional[str] = None):
        self._event_bus = event_bus
        self._project_root = Path(project_root).resolve() if project_root else Path.cwd()
        self._dependencies: Dict[str, DependencyEntry] = {}

    def discover(self, files: List[str] = None) -> List[DependencyEntry]:
        """Discover dependencies from project configuration files.

        Args:
            files: Specific files to scan (auto-detects common files if empty)

        Returns:
            List of discovered DependencyEntry objects
        """
        if files:
            target_files = [Path(f) for f in files]
        else:
            target_files = self._find_dependency_files()

        discovered = []

        for file_path in target_files:
            if not file_path.exists():
                continue

            try:
                deps = self._parse_file(file_path)
                discovered.extend(deps)

                for dep in deps:
                    existing = self._dependencies.get(dep.name)
                    if existing:
                        # Merge information
                        existing.version = existing.version or dep.version
                        existing.required_version = dep.required_version or existing.required_version
                        existing.type = dep.type or existing.type
                        existing.source = existing.source or dep.source
                    else:
                        self._dependencies[dep.name] = dep

            except Exception as exc:
                logger.warning("DependencyManager: failed to parse %s: %s",
                              file_path, exc)

        logger.info(
            "DependencyManager: discovered %d dependencies from %d files",
            len(discovered), len(target_files),
        )

        if self._event_bus:
            self._event_bus.emit_async("engineering.dependencies_discovered", {
                "count": len(discovered),
                "files": [str(f) for f in target_files],
            })

        return discovered

    def _find_dependency_files(self) -> List[Path]:
        """Find common dependency configuration files."""
        files = []
        candidates = [
            "pyproject.toml",
            "requirements.txt",
            "requirements-dev.txt",
            "setup.py",
            "setup.cfg",
            "Pipfile",
            "Pipfile.lock",
            "package.json",
            "Cargo.toml",
            "go.mod",
            "go.sum",
        ]

        for candidate in candidates:
            path = self._project_root / candidate
            if path.exists():
                files.append(path)

        return files

    def _parse_file(self, file_path: Path) -> List[DependencyEntry]:
        """Parse a dependency file and extract entries."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        name = file_path.name

        if name == "pyproject.toml":
            return self._parse_pyproject(content)
        elif name == "requirements.txt" or name == "requirements-dev.txt":
            return self._parse_requirements(content, name == "requirements-dev.txt")
        elif name == "setup.py":
            return self._parse_setup_py(content)
        elif name == "package.json":
            return self._parse_package_json(content)
        elif name == "Cargo.toml":
            return self._parse_cargo_toml(content)
        elif name == "go.mod":
            return self._parse_go_mod(content)

        return []

    def _parse_pyproject(self, content: str) -> List[DependencyEntry]:
        """Parse dependencies from pyproject.toml."""
        deps = []

        # Parse project.dependencies
        dep_section = re.search(
            r'\[project\.dependencies\](.*?)(?=\[|$)',
            content, re.DOTALL,
        )
        if dep_section:
            for line in dep_section.group(1).splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    name = parts[0].strip().strip('"').strip("'")
                    version = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else "*"
                    deps.append(DependencyEntry(
                        name=name,
                        required_version=version,
                        type="production",
                        source="pyproject.toml",
                    ))

        return deps

    def _parse_requirements(self, content: str,
                            is_dev: bool = False) -> List[DependencyEntry]:
        """Parse dependencies from requirements.txt."""
        deps = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Handle version specifiers
            match = re.match(r'^([a-zA-Z0-9_.-]+)\s*([><=!~]+\s*.*)?$', line)
            if match:
                name = match.group(1)
                version = match.group(2) or "*"
                deps.append(DependencyEntry(
                    name=name,
                    required_version=version.strip(),
                    type="development" if is_dev else "production",
                    source="requirements.txt",
                ))

        return deps

    def _parse_setup_py(self, content: str) -> List[DependencyEntry]:
        """Parse dependencies from setup.py."""
        deps = []

        # Parse install_requires
        match = re.search(
            r'install_requires\s*=\s*\[(.*?)\]',
            content, re.DOTALL,
        )
        if match:
            for line in match.group(1).splitlines():
                line = line.strip().strip('"').strip("'").strip(",")
                if line:
                    match2 = re.match(r'^([a-zA-Z0-9_.-]+)(.*)', line)
                    if match2:
                        deps.append(DependencyEntry(
                            name=match2.group(1),
                            required_version=match2.group(2).strip().strip('"').strip("'") or "*",
                            type="production",
                            source="setup.py",
                        ))

        return deps

    def _parse_package_json(self, content: str) -> List[DependencyEntry]:
        """Parse dependencies from package.json."""
        deps = []

        try:
            import json
            data = json.loads(content)

            for dep_type, section in [("production", "dependencies"),
                                       ("development", "devDependencies")]:
                for name, version in data.get(section, {}).items():
                    deps.append(DependencyEntry(
                        name=name,
                        required_version=str(version),
                        type=dep_type,
                        source="package.json",
                    ))
        except json.JSONDecodeError:
            pass

        return deps

    def _parse_cargo_toml(self, content: str) -> List[DependencyEntry]:
        """Parse dependencies from Cargo.toml."""
        deps = []
        dep_section = re.search(
            r'\[dependencies\](.*?)(?=\[|$)',
            content, re.DOTALL,
        )
        if dep_section:
            for line in dep_section.group(1).splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    name = parts[0].strip()
                    version = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else "*"
                    deps.append(DependencyEntry(
                        name=name,
                        required_version=version,
                        type="production",
                        source="Cargo.toml",
                    ))

        return deps

    def _parse_go_mod(self, content: str) -> List[DependencyEntry]:
        """Parse dependencies from go.mod."""
        deps = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("require ") or line.startswith("\t"):
                line = line.replace("require ", "").strip()
                parts = line.split()
                if len(parts) >= 2:
                    deps.append(DependencyEntry(
                        name=parts[0],
                        version=parts[1].strip('//'),
                        type="production",
                        source="go.mod",
                    ))

        return deps

    # ------------------------------------------------------------------
    # Dependency queries
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[DependencyEntry]:
        """Get a dependency by name."""
        return self._dependencies.get(name)

    def list_dependencies(self, type: Optional[str] = None,
                          status: Optional[DependencyStatus] = None) -> List[DependencyEntry]:
        """List dependencies, optionally filtered.

        Args:
            type: Filter by dependency type (production, development)
            status: Filter by status

        Returns:
            Filtered list of dependencies
        """
        results = list(self._dependencies.values())

        if type:
            results = [d for d in results if d.type == type]
        if status:
            results = [d for d in results if d.status == status]

        results.sort(key=lambda d: d.name)
        return results

    def get_vulnerable(self) -> List[DependencyEntry]:
        """Get dependencies with known vulnerabilities."""
        return [d for d in self._dependencies.values() if d.vulnerabilities]

    def get_outdated(self) -> List[DependencyEntry]:
        """Get dependencies that are outdated."""
        return [
            d for d in self._dependencies.values()
            if d.status == DependencyStatus.OUTDATED
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            "total_dependencies": len(self._dependencies),
            "by_type": {
                "production": sum(1 for d in self._dependencies.values()
                                  if d.type == "production"),
                "development": sum(1 for d in self._dependencies.values()
                                   if d.type == "development"),
            },
            "by_status": {
                s.value: sum(1 for d in self._dependencies.values()
                             if d.status == s)
                for s in DependencyStatus
            },
            "vulnerable_count": len(self.get_vulnerable()),
        }
