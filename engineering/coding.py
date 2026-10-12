"""
Implementation Coordinator — assigns and tracks engineering work.

Assigns work to specialized coding agents, tracks progress, manages
modified files, pending work, generated artifacts, and review status.
Supports resumable execution.
"""

from __future__ import annotations

import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ChangeType(enum.Enum):
    """Types of file changes."""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"
    COPY = "copy"


class AssignmentStatus(enum.Enum):
    """Status of a coding assignment."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REVIEWED = "reviewed"


@dataclass
class FileChange:
    """Record of a file change made during implementation.

    Attributes:
        id: Unique change ID
        file_path: Path to the file
        change_type: Type of change
        original_content: Content before change (for rollback)
        new_content: Content after change
        language: Programming language of the file
        lines_added: Number of lines added
        lines_removed: Number of lines removed
        checksum_before: SHA-256 of content before
        checksum_after: SHA-256 of content after
        timestamp: When the change was made
        assignment_id: Assignment that produced this change
        reviewed: Whether this change has been reviewed
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    file_path: str = ""
    change_type: ChangeType = ChangeType.MODIFY
    original_content: str = ""
    new_content: str = ""
    language: str = ""
    lines_added: int = 0
    lines_removed: int = 0
    checksum_before: str = ""
    checksum_after: str = ""
    timestamp: float = field(default_factory=time.time)
    assignment_id: str = ""
    reviewed: bool = False


