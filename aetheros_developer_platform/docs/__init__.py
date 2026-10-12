"""
Documentation for AetherOS Developer Platform
==============================================

Auto-generated SDK documentation, API explorer, examples, templates, and tutorials.

Usage::

    from aetheros_developer_platform.docs import DocumentationManager

    manager = DocumentationManager()
    manager.generate_sdk_docs("python")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DocPage:
    """A documentation page."""
    title: str
    content: str
    path: str = ""
    category: str = ""
    order: int = 0


class DocumentationManager:
    """Manages documentation for the developer platform.

    Usage::

        manager = DocumentationManager()

        # Generate SDK docs
        manager.generate_sdk_docs("python")

        # Get API reference
        api_ref = manager.get_api_reference()

        # Get examples
        examples = manager.get_examples("plugin")
    """

    def __init__(self) -> None:
        self._pages: Dict[str, DocPage] = {}
        self._examples: Dict[str, List[Dict[str, Any]]] = {}
        self._templates: Dict[str, str] = {}

    def generate_sdk_docs(self, language: str) -> DocPage:
        """Generate SDK documentation for a language."""
        docs = {
            "python": self._generate_python_docs(),
            "typescript": self._generate_typescript_docs(),
            "javascript": self._generate_javascript_docs(),
            "go": self._generate_go_docs(),
            "rust": self._generate_rust_docs(),
            "csharp": self._generate_csharp_docs(),
            "java": self._generate_java_docs(),
        }

        doc = docs.get(language, DocPage(
            title=f"{language.title()} SDK Documentation",
            content=f"Documentation for the {language.title()} SDK.",
        ))

        self._pages[f"sdk/{language}"] = doc
        return doc

    def _generate_python_docs(self) -> DocPage:
        """Generate Python SDK documentation."""
        content = """
# Python SDK for AetherOS

## Installation

```bash
pip install aetheros-sdk
```

## Quick Start

```python
from aetheros_sdk import ExtensionContext

def register(ctx: ExtensionContext):
    # Register tools
    ctx.tools.register_tool(
        name="my_tool",
        description="My custom tool",
        parameters={},
        handler=my_handler,
    )

    # Register event handlers
    @ctx.events.on("session:start")
    def on_start(event):
        print("Session started!")
```

## API Reference

### ExtensionContext

The main interface between your extension and AetherOS.

#### Properties
- `name`: Extension name
- `manifest`: Extension manifest
- `tools`: Tool API
- `events`: Event API
- `memory`: Memory API
- `permissions`: Permission set

#### Methods
- `log(level, message)`: Log a message
- `get_config(key, default)`: Get config value
- `http_get(url)`: Make HTTP request
- `read_file(path)`: Read a file
- `write_file(path, content)`: Write a file

### ToolAPI

Register and manage tools.

```python
ctx.tools.register_tool(
    name="tool_name",
    description="Tool description",
    parameters={"type": "object", "properties": {...}},
    handler=my_handler,
)
```

### EventAPI

Publish and subscribe to events.

```python
# Subscribe
@ctx.events.on("file:created")
def on_file_created(event):
    print(f"File: {event.data['path']}")

# Publish
ctx.events.publish("custom:event", {"key": "value"})
```

### MemoryAPI

Access the memory system.

```python
# Search
results = ctx.memory.search("query", limit=10)

# Store
ctx.memory.store("key", {"data": "value"})
```
"""
        return DocPage(
            title="Python SDK Documentation",
            content=content,
            category="sdk",
        )

    def _generate_typescript_docs(self) -> DocPage:
        """Generate TypeScript SDK documentation."""
        content = """
# TypeScript SDK for AetherOS

## Installation

```bash
npm install @aetheros/sdk
```

## Quick Start

```typescript
import { ExtensionContext } from '@aetheros/sdk';

export function register(ctx: ExtensionContext): void {
    // Register tools
    ctx.tools.registerTool({
        name: 'my_tool',
        description: 'My custom tool',
        parameters: {},
        handler: myHandler,
    });

    // Register event handlers
    ctx.events.on('session:start', (event) => {
        console.log('Session started!');
    });
}
```

