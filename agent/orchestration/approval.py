"""Approval System for AetherOS Orchestration Layer.

Implements Phases 51-55 of Master Prompt 11: human approval gates for high-risk actions
with expiration, scope, and dry-run support.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from agent.orchestration.types import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalAction,
    RiskLevel,
    TaskSpec,
    AgentIdentity,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Approval Types
# =============================================================================


class ApprovalScope(Enum):
    """Scope of an approval."""

    SINGLE_USE = "single_use"      # Valid for one action only
    TASK = "task"                  # Valid for all actions in a task
    SESSION = "session"            # Valid for the session
    ALWAYS = "always"              # Persistent (use with caution)


class ApprovalStatus(Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class ApprovalPolicy:
    """Policy defining when approval is required."""

    action: ApprovalAction
    risk_level: RiskLevel = RiskLevel.MEDIUM
    require_approval: bool = True
    default_scope: ApprovalScope = ApprovalScope.SINGLE_USE
    default_expiration_hours: float = 24.0
    allowed_responders: List[str] = field(default_factory=list)  # User IDs or roles
    auto_approve_conditions: Dict[str, Any] = field(default_factory=dict)
    auto_deny_conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalDecision:
    """Record of an approval decision."""

    request_id: str
    response: ApprovalResponse
    responded_by: str
    responded_at: float
    scope: ApprovalScope
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Approval Manager
# =============================================================================


class ApprovalManager:
    """Manages approval requests, responses, and policies."""

    def __init__(self):
        self._policies: Dict[ApprovalAction, ApprovalPolicy] = {}
        self._requests: Dict[str, ApprovalRequest] = {}
        self._decisions: Dict[str, List[ApprovalDecision]] = {}
        self._pending_callbacks: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Default policies
        self._register_default_policies()

    def _register_default_policies(self) -> None:
        """Register default approval policies."""
        defaults = [
            ApprovalPolicy(
                action=ApprovalAction.DESTRUCTIVE_ACTION,
                risk_level=RiskLevel.HIGH,
                default_scope=ApprovalScope.SINGLE_USE,
            ),
            ApprovalPolicy(
                action=ApprovalAction.SENSITIVE_DATA,
                risk_level=RiskLevel.HIGH,
                default_scope=ApprovalScope.TASK,
            ),
            ApprovalPolicy(
                action=ApprovalAction.EXTERNAL_COMMUNICATION,
                risk_level=RiskLevel.MEDIUM,
                default_scope=ApprovalScope.TASK,
            ),
            ApprovalPolicy(
                action=ApprovalAction.PAYMENT,
                risk_level=RiskLevel.CRITICAL,
                default_scope=ApprovalScope.SINGLE_USE,
            ),
            ApprovalPolicy(
                action=ApprovalAction.PERMISSION_ESCALATION,
                risk_level=RiskLevel.CRITICAL,
                default_scope=ApprovalScope.SINGLE_USE,
            ),
            ApprovalPolicy(
                action=ApprovalAction.CODE_EXECUTION,
                risk_level=RiskLevel.MEDIUM,
                default_scope=ApprovalScope.TASK,
            ),
            ApprovalPolicy(
                action=ApprovalAction.NETWORK_ACCESS,
                risk_level=RiskLevel.MEDIUM,
                default_scope=ApprovalScope.TASK,
            ),
            ApprovalPolicy(
                action=ApprovalAction.FILE_DELETE,
                risk_level=RiskLevel.HIGH,
                default_scope=ApprovalScope.SINGLE_USE,
            ),
            ApprovalPolicy(
                action=ApprovalAction.FILE_WRITE,
                risk_level=RiskLevel.LOW,
                default_scope=ApprovalScope.TASK,
            ),
        ]

        for policy in defaults:
            self._policies[policy.action] = policy

    async def start(self):
        """Start the approval manager background tasks."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """Stop the approval manager."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    def _cleanup_loop(self):
        """Periodic cleanup of expired requests."""
        while self._running:
            try:
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Approval cleanup error: {e}")
            time.sleep(300)  # Every 5 minutes

    def _cleanup_expired(self):
        """Remove expired requests."""
        now = time.time()
        expired = [
            req_id for req_id, req in self._requests.items()
            if req.expires_at and req.expires_at < now and req.status == "pending"
        ]
        for req_id in expired:
            req = self._requests[req_id]
            req.status = "expired"
            logger.info(f"Approval request expired: {req_id}")

    def register_policy(self, policy: ApprovalPolicy) -> None:
        """Register or update an approval policy."""
        self._policies[policy.action] = policy

    def get_policy(self, action: ApprovalAction) -> Optional[ApprovalPolicy]:
        """Get policy for an action."""
        return self._policies.get(action)

    def is_approval_required(self, action: ApprovalAction, context: Dict[str, Any] = None) -> bool:
        """Check if an action requires approval."""
        policy = self._policies.get(action)
        if not policy:
            return False

        # Check auto-approve conditions
        if context and policy.auto_approve_conditions:
            if self._match_conditions(policy.auto_approve_conditions, context):
                return False

        # Check auto-deny conditions
        if context and policy.auto_deny_conditions:
            if self._match_conditions(policy.auto_deny_conditions, context):
                return False

        return policy.require_approval

    def _match_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if context matches conditions."""
        for key, value in conditions.items():
            if key not in context:
                return False
            if isinstance(value, list):
                if context[key] not in value:
                    return False
            elif context[key] != value:
                return False
        return True

    async def request_approval(
        self,
        task_id: str,
        agent_id: str,
        action: ApprovalAction,
        description: str,
        details: Dict[str, Any] = None,
        risk_level: RiskLevel = None,
        scope: ApprovalScope = None,
        expiration_hours: float = None,
        allowed_responders: List[str] = None,
    ) -> ApprovalRequest:
        """Create an approval request."""
        policy = self._policies.get(action)

        request = ApprovalRequest(
            task_id=task_id,
            agent_id=agent_id,
            action=action,
            description=description,
            details=details or {},
            risk_level=risk_level or (policy.risk_level if policy else RiskLevel.MEDIUM),
            scope=scope.value if scope else (policy.default_scope.value if policy else ApprovalScope.SINGLE_USE.value),
        )

        # Set expiration
        exp_hours = expiration_hours or (policy.default_expiration_hours if policy else 24.0)
        request.expires_at = time.time() + (exp_hours * 3600)

        # Store request
        self._requests[request.request_id] = request

        # Notify waiting callbacks
        if request.request_id in self._pending_callbacks:
            future = self._pending_callbacks.pop(request.request_id)
            if not future.done():
                future.set_result(request)

        logger.info(f"Approval requested: {request.request_id} ({action.value})")
        return request

    async def wait_for_approval(
        self,
        request_id: str,
        timeout: float = 3600.0,
    ) -> Optional[ApprovalResponse]:
        """Wait for an approval decision."""
        request = self._requests.get(request_id)
        if not request:
            return None

        if request.status != "pending":
            return request.response

        # Create future to wait for response
        future = asyncio.get_event_loop().create_future()
        self._pending_callbacks[request_id] = future

        try:
            await asyncio.wait_for(future, timeout=timeout)
            request = self._requests.get(request_id)
            return request.response if request else None
        except asyncio.TimeoutError:
            # Mark as expired
            if request_id in self._requests:
                self._requests[request_id].status = "expired"
            return None
        finally:
            self._pending_callbacks.pop(request_id, None)

    def respond_to_approval(
        self,
        request_id: str,
        response: ApprovalResponse,
        responded_by: str,
        scope: ApprovalScope = None,
    ) -> bool:
        """Respond to an approval request."""
        request = self._requests.get(request_id)
        if not request:
            return False

        if request.status != "pending":
            logger.warning(f"Approval request {request_id} already resolved: {request.status}")
            return False

        # Update request
        request.status = "approved" if response in (ApprovalResponse.APPROVE_ONCE, ApprovalResponse.APPROVE_SESSION, ApprovalResponse.ALWAYS_ALLOW) else "denied"
        request.response = response
        request.responded_at = time.time()
        request.responded_by = responded_by
        request.scope = scope.value if scope else request.scope

        # Record decision
        decision = ApprovalDecision(
            request_id=request_id,
            response=response,
            responded_by=responded_by,
            responded_at=time.time(),
            scope=scope or ApprovalScope(request.scope),
            expires_at=self._calculate_expiration(response, request),
        )
        self._decisions.setdefault(request_id, []).append(decision)

        # Notify waiting callback
        if request_id in self._pending_callbacks:
            future = self._pending_callbacks.pop(request_id)
            if not future.done():
                future.set_result(request)

        logger.info(f"Approval {request_id}: {response.value} by {responded_by}")
        return True

    def _calculate_expiration(self, response: ApprovalResponse, request: ApprovalRequest) -> Optional[float]:
        """Calculate expiration based on response and scope."""
        if response == ApprovalResponse.ALWAYS_ALLOW:
            return None  # Never expires

        scope = ApprovalScope(request.scope)
        if scope == ApprovalScope.SINGLE_USE:
            return time.time() + 60  # Expire quickly after use
        elif scope == ApprovalScope.TASK:
            return request.expires_at
        elif scope == ApprovalScope.SESSION:
            return time.time() + 86400  # 24 hours

        return request.expires_at

    def check_approval(
        self,
        action: ApprovalAction,
        task_id: str = "",
        agent_id: str = "",
        context: Dict[str, Any] = None,
    ) -> tuple[bool, Optional[ApprovalResponse]]:
        """Check if an action is approved (for runtime checks)."""
        # Find matching approved request
        for req in self._requests.values():
            if req.status != "approved":
                continue
            if req.action != action:
                continue
            if task_id and req.task_id != task_id:
                continue
            if agent_id and req.agent_id != agent_id:
                continue

            # Check expiration
            if req.expires_at and req.expires_at < time.time():
                continue

            # Check scope
            scope = ApprovalScope(req.scope)
            if scope == ApprovalScope.SINGLE_USE:
                # Mark as used
                req.status = "used"
                return True, req.response
            elif scope in (ApprovalScope.TASK, ApprovalScope.SESSION, ApprovalScope.ALWAYS):
                return True, req.response

        return False, None

    def cancel_approval(self, request_id: str, reason: str = "") -> bool:
        """Cancel a pending approval request."""
        request = self._requests.get(request_id)
        if not request or request.status != "pending":
            return False

        request.status = "cancelled"
        request.metadata["cancellation_reason"] = reason
        logger.info(f"Approval cancelled: {request_id} ({reason})")
        return True

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        return self._requests.get(request_id)

    def get_pending_requests(
        self,
        task_id: str = "",
        agent_id: str = "",
        action: ApprovalAction = None,
    ) -> List[ApprovalRequest]:
        """Get pending approval requests with filters."""
        results = [r for r in self._requests.values() if r.status == "pending"]

        if task_id:
            results = [r for r in results if r.task_id == task_id]
        if agent_id:
            results = [r for r in results if r.agent_id == agent_id]
        if action:
            results = [r for r in results if r.action == action]

        return results

    def get_approval_history(
        self,
        task_id: str = "",
        limit: int = 100,
    ) -> List[ApprovalDecision]:
        """Get approval decision history."""
        all_decisions = []
        for decisions in self._decisions.values():
            all_decisions.extend(decisions)

        if task_id:
            # Filter by task
            task_requests = {r.request_id for r in self._requests.values() if r.task_id == task_id}
            all_decisions = [d for d in all_decisions if d.request_id in task_requests]

        all_decisions.sort(key=lambda d: d.responded_at, reverse=True)
        return all_decisions[:limit]


# =============================================================================
# Dry Run Support
# =============================================================================


class DryRunExecutor:
    """Executes actions in dry-run mode to preview effects."""

    def __init__(self, approval_manager: ApprovalManager):
        self._approval = approval_manager

    async def preview_action(
        self,
        action: ApprovalAction,
        task: TaskSpec,
        agent: AgentIdentity,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Preview what an action would do without executing it."""
        preview = {
            "action": action.value,
            "would_require_approval": self._approval.is_approval_required(action),
            "estimated_effects": [],
            "affected_resources": [],
            "risk_assessment": "unknown",
            "reversible": True,
        }

        # Action-specific previews
        if action == ApprovalAction.FILE_WRITE:
            path = parameters.get("path", "unknown")
            preview["estimated_effects"].append(f"Write file: {path}")
            preview["affected_resources"].append(f"file:{path}")
            preview["reversible"] = True  # Can restore from backup
            preview["risk_assessment"] = "low"

        elif action == ApprovalAction.FILE_DELETE:
            path = parameters.get("path", "unknown")
            preview["estimated_effects"].append(f"Delete file: {path}")
            preview["affected_resources"].append(f"file:{path}")
            preview["reversible"] = False  # May not be recoverable
            preview["risk_assessment"] = "high"

        elif action == ApprovalAction.CODE_EXECUTION:
            code = parameters.get("code", "unknown")
            preview["estimated_effects"].append(f"Execute code ({len(code)} chars)")
            preview["affected_resources"].append("process:execution")
            preview["reversible"] = False
            preview["risk_assessment"] = "medium"

        elif action == ApprovalAction.EXTERNAL_COMMUNICATION:
            target = parameters.get("target", "unknown")
            preview["estimated_effects"].append(f"Send message to: {target}")
            preview["affected_resources"].append(f"network:{target}")
            preview["reversible"] = False
            preview["risk_assessment"] = "medium"

        elif action == ApprovalAction.PAYMENT:
            amount = parameters.get("amount", "unknown")
            preview["estimated_effects"].append(f"Process payment: {amount}")
            preview["affected_resources"].append("financial:payment")
            preview["reversible"] = False
            preview["risk_assessment"] = "critical"

        elif action == ApprovalAction.PERMISSION_ESCALATION:
            preview["estimated_effects"].append("Escalate permissions")
            preview["affected_resources"].append("security:permissions")
            preview["reversible"] = True
            preview["risk_assessment"] = "critical"

        # Check if approval would be needed
        if preview["would_require_approval"]:
            policy = self._approval.get_policy(action)
            if policy:
                preview["approval_scope"] = policy.default_scope.value
                preview["approval_expiration_hours"] = policy.default_expiration_hours

        return preview

    async def dry_run_task(self, task: TaskSpec) -> Dict[str, Any]:
        """Perform a dry run of an entire task."""
        # This would simulate the task execution
        # For now, return a summary
        return {
            "task_id": task.task_id,
            "goal": task.goal,
            "estimated_steps": len(task.metadata.get("steps", [])),
            "required_approvals": self._estimate_required_approvals(task),
            "estimated_cost": task.budget.max_cost_usd,
            "estimated_time": task.budget.max_time_seconds,
            "risk_level": task.metadata.get("risk_level", "medium"),
        }

    def _estimate_required_approvals(self, task: TaskSpec) -> List[Dict[str, Any]]:
        """Estimate which approvals a task will need."""
        approvals = []

        # Check common patterns
        for cap in task.required_capabilities:
            if cap in ["file_write", "file_delete"]:
                approvals.append({
                    "action": ApprovalAction.FILE_WRITE.value if cap == "file_write" else ApprovalAction.FILE_DELETE.value,
                    "reason": f"Task requires {cap}",
                })
            elif cap == "code_execution":
                approvals.append({
                    "action": ApprovalAction.CODE_EXECUTION.value,
                    "reason": "Task executes code",
                })
            elif cap in ["web_search", "browser_navigate"]:
                approvals.append({
                    "action": ApprovalAction.NETWORK_ACCESS.value,
                    "reason": "Task accesses network",
                })

        return approvals


