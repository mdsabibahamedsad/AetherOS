"""
AetherOS Extension System
=========================

Manages the lifecycle, loading, sandboxing, and security of extensions.

Architecture::

    extensions/
        __init__.py      Package exports
        manager.py       Central extension manager
        loader.py        Extension loader (disk, URL, package)
        sandbox.py       Extension sandbox (isolation + permissions)
        registry.py      Extension capability registry
        capability.py    Capability declarations
        policy.py        Security policies for extensions
        events.py        Extension events and observability
"""

from __future__ import annotations

from extensions.manager import (
    ExtensionManager,
    get_extension_manager,
    ExtensionState,
)
from extensions.loader import (
    load_extension,
    load_extensions_from_dir,
    LoaderResult,
)
from extensions.sandbox import (
    ExtensionSandbox,
    SandboxConfig,
    SandboxMode,
)
from extensions.registry import (
    CapabilityRegistry,
    get_capability_registry,
)
from extensions.capability import (
    Capability,
    CapabilitySet,
    ALL_CAPABILITIES,
)
from extensions.policy import (
    ExtensionPolicy,
    PolicyRule,
    PolicyEngine,
    DEFAULT_POLICY,
)
from extensions.events import (
    ExtensionEvent,
    ExtensionEventType,
    get_event_bus,
)

__all__ = [
    "ExtensionManager",
    "get_extension_manager",
    "ExtensionState",
    "load_extension",
    "load_extensions_from_dir",
    "LoaderResult",
    "ExtensionSandbox",
    "SandboxConfig",
    "SandboxMode",
    "CapabilityRegistry",
    "get_capability_registry",
    "Capability",
    "CapabilitySet",
    "ALL_CAPABILITIES",
    "ExtensionPolicy",
    "PolicyRule",
    "PolicyEngine",
    "DEFAULT_POLICY",
    "ExtensionEvent",
    "ExtensionEventType",
    "get_event_bus",
]
