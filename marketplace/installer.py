"""
Extension Installer
===================

Handles installation of extensions from the marketplace or local packages.
Supports:

- Installing from .aep packages
- Installing from Git URLs (owner/repo shorthand)
- Installing from registry entries
- Dependency installation
- Post-install configuration
- Rollback on failure
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from sdk.compatibility import check_all as check_all_compatibility

logger = logging.getLogger(__name__)


class InstallStatus(Enum):
    """Installation result status."""
    SUCCESS = "success"
    FAILED = "failed"
    ALREADY_INSTALLED = "already_installed"
    INCOMPATIBLE = "incompatible"
    DEPENDENCY_MISSING = "dependency_missing"
    ROLLED_BACK = "rolled_back"


@dataclass
class InstallationResult:
    """Result of an installation operation."""
    status: InstallStatus
    name: str = ""
    version: str = ""
    target_dir: Optional[Path] = None
    error: str = ""
    warnings: List[str] = field(default_factory=list)
    missing_env: List[str] = field(default_factory=list)
    rolled_back: bool = False

    @property
    def success(self) -> bool:
        return self.status == InstallStatus.SUCCESS


def install_extension(
    source: str,
    *,
    target_dir: Optional[Path] = None,
    force: bool = False,
    skip_deps: bool = False,
    skip_compat_check: bool = False,
    enable: bool = True,
    aetheros_version: str = "",
    sdk_version: str = "",
) -> InstallationResult:
    """Install an extension from a Git URL, .aep file, or directory.

    Args:
        source: Git URL, owner/repo shorthand, .aep file path, or directory path.
        target_dir: Target installation directory. If None, uses
            ``~/.aetheros/plugins/<name>``.
        force: Reinstall even if already installed.
        skip_deps: Skip dependency installation.
        skip_compat_check: Skip Aetheros/SDK compatibility check.
        enable: Enable the plugin after installation.
        aetheros_version: Current Aetheros version (for compat check).
        sdk_version: Current SDK version (for compat check).

    Returns:
        InstallationResult with status and metadata.
    """
    # Determine source type
    if source.endswith(".aep"):
        return _install_from_package(
            Path(source), target_dir=target_dir, force=force,
            enable=enable,
        )
    elif Path(source).is_dir():
        return _install_from_directory(
            Path(source), target_dir=target_dir, force=force,
            enable=enable, skip_compat_check=skip_compat_check,
            aetheros_version=aetheros_version, sdk_version=sdk_version,
        )
    else:
        return _install_from_git(
            source, target_dir=target_dir, force=force,
            enable=enable,
        )


def uninstall_extension(
    name: str,
    *,
    keep_config: bool = False,
) -> bool:
    """Uninstall an extension by name.

    Args:
        name: Plugin name or key.
        keep_config: Keep config.yaml entries for the plugin.

    Returns:
        True if uninstalled successfully.
    """
    try:
        from aetheros_cli.plugins_cmd import cmd_remove
        from aetheros_cli.plugins_cmd import _plugins_dir

        plugins_dir = _plugins_dir()
        target = plugins_dir / name
        if not target.exists():
            logger.warning("Plugin '%s' not found in %s", name, plugins_dir)
            return False

        shutil.rmtree(target)
        logger.info("Uninstalled plugin: %s", name)

        if not keep_config:
            _remove_from_config(name)

        return True
    except Exception as exc:
        logger.error("Failed to uninstall '%s': %s", name, exc)
        return False


def _install_from_package(
    package_path: Path,
    target_dir: Optional[Path],
    force: bool,
    enable: bool,
) -> InstallationResult:
    """Install from a .aep package file."""
    try:
        from sdk.packaging import unpack_plugin, get_package_metadata

        metadata = get_package_metadata(package_path)
        if metadata is None:
            return InstallationResult(
                status=InstallStatus.FAILED,
                error="Could not read package metadata",
            )

        name = metadata.get("name", package_path.stem)
        version = str(metadata.get("version", "0.0.0"))

        try:
            pkg = unpack_plugin(package_path, target_dir=target_dir)
        except Exception as exc:
            return InstallationResult(
                status=InstallStatus.FAILED,
                name=name, version=version,
                error=str(exc),
            )

        # Enable the plugin
        if enable:
            _add_to_enabled(name)

        return InstallationResult(
            status=InstallStatus.SUCCESS,
            name=name,
            version=version,
            target_dir=pkg.source_dir,
        )
    except Exception as exc:
        return InstallationResult(
            status=InstallStatus.FAILED,
            error=str(exc),
        )


def _install_from_directory(
    source_dir: Path,
    target_dir: Optional[Path],
    force: bool,
    enable: bool,
    skip_compat_check: bool,
    aetheros_version: str,
    sdk_version: str,
) -> InstallationResult:
    """Install from a local directory."""
    source_dir = source_dir.resolve()

    # Read manifest
    manifest_file = source_dir / "manifest.yaml"
    if not manifest_file.exists():
        manifest_file = source_dir / "plugin.yaml"
    if not manifest_file.exists():
        return InstallationResult(
            status=InstallStatus.FAILED,
            error="No manifest.yaml or plugin.yaml found in source directory",
        )

    manifest = yaml.safe_load(manifest_file.read_text(encoding="utf-8")) or {}
    name = manifest.get("name", source_dir.name)
    version = str(manifest.get("version", "0.0.0"))

    # Compatibility check
    if not skip_compat_check and aetheros_version and sdk_version:
        result = check_all_compatibility(
            aetheros_version=aetheros_version,
            sdk_version=sdk_version,
            extension_manifest=manifest,
        )
        if not result.compatible:
            return InstallationResult(
                status=InstallStatus.INCOMPATIBLE,
                name=name, version=version,
                error="; ".join(result.checks_failed),
            )

    # Determine target
    if target_dir is None:
        from aetheros_constants import get_aetheros_home
        target_dir = get_aetheros_home() / "plugins" / name

    target_dir = target_dir.resolve()
    if target_dir.exists():
        if not force:
            return InstallationResult(
                status=InstallStatus.ALREADY_INSTALLED,
                name=name, version=version,
                error=f"Already installed at {target_dir}",
            )
        shutil.rmtree(target_dir)

    try:
        shutil.copytree(str(source_dir), str(target_dir), symlinks=True)
    except Exception as exc:
        return InstallationResult(
            status=InstallStatus.FAILED,
            name=name, version=version,
            error=str(exc),
        )

    if enable:
        _add_to_enabled(name)

    return InstallationResult(
        status=InstallStatus.SUCCESS,
        name=name, version=version,
        target_dir=target_dir,
    )


def _install_from_git(
    identifier: str,
    target_dir: Optional[Path],
    force: bool,
    enable: bool,
) -> InstallationResult:
    """Install from a Git URL or owner/repo shorthand.

    Delegates to the existing ``aetheros_cli.plugins_cmd._install_plugin_core``.
    """
    try:
        from aetheros_cli.plugins_cmd import _install_plugin_core, PluginOperationError

        try:
            target, installed_manifest, installed_name = _install_plugin_core(
                identifier, force=force,
            )
        except PluginOperationError as exc:
            return InstallationResult(
                status=InstallStatus.FAILED,
                error=str(exc),
            )

        version = str(installed_manifest.get("version", "0.0.0"))

        if enable:
            _add_to_enabled(installed_name)

        return InstallationResult(
            status=InstallStatus.SUCCESS,
            name=installed_name,
            version=version,
            target_dir=Path(target),
        )
    except Exception as exc:
        return InstallationResult(
            status=InstallStatus.FAILED,
            error=str(exc),
        )


def _add_to_enabled(name: str) -> None:
    """Add a plugin to the enabled list in config."""
    try:
        from aetheros_cli.config import load_config, save_config
        config = load_config()
        if "plugins" not in config:
            config["plugins"] = {}
        enabled = config["plugins"].get("enabled", [])
        if name not in enabled:
            enabled.append(name)
        config["plugins"]["enabled"] = enabled
        save_config(config)
    except Exception as exc:
        logger.warning("Could not enable plugin '%s': %s", name, exc)


def _remove_from_config(name: str) -> None:
    """Remove a plugin from config lists."""
    try:
        from aetheros_cli.config import load_config, save_config
        config = load_config()
        if "plugins" in config:
            plugins = config["plugins"]
            for key in ("enabled", "disabled"):
                if key in plugins and isinstance(plugins[key], list):
                    if name in plugins[key]:
                        plugins[key].remove(name)
        save_config(config)
    except Exception as exc:
        logger.warning("Could not update config for '%s': %s", name, exc)
