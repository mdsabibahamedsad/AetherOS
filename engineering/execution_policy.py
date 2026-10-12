"""
Execution Policy — configurable safety modes for the engineering platform.

Supports five modes:
  - READ_ONLY_ANALYSIS: Only read, never write
  - DRAFT_CHANGES: Generate patches/diffs but don't apply
  - HUMAN_APPROVAL: Require approval before file writes
  - AUTOMATIC_LOCAL: Execute automatically (where enabled)
  - CI_ORIENTED: For CI pipeline execution

Policies are explicit, auditable, and enforced at every mutation point.
"""

from __future__ import annotations

import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PolicyMode(enum.Enum):
    """Execution policy modes for the engineering platform.

    Each mode represents a different level of autonomy and safety.
    Higher modes allow more automation but require more trust.
    """
    READ_ONLY_ANALYSIS = "read_only_analysis"
    """Analyze only — never create or modify files. Ideal for audits."""
    DRAFT_CHANGES = "draft_changes"
    """Generate patches/diffs but do not apply them. Human reviews first."""
    HUMAN_APPROVAL = "human_approval"
    """Execute automatically but pause for human approval before file writes."""
    AUTOMATIC_LOCAL = "automatic_local"
    """Full automatic execution where enabled. May still gate destructive ops."""
    CI_ORIENTED = "ci_oriented"
    """CI-optimized: run tests, lint, typecheck, but gate deployments."""


class PolicyDecision(enum.Enum):
    """Result of a policy check."""
    ALLOWED = "allowed"
    DENIED = "denied"
    REQUIRES_APPROVAL = "requires_approval"
    DEFERRED = "deferred"


