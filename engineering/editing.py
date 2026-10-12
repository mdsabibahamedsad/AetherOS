"""
Code Editor — handles file modifications with safety and policy enforcement.

Provides safe file editing operations that integrate with the execution
policy enforcer for approval gates and audit trails.
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
from engineering.execution_policy import (
    PolicyEnforcer,
    PolicyMode,
    PolicyDecision,
    HumanApprovalRequired,
)

logger = logging.getLogger(__name__)


class SafetyCheck(enum.Enum):
    """Safety check results."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    REQUIRES_REVIEW = "requires_review"


@dataclass
class EditOperation:
    """A single edit operation on a file.

    Attributes:
        id: Unique operation ID
        file_path: Path to the file to edit
        operation: Operation type (create, modify, delete, rename)
        old_content: Current file content (for modify/delete)
        new_content: New file content (for create/modify)
        new_path: New path (for rename/copy)
        language: Programming language of the file
        description: Description of what this edit does
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    file_path: str = ""
    operation: str = "modify"  # create, modify, delete, rename
    old_content: str = ""
    new_content: str = ""
    new_path: str = ""
    language: str = ""
    description: str = ""


@dataclass
class EditPlan:
    """A plan for multiple edit operations.

    Attributes:
        id: Unique edit plan ID
        description: High-level description of the planned changes
        operations: List of edit operations
        created_at: When the plan was created
        is_applied: Whether the plan has been applied
        applied_at: When the plan was applied
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    operations: List[EditOperation] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    is_applied: bool = False
    applied_at: Optional[float] = None


@dataclass
class EditResult:
    """Result of applying an edit operation.

    Attributes:
        operation_id: ID of the operation
        success: Whether the operation succeeded
        error: Error message if failed
        safety_check: Safety check result
        lines_changed: Number of lines changed
    """
    operation_id: str = ""
    success: bool = True
    error: str = ""
    safety_check: SafetyCheck = SafetyCheck.PASSED
    lines_changed: int = 0


