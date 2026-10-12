"""
AetherOS Extension Marketplace
==============================

A managed marketplace for discovering, installing, updating, and managing
Aetheros extensions. Supports both public and private registries.

Architecture::

    marketplace/
        __init__.py      Package exports and registry connection
        registry.py      Extension registry (public + private repos)
        installer.py     Extension installation and lifecycle
        updater.py       Update checking and application
        dependency.py    Dependency resolution
        publisher.py     Publisher management
        ratings.py       Ratings and reviews
        discovery.py     Extension discovery
        search.py        Search and filtering
        cache.py         Local marketplace cache
        manifests.py     Manifest generation

Usage::

    from marketplace.registry import MarketplaceRegistry
    from marketplace.installer import install_extension
    from marketplace.search import search_extensions

    registry = MarketplaceRegistry()
    results = registry.search("code assistant")
    install_extension(results[0])
"""

from __future__ import annotations

from marketplace.registry import (
    MarketplaceRegistry,
    RegistrySource,
    ExtensionEntry,
    get_registry,
)
from marketplace.installer import (
    install_extension,
    uninstall_extension,
    InstallationResult,
)
from marketplace.updater import (
    check_for_updates,
    update_extension,
    UpdateResult,
)
from marketplace.dependency import (
    resolve_dependencies,
    DependencyGraph,
    DependencyError,
)
from marketplace.publisher import (
    Publisher,
    PublisherRegistry,
    verify_publisher,
)
from marketplace.ratings import (
    Rating,
    Review,
    RatingsManager,
)
from marketplace.discovery import (
    discover_extensions,
    discover_local_extensions,
)
from marketplace.search import (
    search_extensions,
    SearchQuery,
    SearchResult,
)
from marketplace.manifests import (
    generate_manifest,
    ManifestGenerator,
)

__all__ = [
    "MarketplaceRegistry",
    "RegistrySource",
    "ExtensionEntry",
    "get_registry",
    "install_extension",
    "uninstall_extension",
    "InstallationResult",
    "check_for_updates",
    "update_extension",
    "UpdateResult",
    "resolve_dependencies",
    "DependencyGraph",
    "DependencyError",
    "Publisher",
    "PublisherRegistry",
    "verify_publisher",
    "Rating",
    "Review",
    "RatingsManager",
    "discover_extensions",
    "discover_local_extensions",
    "search_extensions",
    "SearchQuery",
    "SearchResult",
    "generate_manifest",
    "ManifestGenerator",
]
