"""
Approval Workflows
==================

Configurable approval workflows for engineering changes, workflow execution,
plugin installation, policy exceptions, and deployment actions.
Supports multi-step approval chains with escalation.
"""

from __future__ import annotations

import enum
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ApprovalStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"
    EXPIRED = "expired"


@dataclass
class ApprovalStep:
    """A single step in an approval chain."""
    id: str = ""
    name: str = ""
    approver_type: str = "user"  # user, role, group
    approver_id: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    comment: str = ""
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None
    order: int = 0
    timeout_minutes: int = 1440  # 24h default
    escalation_user: Optional[str] = None

    def approve(self, user_id: str, comment: str = "") -> None:
        self.status = ApprovalStatus.APPROVED
        self.decided_at = datetime.utcnow()
        self.decided_by = user_id
        self.comment = comment

    def reject(self, user_id: str, comment: str = "") -> None:
        self.status = ApprovalStatus.REJECTED
        self.decided_at = datetime.utcnow()
        self.decided_by = user_id
        self.comment = comment

    def escalate(self) -> None:
        self.status = ApprovalStatus.ESCALATED

    def is_pending(self) -> bool:
        return self.status == ApprovalStatus.PENDING

    def is_expired(self, reference_time: Optional[datetime] = None) -> bool:
        if self.status == ApprovalStatus.PENDING and self.timeout_minutes > 0:
            from datetime import timedelta
            # If the step has been assigned (decided_at set), check against that
            # Otherwise check against the request's creation time (passed in)
            ref = self.decided_at or reference_time or datetime.utcnow()
            return datetime.utcnow() > ref + timedelta(minutes=self.timeout_minutes)
        return False


@dataclass
class ApprovalRequest:
    """A request for approval through a multi-step workflow."""
    title: str
    description: str = ""
    id: str = field(default_factory=lambda: f"apr_{uuid.uuid4().hex[:12]}")
    request_type: str = "general"  # general, plugin_install, policy_exception, deployment, workflow
    status: ApprovalStatus = ApprovalStatus.PENDING
    steps: List[ApprovalStep] = field(default_factory=list)
    requested_by: str = ""
    requested_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    resource: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    org_id: str = ""

    @property
    def current_step(self) -> Optional[ApprovalStep]:
        """Get the current pending step, if any."""
        for step in self.steps:
            if step.is_pending():
                return step
        return None

    @property
    def all_approved(self) -> bool:
        """Check if all steps are approved."""
        if not self.steps:
            return False
        return all(s.status == ApprovalStatus.APPROVED for s in self.steps)

    @property
    def is_rejected(self) -> bool:
        return any(s.status == ApprovalStatus.REJECTED for s in self.steps)

    def submit(self, user_id: str) -> None:
        self.requested_by = user_id
        self.status = ApprovalStatus.PENDING
        self.updated_at = datetime.utcnow()

    def cancel(self) -> None:
        self.status = ApprovalStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "request_type": self.request_type,
            "status": self.status.value,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at.isoformat(),
            "steps": [
                {
                    "id": s.id, "name": s.name,
                    "status": s.status.value,
                    "approver": s.approver_id,
                    "order": s.order,
                }
                for s in self.steps
            ],
        }


class ApprovalWorkflow:
    """A template for approval workflows — defines the required approval chain."""

    def __init__(
        self,
        name: str,
        description: str = "",
        steps: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.name = name
        self.description = description
        self._step_definitions = steps or []

    def create_request(
        self,
        title: str,
        description: str = "",
        request_type: str = "general",
        resource: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """Create a new approval request from this workflow template."""
        request = ApprovalRequest(
            title=title,
            description=description,
            request_type=request_type,
            resource=resource,
            details=details or {},
        )
        for i, step_def in enumerate(self._step_definitions):
            step = ApprovalStep(
                id=f"step_{uuid.uuid4().hex[:8]}",
                name=step_def.get("name", f"Step {i + 1}"),
                approver_type=step_def.get("approver_type", "user"),
                approver_id=step_def.get("approver_id", ""),
                order=step_def.get("order", i),
                timeout_minutes=step_def.get("timeout_minutes", 1440),
                escalation_user=step_def.get("escalation_user"),
            )
            request.steps.append(step)
        return request


class ApprovalManager:
    """Manages approval requests and workflows."""

    def __init__(self) -> None:
        self._requests: Dict[str, ApprovalRequest] = {}
        self._workflows: Dict[str, ApprovalWorkflow] = {}

    def register_workflow(self, workflow: ApprovalWorkflow) -> None:
        self._workflows[workflow.name] = workflow

    def get_workflow(self, name: str) -> Optional[ApprovalWorkflow]:
        return self._workflows.get(name)

    def submit_request(self, request: ApprovalRequest) -> ApprovalRequest:
        self._requests[request.id] = request
        logger.info("Approval request submitted: %s (%s)", request.id, request.title)
        return request

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def approve_step(self, request_id: str, step_id: str, user_id: str, comment: str = "") -> bool:
        """Approve a specific step in an approval request."""
        request = self._requests.get(request_id)
        if not request:
            return False
        for step in request.steps:
            if step.id == step_id and step.is_pending():
                step.approve(user_id, comment)
                request.updated_at = datetime.utcnow()
                if request.all_approved:
                    request.status = ApprovalStatus.APPROVED
                return True
        return False

    def reject_step(self, request_id: str, step_id: str, user_id: str, comment: str = "") -> bool:
        """Reject a specific step in an approval request."""
        request = self._requests.get(request_id)
        if not request:
            return False
        for step in request.steps:
            if step.id == step_id and step.is_pending():
                step.reject(user_id, comment)
                request.status = ApprovalStatus.REJECTED
                request.updated_at = datetime.utcnow()
                return True
        return False

    def list_requests(
        self,
        status: Optional[ApprovalStatus] = None,
        request_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[ApprovalRequest]:
        results = list(self._requests.values())
        if status:
            results = [r for r in results if r.status == status]
        if request_type:
            results = [r for r in results if r.request_type == request_type]
        results.sort(key=lambda r: r.requested_at, reverse=True)
        return results[:limit]

    def list_pending_for_user(self, user_id: str) -> List[ApprovalRequest]:
        """List approval requests pending a specific user's approval."""
        pending = []
        for request in self._requests.values():
            if request.status != ApprovalStatus.PENDING:
                continue
            for step in request.steps:
                if step.is_pending() and step.approver_id == user_id:
                    pending.append(request)
                    break
        return pending
