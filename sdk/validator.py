"""
Plugin Manifest Validator
=========================

Validates plugin and extension manifests against the SDK schema.
Ensures required fields are present, types are correct, and values
are within acceptable ranges.

Validated against:
    - Required fields (name, version)
    - AetherOS/SDK version constraints
    - Permission declarations
    - Dependency declarations
    - Platform constraints
    - Runtime requirements
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sdk.compatibility import (
    CompatibilityResult,
    check_aetheros_compatibility,
    check_platform_compatibility,
)
from sdk.versioning import Version, VersionRange

logger = logging.getLogger(__name__)


class ManifestValidationError(Exception):
    """Raised when a manifest fails validation."""

    def __init__(self, message: str, errors: List[str]) -> None:
        super().__init__(message)
        self.errors = errors


# Valid plugin kinds
_VALID_KINDS = frozenset({
    "standalone", "backend", "exclusive", "platform", "model-provider",
    "tool", "agent", "workflow", "memory", "voice", "desktop",
    "engineering", "notification", "enterprise",
})

# Valid permission categories
_VALID_PERMISSION_CATEGORIES = frozenset({
    "filesystem", "network", "clipboard", "microphone", "camera",
    "notifications", "workspace",
})

# Allowed package name pattern (lowercase, digits, hyphens)
_PACKAGE_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")

# Valid version string pattern
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$")


def validate_plugin_manifest(manifest: Dict[str, Any]) -> List[str]:
    """Validate a plugin manifest dictionary.

    Args:
        manifest: The parsed plugin.yaml manifest.

    Returns:
        List of validation error messages. Empty list means valid.
    """
    errors: List[str] = []

    # --- Required fields ---
    if "name" not in manifest:
        errors.append("Missing required field: 'name'")
    else:
        name = manifest["name"]
        if not isinstance(name, str) or not _PACKAGE_NAME_RE.match(name):
            errors.append(
                f"Invalid 'name': '{name}'. Must match [a-z][a-z0-9_-]{0,63}"
            )

    if "version" not in manifest:
        errors.append("Missing required field: 'version'")
    elif not _VERSION_RE.match(str(manifest["version"])):
        errors.append(
            f"Invalid 'version': '{manifest['version']}'. "
            f"Expected SemVer format (e.g. '1.0.0')"
        )

    # --- Optional fields ---
    kind = manifest.get("kind", "standalone")
    if kind not in _VALID_KINDS:
        errors.append(
            f"Invalid 'kind': '{kind}'. "
            f"Valid: {', '.join(sorted(_VALID_KINDS))}"
        )

    description = manifest.get("description", "")
    if description and not isinstance(description, str):
        errors.append("'description' must be a string")

    author = manifest.get("author", "")
    if author and not isinstance(author, str):
        errors.append("'author' must be a string")

    # --- Permissions ---
    permissions = manifest.get("permissions", [])
    if permissions:
        if not isinstance(permissions, list):
            errors.append("'permissions' must be a list")
        else:
            for i, perm in enumerate(permissions):
                if not isinstance(perm, str) or ":" not in perm:
                    errors.append(
                        f"Invalid permission at index {i}: '{perm}'. "
                        f"Must be '<category>:<action>'"
                    )
                else:
                    cat = perm.split(":", 1)[0]
                    if cat not in _VALID_PERMISSION_CATEGORIES:
                        errors.append(
                            f"Unknown permission category '{cat}' at index {i}. "
                            f"Valid: {', '.join(sorted(_VALID_PERMISSION_CATEGORIES))}"
                        )

    # --- Dependencies ---
    deps = manifest.get("dependencies", [])
    if deps:
        if not isinstance(deps, list):
            errors.append("'dependencies' must be a list")
        elif not all(isinstance(d, str) for d in deps):
            errors.append("Each dependency must be a string (plugin name)")

    # --- SDK / AetherOS version ---
    sdk_version = manifest.get("sdk_version", "")
    if sdk_version and not _VERSION_RE.match(str(sdk_version)):
        errors.append(f"Invalid 'sdk_version': '{sdk_version}'")

    aetheros_version = manifest.get("aetheros_version", "")
    if aetheros_version and not isinstance(aetheros_version, str):
        errors.append("'aetheros_version' must be a string (version range)")

    # --- Platforms ---
    platforms = manifest.get("platforms", [])
    if platforms:
        if not isinstance(platforms, list):
            errors.append("'platforms' must be a list of platform names")
        elif not all(isinstance(p, str) for p in platforms):
            errors.append("Each platform must be a string (e.g. 'linux', 'macos')")

    # --- Runtime requirements ---
    runtime = manifest.get("runtime_requirements", {})
    if runtime and not isinstance(runtime, dict):
        errors.append("'runtime_requirements' must be a dict")

    return errors


def validate_extension_manifest(manifest: Dict[str, Any]) -> List[str]:
    """Validate an extension manifest (marketplace format).

    Similar to ``validate_plugin_manifest`` but with marketplace-specific
    fields like ``icon``, ``screenshots``, ``categories``, etc.
    """
    errors: List[str] = []

    # Core plugin validation
    errors.extend(validate_plugin_manifest(manifest))

    # Marketplace-specific fields
    icon = manifest.get("icon", "")
    if icon and not isinstance(icon, str):
        errors.append("'icon' must be a string (URL or file path)")

    categories = manifest.get("categories", [])
    if categories:
        if not isinstance(categories, list):
            errors.append("'categories' must be a list")
        elif not all(isinstance(c, str) for c in categories):
            errors.append("Each category must be a string")

    license_name = manifest.get("license", "")
    if license_name and not isinstance(license_name, str):
        errors.append("'license' must be a string")

    return errors
