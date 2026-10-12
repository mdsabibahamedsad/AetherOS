"""
Plugin Packaging
================

Defines the standard format for packaging Aetheros plugins and extensions.

Package format: ``.aep`` (Aetheros Extension Package)

A .aep file is a gzipped tarball containing:

    manifest.yaml        — plugin manifest (required)
    __init__.py          — plugin entry point (required)
    plugin.yaml          — legacy manifest (optional, for backward compat)
    after-install.md     — post-install instructions (optional)
    icon.png             — plugin icon (optional)
    screenshots/         — screenshots for marketplace (optional)
    scripts/             — helper scripts (optional)
    templates/           — templates (optional)
    assets/              — other assets (optional)
    .signature           — detached signature (optional, for signed packages)

The ``pack_plugin()`` and ``unpack_plugin()`` functions handle creation
and extraction.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import shutil
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from sdk.validator import validate_plugin_manifest

logger = logging.getLogger(__name__)


class PackageError(Exception):
    """Raised on packaging/unpacking errors."""


@dataclass
class PluginPackage:
    """Represents a packaged plugin."""
    manifest: Dict[str, Any]
    source_dir: Optional[Path] = None
    package_path: Optional[Path] = None
    file_hash: str = ""
    file_size: int = 0

    def __post_init__(self) -> None:
        if self.package_path and self.package_path.exists():
            self.file_size = self.package_path.stat().st_size
            self.file_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        if not self.package_path or not self.package_path.exists():
            return ""
        h = hashlib.sha256()
        with open(self.package_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def verify_integrity(self) -> bool:
        """Verify the package file hasn't been modified."""
        if not self.package_path or not self.package_path.exists():
            return False
        return self._compute_hash() == self.file_hash


class PackageFormat:
    """Constants for the package format."""
    EXTENSION = ".aep"
    MIME_TYPE = "application/vnd.aetheros.plugin"
    MANIFEST_FILE = "manifest.yaml"
    ENTRY_POINT = "__init__.py"
    LEGACY_MANIFEST = "plugin.yaml"
    AFTER_INSTALL = "after-install.md"
    ICON = "icon.png"
    SCREENSHOTS_DIR = "screenshots/"
    SCRIPTS_DIR = "scripts/"
    TEMPLATES_DIR = "templates/"
    ASSETS_DIR = "assets/"
    SIGNATURE_FILE = ".signature"


def pack_plugin(
    source_dir: Path,
    output_path: Optional[Path] = None,
    *,
    include_git: bool = False,
    compress_level: int = 9,
) -> PluginPackage:
    """Pack a plugin directory into a .aep file.

    Args:
        source_dir: Directory containing the plugin source.
        output_path: Desired output path. If None, ``<name>-<version>.aep``
            in the current directory.
        include_git: Include ``.git/`` directory in the package.
        compress_level: Gzip compression level (0-9).

    Returns:
        PluginPackage describing the created package.

    Raises:
        PackageError: If the plugin directory is invalid or packaging fails.
    """
    source_dir = Path(source_dir).resolve()
    if not source_dir.is_dir():
        raise PackageError(f"Source directory does not exist: {source_dir}")

    # Read manifest
    manifest_path = source_dir / PackageFormat.MANIFEST_FILE
    if not manifest_path.exists():
        manifest_path = source_dir / PackageFormat.LEGACY_MANIFEST
    if not manifest_path.exists():
        raise PackageError(
            f"No manifest file found in {source_dir}. "
            f"Expected '{PackageFormat.MANIFEST_FILE}' or '{PackageFormat.LEGACY_MANIFEST}'."
        )

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f) or {}

    # Validate manifest
    errors = validate_plugin_manifest(manifest)
    if errors:
        raise PackageError(f"Invalid manifest:\n" + "\n".join(f"  - {e}" for e in errors))

    # Determine output path
    name = manifest.get("name", source_dir.name)
    version = manifest.get("version", "0.0.0")
    safe_name = name.replace("/", "_").replace(" ", "_")
    if output_path is None:
        output_path = Path.cwd() / f"{safe_name}-{version}{PackageFormat.EXTENSION}"

    # Pack
    try:
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        with tarfile.open(tmp_path, "w") as tar:
            source_dir_resolved = source_dir.resolve()
            for item in source_dir_resolved.rglob("*"):
                if not include_git and ".git" in item.parts:
                    continue
                if item.is_file():
                    arcname = str(item.relative_to(source_dir_resolved))
                    tar.add(str(item), arcname=arcname)

        # Gzip compress
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "rb") as f_in:
            with gzip.open(output_path, "wb", compresslevel=compress_level) as f_out:
                shutil.copyfileobj(f_in, f_out)

    except Exception as exc:
        raise PackageError(f"Packaging failed: {exc}") from exc
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return PluginPackage(
        manifest=manifest,
        source_dir=source_dir,
        package_path=output_path,
    )


def unpack_plugin(
    package_path: Path,
    target_dir: Optional[Path] = None,
    *,
    verify: bool = False,
) -> PluginPackage:
    """Unpack a .aep file into a directory.

    Args:
        package_path: Path to the .aep file.
        target_dir: Directory to extract into. If None,
            ``~/.aetheros/plugins/<name>/``.
        verify: Verify package hash before extraction.

    Returns:
        PluginPackage with extracted manifest.

    Raises:
        PackageError: If the package is invalid or extraction fails.
    """
    package_path = Path(package_path).resolve()
    if not package_path.exists():
        raise PackageError(f"Package not found: {package_path}")

    # Verify integrity
    pkg = PluginPackage(package_path=package_path, manifest={})
    if verify and not pkg.verify_integrity():
        raise PackageError("Package integrity check failed (hash mismatch)")

    # Read manifest first (without full extraction)
    manifest = _read_manifest_from_package(package_path)
    if manifest is None:
        raise PackageError("Could not read manifest from package")

    # Determine target directory
    if target_dir is None:
        from aetheros_constants import get_aetheros_home
        name = manifest.get("name", package_path.stem)
        target_dir = get_aetheros_home() / "plugins" / name

    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        with gzip.open(package_path, "rb") as f_gz:
            with tarfile.open(fileobj=f_gz, mode="r") as tar:
                tar.extractall(path=str(target_dir))
    except Exception as exc:
        raise PackageError(f"Extraction failed: {exc}") from exc

    return PluginPackage(
        manifest=manifest,
        source_dir=target_dir,
        package_path=package_path,
    )


def _read_manifest_from_package(package_path: Path) -> Optional[Dict[str, Any]]:
    """Read the manifest from a .aep file without full extraction."""
    try:
        with gzip.open(package_path, "rb") as f_gz:
            with tarfile.open(fileobj=f_gz, mode="r") as tar:
                # Try manifest.yaml first, then plugin.yaml
                for fname in (PackageFormat.MANIFEST_FILE, PackageFormat.LEGACY_MANIFEST):
                    try:
                        member = tar.getmember(fname)
                    except KeyError:
                        continue
                    f = tar.extractfile(member)
                    if f:
                        return yaml.safe_load(f.read().decode("utf-8")) or {}
    except Exception as exc:
        logger.warning("Failed to read manifest from package: %s", exc)
    return None


def get_package_metadata(package_path: Path) -> Optional[Dict[str, Any]]:
    """Get metadata from a .aep file without extracting.

    Returns manifest dict or None on failure.
    """
    manifest = _read_manifest_from_package(package_path)
    if manifest is None:
        return None
    manifest["_package"] = {
        "path": str(package_path),
        "size": package_path.stat().st_size,
        "format": PackageFormat.EXTENSION,
    }
    return manifest
