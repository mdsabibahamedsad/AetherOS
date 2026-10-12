"""
Extension Discovery
===================

Discovers available extensions from multiple sources:
- Public marketplace registry
- Private/enterprise registries
- Local filesystem (installed plugins)
- Git repositories
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from marketplace.registry import (
    ExtensionEntry,
    MarketplaceRegistry,
    RegistryConfig,
    RegistrySource,
    get_registry,
)
from marketplace.search import search_extensions

logger = logging.getLogger(__name__)


def discover_extensions(
    *,
    query: str = "",
    kind: Optional[str] = None,
    category: Optional[str] = None,
    publisher: Optional[str] = None,
    verified_only: bool = False,
    include_local: bool = True,
    include_remote: bool = True,
) -> List[ExtensionEntry]:
    """Discover extensions from all configured sources.

    Args:
        query: Optional search term.
        kind: Filter by extension kind (tool, agent, workflow, etc.).
        category: Filter by category.
        publisher: Filter by publisher.
        verified_only: Only show verified extensions.
        include_local: Include locally installed extensions.
        include_remote: Include remote registry extensions.

    Returns:
        List of matching ExtensionEntry objects.
    """
    registry = get_registry()

    if query:
        results = registry.search(
            query,
            kind=kind,
            category=category,
            publisher=publisher,
        )
    else:
        results = registry.list_extensions()

    # Filter
    if verified_only:
        results = [r for r in results if r.verified]
    if kind:
        results = [r for r in results if r.kind == kind]
    if category:
        results = [r for r in results if category in r.categories]
    if publisher:
        results = [r for r in results if r.publisher == publisher]

    return results


def discover_local_extensions() -> List[ExtensionEntry]:
    """Discover only locally installed extensions."""
    registry = get_registry()
    return registry.list_extensions(source_filter=RegistrySource.LOCAL)


def discover_by_kind(kind: str) -> List[ExtensionEntry]:
    """Discover extensions of a specific kind.

    Args:
        kind: Extension kind (tool, agent, workflow, memory, model, etc.).

    Returns:
        List of matching ExtensionEntry objects.
    """
    return discover_extensions(kind=kind)


def get_popular_extensions(limit: int = 10) -> List[ExtensionEntry]:
    """Get the most popular extensions by download count."""
    results = discover_extensions()
    results.sort(key=lambda r: r.downloads, reverse=True)
    return results[:limit]


def get_top_rated_extensions(limit: int = 10) -> List[ExtensionEntry]:
    """Get the highest-rated extensions."""
    results = discover_extensions()
    results.sort(key=lambda r: r.rating, reverse=True)
    return results[:limit]


def get_recently_updated_extensions(limit: int = 10) -> List[ExtensionEntry]:
    """Get recently updated extensions."""
    results = discover_extensions()
    results.sort(key=lambda r: r.updated_at, reverse=True)
    return results[:limit]
