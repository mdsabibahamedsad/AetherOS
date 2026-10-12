"""
REST API for AetherOS Developer Platform
========================================

REST API endpoints for the developer platform.

Endpoints:
    - GET /api/extensions - List all extensions
    - GET /api/extensions/:id - Get extension details
    - POST /api/extensions - Install an extension
    - DELETE /api/extensions/:id - Uninstall an extension
    - GET /api/marketplace/search - Search marketplace
    - GET /api/marketplace/trending - Get trending extensions
    - GET /api/marketplace/featured - Get featured extensions
    - POST /api/publish - Publish an extension
    - GET /api/developer/stats - Get developer statistics

Usage::

    from aetheros_developer_platform.api import DeveloperAPI

    api = DeveloperAPI()
    extensions = api.list_extensions()
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """API response wrapper."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "success": self.success,
            "timestamp": self.timestamp,
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class DeveloperAPI:
    """REST API for the developer platform.

    Usage::

        api = DeveloperAPI()

        # List extensions
        response = api.list_extensions()

        # Search marketplace
        response = api.search_marketplace("code assistant")

        # Get trending extensions
        response = api.get_trending()
    """

    def __init__(self) -> None:
        self._routes: Dict[str, Callable] = {}
        self._register_routes()

    def _register_routes(self) -> None:
        """Register API routes."""
        self._routes["GET /api/extensions"] = self.list_extensions
        self._routes["GET /api/extensions/:id"] = self.get_extension
        self._routes["POST /api/extensions"] = self.install_extension
        self._routes["DELETE /api/extensions/:id"] = self.uninstall_extension
        self._routes["GET /api/marketplace/search"] = self.search_marketplace
        self._routes["GET /api/marketplace/trending"] = self.get_trending
        self._routes["GET /api/marketplace/featured"] = self.get_featured
        self._routes["POST /api/publish"] = self.publish_extension
        self._routes["GET /api/developer/stats"] = self.get_developer_stats

    def list_extensions(self, **kwargs: Any) -> APIResponse:
        """List all installed extensions."""
        try:
            from extensions.manager import get_extension_manager
            manager = get_extension_manager()
            extensions = manager.list_extensions()

            data = [
                {
                    "name": ext.name,
                    "version": ext.version,
                    "state": ext.state.value,
                    "description": ext.manifest.description,
                }
                for ext in extensions
            ]

            return APIResponse(success=True, data=data)
        except Exception as exc:
            return APIResponse(success=False, error=str(exc))

    def get_extension(self, extension_id: str, **kwargs: Any) -> APIResponse:
        """Get extension details."""
        try:
            from extensions.manager import get_extension_manager
            manager = get_extension_manager()
            ext = manager.get_extension(extension_id)

            if not ext:
                return APIResponse(success=False, error="Extension not found")

            data = {
                "name": ext.name,
                "version": ext.version,
                "state": ext.state.value,
                "description": ext.manifest.description,
                "author": ext.manifest.author,
                "permissions": ext.manifest.permissions,
                "dependencies": ext.manifest.dependencies,
            }

            return APIResponse(success=True, data=data)
        except Exception as exc:
            return APIResponse(success=False, error=str(exc))

    def install_extension(self, source: str, **kwargs: Any) -> APIResponse:
        """Install an extension."""
        try:
            from marketplace.installer import install_extension

            result = install_extension(source, **kwargs)

            if result.success:
                return APIResponse(
                    success=True,
                    data={
                        "name": result.name,
                        "version": result.version,
                        "status": result.status.value,
                    },
                )
            else:
                return APIResponse(success=False, error=result.error)
        except Exception as exc:
            return APIResponse(success=False, error=str(exc))

    def uninstall_extension(self, extension_id: str, **kwargs: Any) -> APIResponse:
        """Uninstall an extension."""
        try:
            from marketplace.installer import uninstall_extension

            success = uninstall_extension(extension_id, **kwargs)

            if success:
                return APIResponse(success=True, data={"name": extension_id})
            else:
                return APIResponse(success=False, error="Failed to uninstall")
        except Exception as exc:
            return APIResponse(success=False, error=str(exc))

    def search_marketplace(
        self,
        query: str,
        limit: int = 20,
        **kwargs: Any,
    ) -> APIResponse:
        """Search the marketplace."""
        try:
            from marketplace.search import search_extensions

            results = search_extensions(query, limit=limit)

            data = [
                {
                    "name": ext.full_name,
                    "version": ext.version,
                    "description": ext.description,
                    "downloads": ext.downloads,
                    "rating": ext.rating,
                }
                for ext in results
            ]

            return APIResponse(success=True, data=data)
        except Exception as exc:
            return APIResponse(success=False, error=str(exc))

    def get_trending(self, limit: int = 20, **kwargs: Any) -> APIResponse:
        """Get trending extensions."""
        try:
            from marketplace.registry import get_registry

            registry = get_registry()
            extensions = registry.list_extensions()

            # Sort by downloads
            extensions.sort(key=lambda e: e.downloads, reverse=True)
            extensions = extensions[:limit]

            data = [
                {
                    "name": ext.full_name,
                    "version": ext.version,
                    "description": ext.description,
                    "downloads": ext.downloads,
                    "rating": ext.rating,
                }
                for ext in extensions
            ]

            return APIResponse(success=True, data=data)
        except Exception as exc:
            return APIResponse(success=False, error=str(exc))

    def get_featured(self, limit: int = 20, **kwargs: Any) -> APIResponse:
        """Get featured extensions."""
        try:
            from marketplace.registry import get_registry

            registry = get_registry()
            extensions = registry.list_extensions()

            # Filter verified extensions
            extensions = [e for e in extensions if e.verified]
            extensions = extensions[:limit]

            data = [
                {
                    "name": ext.full_name,
                    "version": ext.version,
                    "description": ext.description,
                    "downloads": ext.downloads,
                    "rating": ext.rating,
                }
                for ext in extensions
            ]

            return APIResponse(success=True, data=data)
        except Exception as exc:
            return APIResponse(success=False, error=str(exc))

    def publish_extension(
        self,
        extension_path: str,
        registry_url: Optional[str] = None,
        **kwargs: Any,
    ) -> APIResponse:
        """Publish an extension to the marketplace."""
        try:
            from marketplace.publisher import Publisher

            publisher = Publisher()
            result = publisher.publish(extension_path, registry_url=registry_url)

            if result.get("success"):
                return APIResponse(success=True, data=result)
            else:
                return APIResponse(success=False, error=result.get("error", "Publish failed"))
        except Exception as exc:
            return APIResponse(success=False, error=str(exc))

    def get_developer_stats(self, **kwargs: Any) -> APIResponse:
        """Get developer statistics."""
        try:
            from extensions.manager import get_extension_manager
            from marketplace.registry import get_registry

            ext_manager = get_extension_manager()
            registry = get_registry()

            extensions = ext_manager.list_extensions()
            marketplace_extensions = registry.list_extensions()

            data = {
                "installed_extensions": len(extensions),
                "marketplace_extensions": len(marketplace_extensions),
                "enabled_extensions": sum(
                    1 for e in extensions if e.state.value == "enabled"
                ),
                "health_summary": ext_manager.get_health_summary(),
            }

            return APIResponse(success=True, data=data)
        except Exception as exc:
            return APIResponse(success=False, error=str(exc))

    def handle_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """Handle an API request.

        Args:
            method: HTTP method.
            path: Request path.
            body: Request body.
            params: Query parameters.

        Returns:
            API response.
        """
        # Match route
        for route, handler in self._routes.items():
            route_method, route_path = route.split(" ", 1)

            if route_method != method:
                continue

            # Simple pattern matching
            if route_path == path:
                return handler(**(body or {}))

            # Parameter matching
            if ":id" in route_path:
                base_path = route_path.replace("/:id", "")
                if path.startswith(base_path + "/"):
                    ext_id = path[len(base_path) + 1 :]
                    return handler(ext_id, **(body or {}))

        return APIResponse(success=False, error="Not found")


# Global API instance
_api: Optional[DeveloperAPI] = None


def get_developer_api() -> DeveloperAPI:
    """Return the global DeveloperAPI singleton."""
    global _api
    if _api is None:
        _api = DeveloperAPI()
    return _api