# =============================================================================
# Action Preview
# =============================================================================


class ActionPreview:
    """Generates user-facing previews of risky actions."""

    @staticmethod
    def format_preview(preview: Dict[str, Any]) -> str:
        """Format a preview for user display."""
        lines = [
            f"Action: {preview['action']}",
            f"Risk: {preview['risk_assessment'].upper()}",
            f"Reversible: {'Yes' if preview['reversible'] else 'No'}",
            "",
            "Estimated Effects:",
        ]

        for effect in preview["estimated_effects"]:
            lines.append(f"  • {effect}")

        if preview["affected_resources"]:
            lines.append("")
            lines.append("Affected Resources:")
            for resource in preview["affected_resources"]:
                lines.append(f"  • {resource}")

        if preview.get("would_require_approval"):
            lines.append("")
            lines.append("⚠️  This action requires approval")
            if "approval_scope" in preview:
                lines.append(f"   Scope: {preview['approval_scope']}")
            if "approval_expiration_hours" in preview:
                lines.append(f"   Expires in: {preview['approval_expiration_hours']} hours")

        return "\n".join(lines)

    @staticmethod
    def format_task_preview(preview: Dict[str, Any]) -> str:
        """Format a task dry-run preview."""
        lines = [
            f"Task: {preview['goal']}",
            f"ID: {preview['task_id']}",
            f"Estimated Cost: ${preview['estimated_cost']:.2f}",
            f"Estimated Time: {preview['estimated_time']:.0f}s",
            f"Risk Level: {preview['risk_level'].upper()}",
            "",
            "Required Approvals:",
        ]

        for appr in preview["required_approvals"]:
            lines.append(f"  • {appr['action']}: {appr['reason']}")

        return "\n".join(lines)


# =============================================================================
# Factory
# =============================================================================


def create_approval_manager() -> ApprovalManager:
    """Create an approval manager with default policies."""
    return ApprovalManager()


def create_dry_run_executor(approval_manager: ApprovalManager) -> DryRunExecutor:
    """Create a dry-run executor."""
    return DryRunExecutor(approval_manager)


__all__ = [
    "ApprovalScope",
    "ApprovalStatus",
    "ApprovalPolicy",
    "ApprovalDecision",
    "ApprovalManager",
    "DryRunExecutor",
    "ActionPreview",
    "create_approval_manager",
    "create_dry_run_executor",
]