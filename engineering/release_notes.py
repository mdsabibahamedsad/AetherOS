"""
Release Notes Generator — creates structured release notes from changes.

Generates release notes organized by:
  - Features
  - Bug Fixes
  - Improvements
  - Breaking Changes
  - Security
  - Documentation
"""

from __future__ import annotations

import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ChangeCategory(enum.Enum):
    """Categories for changes in release notes."""
    FEATURE = "feature"
    BUG_FIX = "bug_fix"
    IMPROVEMENT = "improvement"
    BREAKING_CHANGE = "breaking_change"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    DEPRECATION = "deprecation"
    PERFORMANCE = "performance"
    REFACTOR = "refactor"
    TESTING = "testing"
    BUILD = "build"
    OTHER = "other"


@dataclass
class ChangeEntry:
    """A single change entry for release notes.

    Attributes:
        id: Unique entry ID
        category: Change category
        description: Description of the change
        issue_ref: Reference to issue or PR (optional)
        author: Author of the change
        component: Component affected
        notes: Additional notes
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    category: ChangeCategory = ChangeCategory.IMPROVEMENT
    description: str = ""
    issue_ref: str = ""
    author: str = ""
    component: str = ""
    notes: str = ""


@dataclass
class ReleaseNotes:
    """Complete release notes for a version.

    Attributes:
        id: Unique notes ID
        version: Version number
        title: Release title
        date: Release date
        summary: High-level summary
        changes: List of changes
        known_issues: Known issues in this release
        upgrade_notes: Upgrade instructions
        contributors: List of contributors
        generated_at: When the notes were generated
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    version: str = "0.1.0"
    title: str = ""
    date: str = ""
    summary: str = ""
    changes: List[ChangeEntry] = field(default_factory=list)
    known_issues: List[str] = field(default_factory=list)
    upgrade_notes: List[str] = field(default_factory=list)
    contributors: List[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


_CHANGE_ICONS = {
    ChangeCategory.FEATURE: ":sparkles:",
    ChangeCategory.BUG_FIX: ":bug:",
    ChangeCategory.IMPROVEMENT: ":zap:",
    ChangeCategory.BREAKING_CHANGE: ":warning:",
    ChangeCategory.SECURITY: ":lock:",
    ChangeCategory.DOCUMENTATION: ":books:",
    ChangeCategory.DEPRECATION: ":hourglass:",
    ChangeCategory.PERFORMANCE: ":rocket:",
    ChangeCategory.REFACTOR: ":recycle:",
    ChangeCategory.TESTING: ":test_tube:",
    ChangeCategory.BUILD: ":hammer:",
    ChangeCategory.OTHER: ":memo:",
}

_CHANGE_LABELS = {
    ChangeCategory.FEATURE: "Features",
    ChangeCategory.BUG_FIX: "Bug Fixes",
    ChangeCategory.IMPROVEMENT: "Improvements",
    ChangeCategory.BREAKING_CHANGE: "Breaking Changes",
    ChangeCategory.SECURITY: "Security",
    ChangeCategory.DOCUMENTATION: "Documentation",
    ChangeCategory.DEPRECATION: "Deprecations",
    ChangeCategory.PERFORMANCE: "Performance",
    ChangeCategory.REFACTOR: "Refactoring",
    ChangeCategory.TESTING: "Testing",
    ChangeCategory.BUILD: "Build System",
    ChangeCategory.OTHER: "Other Changes",
}


class ReleaseNotesGenerator:
    """Generates structured release notes from changes.

    Organizes changes by category and produces formatted output
    suitable for CHANGELOG.md, GitHub releases, or other formats.

    Usage:
        gen = ReleaseNotesGenerator(event_bus)
        notes = gen.generate_for_version("1.0.0", changes)
        markdown = gen.to_markdown(notes)
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._notes_list: Dict[str, ReleaseNotes] = {}

    def create_notes(self, version: str, title: str = "",
                     summary: str = "",
                     changes: List[ChangeEntry] = None) -> ReleaseNotes:
        """Create release notes for a version.

        Args:
            version: Version number
            title: Release title
            summary: High-level summary
            changes: List of changes

        Returns:
            ReleaseNotes object
        """
        import datetime

        notes = ReleaseNotes(
            version=version,
            title=title or f"Version {version}",
            date=datetime.date.today().isoformat(),
            summary=summary,
            changes=changes or [],
        )

        self._notes_list[notes.id] = notes

        logger.info(
            "ReleaseNotesGenerator: created notes for v%s with %d changes",
            version, len(notes.changes),
        )

        if self._event_bus:
            self._event_bus.emit_async("engineering.release_notes_created", {
                "notes_id": notes.id,
                "version": version,
                "changes": len(notes.changes),
            })

        return notes

    def add_change(self, notes_id: str, description: str,
                   category: ChangeCategory = ChangeCategory.IMPROVEMENT,
                   component: str = "",
                   issue_ref: str = "") -> Optional[ChangeEntry]:
        """Add a change to existing release notes.

        Args:
            notes_id: Release notes ID
            description: Change description
            category: Change category
            component: Affected component
            issue_ref: Reference to issue/PR

        Returns:
            The created ChangeEntry, or None if notes not found
        """
        notes = self._notes_list.get(notes_id)
        if notes is None:
            return None

        entry = ChangeEntry(
            category=category,
            description=description,
            component=component,
            issue_ref=issue_ref,
        )
        notes.changes.append(entry)
        return entry

    def add_changelog_entry(self, version: str, description: str,
                            category: ChangeCategory = ChangeCategory.IMPROVEMENT,
                            issue_ref: str = "",
                            component: str = "") -> ChangeEntry:
        """Add a changelog entry, creating notes if needed.

        Automatically finds or creates release notes for the given version.

        Args:
            version: Version string
            description: Change description
            category: Change category
            issue_ref: Reference to issue/PR
            component: Affected component

        Returns:
            The created ChangeEntry
        """
        # Find existing notes for this version or create new ones
        for notes in self._notes_list.values():
            if notes.version == version:
                return self.add_change(
                    notes.id, description, category,
                    component=component, issue_ref=issue_ref,
                )

        # Create new notes
        notes = self.create_notes(version)
        return self.add_change(
            notes.id, description, category,
            component=component, issue_ref=issue_ref,
        )

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def to_markdown(self, notes: ReleaseNotes) -> str:
        """Format release notes as Markdown.

        Args:
            notes: ReleaseNotes object

        Returns:
            Markdown formatted release notes
        """
        parts = [
            f"# {notes.title}",
            f"",
            f"**Released**: {notes.date}",
            f"",
        ]

        if notes.summary:
            parts.extend([notes.summary, ""])

        if notes.upgrade_notes:
            parts.extend(["## Upgrade Notes", ""])
            for note in notes.upgrade_notes:
                parts.append(f"- {note}")
            parts.append("")

        # Group changes by category
        categorized: Dict[str, List[ChangeEntry]] = {}
        for change in notes.changes:
            label = _CHANGE_LABELS.get(change.category, "Other")
            if label not in categorized:
                categorized[label] = []
            categorized[label].append(change)

        # Output in standard order
        category_order = [
            "Breaking Changes", "Features", "Improvements", "Bug Fixes",
            "Security", "Performance", "Documentation", "Deprecations",
            "Refactoring", "Testing", "Build System", "Other Changes",
        ]

        for label in category_order:
            entries = categorized.get(label)
            if entries:
                icon = _CHANGE_ICONS.get(
                    next(c.category for c in notes.changes
                         if _CHANGE_LABELS.get(c.category) == label),
                    ":memo:",
                )
                parts.extend([f"## {icon} {label}", ""])
                for entry in entries:
                    prefix = f"- **{entry.component}**: " if entry.component else "- "
                    parts.append(f"{prefix}{entry.description}")
                    if entry.issue_ref:
                        parts[-1] += f" (#{entry.issue_ref})"
                parts.append("")

        if notes.known_issues:
            parts.extend(["## Known Issues", ""])
            for issue in notes.known_issues:
                parts.append(f"- {issue}")
            parts.append("")

        if notes.contributors:
            parts.extend(["## Contributors", ""])
            for contributor in notes.contributors:
                parts.append(f"- {contributor}")

        return "\n".join(parts)

    def to_json(self, notes: ReleaseNotes) -> Dict[str, Any]:
        """Format release notes as a JSON-serializable dict."""
        return {
            "version": notes.version,
            "title": notes.title,
            "date": notes.date,
            "summary": notes.summary,
            "changes": [
                {
                    "category": c.category.value,
                    "description": c.description,
                    "component": c.component,
                    "issue_ref": c.issue_ref,
                }
                for c in notes.changes
            ],
            "known_issues": notes.known_issues,
            "upgrade_notes": notes.upgrade_notes,
            "contributors": notes.contributors,
        }

    def get_notes(self, notes_id: str) -> Optional[ReleaseNotes]:
        """Get release notes by ID."""
        return self._notes_list.get(notes_id)

    def find_by_version(self, version: str) -> Optional[ReleaseNotes]:
        """Find release notes by version string."""
        for notes in self._notes_list.values():
            if notes.version == version:
                return notes
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get generator statistics."""
        total_changes = sum(len(n.changes) for n in self._notes_list.values())
        return {
            "total_releases": len(self._notes_list),
            "total_changes": total_changes,
            "versions": [n.version for n in self._notes_list.values()],
        }
