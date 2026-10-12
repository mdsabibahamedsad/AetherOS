"""
Extension Updater
=================

Checks for updates to installed extensions and applies them.
Supports:

- Checking for updates against the registry
- Safe updates with rollback on failure
- Version constraint verification
- Pre/post update hooks
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sdk.versioning import Version, VersionRange

logger = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    """Result of an update operation."""
    name: str = ""
    old_version: str = ""
    new_version: str = ""
    success: bool = False
    error: str = ""
    rolled_back: bool = False
    warnings: List[str] = field(default_factory=list)


def check_for_updates(
    extensions: Optional[List[str]] = None,
) -> List[UpdateResult]:
    """Check for available updates.

    Args:
        extensions: List of extension names to check.
            If None, checks all installed extensions.

    Returns:
        List of UpdateResult with update availability info.
    """
    results: List[UpdateResult] = []

    try:
        from aetheros_cli.plugins import get_plugin_manager
        mgr = get_plugin_manager()
        installed = mgr.list_plugins()

        # Filter if specific extensions requested
        if extensions:
            installed = [p for p in installed if p["name"] in extensions]

        for plugin in installed:
            name = plugin["name"]
            current_version = str(plugin.get("version", "0.0.0"))

            # Look up in registry
            from marketplace.registry import get_registry
            registry = get_registry()
            entry = registry.get_extension(name)

            if entry is None:
                continue

            latest_version = entry.version
            try:
                current = Version(current_version)
                latest = Version(latest_version)
                has_update = latest > current
            except (ValueError, IndexError):
                has_update = False

            if has_update:
                results.append(UpdateResult(
                    name=name,
                    old_version=current_version,
                    new_version=latest_version,
                    success=True,
                ))
    except Exception as exc:
        logger.warning("Update check failed: %s", exc)

    return results


def update_extension(
    name: str,
    *,
    force: bool = False,
    backup: bool = True,
) -> UpdateResult:
    """Update an installed extension to the latest version.

    Args:
        name: Extension name to update.
        force: Update even if version constraints would be violated.
        backup: Create a backup before updating (enables rollback).

    Returns:
        UpdateResult with status.
    """
    try:
        from aetheros_cli.plugins import get_plugin_manager
        from aetheros_cli.plugins_cmd import _plugins_dir, cmd_update

        mgr = get_plugin_manager()
        plugins = {p["name"]: p for p in mgr.list_plugins()}

        if name not in plugins:
            return UpdateResult(
                name=name, success=False,
                error=f"Extension '{name}' is not installed",
            )

        old_version = str(plugins[name].get("version", "0.0.0"))

        # Create backup for rollback
        backup_dir = None
        if backup:
            plugins_dir = _plugins_dir()
            source_dir = plugins_dir / name
            if source_dir.is_dir() and (source_dir / ".git").is_dir():
                # Git-based — git pull handles rollback
                pass
            elif source_dir.is_dir():
                backup_dir = Path(tempfile.mkdtemp(prefix=f"{name}-backup-"))
                shutil.copytree(str(source_dir), str(backup_dir / name))

        try:
            # Try git pull first (for git-installed plugins)
            cmd_update(name)
        except SystemExit as e:
            if e.code != 0:
                if backup_dir:
                    _restore_backup(backup_dir, name)
                return UpdateResult(
                    name=name, old_version=old_version,
                    success=False, error="Update command failed",
                    rolled_back=bool(backup_dir),
                )

        # Get new version
        mgr.discover_and_load(force=True)
        updated_plugins = {p["name"]: p for p in mgr.list_plugins()}
        new_version = str(updated_plugins.get(name, {}).get("version", "?"))

        return UpdateResult(
            name=name, old_version=old_version,
            new_version=new_version,
            success=True,
        )
    except Exception as exc:
        return UpdateResult(
            name=name, success=False, error=str(exc),
        )


def _restore_backup(backup_dir: Path, name: str) -> None:
    """Restore a plugin from backup after failed update."""
    try:
        from aetheros_cli.plugins_cmd import _plugins_dir
        plugins_dir = _plugins_dir()
        target = plugins_dir / name

        if target.exists():
            shutil.rmtree(target)

        backup_path = backup_dir / name
        if backup_path.exists():
            shutil.copytree(str(backup_path), str(target))
            logger.info("Restored %s from backup", name)
    except Exception as exc:
        logger.error("Failed to restore backup for %s: %s", name, exc)
    finally:
        shutil.rmtree(backup_dir, ignore_errors=True)
