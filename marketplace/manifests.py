"""
Manifest Generation
===================

Generates standard plugin/extensions manifests for marketplace submission.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from sdk.validator import validate_extension_manifest

logger = logging.getLogger(__name__)


class ManifestGenerator:
    """Generates plugin and extension manifests."""

    @staticmethod
    def generate_plugin_manifest(
        name: str,
        version: str = "1.0.0",
        description: str = "",
        author: str = "",
        kind: str = "standalone",
        *,
        sdk_version: str = ">=1.0.0",
        aetheros_version: str = ">=0.1.0",
        permissions: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        platforms: Optional[List[str]] = None,
        requires_env: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        license: str = "MIT",
    ) -> Dict[str, Any]:
        """Generate a plugin manifest dictionary.

        Args:
            name: Plugin name.
            version: Plugin version (SemVer).
            description: Short description.
            author: Plugin author.
            kind: Plugin kind.
            sdk_version: Required SDK version range.
            aetheros_version: Required Aetheros version range.
            permissions: List of required permissions.
            dependencies: List of dependency plugin names.
            platforms: Supported platforms.
            requires_env: Required environment variables.
            categories: Marketplace categories.
            tags: Search tags.
            license: License identifier.

        Returns:
            Manifest dictionary ready for YAML serialization.
        """
        manifest: Dict[str, Any] = {
            "name": name,
            "version": version,
            "description": description,
            "author": author,
            "kind": kind,
            "sdk_version": sdk_version,
            "aetheros_version": aetheros_version,
        }

        if permissions:
            manifest["permissions"] = permissions
        if dependencies:
            manifest["dependencies"] = dependencies
        if platforms:
            manifest["platforms"] = platforms
        if requires_env:
            manifest["requires_env"] = requires_env
        if categories:
            manifest["categories"] = categories
        if tags:
            manifest["tags"] = tags
        if license:
            manifest["license"] = license

        return manifest

    @staticmethod
    def save_manifest(
        manifest: Dict[str, Any],
        path: Path,
        fmt: str = "yaml",
    ) -> None:
        """Save a manifest to a file.

        Args:
            manifest: Manifest dictionary.
            path: Output file path.
            fmt: Format ("yaml" or "json").
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "json":
            path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        else:
            path.write_text(yaml.dump(manifest, default_flow_style=False), encoding="utf-8")

    @staticmethod
    def load_manifest(path: Path) -> Dict[str, Any]:
        """Load and validate a manifest from a file.

        Args:
            path: Path to manifest file (YAML or JSON).

        Returns:
            Validated manifest dictionary.

        Raises:
            ValueError: If the manifest is invalid.
        """
        if not path.exists():
            raise ValueError(f"Manifest file not found: {path}")

        raw = path.read_text(encoding="utf-8")
        if path.suffix in (".yaml", ".yml"):
            manifest = yaml.safe_load(raw) or {}
        else:
            manifest = json.loads(raw)

        errors = validate_extension_manifest(manifest)
        if errors:
            raise ValueError(
                f"Invalid manifest in {path}:\n" +
                "\n".join(f"  - {e}" for e in errors)
            )

        return manifest


def generate_manifest(
    name: str,
    **kwargs,
) -> Dict[str, Any]:
    """Convenience function to generate a plugin manifest.

    Usage::

        manifest = generate_manifest(
            "my-plugin",
            description="My awesome plugin",
            author="Me",
            kind="tool",
            permissions=["filesystem:read"],
        )
    """
    return ManifestGenerator.generate_plugin_manifest(name, **kwargs)
