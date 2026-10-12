"""
Capability Registry
===================

Registry for extension capabilities. Extensions declare their capabilities
in their manifest, and the registry validates them, checks for conflicts,
and provides runtime lookup.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from extensions.capability import Capability, CapabilitySet

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """Registry for extension capabilities.

    Tracks which extensions provide which capabilities, validates
    capability declarations, and detects conflicts.

    Usage::

        registry = get_capability_registry()
        registry.register("my-plugin", [CAP_TOOL_REGISTER, CAP_EVENT_PUBLISH])
        providers = registry.find_providers(CAP_TOOL_REGISTER)
    """

    def __init__(self) -> None:
        self._extension_caps: Dict[str, CapabilitySet] = {}
        self._cap_providers: Dict[str, Set[str]] = {}

    def register(
        self,
        extension_name: str,
        capabilities: List[Capability],
    ) -> List[str]:
        """Register capabilities for an extension.

        Args:
            extension_name: Name of the extension.
            capabilities: List of capabilities it provides.

        Returns:
            List of warnings (e.g., conflicting capabilities).
        """
        warnings: List[str] = []
        cap_set = CapabilitySet(capabilities)
        self._extension_caps[extension_name] = cap_set

        for cap in capabilities:
            if cap.name not in self._cap_providers:
                self._cap_providers[cap.name] = set()
            self._cap_providers[cap.name].add(extension_name)

        return warnings

    def unregister(self, extension_name: str) -> None:
        """Remove all capabilities for an extension."""
        caps = self._extension_caps.pop(extension_name, None)
        if caps:
            for cap_name in list(self._cap_providers.keys()):
                self._cap_providers[cap_name].discard(extension_name)
                if not self._cap_providers[cap_name]:
                    del self._cap_providers[cap_name]

    def has_capability(self, extension_name: str, capability: Capability) -> bool:
        """Check if an extension has a specific capability."""
        caps = self._extension_caps.get(extension_name)
        if caps is None:
            return False
        return caps.has(capability)

    def get_capabilities(self, extension_name: str) -> CapabilitySet:
        """Get all capabilities for an extension."""
        return self._extension_caps.get(extension_name, CapabilitySet())

    def find_providers(self, capability: Capability) -> List[str]:
        """Find all extensions that provide a specific capability."""
        return sorted(self._cap_providers.get(capability.name, set()))

    def find_all_providers(self) -> Dict[str, List[str]]:
        """Find all capability providers."""
        return {
            cap: sorted(providers)
            for cap, providers in self._cap_providers.items()
        }

    def list_capabilities(self) -> List[str]:
        """List all registered capability names."""
        return sorted(self._cap_providers.keys())

    def list_extensions(self) -> List[str]:
        """List all extensions with registered capabilities."""
        return sorted(self._extension_caps.keys())

    def check_conflicts(self) -> List[Dict[str, Any]]:
        """Check for capability conflicts.

        Returns a list of conflict dicts:
            {"capability": str, "extensions": [str, ...], "issue": str}
        """
        conflicts = []
        for cap_name, providers in self._cap_providers.items():
            # More than one provider for exclusive capabilities
            # (exclusive capabilities are rare, but we check)
            if len(providers) > 1 and cap_name in {
                "memory:provider", "context:engine",
            }:
                conflicts.append({
                    "capability": cap_name,
                    "extensions": sorted(providers),
                    "issue": f"Multiple providers for exclusive capability '{cap_name}'",
                })
        return conflicts


# Global singleton
_registry_instance: Optional[CapabilityRegistry] = None


def get_capability_registry() -> CapabilityRegistry:
    """Return the global CapabilityRegistry singleton."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = CapabilityRegistry()
    return _registry_instance