@dataclass
class CodingAssignment:
    """An assignment to implement a specific task.

    Attributes:
        id: Unique assignment ID
        task_id: Engineering task ID
        plan_id: Implementation plan ID
        description: What to implement
        files_to_modify: Files that need changes
        files_created: Files that were created
        status: Assignment status
        assigned_to: Agent assigned to this work
        notes: Execution notes
        result: Result summary
        error: Error message if failed
        created_at: When assigned
        completed_at: When completed
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str = ""
    plan_id: str = ""
    description: str = ""
    files_to_modify: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    status: AssignmentStatus = AssignmentStatus.PENDING
    assigned_to: str = ""
    notes: str = ""
    result: str = ""
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class ImplementationCoordinator:
    """Coordinates implementation work across coding agents.

    Assigns tasks to agents, tracks file changes, manages pending work,
    and supports resumable execution with checkpointing.

    Usage:
        coordinator = ImplementationCoordinator(event_bus)
        assignment = coordinator.create_assignment(
            task_id="task-123",
            description="Implement user auth module",
        )
        coordinator.mark_completed(assignment.id, result="Implementation done")
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._assignments: Dict[str, CodingAssignment] = {}
        self._file_changes: Dict[str, FileChange] = {}

    def create_assignment(self, task_id: str, plan_id: str = "",
                          description: str = "",
                          files_to_modify: List[str] = None,
                          assigned_to: str = "") -> CodingAssignment:
        """Create a new coding assignment.

        Args:
            task_id: Engineering task ID
            plan_id: Implementation plan ID (optional)
            description: What to implement
            files_to_modify: Files that will need changes
            assigned_to: Agent to assign to

        Returns:
            The created CodingAssignment
        """
        assignment = CodingAssignment(
            task_id=task_id,
            plan_id=plan_id,
            description=description,
            files_to_modify=files_to_modify or [],
            assigned_to=assigned_to or "coding-agent",
        )

        self._assignments[assignment.id] = assignment

        logger.info(
            "ImplementationCoordinator: created assignment %s: %s",
            assignment.id[:8], description[:60],
        )

        if self._event_bus:
            self._event_bus.emit_async("engineering.assignment_created", {
                "assignment_id": assignment.id,
                "task_id": task_id,
                "description": description[:100],
                "assigned_to": assignment.assigned_to,
            })

        return assignment

    def mark_in_progress(self, assignment_id: str) -> bool:
        """Mark an assignment as in progress.

        Args:
            assignment_id: Assignment ID

        Returns:
            True if successful
        """
        assignment = self._assignments.get(assignment_id)
        if assignment is None:
            return False
        assignment.status = AssignmentStatus.IN_PROGRESS
        return True

    def mark_completed(self, assignment_id: str, result: str = "",
                       file_changes: List[FileChange] = None) -> bool:
        """Mark an assignment as completed.

        Args:
            assignment_id: Assignment ID
            result: Summary of what was accomplished
            file_changes: List of file changes made

        Returns:
            True if successful
        """
        assignment = self._assignments.get(assignment_id)
        if assignment is None:
            return False

        assignment.status = AssignmentStatus.COMPLETED
        assignment.result = result or "Implementation completed"
        assignment.completed_at = time.time()

        # Register file changes
        if file_changes:
            for change in file_changes:
                change.assignment_id = assignment_id
                self._file_changes[change.id] = change
                if (change.change_type == ChangeType.CREATE
                        and change.file_path not in assignment.files_created):
                    assignment.files_created.append(change.file_path)

        logger.info(
            "ImplementationCoordinator: assignment %s completed: %d changes",
            assignment_id[:8], len(file_changes or []),
        )

        if self._event_bus:
            self._event_bus.emit_async("engineering.assignment_completed", {
                "assignment_id": assignment_id,
                "task_id": assignment.task_id,
                "file_changes": len(file_changes or []),
            })

        return True

    def mark_failed(self, assignment_id: str, error: str) -> bool:
        """Mark an assignment as failed.

        Args:
            assignment_id: Assignment ID
            error: Error description

        Returns:
            True if successful
        """
        assignment = self._assignments.get(assignment_id)
        if assignment is None:
            return False

        assignment.status = AssignmentStatus.FAILED
        assignment.error = error
        assignment.completed_at = time.time()

        logger.error("ImplementationCoordinator: assignment %s failed: %s",
                     assignment_id[:8], error[:100])

        if self._event_bus:
            self._event_bus.emit_async("engineering.assignment_failed", {
                "assignment_id": assignment_id,
                "error": error,
            })

        return True

    def mark_reviewed(self, assignment_id: str) -> bool:
        """Mark an assignment's output as reviewed.

        Args:
            assignment_id: Assignment ID

        Returns:
            True if successful
        """
        assignment = self._assignments.get(assignment_id)
        if assignment is None:
            return False

        assignment.status = AssignmentStatus.REVIEWED

        # Also mark file changes as reviewed
        for change in self._file_changes.values():
            if change.assignment_id == assignment_id:
                change.reviewed = True

        return True

    # ------------------------------------------------------------------
    # File change tracking
    # ------------------------------------------------------------------

    def register_file_change(self, file_path: str,
                             change_type: ChangeType,
                             original_content: str = "",
                             new_content: str = "",
                             assignment_id: str = "") -> FileChange:
        """Register a file change.

        Args:
            file_path: Path to the changed file
            change_type: Type of change
            original_content: Content before change
            new_content: Content after change
            assignment_id: Associated assignment ID

        Returns:
            The registered FileChange
        """
        import hashlib

        change = FileChange(
            file_path=file_path,
            change_type=change_type,
            original_content=original_content,
            new_content=new_content,
            language=self._detect_language(file_path),
            lines_added=len(new_content.splitlines()) - len(original_content.splitlines())
            if original_content and new_content else 0,
            lines_removed=0,  # Approximate
            checksum_before=hashlib.sha256(original_content.encode()).hexdigest()[:16]
            if original_content else "",
            checksum_after=hashlib.sha256(new_content.encode()).hexdigest()[:16]
            if new_content else "",
            assignment_id=assignment_id,
        )

        if change.lines_added < 0:
            change.lines_removed = abs(change.lines_added)
            change.lines_added = 0

        self._file_changes[change.id] = change

        if self._event_bus:
            self._event_bus.emit_async("engineering.file_changed", {
                "file_path": file_path,
                "change_type": change_type.value,
                "assignment_id": assignment_id,
            })

        return change

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        language_map = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "tsx": "TypeScript (React)",
            "jsx": "JavaScript (React)",
            "go": "Go",
            "rs": "Rust",
            "java": "Java",
            "rb": "Ruby",
            "c": "C",
            "cpp": "C++",
            "cs": "C#",
            "swift": "Swift",
            "kt": "Kotlin",
            "sh": "Shell",
            "yaml": "YAML",
            "yml": "YAML",
            "json": "JSON",
            "md": "Markdown",
            "html": "HTML",
            "css": "CSS",
            "toml": "TOML",
        }
        return language_map.get(ext, "Unknown")

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_assignment(self, assignment_id: str) -> Optional[CodingAssignment]:
        """Get an assignment by ID."""
        return self._assignments.get(assignment_id)

    def get_assignments_by_task(self, task_id: str) -> List[CodingAssignment]:
        """Get all assignments for a given task."""
        return [
            a for a in self._assignments.values()
            if a.task_id == task_id
        ]

    def get_assignments_by_plan(self, plan_id: str) -> List[CodingAssignment]:
        """Get all assignments for a given plan."""
        return [
            a for a in self._assignments.values()
            if a.plan_id == plan_id
        ]

    def get_file_changes(self, assignment_id: str = None,
                         file_path: str = None) -> List[FileChange]:
        """Get file changes, optionally filtered.

        Args:
            assignment_id: Filter by assignment
            file_path: Filter by file path

        Returns:
            List of matching FileChange objects
        """
        results = list(self._file_changes.values())

        if assignment_id:
            results = [c for c in results if c.assignment_id == assignment_id]
        if file_path:
            results = [c for c in results if c.file_path == file_path]

        results.sort(key=lambda c: c.timestamp, reverse=True)
        return results

    def get_pending_assignments(self) -> List[CodingAssignment]:
        """Get all pending assignments."""
        return [
            a for a in self._assignments.values()
            if a.status in (AssignmentStatus.PENDING, AssignmentStatus.ASSIGNED)
        ]

    def get_active_assignments(self) -> List[CodingAssignment]:
        """Get all in-progress assignments."""
        return [
            a for a in self._assignments.values()
            if a.status == AssignmentStatus.IN_PROGRESS
        ]

    def get_unreviewed_changes(self) -> List[FileChange]:
        """Get file changes that haven't been reviewed yet."""
        return [
            c for c in self._file_changes.values()
            if not c.reviewed
        ]

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def rollback_changes(self, assignment_id: str) -> List[str]:
        """Rollback all file changes for an assignment.

        Args:
            assignment_id: Assignment ID to rollback

        Returns:
            List of files that were rolled back
        """
        changes = self.get_file_changes(assignment_id=assignment_id)
        rolled_back = []

        for change in changes:
            if change.original_content:
                try:
                    from pathlib import Path
                    Path(change.file_path).write_text(
                        change.original_content, encoding="utf-8",
                    )
                    rolled_back.append(change.file_path)
                except Exception as exc:
                    logger.error("ImplementationCoordinator: rollback failed for %s: %s",
                                 change.file_path, exc)

        # Mark assignment as rolled back
        assignment = self._assignments.get(assignment_id)
        if assignment:
            assignment.status = AssignmentStatus.CANCELLED
            assignment.notes = "Changes rolled back"

        if rolled_back:
            logger.info("ImplementationCoordinator: rolled back %d files for %s",
                        len(rolled_back), assignment_id[:8])

        return rolled_back

    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        return {
            "total_assignments": len(self._assignments),
            "total_file_changes": len(self._file_changes),
            "by_status": {
                status.value: sum(
                    1 for a in self._assignments.values()
                    if a.status == status
                )
                for status in AssignmentStatus
            },
            "pending_review": len(self.get_unreviewed_changes()),
        }
