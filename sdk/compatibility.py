"""
AetherOS Compatibility Checking
===============================

Verifies that an extension is compatible with the current AetherOS runtime,
SDK version, platform, and dependencies.

Checks performed:
    1. AetherOS version compatibility (declared min/max)
    2. SDK version compatibility
    3. Platform/OS compatibility
    4. Runtime requirements (Python version, RAM, disk)
    5. Dependency availability
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sdk.versioning import Version, VersionRange

logger = logging.getLogger(__name__)


@dataclass
class CompatibilityResult:
    """Result of a compatibility check."""
    compatible: bool
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def merge(self, other: "CompatibilityResult") -> "CompatibilityResult":
        """Merge another result into this one."""
        return CompatibilityResult(
            compatible=self.compatible and other.compatible,
            checks_passed=self.checks_passed + other.checks_passed,
            checks_failed=self.checks_failed + other.checks_failed,
            warnings=self.warnings + other.warnings,
        )

    @property
    def summary(self) -> str:
        if self.compatible:
            parts = [f"✓ {len(self.checks_passed)} check(s) passed"]
            if self.warnings:
                parts.append(f"⚠ {len(self.warnings)} warning(s)")
            return "; ".join(parts)
        return f"✗ {len(self.checks_failed)} check(s) failed: {'; '.join(self.checks_failed)}"


def check_aetheros_compatibility(
    aetheros_version: str,
    *,
    min_version: str = "",
    max_version: str = "",
) -> CompatibilityResult:
    """Check if the current Aetheros runtime version meets requirements.

    Args:
        aetheros_version: The actual Aetheros version string.
        min_version: Minimum required Aetheros version (e.g. ``"0.5.0"``).
        max_version: Maximum allowed version (e.g. ``"1.0.0"``).

    Returns:
        CompatibilityResult with detailed check information.
    """
    result = CompatibilityResult(compatible=True)
    current = Version(aetheros_version)

    if min_version:
        min_v = Version(min_version)
        if current < min_v:
            result.compatible = False
            result.checks_failed.append(
                f"AetherOS {current} is older than minimum required {min_v}"
            )
        else:
            result.checks_passed.append(
                f"AetherOS {current} ≥ minimum {min_v}"
            )

    if max_version:
        max_v = Version(max_version)
        if current >= max_v:
            result.compatible = False
            result.checks_failed.append(
                f"AetherOS {current} is not less than maximum {max_v}"
            )
        else:
            result.checks_passed.append(
                f"AetherOS {current} < maximum {max_v}"
            )

    if not min_version and not max_version:
        result.checks_passed.append("No AetherOS version constraints specified")

    return result


def check_sdk_compatibility(
    sdk_version: str,
    *,
    min_version: str = "",
    max_version: str = "",
) -> CompatibilityResult:
    """Check if the current SDK version meets requirements.

    Args:
        sdk_version: The actual SDK version string.
        min_version: Minimum required SDK version.
        max_version: Maximum allowed SDK version.
    """
    return check_aetheros_compatibility(
        sdk_version,
        min_version=min_version,
        max_version=max_version,
    )


def check_platform_compatibility(
    supported_platforms: Optional[List[str]] = None,
) -> CompatibilityResult:
    """Check if the current OS/platform is supported.

    Args:
        supported_platforms: List of supported platforms
            (e.g. ``["linux", "darwin", "win32"]``).
            If None or empty, assumes all platforms are supported.

    Returns:
        CompatibilityResult with platform check details.
    """
    result = CompatibilityResult(compatible=True)
    if not supported_platforms:
        result.checks_passed.append("No platform constraints specified")
        return result

    current_os = sys.platform
    normalized: Dict[str, List[str]] = {
        "linux": ["linux", "linux2"],
        "macos": ["darwin"],
        "windows": ["win32", "cygwin"],
        "win32": ["win32"],
    }

    # Build reverse lookup: sys.platform value -> normalized name
    sys_to_name: Dict[str, str] = {}
    for name, platforms in normalized.items():
        for p in platforms:
            sys_to_name[p] = name

    current_name = sys_to_name.get(current_os, current_os)
    supported_lower = [p.lower() for p in supported_platforms]

    # Check against normalized names
    compatible_platform = current_name in supported_lower or current_os in supported_lower

    if compatible_platform:
        result.checks_passed.append(f"Platform '{current_name}' is supported")
    else:
        result.compatible = False
        result.checks_failed.append(
            f"Platform '{current_name}' is not in supported list: {supported_platforms}"
        )

    return result


def check_runtime_requirements(
    requirements: Optional[Dict[str, Any]] = None,
) -> CompatibilityResult:
    """Check runtime requirements like Python version, memory, disk.

    Args:
        requirements: Dict with optional keys:
            - ``python``: Python version string (e.g. ``">=3.10"``)
            - ``memory_mb``: Minimum RAM in MB
            - ``disk_mb``: Minimum free disk in MB

    Returns:
        CompatibilityResult with requirement check details.
    """
    result = CompatibilityResult(compatible=True)
    if not requirements:
        result.checks_passed.append("No runtime requirements specified")
        return result

    # Python version
    python_req = requirements.get("python", "")
    if python_req:
        current_py = f"{sys.version_info.major}.{sys.version_info.minor}"
        try:
            vr = VersionRange.parse(python_req)
            if vr.contains(Version(current_py)):
                result.checks_passed.append(f"Python {current_py} satisfies '{python_req}'")
            else:
                result.compatible = False
                result.checks_failed.append(
                    f"Python {current_py} does not satisfy requirement '{python_req}'"
                )
        except (ValueError, IndexError):
            result.warnings.append(f"Could not parse Python requirement '{python_req}'")

    # Memory
    memory_mb = requirements.get("memory_mb", 0)
    if memory_mb > 0:
        try:
            import psutil
            available = psutil.virtual_memory().available / (1024 * 1024)
            if available >= memory_mb:
                result.checks_passed.append(f"Available memory {available:.0f}MB >= {memory_mb}MB")
            else:
                result.compatible = False
                result.checks_failed.append(
                    f"Available memory {available:.0f}MB < required {memory_mb}MB"
                )
        except ImportError:
            result.warnings.append("psutil not available — skipping memory check")

    return result


def check_dependencies(
    dependencies: Optional[List[str]] = None,
) -> CompatibilityResult:
    """Check that declared dependencies are available.

    Dependencies are plugin names that must be installed and enabled.
    """
    result = CompatibilityResult(compatible=True)
    if not dependencies:
        result.checks_passed.append("No dependencies declared")
        return result

    try:
        from aetheros_cli.plugins import get_plugin_manager
        mgr = get_plugin_manager()
        plugins = mgr.list_plugins()

        for dep in dependencies:
            found = any(
                p["name"] == dep or p["key"] == dep
                for p in plugins
            )
            if found:
                enabled = any(
                    p["name"] == dep and p["enabled"]
                    for p in plugins
                )
                if enabled:
                    result.checks_passed.append(f"Dependency '{dep}' is installed and enabled")
                else:
                    result.compatible = False
                    result.checks_failed.append(
                        f"Dependency '{dep}' is installed but not enabled"
                    )
            else:
                result.compatible = False
                result.checks_failed.append(f"Dependency '{dep}' is not installed")
    except Exception as exc:
        result.warnings.append(f"Could not check dependencies: {exc}")

    return result


def check_all(
    *,
    aetheros_version: str,
    sdk_version: str,
    extension_manifest: Optional[Dict[str, Any]] = None,
) -> CompatibilityResult:
    """Run all compatibility checks for an extension.

    Args:
        aetheros_version: Current Aetheros version string.
        sdk_version: Current SDK version string.
        extension_manifest: Extension manifest dict with keys:
            ``aetheros_version``, ``sdk_version``, ``platforms``,
            ``runtime_requirements``, ``dependencies``.

    Returns:
        Aggregated CompatibilityResult.
    """
    result = CompatibilityResult(compatible=True)

    if extension_manifest is None:
        return result

    # Aetheros version compatibility
    manifest_aetheros = extension_manifest.get("aetheros_version", "")
    if manifest_aetheros:
        try:
            vr = VersionRange.parse(manifest_aetheros)
            result = result.merge(
                check_aetheros_compatibility(
                    aetheros_version,
                    min_version=str(vr.min_version) if vr.min_version else "",
                    max_version=str(vr.max_version) if vr.max_version else "",
                )
            )
        except (ValueError, IndexError) as exc:
            result.warnings.append(f"Could not parse aetheros_version '{manifest_aetheros}': {exc}")

    # SDK version compatibility
    manifest_sdk = extension_manifest.get("sdk_version", "")
    if manifest_sdk:
        try:
            vr = VersionRange.parse(manifest_sdk)
            result = result.merge(
                check_sdk_compatibility(
                    sdk_version,
                    min_version=str(vr.min_version) if vr.min_version else "",
                    max_version=str(vr.max_version) if vr.max_version else "",
                )
            )
        except (ValueError, IndexError) as exc:
            result.warnings.append(f"Could not parse sdk_version '{manifest_sdk}': {exc}")

    # Platform compatibility
    platforms = extension_manifest.get("platforms")
    if platforms:
        result = result.merge(check_platform_compatibility(platforms))

    # Runtime requirements
    runtime_reqs = extension_manifest.get("runtime_requirements")
    if runtime_reqs:
        result = result.merge(check_runtime_requirements(runtime_reqs))

    # Dependencies
    deps = extension_manifest.get("dependencies")
    if deps:
        result = result.merge(check_dependencies(deps))

    return result
