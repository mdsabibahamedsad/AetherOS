"""
Human Approval Layer — gating system for high-risk actions.

Every action that could cause irreversible or impactful changes must
pass through the human approval gate before execution.

Actions requiring approval:
  - Delete files or directories
  - Push Git commits
  - Run arbitrary shell commands
  - Modify production configurations
  - Browser logins or form submissions
  - Install packages or plugins
  - Modify system settings
  - Send external communications
  - Access credentials or tokens

The approval layer never bypasses permissions and always logs
all approval requests and resolutions.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ApprovalAction(enum.Enum):
    DELETE_FILE = "delete_file"
    DELETE_DIRECTORY = "delete_directory"
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"
    SHELL_COMMAND = "shell_command"
    MODIFY_CONFIG = "modify_config"
    MODIFY_PRODUCTION = "modify_production"
    BROWSER_LOGIN = "browser_login"
    BROWSER_SUBMIT = "browser_submit"
    INSTALL_PACKAGE = "install_package"
    INSTALL_PLUGIN = "install_plugin"
    MODIFY_SYSTEM = "modify_system"
    SEND_MESSAGE = "send_message"
    ACCESS_CREDENTIALS = "access_credentials"
    ACCESS_TOKEN = "access_token"
    NETWORK_REQUEST = "network_request"
    START_AGENT = "start_agent"
    STOP_AGENT = "stop_agent"
    DELEGATE_TASK = "delegate_task"
    EXECUTE_CODE = "execute_code"


class ApprovalStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalPriority(enum.IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class ApprovalRequest:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    action: ApprovalAction = ApprovalAction.SHELL_COMMAND
    description: str = ""
    details: str = ""
    agent_id: str = ""
    plan_id: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    priority: ApprovalPriority = ApprovalPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    resolved_by: str = ""
    resolution_reason: str = ""
    timeout_seconds: float = 300.0
    escalation_level: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.status != ApprovalStatus.PENDING:
            return False
        return time.time() - self.created_at > self.timeout_seconds

    @property
    def description_summary(self) -> str:
        return self.description[:120]


@dataclass
class ApprovalPolicy:
    action: ApprovalAction = ApprovalAction.SHELL_COMMAND
    require_approval: bool = True
    auto_approve_patterns: List[str] = field(default_factory=list)
    auto_deny_patterns: List[str] = field(default_factory=list)
    timeout_seconds: float = 300.0
    escalation_delay: float = 60.0
    max_escalation_level: int = 3
    description: str = ""


class ApprovalLayer:
    """Human approval gating system for high-risk actions.

    All high-risk actions must pass through this layer. The layer never
    bypasses permissions and maintains a complete audit log.

    Usage:
        approvals = ApprovalLayer(event_bus)

        # Request approval for an action
        req = approvals.request_approval(
            action=ApprovalAction.DELETE_FILE,
            description="Delete config.yaml",
            agent_id="agent-1",
        )

        # Resolve from CLI or UI
        approvals.resolve_approval(req.id, granted=True, resolved_by="human-user")
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._requests: Dict[str, ApprovalRequest] = {}
        self._policies: Dict[ApprovalAction, ApprovalPolicy] = {}
        self._callbacks: Dict[str, List[Callable[[ApprovalRequest], None]]] = {}
        self._audit_log: List[Dict[str, Any]] = []
        self._auto_approve_contexts: Dict[str, Set[str]] = {}
        self._shutdown_flag = False

        self._init_default_policies()

    def _init_default_policies(self) -> None:
        """Set up default approval policies for high-risk actions."""
        always_require = [
            ApprovalAction.DELETE_FILE,
            ApprovalAction.DELETE_DIRECTORY,
            ApprovalAction.GIT_PUSH,
            ApprovalAction.SHELL_COMMAND,
            ApprovalAction.MODIFY_PRODUCTION,
            ApprovalAction.BROWSER_LOGIN,
            ApprovalAction.BROWSER_SUBMIT,
            ApprovalAction.INSTALL_PACKAGE,
            ApprovalAction.INSTALL_PLUGIN,
            ApprovalAction.MODIFY_SYSTEM,
            ApprovalAction.ACCESS_CREDENTIALS,
            ApprovalAction.ACCESS_TOKEN,
        ]
        for action in always_require:
            self._policies[action] = ApprovalPolicy(
                action=action,
                require_approval=True,
                timeout_seconds=300.0,
                description=f"Requires human approval: {action.value}",
            )

        conditional = {
            ApprovalAction.GIT_COMMIT: ApprovalPolicy(
                action=ApprovalAction.GIT_COMMIT,
                require_approval=True,
                auto_approve_patterns=["wip", "draft", "temp"],
                timeout_seconds=120.0,
                description="Git commits require approval unless auto-approved by pattern",
            ),
            ApprovalAction.DELEGATE_TASK: ApprovalPolicy(
                action=ApprovalAction.DELEGATE_TASK,
                require_approval=True,
                auto_approve_patterns=["read", "search", "list", "get", "check"],
                timeout_seconds=60.0,
                description="Task delegation requires approval unless read-only",
            ),
            ApprovalAction.NETWORK_REQUEST: ApprovalPolicy(
                action=ApprovalAction.NETWORK_REQUEST,
                require_approval=False,
                auto_deny_patterns=["10.", "172.16.", "192.168.", "127.", "localhost"],
                timeout_seconds=30.0,
                description="Network requests to private IPs are denied by default",
            ),
            ApprovalAction.SEND_MESSAGE: ApprovalPolicy(
                action=ApprovalAction.SEND_MESSAGE,
                require_approval=False,
                description="Message sending requires approval only in interactive mode",
            ),
        }
        self._policies.update(conditional)

    def set_policy(self, policy: ApprovalPolicy) -> None:
        with self._lock:
            self._policies[policy.action] = policy

    def get_policy(self, action: ApprovalAction) -> Optional[ApprovalPolicy]:
        with self._lock:
            return self._policies.get(action)

    # ------------------------------------------------------------------
    # Approval request flow
    # ------------------------------------------------------------------

    def request_approval(self, action: ApprovalAction,
                         description: str,
                         agent_id: str = "",
                         plan_id: str = "",
                         context: Dict[str, Any] = None,
                         details: str = "",
                         priority: ApprovalPriority = ApprovalPriority.NORMAL,
                         timeout_seconds: Optional[float] = None) -> ApprovalRequest:
        context = context or {}

        policy = self.get_policy(action)
        if policy and not policy.require_approval:
            if self._is_auto_denied(action, description, policy):
                return self._create_denied(action, description, agent_id, "Auto-denied by policy")
            return self._create_approved(action, description, agent_id, "No approval required by policy")

        if policy and self._is_auto_approved(action, description, policy):
            return self._create_approved(action, description, agent_id, "Auto-approved by policy pattern")

        timeout = timeout_seconds or (policy.timeout_seconds if policy else 300.0)
        req = ApprovalRequest(
            action=action,
            description=description,
            details=details or description,
            agent_id=agent_id,
            plan_id=plan_id,
            context=context,
            priority=priority,
            timeout_seconds=timeout,
        )

        with self._lock:
            self._requests[req.id] = req
            self._audit_log.append({
                "type": "request",
                "request_id": req.id,
                "action": action.value,
                "description": description,
                "agent_id": agent_id,
                "timestamp": time.time(),
            })

        self._emit("approval.requested", req)

        if self._event_bus:
            self._event_bus.emit_async("approval.requested", {
                "approval_id": req.id,
                "action": action.value,
                "description": description,
                "agent_id": agent_id,
                "priority": priority.name,
            })

        logger.info("ApprovalLayer: request %s for %s: %s",
                     req.id, action.value, description[:60])
        return req

    def resolve_approval(self, request_id: str, granted: bool,
                         resolved_by: str = "",
                         reason: str = "") -> bool:
        with self._lock:
            req = self._requests.get(request_id)
            if req is None or req.status != ApprovalStatus.PENDING:
                return False

            if req.is_expired:
                req.status = ApprovalStatus.EXPIRED
                self._emit("approval.expired", req)
                return False

            req.status = ApprovalStatus.APPROVED if granted else ApprovalStatus.DENIED
            req.resolved_at = time.time()
            req.resolved_by = resolved_by
            req.resolution_reason = reason

            self._audit_log.append({
                "type": "resolve",
                "request_id": request_id,
                "granted": granted,
                "resolved_by": resolved_by,
                "reason": reason,
                "timestamp": time.time(),
            })

        self._emit(
            "approval.approved" if granted else "approval.denied",
            req,
        )

        if self._event_bus:
            self._event_bus.emit_async("approval.resolved", {
                "approval_id": request_id,
                "granted": granted,
                "resolved_by": resolved_by,
                "reason": reason,
            })

        logger.info("ApprovalLayer: request %s %s by %s (reason: %s)",
                     request_id,
                     "APPROVED" if granted else "DENIED",
                     resolved_by or "unknown",
                     reason or "no reason given")
        return True

    def cancel_request(self, request_id: str, reason: str = "") -> bool:
        with self._lock:
            req = self._requests.get(request_id)
            if req is None or req.status != ApprovalStatus.PENDING:
                return False
            req.status = ApprovalStatus.CANCELLED
            req.resolved_at = time.time()
            req.resolution_reason = reason or "cancelled"
        self._emit("approval.cancelled", req)
        return True

    def check_approval(self, request_id: str) -> Optional[bool]:
        with self._lock:
            req = self._requests.get(request_id)
            if req is None:
                return None
            if req.status == ApprovalStatus.APPROVED:
                return True
            if req.status == ApprovalStatus.DENIED:
                return False
            if req.is_expired:
                req.status = ApprovalStatus.EXPIRED
                self._emit("approval.expired", req)
                return False
        return None

    # ------------------------------------------------------------------
    # Auto-approve/deny logic
    # ------------------------------------------------------------------

    def _is_auto_approved(self, action: ApprovalAction,
                          description: str,
                          policy: ApprovalPolicy) -> bool:
        desc_lower = description.lower()
        for pattern in policy.auto_approve_patterns:
            if pattern.lower() in desc_lower:
                return True
        return False

    def _is_auto_denied(self, action: ApprovalAction,
                        description: str,
                        policy: ApprovalPolicy) -> bool:
        desc_lower = description.lower()
        for pattern in policy.auto_deny_patterns:
            if pattern.lower() in desc_lower:
                return True
        return False

    def _create_approved(self, action: ApprovalAction, description: str,
                         agent_id: str, reason: str) -> ApprovalRequest:
        req = ApprovalRequest(
            action=action,
            description=description,
            agent_id=agent_id,
            status=ApprovalStatus.APPROVED,
            resolution_reason=reason,
            resolved_at=time.time(),
            resolved_by="system",
        )
        with self._lock:
            self._requests[req.id] = req
        return req

    def _create_denied(self, action: ApprovalAction, description: str,
                       agent_id: str, reason: str) -> ApprovalRequest:
        req = ApprovalRequest(
            action=action,
            description=description,
            agent_id=agent_id,
            status=ApprovalStatus.DENIED,
            resolution_reason=reason,
            resolved_at=time.time(),
            resolved_by="system",
        )
        with self._lock:
            self._requests[req.id] = req
        return req

    # ------------------------------------------------------------------
    # Escalation
    # ------------------------------------------------------------------

    def escalate(self, request_id: str) -> bool:
        with self._lock:
            req = self._requests.get(request_id)
            if req is None or req.status != ApprovalStatus.PENDING:
                return False
            policy = self._policies.get(req.action)
            max_level = policy.max_escalation_level if policy else 3
            if req.escalation_level >= max_level:
                return False
            req.escalation_level += 1
        self._emit("approval.escalated", req)
        return True

    # ------------------------------------------------------------------
    # Session-based auto-approval
    # ------------------------------------------------------------------

    def grant_session_approval(self, session_id: str,
                               action: ApprovalAction) -> None:
        with self._lock:
            self._auto_approve_contexts.setdefault(session_id, set()).add(action.value)

    def revoke_session_approval(self, session_id: str,
                                action: ApprovalAction) -> None:
        with self._lock:
            contexts = self._auto_approve_contexts.get(session_id)
            if contexts:
                contexts.discard(action.value)

    def is_session_approved(self, session_id: str,
                            action: ApprovalAction) -> bool:
        with self._lock:
            contexts = self._auto_approve_contexts.get(session_id)
            if contexts:
                return action.value in contexts
        return False

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        with self._lock:
            return self._requests.get(request_id)

    def list_requests(self, status: ApprovalStatus = None,
                      action: ApprovalAction = None,
                      agent_id: str = "",
                      limit: int = 100) -> List[ApprovalRequest]:
        with self._lock:
            requests = list(self._requests.values())
        if status:
            requests = [r for r in requests if r.status == status]
        if action:
            requests = [r for r in requests if r.action == action]
        if agent_id:
            requests = [r for r in requests if r.agent_id == agent_id]
        requests.sort(key=lambda r: (r.priority, r.created_at), reverse=True)
        return requests[:limit]

    def list_pending(self) -> List[ApprovalRequest]:
        return self.list_requests(status=ApprovalStatus.PENDING)

    def get_audit_log(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._audit_log[-limit:])

    # ------------------------------------------------------------------
    # Event system
    # ------------------------------------------------------------------

    def on(self, event: str, callback: Callable[[ApprovalRequest], None]) -> None:
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, req: ApprovalRequest) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(req)
            except Exception as exc:
                logger.error("ApprovalLayer: callback error for %s: %s", event, exc)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._requests)
            pending = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.PENDING)
            approved = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.APPROVED)
            denied = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.DENIED)
            expired = sum(1 for r in self._requests.values() if r.is_expired)
        return {
            "total_requests": total,
            "pending": pending,
            "approved": approved,
            "denied": denied,
            "expired": expired,
            "policies": len(self._policies),
            "active_sessions": len(self._auto_approve_contexts),
        }