"""
AetherOS Developer SDK
=====================

Stable, versioned SDK for building plugins, extensions, tool providers,
model providers, memory providers, workflow packs, UI extensions,
interaction adapters, engineering extensions, and enterprise integrations.

The SDK is the **narrow waist** between external code and the Aetheros core.
Every public API is versioned, documented, and guaranteed backward-compatible
within the same major version.

Usage::

    from sdk.api import PluginAPI, ToolAPI, EventAPI
    from sdk.context import ExtensionContext
    from sdk.lifecycle import PluginLifecycle
    from sdk.permissions import PermissionSet, Permission

Architecture
------------
sdk/
    __init__.py         Package version, public API exports
    api.py              High-level facades (PluginAPI, ToolAPI, EventAPI, WorkflowAPI, ...)
    lifecycle.py        Plugin lifecycle state machine (install → enable → disable → remove)
    context.py          ExtensionContext — runtime facade for extensions
    permissions.py      Permission model — declare, check, audit permissions
    compatibility.py    AetherOS version compatibility checking
    versioning.py       Semantic version helpers, breaking-change detection
    templates.py        Starter templates for all plugin types
    validator.py        Plugin manifest/schema validation
    packaging.py        Plugin packaging and distribution format
    signing.py          Cryptographic signing and verification
"""

from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)

# SDK version — bumped on breaking changes.
# Extensions declare ``sdk_version`` in their manifest; the loader rejects
# them when the version is outside the supported range.
__version__: Final[str] = "1.0.0"

# Minimum AetherOS version required for this SDK version.
# Extensions declare ``aetheros_version``; the compatibility layer checks
# against this.
_MIN_AETHEROS_VERSION: Final[str] = "0.1.0"

# Supported SDK version range — extensions must be within this.
_SDK_VERSION_MIN: Final[str] = "1.0.0"
_SDK_VERSION_MAX: Final[str] = "1.999.999"

# Public API exports — importable from ``sdk`` directly.
from sdk.api import (
    PluginAPI,
    ToolAPI,
    EventAPI,
    WorkflowAPI,
    AgentAPI,
    MemoryAPI,
    InteractionAPI,
    EngineeringAPI,
    ClusterAPI,
)
from sdk.context import ExtensionContext
from sdk.lifecycle import (
    PluginLifecycle,
    LifecycleState,
    StateTransition,
)
from sdk.permissions import (
    Permission,
    PermissionSet,
    PermissionAudit,
)
from sdk.compatibility import (
    check_aetheros_compatibility,
    check_sdk_compatibility,
    check_platform_compatibility,
)
from sdk.versioning import (
    Version,
    VersionRange,
    BreakingChange,
    MigrationWarning,
)
from sdk.validator import (
    validate_plugin_manifest,
    validate_extension_manifest,
    ManifestValidationError,
)
from sdk.packaging import (
    PluginPackage,
    PackageFormat,
    pack_plugin,
    unpack_plugin,
)
from sdk.signing import (
    sign_package,
    verify_signature,
    PublisherKey,
    SignatureError,
)

__all__ = [
    # Version info
    "__version__",
    "_MIN_AETHEROS_VERSION",
    "_SDK_VERSION_MIN",
    "_SDK_VERSION_MAX",
    # API facades
    "PluginAPI",
    "ToolAPI",
    "EventAPI",
    "WorkflowAPI",
    "AgentAPI",
    "MemoryAPI",
    "InteractionAPI",
    "EngineeringAPI",
    "ClusterAPI",
    # Core abstractions
    "ExtensionContext",
    "PluginLifecycle",
    "LifecycleState",
    "StateTransition",
    # Permissions
    "Permission",
    "PermissionSet",
    "PermissionAudit",
    # Compatibility
    "check_aetheros_compatibility",
    "check_sdk_compatibility",
    "check_platform_compatibility",
    # Versioning
    "Version",
    "VersionRange",
    "BreakingChange",
    "MigrationWarning",
    # Validation
    "validate_plugin_manifest",
    "validate_extension_manifest",
    "ManifestValidationError",
    # Packaging
    "PluginPackage",
    "PackageFormat",
    "pack_plugin",
    "unpack_plugin",
    # Signing
    "sign_package",
    "verify_signature",
    "PublisherKey",
    "SignatureError",
]
