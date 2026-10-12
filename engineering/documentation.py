"""
Documentation Generator — generates and updates project documentation.

Generates:
  - API documentation
  - Architecture documentation
  - Developer guides
  - Migration notes
  - Release notes

Only modifies documentation relevant to the implemented changes.
"""

from __future__ import annotations

import enum
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class DocumentationType(enum.Enum):
    """Types of documentation that can be generated."""
    API = "api"
    ARCHITECTURE = "architecture"
    DEVELOPER_GUIDE = "developer_guide"
    USER_GUIDE = "user_guide"
    README = "readme"
    MIGRATION_NOTE = "migration_note"
    RELEASE_NOTE = "release_note"
    CONTRIBUTING = "contributing"
    CHANGELOG = "changelog"
    ADR = "adr"  # Architecture Decision Record


@dataclass
class DocumentationSection:
    """A section of documentation.

    Attributes:
        title: Section title
        content: Section content (Markdown)
        type: Section type
        order: Display order
    """
    title: str = ""
    content: str = ""
    type: str = "markdown"
    order: int = 0


@dataclass
class DocChange:
    """A change to a documentation file.

    Attributes:
        id: Unique change ID
        file_path: Path to the documentation file
        change_type: Type of change (create, update, delete)
        original_content: Previous content
        new_content: New content
        reason: Why this change was made
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    file_path: str = ""
    change_type: str = "update"  # create, update, delete
    original_content: str = ""
    new_content: str = ""
    reason: str = ""


class DocumentationGenerator:
    """Generates and updates project documentation.

    Creates structured documentation for APIs, architecture, developer guides,
    and release notes. Only touches files relevant to the implemented changes.

    Usage:
        gen = DocumentationGenerator(event_bus)
        changes = gen.generate_api_doc(module_name, interfaces)
        gen.apply_changes(changes)
    """

    def __init__(self, event_bus: Optional[EventBus] = None,
                 docs_dir: Optional[str] = None):
        self._event_bus = event_bus
        self._docs_dir = Path(docs_dir) if docs_dir else Path("docs")
        self._changes: Dict[str, DocChange] = {}

    def set_docs_dir(self, path: str) -> None:
        """Set the documentation directory."""
        self._docs_dir = Path(path)

    # ------------------------------------------------------------------
    # Documentation generation
    # ------------------------------------------------------------------

    def generate_readme(self, project_name: str,
                        description: str = "",
                        sections: List[DocumentationSection] = None,
                        changes: List[str] = None) -> DocChange:
        """Generate or update a README file.

        Args:
            project_name: Name of the project
            description: Project description
            sections: Additional sections to include
            changes: List of changes to document

        Returns:
            DocChange for the README update
        """
        readme_path = self._docs_dir.parent / "README.md"

        # Build README content
        parts = [
            f"# {project_name}",
            f"",
            description or f"## Overview",
        ]

        if sections:
            for section in sections:
                parts.extend(["", f"## {section.title}", "", section.content])

        if changes:
            parts.extend(["", "## Recent Changes", ""])
            for change in changes:
                parts.append(f"- {change}")

        new_content = "\n".join(parts)

        # Read existing content
        original = ""
        if readme_path.exists():
            original = readme_path.read_text(encoding="utf-8")

        change = DocChange(
            file_path=str(readme_path),
            change_type="update" if original else "create",
            original_content=original,
            new_content=new_content,
            reason="Updated README with project documentation",
        )

        self._changes[change.id] = change

        logger.info("DocumentationGenerator: %s README", change.change_type)

        if self._event_bus:
            self._event_bus.emit_async("engineering.doc_generated", {
                "file_path": change.file_path,
                "change_type": change.change_type,
            })

        return change

    def generate_api_doc(self, module_name: str,
                         endpoints: List[Dict[str, Any]] = None,
                         output_path: str = "") -> DocChange:
        """Generate API documentation for a module.

        Args:
            module_name: Name of the module
            endpoints: List of API endpoint definitions
            output_path: Output file path (generated if empty)

        Returns:
            DocChange for the API documentation
        """
        if not output_path:
            output_path = str(self._docs_dir / "api" / f"{module_name.lower()}.md")

        parts = [
            f"# {module_name} API",
            f"",
            f"## Overview",
            f"",
            f"API documentation for the {module_name} module.",
        ]

        if endpoints:
            parts.extend(["", "## Endpoints", ""])
            for endpoint in endpoints:
                method = endpoint.get("method", "GET")
                path = endpoint.get("path", "/")
                description = endpoint.get("description", "")
                parts.append(f"### {method} `{path}`")
                if description:
                    parts.append(f"")
                    parts.append(description)
                parts.append(f"")

        new_content = "\n".join(parts)
        output_path_obj = Path(output_path)

        original = ""
        if output_path_obj.exists():
            original = output_path_obj.read_text(encoding="utf-8")

        change = DocChange(
            file_path=str(output_path),
            change_type="update" if original else "create",
            original_content=original,
            new_content=new_content,
            reason=f"Generated API documentation for {module_name}",
        )

        self._changes[change.id] = change
        return change

    def generate_architecture_doc(self, architecture: Any) -> DocChange:
        """Generate architecture documentation from an ArchitectureDesign.

        Args:
            architecture: ArchitectureDesign object

        Returns:
            DocChange for the architecture document
        """
        title = getattr(architecture, 'title', 'Architecture')
        arch_id = getattr(architecture, 'id', '')

        output_path = self._docs_dir / "architecture" / f"{arch_id}.md"

        parts = [
            f"# {title}",
            f"",
            f"## Overview",
            f"",
        ]

        # Overview
        overview = getattr(architecture, 'overview', '')
        if overview:
            parts.append(overview)
            parts.append("")

        # Modules
        if hasattr(architecture, 'modules') and architecture.modules:
            parts.extend(["## Module Architecture", ""])
            parts.append("| Module | Description | Technology | Status |")
            parts.append("|--------|-------------|------------|--------|")
            for module in architecture.modules:
                parts.append(
                    f"| {module.name} | {module.description[:60]} | "
                    f"{module.technology or 'N/A'} | {module.status} |"
                )
            parts.append("")

        # Interfaces
        if hasattr(architecture, 'interfaces') and architecture.interfaces:
            parts.extend(["## Interfaces", ""])
            for iface in architecture.interfaces:
                parts.extend([
                    f"### {iface.name}",
                    f"",
                    f"- **Provider**: {iface.provider}",
                    f"- **Consumer**: {iface.consumer}",
                    f"- **Contract**: {iface.contract}",
                    f"- **Data Format**: {iface.data_format}",
                    f"",
                ])

        # Technology recommendations
        if hasattr(architecture, 'technologies') and architecture.technologies:
            parts.extend(["## Technology Stack", ""])
            parts.append("| Technology | Category | Risk | Rationale |")
            parts.append("|------------|----------|------|-----------|")
            for tech in architecture.technologies:
                parts.append(
                    f"| {tech.name} | {tech.category} | {tech.risk_level} | "
                    f"{tech.rationale[:60]} |"
                )
            parts.append("")

        # Design decisions
        if hasattr(architecture, 'design_decisions') and architecture.design_decisions:
            parts.extend(["## Design Decisions", ""])
            for decision in architecture.design_decisions:
                parts.extend([
                    f"### {decision.title}",
                    f"",
                    f"- **Status**: {decision.status}",
                    f"- **Decision**: {decision.decision[:100]}",
                    f"- **Rationale**: {decision.rationale[:200]}",
                    f"",
                ])

        new_content = "\n".join(parts)

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        original = ""
        if output_path_obj.exists():
            original = output_path_obj.read_text(encoding="utf-8")

        change = DocChange(
            file_path=str(output_path),
            change_type="update" if original else "create",
            original_content=original,
            new_content=new_content,
            reason=f"Generated architecture documentation for {title}",
        )

        self._changes[change.id] = change
        return change

    def generate_developer_guide(self, module_name: str,
                                 setup_steps: List[str] = None,
                                 usage_examples: List[str] = None,
                                 output_path: str = "") -> DocChange:
        """Generate a developer guide for a module.

        Args:
            module_name: Module name
            setup_steps: Setup instructions
            usage_examples: Usage examples
            output_path: Output path

        Returns:
            DocChange for the guide
        """
        if not output_path:
            output_path = str(self._docs_dir / "guides" / f"{module_name.lower()}.md")

        parts = [
            f"# {module_name} Developer Guide",
            f"",
            f"## Getting Started",
            f"",
        ]

        if setup_steps:
            parts.extend(["### Setup", ""])
            for i, step in enumerate(setup_steps, 1):
                parts.append(f"{i}. {step}")
            parts.append("")

        if usage_examples:
            parts.extend(["### Usage Examples", ""])
            for example in usage_examples:
                parts.extend([f"```", example, "```", ""])

        new_content = "\n".join(parts)
        output_path_obj = Path(output_path)

        original = ""
        if output_path_obj.exists():
            original = output_path_obj.read_text(encoding="utf-8")

        change = DocChange(
            file_path=str(output_path),
            change_type="update" if original else "create",
            original_content=original,
            new_content=new_content,
            reason=f"Generated developer guide for {module_name}",
        )

        self._changes[change.id] = change
        return change

    def generate_api_reference(self, module_name: str,
                                classes: List[Dict[str, Any]] = None,
                                functions: List[Dict[str, Any]] = None,
                                output_path: str = "") -> DocChange:
        """Generate API reference documentation.

        Args:
            module_name: Module name
            classes: Class definitions
            functions: Function definitions
            output_path: Output path

        Returns:
            DocChange for the reference
        """
        if not output_path:
            output_path = str(self._docs_dir / "api" / f"{module_name.lower()}-reference.md")

        parts = [
            f"# {module_name} API Reference",
            f"",
        ]

        if classes:
            parts.extend(["## Classes", ""])
            for cls in classes:
                name = cls.get("name", "")
                docstring = cls.get("docstring", "")
                methods = cls.get("methods", [])

                parts.extend([f"### `{name}`", ""])
                if docstring:
                    parts.append(docstring)
                    parts.append("")

                if methods:
                    parts.extend(["**Methods:**", ""])
                    for method in methods:
                        m_name = method.get("name", "")
                        m_doc = method.get("docstring", "")
                        parts.append(f"- `{m_name}()`: {m_doc[:100]}")
                    parts.append("")

        if functions:
            parts.extend(["## Functions", ""])
            for func in functions:
                name = func.get("name", "")
                docstring = func.get("docstring", "")
                args = func.get("args", [])

                parts.extend([f"### `{name}()`", ""])
                if docstring:
                    parts.append(docstring)
                    parts.append("")
                if args:
                    parts.append(f"**Args:** {', '.join(args)}")
                    parts.append("")

        new_content = "\n".join(parts)
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        original = ""
        if output_path_obj.exists():
            original = output_path_obj.read_text(encoding="utf-8")

        change = DocChange(
            file_path=str(output_path),
            change_type="update" if original else "create",
            original_content=original,
            new_content=new_content,
            reason=f"Generated API reference for {module_name}",
        )

        self._changes[change.id] = change
        return change

    # ------------------------------------------------------------------
    # Change management
    # ------------------------------------------------------------------

    def apply_changes(self, changes: List[DocChange]) -> int:
        """Apply documentation changes to disk.

        Args:
            changes: List of DocChange objects to apply

        Returns:
            Number of changes applied
        """
        applied = 0
        for change in changes:
            try:
                path = Path(change.file_path)
                path.parent.mkdir(parents=True, exist_ok=True)

                if change.change_type == "delete":
                    if path.exists():
                        path.unlink()
                else:
                    path.write_text(change.new_content, encoding="utf-8")

                applied += 1
                logger.debug("DocumentationGenerator: applied %s to %s",
                             change.change_type, change.file_path)
            except Exception as exc:
                logger.error("DocumentationGenerator: failed to apply %s: %s",
                             change.file_path, exc)

        if self._event_bus and applied > 0:
            self._event_bus.emit_async("engineering.docs_applied", {
                "applied": applied,
                "total": len(changes),
            })

        return applied

    def get_change(self, change_id: str) -> Optional[DocChange]:
        """Get a documentation change by ID."""
        return self._changes.get(change_id)

    def get_open_changes(self) -> List[DocChange]:
        """Get all unapplied documentation changes."""
        return list(self._changes.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get generator statistics."""
        return {
            "total_changes": len(self._changes),
            "by_type": {
                ct: sum(1 for c in self._changes.values() if c.change_type == ct)
                for ct in {"create", "update", "delete"}
            },
            "docs_directory": str(self._docs_dir),
        }