@dataclass
class PolicyCheck:
    """Record of a single policy enforcement check.

    Attributes:
        id: Unique check ID
        action: The action being checked (e.g. "write_file", "delete_file")
        target: The target of the action (e.g. file path, API endpoint)
        mode: The policy mode at time of check
        decision: The policy decision
        reason: Human-readable reason for the decision
        timestamp: When the check occurred
        approved_by: Who approved it (if applicable)
        context: Additional context about the check
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action: str = ""
    target: str = ""
    mode: PolicyMode = PolicyMode.READ_ONLY_ANALYSIS
    decision: PolicyDecision = PolicyDecision.DENIED
    reason: str = ""
    timestamp: float = field(default_factory=time.time)
    approved_by: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


class HumanApprovalRequired(Exception):
    """Raised when a policy check requires human approval.

    The caller should pause and present the pending action for approval.
    """
    def __init__(self, check: PolicyCheck, message: str = ""):
        self.check = check
        self.message = message or (
            f"Action '{check.action}' on '{check.target}' "
            f"requires human approval (mode: {check.mode.value})"
        )
        super().__init__(self.message)


class PolicyEnforcer:
    """Enforces execution policies across the engineering platform.

    Every mutation (file write, delete, rename, API call, deployment) must
    pass through this enforcer. It maintains an audit trail of all checks.

    Usage:
        enforcer = PolicyEnforcer(mode=PolicyMode.HUMAN_APPROVAL)
        check = enforcer.check("write_file", "src/main.py")
        if check.decision == PolicyDecision.DENIED:
            print(f"Cannot write: {check.reason}")
    """

    def __init__(self, mode: PolicyMode = PolicyMode.READ_ONLY_ANALYSIS):
        self._mode = mode
        self._audit_log: List[PolicyCheck] = []
        self._pending_approvals: Dict[str, PolicyCheck] = {}
        self._auto_approve_patterns: List[str] = []

    @property
    def mode(self) -> PolicyMode:
        """Current policy mode."""
        return self._mode

    def set_mode(self, mode: PolicyMode) -> None:
        """Change the policy mode at runtime.

        Logs the change for auditability.
        """
        old_mode = self._mode
        self._mode = mode
        logger.info("PolicyEnforcer: mode changed %s -> %s", old_mode.value, mode.value)

    def check(self, action: str, target: str,
              context: Dict[str, Any] = None) -> PolicyCheck:
        """Check whether an action is allowed under the current policy.

        Args:
            action: The action to check (e.g. "write_file", "delete_file")
            target: The target of the action (e.g. file path)
            context: Additional context for the check

        Returns:
            PolicyCheck with the decision and reason

        Raises:
            HumanApprovalRequired: If the action requires human approval
        """
        # Check auto-approve patterns first
        if self._matches_auto_approve(target):
            decision = PolicyDecision.ALLOWED
            reason = "Auto-approved by pattern match"
        else:
            decision, reason = self._evaluate(action, target, context or {})

        check = PolicyCheck(
            action=action,
            target=target,
            mode=self._mode,
            decision=decision,
            reason=reason,
            context=context or {},
        )

        self._audit_log.append(check)

        if decision == PolicyDecision.REQUIRES_APPROVAL:
            self._pending_approvals[check.id] = check
            raise HumanApprovalRequired(check)

        if decision == PolicyDecision.DENIED:
            logger.info("PolicyEnforcer: DENIED %s on %s: %s", action, target, reason)

        return check

    def _evaluate(self, action: str, target: str,
                  context: Dict[str, Any]) -> tuple[PolicyDecision, str]:
        """Evaluate an action against the current policy mode.

        Returns (decision, reason) tuple.
        """
        # Read vs Write classification
        is_read = action in (
            "read_file", "list_directory", "search_files", "analyze",
            "inspect", "query", "report",
        )
        is_write = action in (
            "write_file", "delete_file", "rename_file", "create_file",
            "modify_file", "apply_patch", "install", "deploy",
        )
        is_destructive = action in (
            "delete_file", "delete_directory", "format", "drop_database",
            "deploy_to_production",
        )

        if self._mode == PolicyMode.READ_ONLY_ANALYSIS:
            if is_read:
                return PolicyDecision.ALLOWED, "Read operations allowed in read-only mode"
            elif is_write or is_destructive:
                return PolicyDecision.DENIED, (
                    "Write operations denied in read-only mode"
                )
            else:
                return PolicyDecision.DENIED, (
                    f"Action '{action}' not allowed in read-only mode"
                )

        if self._mode == PolicyMode.DRAFT_CHANGES:
            if is_read:
                return PolicyDecision.ALLOWED, "Read operations allowed"
            elif is_write:
                return PolicyDecision.ALLOWED, (
                    "Write allowed in draft mode (changes tracked but not applied)"
                )
            elif is_destructive:
                return PolicyDecision.DENIED, (
                    "Destructive operations denied in draft mode"
                )
            return PolicyDecision.ALLOWED, "Action allowed in draft mode"

        if self._mode == PolicyMode.HUMAN_APPROVAL:
            if is_read:
                return PolicyDecision.ALLOWED, "Read operations always allowed"
            elif is_destructive:
                return PolicyDecision.REQUIRES_APPROVAL, (
                    "Destructive operation requires human approval"
                )
            elif is_write:
                return PolicyDecision.REQUIRES_APPROVAL, (
                    "Write operation requires human approval"
                )
            return PolicyDecision.ALLOWED, "Action allowed"

        if self._mode == PolicyMode.AUTOMATIC_LOCAL:
            if is_destructive:
                return PolicyDecision.REQUIRES_APPROVAL, (
                    "Destructive operations require human approval even in auto mode"
                )
            return PolicyDecision.ALLOWED, "Automatic execution allowed"

        if self._mode == PolicyMode.CI_ORIENTED:
            if action in ("deploy", "deploy_to_production", "publish", "release"):
                return PolicyDecision.DENIED, (
                    "Deploy/publish actions denied in CI mode (manual approval required)"
                )
            if is_destructive:
                return PolicyDecision.DENIED, (
                    "Destructive operations denied in CI mode"
                )
            return PolicyDecision.ALLOWED, "CI execution allowed"

        return PolicyDecision.DENIED, f"Unknown policy mode: {self._mode}"

    def _matches_auto_approve(self, target: str) -> bool:
        """Check if target matches any auto-approve pattern."""
        for pattern in self._auto_approve_patterns:
            if pattern in target:
                return True
        return False

    def add_auto_approve_pattern(self, pattern: str) -> None:
        """Add a glob-like pattern for auto-approval.

        Targets matching this pattern will bypass approval gates.
        """
        if pattern not in self._auto_approve_patterns:
            self._auto_approve_patterns.append(pattern)
            logger.debug("PolicyEnforcer: added auto-approve pattern: %s", pattern)

    # ------------------------------------------------------------------
    # Approval workflow
    # ------------------------------------------------------------------

    def approve(self, check_id: str, approved_by: str = "human") -> bool:
        """Approve a pending action.

        Args:
            check_id: The ID of the pending check
            approved_by: Who approved it

        Returns:
            True if approved, False if check not found
        """
        check = self._pending_approvals.pop(check_id, None)
        if check is None:
            logger.warning("PolicyEnforcer: no pending approval for %s", check_id)
            return False

        check.decision = PolicyDecision.ALLOWED
        check.approved_by = approved_by
        logger.info(
            "PolicyEnforcer: approved %s on %s by %s",
            check.action, check.target, approved_by,
        )
        return True

    def deny(self, check_id: str, denied_by: str = "human") -> bool:
        """Deny a pending action."""
        check = self._pending_approvals.pop(check_id, None)
        if check is None:
            return False

        check.decision = PolicyDecision.DENIED
        check.approved_by = denied_by
        logger.info(
            "PolicyEnforcer: denied %s on %s by %s",
            check.action, check.target, denied_by,
        )
        return True

    def pending_approvals(self) -> List[PolicyCheck]:
        """Get all actions currently pending human approval."""
        return list(self._pending_approvals.values())

    # ------------------------------------------------------------------
    # Auditing
    # ------------------------------------------------------------------

    def audit_log(self, limit: int = 100) -> List[PolicyCheck]:
        """Get the audit log of all policy checks, most recent first.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of PolicyCheck records, newest first
        """
        return list(reversed(self._audit_log[-limit:]))

    def audit_log_by_action(self, action: str) -> List[PolicyCheck]:
        """Filter audit log by action type."""
        return [c for c in reversed(self._audit_log) if c.action == action]

    def get_stats(self) -> Dict[str, Any]:
        """Get enforcement statistics."""
        total = len(self._audit_log)
        by_decision: Dict[str, int] = {}
        for check in self._audit_log:
            key = check.decision.value
            by_decision[key] = by_decision.get(key, 0) + 1

        return {
            "mode": self._mode.value,
            "total_checks": total,
            "by_decision": by_decision,
            "pending_approvals": len(self._pending_approvals),
            "auto_approve_patterns": len(self._auto_approve_patterns),
        }