## API Reference

### ExtensionContext

```typescript
interface ExtensionContext {
    name: string;
    manifest: ExtensionManifest;
    tools: ToolAPI;
    events: EventAPI;
    memory: MemoryAPI;
    permissions: PermissionSet;
}
```

### ToolAPI

```typescript
ctx.tools.registerTool({
    name: string,
    description: string,
    parameters: object,
    handler: (args) => Promise<string>,
});
```

### EventAPI

```typescript
ctx.events.on('event:type', (event) => {});
ctx.events.emit('event:type', { data: {} });
```
"""
        return DocPage(
            title="TypeScript SDK Documentation",
            content=content,
            category="sdk",
        )

    def _generate_javascript_docs(self) -> DocPage:
        return DocPage(
            title="JavaScript SDK Documentation",
            content="# JavaScript SDK for AetherOS\n\nSee TypeScript SDK docs for API reference.",
            category="sdk",
        )

    def _generate_go_docs(self) -> DocPage:
        return DocPage(
            title="Go SDK Documentation",
            content="# Go SDK for AetherOS\n\nSee SDK documentation for API reference.",
            category="sdk",
        )

    def _generate_rust_docs(self) -> DocPage:
        return DocPage(
            title="Rust SDK Documentation",
            content="# Rust SDK for AetherOS\n\nSee SDK documentation for API reference.",
            category="sdk",
        )

    def _generate_csharp_docs(self) -> DocPage:
        return DocPage(
            title="C# SDK Documentation",
            content="# C# SDK for AetherOS\n\nSee SDK documentation for API reference.",
            category="sdk",
        )

    def _generate_java_docs(self) -> DocPage:
        return DocPage(
            title="Java SDK Documentation",
            content="# Java SDK for AetherOS\n\nSee SDK documentation for API reference.",
            category="sdk",
        )

    def get_api_reference(self) -> str:
        """Get API reference documentation."""
        return """
# AetherOS Developer Platform API Reference

## Plugin API

### register_plugin(name, **kwargs)
Register a generic plugin.

### register_agent(name, **kwargs)
Register an AI agent.

### register_tool(name, **kwargs)
Register a tool plugin.

### register_workflow(name, **kwargs)
Register a workflow plugin.

### register_mcp(name, **kwargs)
Register an MCP server.

### register_sidebar(name, **kwargs)
Register a sidebar app.

### register_dashboard(name, **kwargs)
Register a dashboard card.

### register_theme(name, **kwargs)
Register a theme.

## Extension Manager

### install_extension(source, **kwargs)
Install an extension.

### uninstall_extension(name, **kwargs)
Uninstall an extension.

### update_extension(name, **kwargs)
Update an extension.

### list_extensions()
List all installed extensions.

## Marketplace

### search_extensions(query, **kwargs)
Search the marketplace.

### get_extension(name)
Get extension details.

### get_trending()
Get trending extensions.

### get_featured()
Get featured extensions.
"""

    def get_examples(self, category: str) -> List[Dict[str, Any]]:
        """Get examples for a category."""
        return self._examples.get(category, [])

    def add_example(
        self,
        category: str,
        title: str,
        code: str,
        description: str = "",
    ) -> None:
        """Add an example."""
        if category not in self._examples:
            self._examples[category] = []
        self._examples[category].append({
            "title": title,
            "code": code,
            "description": description,
        })

    def get_page(self, path: str) -> Optional[DocPage]:
        """Get a documentation page."""
        return self._pages.get(path)

    def list_pages(self, category: Optional[str] = None) -> List[DocPage]:
        """List documentation pages."""
        pages = list(self._pages.values())
        if category:
            pages = [p for p in pages if p.category == category]
        return sorted(pages, key=lambda p: p.order)


# Global documentation manager
_docs_manager: Optional[DocumentationManager] = None


def get_docs_manager() -> DocumentationManager:
    """Return the global DocumentationManager singleton."""
    global _docs_manager
    if _docs_manager is None:
        _docs_manager = DocumentationManager()
    return _docs_manager
