"""
Extension Loader
================

Handles loading extensions from various sources:
- Local directories (installed plugins)
- .aep packages
- Git repositories
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from sdk.context import ExtensionContext, ExtensionManifest

logger = logging.getLogger(__name__)


@dataclass
class LoaderResult:
    """Result of loading an extension."""
    success: bool
    name: str = ""
    version: str = ""
    error: str = ""
    context: Optional[ExtensionContext] = None
    warnings: List[str] = field(default_factory=list)


def load_extension(
    source_dir: Path,
    *,
    skip_register: bool = False,
) -> LoaderResult:
    """Load an extension from a directory.

    Args:
        source_dir: Directory containing the extension.
        skip_register: If True, import the module but don't call register().

    Returns:
        LoaderResult with status and context.
    """
    source_dir = source_dir.resolve()
    if not source_dir.is_dir():
        return LoaderResult(success=False, error=f"Directory not found: {source_dir}")

    # Find manifest
    manifest_file = source_dir / "manifest.yaml"
    if not manifest_file.exists():
        manifest_file = source_dir / "plugin.yaml"
    if not manifest_file.exists():
        return LoaderResult(success=False, error=f"No manifest found in {source_dir}")

    try:
        import yaml
        data = yaml.safe_load(manifest_file.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return LoaderResult(success=False, error=f"Failed to parse manifest: {exc}")

    name = data.get("name", source_dir.name)
    version = str(data.get("version", "0.0.0"))
    warnings: List[str] = []

    # Find __init__.py
    init_file = source_dir / "__init__.py"
    if not init_file.exists():
        return LoaderResult(
            success=False, name=name, version=version,
            error=f"No __init__.py in {source_dir}",
        )

    # Create context
    manifest = ExtensionManifest(
        name=name,
        version=version,
        description=data.get("description", ""),
        author=data.get("author", ""),
        sdk_version=str(data.get("sdk_version", "")),
        aetheros_version=str(data.get("aetheros_version", "")),
        permissions=data.get("permissions", []),
        dependencies=data.get("dependencies", []),
    )

    ctx = ExtensionContext(manifest=manifest, extension_dir=source_dir)

    if not skip_register:
        # Import the module
        module_name = f"_aetheros_ext_{name.replace('-', '_').replace('/', '_')}"
        try:
            if module_name in sys.modules:
                module = sys.modules[module_name]
            else:
                spec = importlib.util.spec_from_file_location(
                    module_name, init_file,
                    submodule_search_locations=[str(source_dir)],
                )
                if spec is None or spec.loader is None:
                    return LoaderResult(
                        success=False, name=name, version=version,
                        error=f"Cannot load module from {init_file}",
                    )
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

            # Call register()
            register_fn = getattr(module, "register", None)
            if register_fn is None:
                warnings.append(f"Extension '{name}' has no register() function")
            else:
                register_fn(ctx)
        except Exception as exc:
            return LoaderResult(
                success=False, name=name, version=version,
                error=f"Failed to load extension: {exc}",
            )

    return LoaderResult(
        success=True, name=name, version=version,
        context=ctx, warnings=warnings,
    )


def load_extensions_from_dir(
    directory: Path,
    *,
    recursive: bool = True,
) -> List[LoaderResult]:
    """Load all extensions from a directory.

    Scans for subdirectories containing manifest files and loads each one.

    Args:
        directory: Directory to scan.
        recursive: Scan subdirectories recursively.

    Returns:
        List of LoaderResult for each extension found.
    """
    results: List[LoaderResult] = []
    if not directory.is_dir():
        return results

    for child in sorted(directory.iterdir()):
        if not child.is_dir():
            continue

        # Quick check: has manifest?
        has_manifest = (
            (child / "manifest.yaml").exists()
            or (child / "plugin.yaml").exists()
        )
        if not has_manifest:
            continue

        result = load_extension(child)
        results.append(result)

    return results
