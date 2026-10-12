"""
Web UI for AetherOS Developer Platform
======================================

Web interface for the developer platform:
    - Developer Center
    - Marketplace
    - Installed Extensions
    - Extension Details
    - Ratings & Reviews
    - Permissions

Usage::

    from aetheros_developer_platform.web_ui import WebUI

    ui = WebUI()
    ui.start(port=8080)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WebPage:
    """A web page definition."""
    path: str
    title: str
    description: str = ""
    template: str = ""
    handler: Optional[Any] = None


class WebUI:
    """Web UI for the developer platform.

    Usage::

        ui = WebUI()

        # Add a page
        ui.add_page("/", "Home", template="home.html")

        # Add an API endpoint
        ui.add_api_endpoint("/api/extensions", list_extensions)

        # Start the server
        ui.start(port=8080)
    """

    def __init__(self) -> None:
        self._pages: Dict[str, WebPage] = {}
        self._api_endpoints: Dict[str, Any] = {}
        self._templates: Dict[str, str] = {}

    def add_page(
        self,
        path: str,
        title: str,
        description: str = "",
        template: str = "",
        handler: Optional[Any] = None,
    ) -> None:
        """Add a web page."""
        page = WebPage(
            path=path,
            title=title,
            description=description,
            template=template,
            handler=handler,
        )
        self._pages[path] = page
        logger.info("Added web page: %s", path)

    def add_api_endpoint(
        self,
        path: str,
        handler: Any,
    ) -> None:
        """Add an API endpoint."""
        self._api_endpoints[path] = handler
        logger.info("Added API endpoint: %s", path)

    def add_template(self, name: str, content: str) -> None:
        """Add a template."""
        self._templates[name] = content

    def get_page(self, path: str) -> Optional[WebPage]:
        """Get a page by path."""
        return self._pages.get(path)

    def list_pages(self) -> List[WebPage]:
        """List all pages."""
        return list(self._pages.values())

    def render_page(self, path: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Render a page."""
        page = self._pages.get(path)
        if not page:
            return "<h1>404 - Page Not Found</h1>"

        if page.handler:
            return page.handler(context or {})

        if page.template and page.template in self._templates:
            template = self._templates[page.template]
            # Simple template rendering
            for key, value in (context or {}).items():
                template = template.replace(f"{{{{{key}}}}}", str(value))
            return template

        return f"<h1>{page.title}</h1><p>{page.description}</p>"

    def get_developer_center_html(self) -> str:
        """Get the Developer Center HTML."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AetherOS Developer Center</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .header { background: #007ACC; color: white; padding: 1rem 2rem; }
        .nav { display: flex; gap: 2rem; padding: 1rem 2rem; background: #f5f5f5; }
        .nav a { text-decoration: none; color: #333; }
        .nav a:hover { color: #007ACC; }
        .content { padding: 2rem; }
        .card { background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
        .card h3 { margin-bottom: 0.5rem; }
        .btn { background: #007ACC; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #005a9e; }
    </style>
</head>
<body>
    <div class="header">
        <h1>AetherOS Developer Center</h1>
    </div>
    <div class="nav">
        <a href="/">Dashboard</a>
        <a href="/marketplace">Marketplace</a>
        <a href="/extensions">Extensions</a>
        <a href="/docs">Documentation</a>
    </div>
    <div class="content">
        <div class="card">
            <h3>Welcome to AetherOS Developer Platform</h3>
            <p>Build, publish, and manage extensions for AetherOS.</p>
        </div>
        <div class="card">
            <h3>Quick Start</h3>
            <p>Create your first extension with the SDK:</p>
            <code>aetheros sdk init my-extension --language python</code>
        </div>
    </div>
</body>
</html>
"""

    def get_marketplace_html(self) -> str:
        """Get the Marketplace HTML."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AetherOS Marketplace</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .header { background: #007ACC; color: white; padding: 1rem 2rem; }
        .search { padding: 1rem 2rem; background: #f5f5f5; }
        .search input { width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; }
        .content { padding: 2rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; }
        .card { background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; }
        .card h3 { margin-bottom: 0.5rem; }
        .card .rating { color: #FF9800; }
        .card .downloads { color: #666; font-size: 0.875rem; }
        .btn { background: #007ACC; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="header">
        <h1>AetherOS Marketplace</h1>
    </div>
    <div class="search">
        <input type="text" placeholder="Search extensions..." id="search">
    </div>
    <div class="content">
        <h2>Trending Extensions</h2>
        <div class="grid" id="extensions">
            <!-- Extensions will be loaded here -->
        </div>
    </div>
</body>
</html>
"""

    def start(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """Start the web server.

        Note: This is a placeholder. In production, use a proper web framework
        like FastAPI, Flask, or aiohttp.
        """
        logger.info("Starting web UI on %s:%d", host, port)
        print(f"Developer Center would start on http://{host}:{port}")
        print("Web UI is a placeholder - use a proper web framework for production")


# Global web UI instance
_web_ui: Optional[WebUI] = None


def get_web_ui() -> WebUI:
    """Return the global WebUI singleton."""
    global _web_ui
    if _web_ui is None:
        _web_ui = WebUI()
    return _web_ui
