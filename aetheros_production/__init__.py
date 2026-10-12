"""
AetherOS Production Infrastructure
===================================

Production-ready infrastructure for AetherOS v1.0.

Modules:
    - quality: QA, testing, regression, smoke, integration, E2E, performance, stress, load
    - security: Dependency audit, secrets scan, static/dynamic analysis, permission/sandbox/plugin audit
    - performance: Startup time, memory/CPU/GPU optimization, background services, indexing
    - observability: Structured logging, metrics, health checks, diagnostics, crash reports
    - crash_recovery: Automatic restart, recovery mode, safe mode, diagnostic mode, rollback
    - backup: Automatic/incremental backup, snapshot, export, restore, disaster recovery
    - packaging: Windows/macOS/Linux installers, Docker, Homebrew, Winget, Chocolatey
    - update_system: Automatic/manual update, rollback, version history, release channels
    - installer: Polished installer with welcome screen, system check, setup wizard
    - documentation: User/Admin/Developer/Plugin/MCP guides, API/CLI reference
    - self_hosting: Docker Compose, Kubernetes, Helm, single binary, offline
    - enterprise: SSO, LDAP, SAML, audit logs, policy management, org deployment
    - monitoring: CPU/RAM/GPU/Disk/Network, agent/workflow/plugin/voice/knowledge health
    - ci_cd: GitHub Actions, release pipeline, security scan, artifact signing
    - signing: Digital signatures for executables, packages, extensions, plugins
    - accessibility: Keyboard navigation, screen reader, high contrast, localization
    - telemetry: Opt-in, transparent, privacy-first telemetry
    - support: Issue reporter, diagnostic bundle, feedback tool, bug report wizard
    - release: Release candidate, stable v1.0, LTS, Enterprise/Community editions

Usage::

    from aetheros_production import ProductionManager
    pm = ProductionManager()
    pm.run_full_audit()
"""

from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)


def _resolve_version() -> str:
    """Resolve the installed AetherOS version.

    Prefers the installed distribution metadata so packaging and update
    systems report the same version users actually have. Falls back to the
    ``pyproject.toml`` source of truth, then a hardcoded default.
    """
    try:
        from importlib.metadata import version
        return version("aetheros")
    except Exception:
        pass
    try:
        from pathlib import Path
        _pyproject = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
        if _pyproject.exists():
            for line in _pyproject.read_text("utf-8").splitlines():
                if line.lstrip().startswith("version ="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "0.0.0"


# Production version (single source of truth: installed distribution metadata)
__version__: Final[str] = _resolve_version()

# Release channels
RELEASE_CHANNELS = ["stable", "beta", "nightly"]

# Supported platforms
SUPPORTED_PLATFORMS = [
    "windows",
    "macos",
    "linux",
    "wsl",
    "docker",
    "self-hosted",
    "cloud",
]

# Supported package formats
PACKAGE_FORMATS = [
    "msi", "exe",           # Windows
    "dmg", "pkg",           # macOS
    "appimage", "deb", "rpm", "snap", "flatpak",  # Linux
    "docker",               # Docker
    "homebrew",             # macOS/Linux
    "winget", "chocolatey", # Windows
]


def get_version() -> str:
    """Return the production version."""
    return __version__


def get_release_channels() -> list[str]:
    """Return available release channels."""
    return list(RELEASE_CHANNELS)


def get_supported_platforms() -> list[str]:
    """Return supported platforms."""
    return list(SUPPORTED_PLATFORMS)


def get_package_formats() -> list[str]:
    """Return available package formats."""
    return list(PACKAGE_FORMATS)


class ProductionManager:
    """Main production manager for AetherOS.

    Usage::

        pm = ProductionManager()
        pm.run_quality_checks()
        pm.run_security_audit()
        pm.optimize_performance()
        pm.generate_packages()
    """

    def __init__(self) -> None:
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the production infrastructure."""
        if self._initialized:
            return

        logger.info("Initializing AetherOS Production Infrastructure v%s", __version__)
        self._initialized = True

    def run_quality_checks(self) -> dict:
        """Run all quality assurance checks."""
        from aetheros_production.quality import QualityManager
        manager = QualityManager()
        return manager.run_all_checks()

    def run_security_audit(self) -> dict:
        """Run all security audits."""
        from aetheros_production.security import SecurityAuditor
        auditor = SecurityAuditor()
        return auditor.run_full_audit()

    def optimize_performance(self) -> dict:
        """Run performance optimizations."""
        from aetheros_production.performance import PerformanceOptimizer
        optimizer = PerformanceOptimizer()
        return optimizer.run_optimizations()

    def get_health_status(self) -> dict:
        """Get system health status."""
        from aetheros_production.observability import HealthChecker
        checker = HealthChecker()
        return checker.get_full_health_status()

    def run_diagnostics(self) -> dict:
        """Run full diagnostics."""
        from aetheros_production.observability import DiagnosticsManager
        manager = DiagnosticsManager()
        return manager.run_diagnostics()

    def backup(self, backup_type: str = "full") -> dict:
        """Create a backup."""
        from aetheros_production.backup import BackupManager
        manager = BackupManager()
        return manager.create_backup(backup_type)

    def restore(self, backup_id: str) -> dict:
        """Restore from backup."""
        from aetheros_production.backup import BackupManager
        manager = BackupManager()
        return manager.restore_backup(backup_id)

    def update(self, channel: str = "stable") -> dict:
        """Check for and apply updates."""
        from aetheros_production.update_system import UpdateManager
        manager = UpdateManager()
        return manager.check_and_update(channel)

    def generate_packages(self, formats: list[str] | None = None) -> dict:
        """Generate packages for distribution."""
        from aetheros_production.packaging import PackagingManager
        manager = PackagingManager()
        return manager.generate_packages(formats)

    def get_version_info(self) -> dict:
        """Get version information."""
        from aetheros_production.release import ReleaseManager
        manager = ReleaseManager()
        return manager.get_version_info()
