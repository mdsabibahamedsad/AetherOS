"""
Extension Manager
=================

Central manager that oversees all installed extensions: their lifecycle,
state, health, and interactions.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sdk.context import ExtensionContext, ExtensionManifest
from sdk.lifecycle import PluginLifecycle, get_lifecycle, LifecycleState

logger = logging.getLogger(__name__)


class ExtensionState(enum.Enum):
    """Runtime state of an extension."""
    DISCOVERED = "discovered"
    LOADING = "loading"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UNINSTALLED = "uninstalled"


@dataclass
class ExtensionRecord:
    """Runtime record for a loaded extension."""
    name: str
    version: str
    manifest: ExtensionManifest
    context: Optional[ExtensionContext] = None
    state: ExtensionState = ExtensionState.DISCOVERED
    source_dir: Optional[Path] = None
    error: Optional[str] = None
    loaded_at: Optional[str] = None
    health_status: str = "unknown"


class ExtensionManager:
    """Central manager for all installed extensions.

    Provides lifecycle management, state tracking, health monitoring,
    and introspection capabilities.

    Usage::

        mgr = get_extension_manager()
        mgr.discover()
        mgr.load_all()
        mgr.enable("my-plugin")
        mgr.get_extension("my-plugin")
    """

    def __init__(self) -> None:
        self._extensions: Dict[str, ExtensionRecord] = {}
        self._discovered = False

    def discover(self, force: bool = False) -> int:
        """Discover all available extensions.

        Args:
            force: Re-discover even if already discovered.

        Returns:
            Number of extensions discovered.
        """
        if self._discovered and not force:
            return len(self._extensions)

        self._extensions.clear()
        count = 0

        # Discover from bundled plugins
        try:
            from aetheros_cli.plugins import get_bundled_plugins_dir
            bundled = get_bundled_plugins_dir()
            if bundled.exists():
                count += self._scan_directory(bundled, "bundled")
        except Exception as exc:
            logger.debug("Failed to scan bundled plugins: %s", exc)

        # Discover from user plugins
        try:
            from aetheros_constants import get_aetheros_home
            user_plugins = get_aetheros_home() / "plugins"
            if user_plugins.exists():
                count += self._scan_directory(user_plugins, "user")
        except Exception as exc:
            logger.debug("Failed to scan user plugins: %s", exc)

        self._discovered = True
        logger.info("Discovered %d extensions", count)
        return count

    def load_all(self) -> int:
        """Load all discovered extensions.

        Returns:
            Number of successfully loaded extensions.
        """
        if not self._discovered:
            self.discover()

        loaded = 0
        for name, record in list(self._extensions.items()):
            if record.state == ExtensionState.DISCOVERED:
                try:
                    self._load_extension(record)
                    loaded += 1
                except Exception as exc:
                    record.state = ExtensionState.ERROR
                    record.error = str(exc)
                    logger.warning("Failed to load extension '%s': %s", name, exc)
        return loaded

    def enable(self, name: str) -> bool:
        """Enable a specific extension.

        Returns True if enabled successfully.
        """
        record = self._extensions.get(name)
        if record is None:
            logger.warning("Cannot enable unknown extension: %s", name)
            return False

        if record.state == ExtensionState.ENABLED:
            return True

        record.state = ExtensionState.ENABLED
        record.loaded_at = datetime.utcnow().isoformat()

        # Update lifecycle
        try:
            lifecycle = get_lifecycle(name)
            lifecycle.enable(reason="manager enable")
        except Exception:
            pass

        return True

    def disable(self, name: str) -> bool:
        """Disable a specific extension."""
        record = self._extensions.get(name)
        if record is None:
            return False

        if record.state == ExtensionState.DISABLED:
            return True

        record.state = ExtensionState.DISABLED
        try:
            lifecycle = get_lifecycle(name)
            lifecycle.disable(reason="manager disable")
        except Exception:
            pass

        return True

    def get_extension(self, name: str) -> Optional[ExtensionRecord]:
        """Get an extension record by name."""
        return self._extensions.get(name)

    def list_extensions(
        self,
        state_filter: Optional[ExtensionState] = None,
    ) -> List[ExtensionRecord]:
        """List all extensions, optionally filtered by state."""
        results = list(self._extensions.values())
        if state_filter:
            results = [r for r in results if r.state == state_filter]
        return results

    def get_health_summary(self) -> Dict[str, Any]:
        """Get a health summary of all extensions."""
        total = len(self._extensions)
        healthy = sum(1 for r in self._extensions.values() if r.state == ExtensionState.ENABLED)
        errors = sum(1 for r in self._extensions.values() if r.state == ExtensionState.ERROR)
        return {
            "total": total,
            "healthy": healthy,
            "error": errors,
            "loaded": sum(1 for r in self._extensions.values() if r.state in
                         (ExtensionState.LOADED, ExtensionState.ENABLED)),
        }

    def _scan_directory(self, directory: Path, source: str) -> int:
        """Scan a directory for extension manifests."""
        count = 0
        for child in sorted(directory.iterdir()):
            if not child.is_dir():
                continue

            # Look for manifest
            manifest_file = child / "manifest.yaml"
            if not manifest_file.exists():
                manifest_file = child / "plugin.yaml"
            if not manifest_file.exists():
                continue

            try:
                import yaml
                data = yaml.safe_load(manifest_file.read_text(encoding="utf-8")) or {}

                ext_manifest = ExtensionManifest(
                    name=data.get("name", child.name),
                    version=str(data.get("version", "0.0.0")),
                    description=data.get("description", ""),
                    author=data.get("author", ""),
                    sdk_version=str(data.get("sdk_version", "")),
                    aetheros_version=str(data.get("aetheros_version", "")),
                    permissions=data.get("permissions", []),
                    dependencies=data.get("dependencies", []),
                )

                record = ExtensionRecord(
                    name=ext_manifest.name,
                    version=ext_manifest.version,
                    manifest=ext_manifest,
                    state=ExtensionState.DISCOVERED,
                    source_dir=child,
                )
                self._extensions[ext_manifest.name] = record
                count += 1
            except Exception as exc:
                logger.debug("Failed to parse %s: %s", manifest_file, exc)

        return count

    def _load_extension(self, record: ExtensionRecord) -> None:
        """Load a single extension."""
        record.state = ExtensionState.LOADING

        if record.source_dir is None:
            raise ValueError(f"Extension '{record.name}' has no source directory")

        # Create extension context
        ctx = ExtensionContext(
            manifest=record.manifest,
            extension_dir=record.source_dir,
        )
        record.context = ctx

        # Load and call register()
        init_file = record.source_dir / "__init__.py"
        if not init_file.exists():
            raise FileNotFoundError(f"No __init__.py in {record.source_dir}")

        import importlib.util
        import sys as _sys

        module_name = f"_aetheros_ext_{record.name.replace('-', '_').replace('/', '_')}"
        if module_name not in _sys.modules:
            spec = importlib.util.spec_from_file_location(
                module_name, init_file,
                submodule_search_locations=[str(record.source_dir)],
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot create module spec for {init_file}")
            module = importlib.util.module_from_spec(spec)
            _sys.modules[module_name] = module
            spec.loader.exec_module(module)
        else:
            module = _sys.modules[module_name]

        # Call register(ctx)
        register_fn = getattr(module, "register", None)
        if register_fn is None:
            raise ValueError(f"Extension '{record.name}' has no register() function")

        register_fn(ctx)
        record.state = ExtensionState.LOADED
        record.loaded_at = datetime.utcnow().isoformat()


# Global singleton
_manager_instance: Optional[ExtensionManager] = None


def get_extension_manager() -> ExtensionManager:
    """Return the global ExtensionManager singleton."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ExtensionManager()
        _manager_instance.discover()
    return _manager_instance
