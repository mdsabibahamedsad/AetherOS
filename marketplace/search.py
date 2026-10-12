"""
Marketplace Search
==================

Full-text search and filtering for marketplace extensions.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from marketplace.registry import ExtensionEntry, MarketplaceRegistry, get_registry

logger = logging.getLogger(__name__)


@dataclass
class SearchQuery:
    """A structured search query."""
    text: str = ""
    kind: Optional[str] = None
    category: Optional[str] = None
    publisher: Optional[str] = None
    tags: Optional[List[str]] = None
    min_rating: float = 0.0
    verified_only: bool = False
    sort_by: str = "relevance"  # relevance, downloads, rating, updated
    limit: int = 50
    offset: int = 0


@dataclass
class SearchResult:
    """A paginated search result."""
    total: int = 0
    results: List[ExtensionEntry] = field(default_factory=list)
    query: SearchQuery = field(default_factory=SearchQuery)
    has_more: bool = False


def search_extensions(
    query: Optional[str] = None,
    *,
    kind: Optional[str] = None,
    category: Optional[str] = None,
    publisher: Optional[str] = None,
    min_rating: float = 0.0,
    verified_only: bool = False,
    sort_by: str = "relevance",
    limit: int = 50,
    offset: int = 0,
) -> SearchResult:
    """Search for extensions.

    Args:
        query: Search text.
        kind: Filter by kind.
        category: Filter by category.
        publisher: Filter by publisher.
        min_rating: Minimum rating (0.0-5.0).
        verified_only: Only verified extensions.
        sort_by: Sort method.
        limit: Max results.
        offset: Pagination offset.

    Returns:
        SearchResult with matching entries.
    """
    registry = get_registry()
    search_query = SearchQuery(
        text=query or "",
        kind=kind,
        category=category,
        publisher=publisher,
        min_rating=min_rating,
        verified_only=verified_only,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )

    # Get all extensions
    all_extensions = registry.list_extensions()

    # Filter
    filtered: List[ExtensionEntry] = []
    for ext in all_extensions:
        # Text search
        if query:
            q = query.lower()
            if not any(q in field.lower() for field in
                       [ext.name, ext.description, ext.publisher, ext.full_name]
                       if field):
                continue

        # Kind filter
        if kind and ext.kind != kind:
            continue

        # Category filter
        if category and category not in ext.categories:
            continue

        # Publisher filter
        if publisher and ext.publisher != publisher:
            continue

        # Rating filter
        if ext.rating < min_rating:
            continue

        # Verified filter
        if verified_only and not ext.verified:
            continue

        filtered.append(ext)

    # Sort
    if sort_by == "downloads":
        filtered.sort(key=lambda e: e.downloads, reverse=True)
    elif sort_by == "rating":
        filtered.sort(key=lambda e: e.rating, reverse=True)
    elif sort_by == "updated":
        filtered.sort(key=lambda e: e.updated_at, reverse=True)
    else:
        # Relevance: exact name match first, then description match
        if query:
            q = query.lower()
            def _relevance(e: ExtensionEntry) -> tuple:
                return (
                    e.name.lower() == q,
                    q in e.name.lower(),
                    q in e.description.lower(),
                )
            filtered.sort(key=_relevance, reverse=True)

    # Paginate
    total = len(filtered)
    paginated = filtered[offset:offset + limit]
    has_more = (offset + limit) < total

    return SearchResult(
        total=total,
        results=paginated,
        query=search_query,
        has_more=has_more,
    )