class CodeEditor:
    """Handles file modifications with safety and policy enforcement.

    Provides safe file editing with:
    - Policy enforcement (read-only, draft, approval gates)
    - Safety checks (file size limits, binary detection)
    - Backup and rollback support
    - Operation audit trail

    Usage:
        editor = CodeEditor(policy_enforcer)
        plan = editor.create_edit_plan("Add user authentication")
        plan.operations.append(EditOperation(
            file_path="src/auth.py",
            operation="create",
            new_content="...",
        ))
        results = editor.apply_plan(plan)
    """

    # Maximum file size (bytes) for safe editing
    MAX_FILE_SIZE = 1024 * 1024  # 1MB

    # Binary file extensions that should not be edited
    BINARY_EXTENSIONS = {
        ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe",
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".zip", ".tar", ".gz", ".bz2", ".7z",
        ".mp3", ".mp4", ".avi", ".mov", ".wav",
        ".bin", ".dat", ".db", ".sqlite",
    }

    def __init__(self, policy_enforcer: Optional[PolicyEnforcer] = None,
                 event_bus: Optional[EventBus] = None,
                 working_dir: Optional[str] = None):
        self._policy = policy_enforcer or PolicyEnforcer()
        self._event_bus = event_bus
        self._working_dir = Path(working_dir).resolve() if working_dir else None
        self._edit_plans: Dict[str, EditPlan] = {}
        self._backup_dir: Optional[Path] = None

    def set_working_dir(self, path: str) -> None:
        """Set the working directory for file operations."""
        self._working_dir = Path(path).resolve()

    def set_backup_dir(self, path: str) -> None:
        """Set the directory for backups."""
        self._backup_dir = Path(path).resolve()
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Edit plans
    # ------------------------------------------------------------------

    def create_edit_plan(self, description: str) -> EditPlan:
        """Create a new edit plan.

        Args:
            description: High-level description of the planned changes

        Returns:
            An empty EditPlan ready for operations
        """
        plan = EditPlan(description=description)
        self._edit_plans[plan.id] = plan
        logger.debug("CodeEditor: created edit plan %s: %s",
                     plan.id[:8], description[:60])
        return plan

    def add_operation(self, plan_id: str, file_path: str,
                      operation: str = "modify",
                      new_content: str = "",
                      new_path: str = "",
                      description: str = "") -> Optional[EditOperation]:
        """Add an edit operation to a plan.

        Args:
            plan_id: Edit plan ID
            file_path: Target file path
            operation: Operation type (create, modify, delete, rename)
            new_content: New content (for create/modify)
            new_path: New path (for rename)
            description: Description of this operation

        Returns:
            The created EditOperation, or None if plan not found
        """
        plan = self._edit_plans.get(plan_id)
        if plan is None:
            return None

        # Resolve path
        resolved_path = self._resolve_path(file_path)

        # Read existing content for modify/delete
        old_content = ""
        current_path = Path(resolved_path)
        if current_path.exists():
            try:
                old_content = current_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

        edit_op = EditOperation(
            file_path=str(resolved_path),
            operation=operation,
            old_content=old_content,
            new_content=new_content,
            new_path=new_path,
            language=self._detect_language(resolved_path),
            description=description,
        )

        plan.operations.append(edit_op)
        logger.debug("CodeEditor: added %s operation on %s", operation, resolved_path)
        return edit_op

    # ------------------------------------------------------------------
    # Plan execution
    # ------------------------------------------------------------------

    def apply_plan(self, plan: EditPlan,
                   mode: Optional[PolicyMode] = None) -> List[EditResult]:
        """Apply an edit plan, with policy enforcement.

        Args:
            plan: The edit plan to apply
            mode: Override policy mode (uses current if not specified)

        Returns:
            List of EditResult for each operation

        Raises:
            HumanApprovalRequired: If policy requires approval and it's not granted
        """
        results = []

        # Switch policy mode if specified
        if mode:
            old_mode = self._policy.mode
            self._policy.set_mode(mode)
            try:
                results = self._execute_plan(plan)
            finally:
                self._policy.set_mode(old_mode)
        else:
            results = self._execute_plan(plan)

        # Mark plan as applied if all succeeded
        if all(r.success for r in results):
            plan.is_applied = True
            plan.applied_at = time.time()

            if self._event_bus:
                self._event_bus.emit_async("engineering.edits_applied", {
                    "plan_id": plan.id,
                    "operations": len(plan.operations),
                    "success_count": sum(1 for r in results if r.success),
                })

        return results

    def _execute_plan(self, plan: EditPlan) -> List[EditResult]:
        """Execute all operations in a plan, checking policy for each."""
        results = []

        for operation in plan.operations:
            result = self._execute_operation(operation)
            results.append(result)

            # If any operation fails, stop the plan
            if not result.success:
                logger.warning(
                    "CodeEditor: plan %s stopped at operation %s: %s",
                    plan.id[:8], operation.id[:8], result.error,
                )
                break

        return results

    def _execute_operation(self, operation: EditOperation) -> EditResult:
        """Execute a single edit operation with policy enforcement."""
        action_map = {
            "create": "write_file",
            "modify": "write_file",
            "delete": "delete_file",
            "rename": "rename_file",
        }

        action = action_map.get(operation.operation, "write_file")
        target = operation.file_path

        # Safety check
        safety = self._perform_safety_check(operation)
        if safety == SafetyCheck.FAILED:
            return EditResult(
                operation_id=operation.id,
                success=False,
                error=f"Safety check failed for {operation.file_path}",
                safety_check=safety,
            )

        # Policy check
        try:
            check = self._policy.check(action, target, {
                "operation": operation.operation,
                "file_path": operation.file_path,
                "description": operation.description,
            })
        except HumanApprovalRequired as ha:
            return EditResult(
                operation_id=operation.id,
                success=False,
                error=f"Requires human approval: {ha.message}",
                safety_check=SafetyCheck.REQUIRES_REVIEW,
            )

        if check.decision == PolicyDecision.DENIED:
            return EditResult(
                operation_id=operation.id,
                success=False,
                error=f"Policy denied: {check.reason}",
                safety_check=SafetyCheck.FAILED,
            )

        # Execute the operation
        try:
            return self._perform_operation(operation, safety)
        except Exception as exc:
            return EditResult(
                operation_id=operation.id,
                success=False,
                error=str(exc),
            )

    def _perform_safety_check(self, operation: EditOperation) -> SafetyCheck:
        """Perform safety checks on an operation."""
        file_path = Path(operation.file_path)

        # Check for binary files
        ext = file_path.suffix.lower()
        if ext in self.BINARY_EXTENSIONS:
            return SafetyCheck.FAILED

        # Check file size for existing files
        if file_path.exists():
            try:
                size = file_path.stat().st_size
                if size > self.MAX_FILE_SIZE:
                    logger.warning("CodeEditor: file too large for editing: %s (%d bytes)",
                                   operation.file_path, size)
                    return SafetyCheck.FAILED
            except OSError:
                pass

        # Check new content size
        if len(operation.new_content) > self.MAX_FILE_SIZE:
            return SafetyCheck.FAILED

        return SafetyCheck.PASSED

    def _perform_operation(self, operation: EditOperation,
                           safety: SafetyCheck) -> EditResult:
        """Perform the actual file operation."""
        file_path = Path(operation.file_path)

        if operation.operation == "create":
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create backup of existing file if it exists
            if file_path.exists():
                self._backup_file(file_path)

            file_path.write_text(operation.new_content, encoding="utf-8")
            lines = len(operation.new_content.splitlines())
            logger.info("CodeEditor: created %s (%d lines)", operation.file_path, lines)

        elif operation.operation == "modify":
            if not file_path.exists():
                # Create if doesn't exist
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(operation.new_content, encoding="utf-8")
                lines = len(operation.new_content.splitlines())
            else:
                self._backup_file(file_path)
                file_path.write_text(operation.new_content, encoding="utf-8")
                lines = len(operation.new_content.splitlines())

            logger.info("CodeEditor: modified %s (%d lines)", operation.file_path, lines)

        elif operation.operation == "delete":
            if file_path.exists():
                self._backup_file(file_path)
                file_path.unlink()
                logger.info("CodeEditor: deleted %s", operation.file_path)

        elif operation.operation == "rename":
            if file_path.exists():
                new_path = Path(operation.new_path)
                new_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.rename(new_path)
                logger.info("CodeEditor: renamed %s -> %s",
                            operation.file_path, operation.new_path)

        return EditResult(
            operation_id=operation.id,
            success=True,
            safety_check=safety,
        )

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    def _backup_file(self, file_path: Path) -> Optional[Path]:
        """Create a backup of a file before modifying it.

        Args:
            file_path: Path to the file to backup

        Returns:
            Path to the backup file, or None if backup failed
        """
        if not file_path.exists() or not self._backup_dir:
            return None

        try:
            backup_name = f"{file_path.name}.{uuid.uuid4().hex[:8]}.bak"
            backup_path = self._backup_dir / backup_name
            backup_path.write_bytes(file_path.read_bytes())
            logger.debug("CodeEditor: backed up %s -> %s",
                         file_path, backup_path)
            return backup_path
        except Exception as exc:
            logger.warning("CodeEditor: backup failed for %s: %s", file_path, exc)
            return None

    def list_backups(self) -> List[Path]:
        """List all backup files."""
        if not self._backup_dir or not self._backup_dir.exists():
            return []
        return sorted(self._backup_dir.iterdir(), key=os.path.getmtime, reverse=True)

    # ------------------------------------------------------------------
    # Diff generation
    # ------------------------------------------------------------------

    def generate_diff(self, plan: EditPlan) -> str:
        """Generate a unified diff for all operations in a plan.

        Args:
            plan: The edit plan

        Returns:
            A string containing the unified diff
        """
        lines = [
            f"# Edit Plan: {plan.description}",
            f"# Operations: {len(plan.operations)}",
            f"# Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(plan.created_at))}",
            f"",
        ]

        for op in plan.operations:
            lines.append(f"## {op.operation.upper()}: {op.file_path}")
            lines.append(f"")

            if op.operation in ("modify",):
                # Generate simple diff
                old_lines = op.old_content.splitlines(True)
                new_lines = op.new_content.splitlines(True)
                lines.append(f"--- a/{op.file_path}")
                lines.append(f"+++ b/{op.file_path}")

                import difflib
                diff = list(difflib.unified_diff(
                    old_lines, new_lines,
                    fromfile=f"a/{op.file_path}",
                    tofile=f"b/{op.file_path}",
                    lineterm="",
                ))
                lines.extend(diff[2:] if len(diff) > 2 else diff)
            elif op.operation == "create":
                lines.append(f"--- /dev/null")
                lines.append(f"+++ b/{op.file_path}")
                for i, line in enumerate(op.new_content.splitlines(), 1):
                    lines.append(f"+{line}")
            elif op.operation == "delete":
                lines.append(f"--- a/{op.file_path}")
                lines.append(f"+++ /dev/null")
                for i, line in enumerate(op.old_content.splitlines(), 1):
                    lines.append(f"-{line}")

            lines.append(f"")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, file_path: str) -> str:
        """Resolve a file path relative to the working directory."""
        if self._working_dir and not Path(file_path).is_absolute():
            return str(self._working_dir / file_path)
        return str(Path(file_path).resolve())

    @staticmethod
    def _detect_language(file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        language_map = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "go": "Go",
            "rs": "Rust",
            "java": "Java",
        }
        return language_map.get(ext, "Unknown")

    def get_plan(self, plan_id: str) -> Optional[EditPlan]:
        """Get an edit plan by ID."""
        return self._edit_plans.get(plan_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get editor statistics."""
        return {
            "total_plans": len(self._edit_plans),
            "applied_plans": sum(1 for p in self._edit_plans.values() if p.is_applied),
            "total_operations": sum(len(p.operations) for p in self._edit_plans.values()),
            "policy_mode": self._policy.mode.value,
        }
