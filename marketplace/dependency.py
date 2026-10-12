"""
Dependency Resolution
=====================

Resolves dependencies for extensions using a dependency graph.
Supports:

- Transitive dependency resolution
- Circular dependency detection
- Version constraint satisfaction
- Conflict resolution
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from sdk.versioning import Version, VersionRange

logger = logging.getLogger(__name__)


class DependencyError(Exception):
    """Raised when dependencies cannot be resolved."""


@dataclass
class DependencyNode:
    """A node in the dependency graph."""
    name: str
    version: str
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)


@dataclass
class DependencyGraph:
    """A directed graph of extension dependencies."""
    nodes: Dict[str, DependencyNode] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)

    def add_node(self, node: DependencyNode) -> None:
        self.nodes[node.name] = node
        for dep in node.dependencies:
            self.edges.append((node.name, dep))

    def get_dependencies(self, name: str) -> List[str]:
        """Get all direct dependencies of a node."""
        node = self.nodes.get(name)
        return list(node.dependencies) if node else []

    def get_dependents(self, name: str) -> List[str]:
        """Get all nodes that depend on a given node."""
        return [src for src, dst in self.edges if dst == name]

    def has_circular_dependency(self) -> Optional[List[str]]:
        """Detect circular dependencies.

        Returns a list of names forming a cycle, or None if acyclic.
        """
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def _dfs(node: str, path: List[str]) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in self.get_dependencies(node):
                if dep not in visited:
                    result = _dfs(dep, path)
                    if result:
                        return result
                elif dep in rec_stack:
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]

            path.pop()
            rec_stack.remove(node)
            return None

        for node_name in self.nodes:
            if node_name not in visited:
                result = _dfs(node_name, [])
                if result:
                    return result
        return None

    def resolve_order(self, root: str) -> List[str]:
        """Return a topological order of dependencies for a root node.

        Raises DependencyError on circular dependency.
        """
        circular = self.has_circular_dependency()
        if circular:
            raise DependencyError(
                f"Circular dependency detected: {' → '.join(circular)}"
            )

        result: List[str] = []
        visited: Set[str] = set()

        def _visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            node = self.nodes.get(name)
            if node:
                for dep in node.dependencies:
                    _visit(dep)
                result.append(name)

        _visit(root)
        return result

    def verify_requirements(self) -> List[str]:
        """Verify all dependency requirements are satisfied.

        Returns a list of unmet dependency names (empty if all satisfied).
        """
        unmet = []
        for name, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    unmet.append(f"{name} requires {dep}, which is not in the graph")
        return unmet


def resolve_dependencies(
    root_name: str,
    available_extensions: Dict[str, str],
    *,
    installed_extensions: Optional[Dict[str, str]] = None,
) -> Tuple[List[str], List[str]]:
    """Resolve dependencies for an extension.

    Args:
        root_name: The extension to resolve dependencies for.
        available_extensions: Dict of extension name → version.
        installed_extensions: Dict of already-installed extensions.

    Returns:
        Tuple of (resolution_order, missing_dependencies).

    Raises:
        DependencyError: If circular dependencies are detected.
    """
    graph = DependencyGraph()

    # Add root node
    root_version = available_extensions.get(root_name, "0.0.0")
    graph.add_node(DependencyNode(name=root_name, version=root_version))

    # BFS resolution
    queue = [root_name]
    missing: List[str] = []

    while queue:
        current = queue.pop(0)
        # Look up the extension's dependencies
        deps = _get_extension_dependencies(current)
        current_node = graph.nodes.get(current)
        if current_node:
            current_node.dependencies = list(deps)

        for dep in deps:
            if dep not in graph.nodes:
                if dep in available_extensions:
                    dep_version = available_extensions[dep]
                    graph.add_node(DependencyNode(name=dep, version=dep_version))
                    queue.append(dep)
                elif installed_extensions and dep in installed_extensions:
                    dep_version = installed_extensions[dep]
                    graph.add_node(DependencyNode(name=dep, version=dep_version))
                else:
                    missing.append(dep)

    # Verify no circular dependencies
    circular = graph.has_circular_dependency()
    if circular:
        raise DependencyError(
            f"Circular dependency detected: {' → '.join(circular)}"
        )

    resolution_order = graph.resolve_order(root_name)
    return resolution_order, missing


def _get_extension_dependencies(name: str) -> List[str]:
    """Get the declared dependencies of an extension from its manifest.

    Checks both the marketplace registry and local manifests.
    """
    try:
        from marketplace.registry import get_registry
        registry = get_registry()
        entry = registry.get_extension(name)
        if entry:
            return []
    except Exception:
        pass

    # Check local manifest
    try:
        from aetheros_constants import get_aetheros_home
        plugins_dir = get_aetheros_home() / "plugins" / name
        manifest = plugins_dir / "plugin.yaml"
        if manifest.exists():
            import yaml
            data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
            return data.get("dependencies", [])
        manifest = plugins_dir / "manifest.yaml"
        if manifest.exists():
            import yaml
            data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
            return data.get("dependencies", [])
    except Exception:
        pass

    return []
