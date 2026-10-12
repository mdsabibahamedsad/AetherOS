#!/usr/bin/env python3
"""
Permission Model — Risk-Based Permission System with Approval Gates

Implements a granular permission system that classifies capabilities by risk
level and enforces appropriate approval gates. Integrates with the existing
AetherOS security infrastructure.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

from .models import RiskLevel, PermissionDecision, Task, TaskStep

# Import existing security infrastructure
try:
    from aetheros_security.tool_authz import ToolAuthorizationService, ToolAuthRequest
    from aetheros_security.runtime import get_security_context
    from aetheros_security.identity import get_identity_registry
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

import logging
logger = logging.getLogger(__name__)


# Default risk classifications for capability categories
CATEGORY_RISK_LEVELS = {
    "computer_control": RiskLevel.HIGH,
    "web_browser": RiskLevel.MEDIUM,
    "file_system": RiskLevel.MEDIUM,
    "terminal": RiskLevel.HIGH,
    "coding": RiskLevel.MEDIUM,
    "research": RiskLevel.LOW,
    "knowledge": RiskLevel.LOW,
    "memory": RiskLevel.LOW,
    "communication": RiskLevel.HIGH,
    "calendar": RiskLevel.MEDIUM,
    "automation": RiskLevel.MEDIUM,
    "multi_agent": RiskLevel.MEDIUM,
    "model_orchestration": RiskLevel.LOW,
    "mcp_plugin": RiskLevel.LOW,
    "voice": RiskLevel.LOW,
    "multimodal": RiskLevel.LOW,
    "creative": RiskLevel.LOW,
    "data_analysis": RiskLevel.LOW,
    "system_integration": RiskLevel.MEDIUM,
    "security": RiskLevel.HIGH,
    "personal_assistant": RiskLevel.LOW,
}


# Default permissions required per category
CATEGORY_PERMISSIONS = {
    "computer_control": ["desktop_automation", "screen_capture", "input_simulation"],
    "web_browser": ["web_access", "network"],
    "file_system": ["file_read", "file_write", "file_delete"],
    "terminal": ["shell_exec", "process_management"],
    "coding": ["code_execution", "file_write", "git"],
    "research": ["web_access"],
    "knowledge": ["knowledge_read", "knowledge_write"],
    "memory": ["memory_read", "memory_write"],
    "communication": ["messaging_send", "contact_read"],
    "calendar": ["calendar_read", "calendar_write"],
    "automation": ["automation_manage", "scheduled_execution"],
    "multi_agent": ["agent_spawn", "delegation"],
    "model_orchestration": ["model_select"],
    "mcp_plugin": ["mcp_access"],
    "voice": ["microphone", "audio_output"],
    "multimodal": ["vision", "audio"],
    "creative": ["generation"],
    "data_analysis": ["data_read", "code_execution"],
    "system_integration": ["system_access"],
    "security": ["security_manage"],
    "personal_assistant": [],
}


@dataclass
class PermissionRule:
    """A permission rule for a capability or category."""
    capability_id: str | None = None
    category: str | None = None
    tool_name: str | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    required_permissions: List[str] = field(default_factory=list)
    required_approval: str = "none"  # none, user, admin
    conditions: List[str] = field(default_factory=list)
    auto_approve_threshold: RiskLevel | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalRequest:
    """Request for user approval."""
    id: str
    task_id: str
    capability_id: str
    risk_level: RiskLevel
    reason: str
    requested_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime | None = None
    status: str = "pending"  # pending, approved, denied, expired
    decided_at: datetime | None = None
    decided_by: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PermissionModel:
    """
    Risk-based permission model with approval gates.
    
    Integrates with AetherOS security infrastructure for tool authorization
    and adds capability-level permission management.
    """
    
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self._rules: Dict[str, PermissionRule] = {}
        self._category_defaults: Dict[str, PermissionRule] = {}
        self._pending_approvals: Dict[str, ApprovalRequest] = {}
        self._approval_history: List[ApprovalRequest] = []
        self._lock = threading.RLock()
        self._approval_callbacks: List[Callable[[ApprovalRequest], None]] = []
        self._auto_approve_low_risk: bool = self.config.get("auto_approve_low_risk", True)
        self._require_approval_for_high_risk: bool = self.config.get("require_approval_for_high_risk", True)
        
        # Initialize with defaults
        self._initialize_defaults()
        
        # Initialize security service if available
        self._authz_service: Optional[ToolAuthorizationService] = None
        if SECURITY_AVAILABLE:
            try:
                self._authz_service = ToolAuthorizationService()
            except Exception as e:
                logger.warning(f"Could not initialize tool authorization service: {e}")

    def _initialize_defaults(self) -> None:
        """Initialize default permission rules from category mappings."""
        for category, risk_level in CATEGORY_RISK_LEVELS.items():
            rule = PermissionRule(
                category=category,
                risk_level=risk_level,
                required_permissions=CATEGORY_PERMISSIONS.get(category, []),
                required_approval=self._determine_approval_requirement(risk_level),
            )
            self._category_defaults[category] = rule

    def _determine_approval_requirement(self, risk_level: RiskLevel) -> str:
        """Determine approval requirement from risk level."""
        if risk_level >= RiskLevel.HIGH:
            return "user"
        elif risk_level >= RiskLevel.CRITICAL:
            return "admin"
        elif risk_level >= RiskLevel.MEDIUM:
            return "user" if self._require_approval_for_high_risk else "none"
        return "none"

    def register_rule(self, rule: PermissionRule) -> None:
        """Register a custom permission rule."""
        with self._lock:
            key = rule.capability_id or rule.category or rule.tool_name or "default"
            self._rules[key] = rule
            logger.debug(f"Registered permission rule: {key}")

    def get_rule(self, capability_id: str | None = None, category: str | None = None, 
                 tool_name: str | None = None) -> Optional[PermissionRule]:
        """Get the applicable permission rule."""
        with self._lock:
            # Check specific capability rule first
            if capability_id and capability_id in self._rules:
                return self._rules[capability_id]
            # Check tool-specific rule
            if tool_name and tool_name in self._rules:
                return self._rules[tool_name]
            # Check category rule
            if category and category in self._category_defaults:
                return self._category_defaults[category]
            # Return default
            return self._category_defaults.get("personal_assistant", PermissionRule())

    def check_capability_permission(self, capability_id: str, category: str | None = None,
                                   tool_name: str | None = None,
                                   context: Dict[str, Any] | None = None) -> PermissionDecision:
        """Check if a capability can be executed with current permissions."""
        rule = self.get_rule(capability_id, category, tool_name)
        context = context or {}
        
        # Check if user has required permissions
        user_permissions = context.get("user_permissions", [])
        missing_permissions = [p for p in rule.required_permissions if p not in user_permissions]
        
        if missing_permissions:
            return PermissionDecision(
                allowed=False,
                risk_level=rule.risk_level,
                required_approval=rule.required_approval,
                reason=f"Missing permissions: {', '.join(missing_permissions)}",
                conditions=[f"Requires permission: {p}" for p in missing_permissions],
            )
        
        # Check tool authorization if available
        if tool_name and self._authz_service:
            try:
                auth_request = ToolAuthRequest(
                    tool_name=tool_name,
                    user_id=context.get("user_id", "default"),
                    arguments=context.get("tool_arguments", {}),
                )
                auth_result = self._authz_service.check_authorization(auth_request)
                if not auth_result.allowed:
                    return PermissionDecision(
                        allowed=False,
                        risk_level=rule.risk_level,
                        required_approval="user",
                        reason=auth_result.reason or "Tool authorization denied",
                    )
            except Exception as e:
                logger.debug(f"Tool authorization check failed: {e}")
        
        # Determine if approval is needed
        if rule.required_approval == "none":
            return PermissionDecision(allowed=True, risk_level=rule.risk_level)
        
        # Check if user has specified a risk tolerance that allows this risk level
        risk_tolerance = context.get("risk_tolerance", RiskLevel.MEDIUM)
        if rule.risk_level <= risk_tolerance:
            return PermissionDecision(allowed=True, risk_level=rule.risk_level)
        
        if rule.required_approval == "user" and self._auto_approve_low_risk and rule.risk_level <= RiskLevel.LOW:
            return PermissionDecision(allowed=True, risk_level=rule.risk_level)
        
        if rule.required_approval == "admin" and rule.risk_level >= RiskLevel.CRITICAL:
            return PermissionDecision(
                allowed=False,
                risk_level=rule.risk_level,
                required_approval="admin",
                reason="Admin approval required for critical operations",
            )
        
        # Default: require user approval
        return PermissionDecision(
            allowed=False,
            risk_level=rule.risk_level,
            required_approval=rule.required_approval,
            reason=f"Requires {rule.required_approval} approval for {rule.risk_level.value} risk operation (tolerance: {risk_tolerance.value})",
        )

    def check_task_permissions(self, task: Task) -> PermissionDecision:
        """Check permissions for an entire task (all steps)."""
        # Check each step's capability
        for step in task.plan:
            cap_id = step.capability_id
            if not cap_id:
                continue
            
            # Get capability spec for category
            from .capability_registry import get_capability_registry
            registry = get_capability_registry()
            cap_spec = registry.get_capability_spec(cap_id)
            category = cap_spec.category.value if cap_spec else None
            
            decision = self.check_capability_permission(
                cap_id, 
                category=category, 
                tool_name=step.tool_name,
                context={"user_permissions": task.request.permissions.get("granted", []) if task.request else []}
            )
            
            if not decision.allowed:
                return decision
        
        # All steps passed
        max_risk = max((self.get_rule(s.capability_id).risk_level for s in task.plan if s.capability_id), 
                      default=RiskLevel.NONE)
        return PermissionDecision(allowed=True, risk_level=max_risk)

    def request_approval(self, task_id: str, capability_id: str, 
                        risk_level: RiskLevel, reason: str,
                        expires_in_minutes: int = 30) -> ApprovalRequest:
        """Request user approval for a capability."""
        import uuid
        approval = ApprovalRequest(
            id=str(uuid.uuid4()),
            task_id=task_id,
            capability_id=capability_id,
            risk_level=risk_level,
            reason=reason,
            expires_at=datetime.now() + timedelta(minutes=expires_in_minutes),
        )
        
        with self._lock:
            self._pending_approvals[approval.id] = approval
        
        # Notify callbacks
        for callback in self._approval_callbacks:
            try:
                callback(approval)
            except Exception as e:
                logger.warning(f"Approval callback error: {e}")
        
        logger.info(f"Approval requested: {approval.id} for {capability_id} ({risk_level.value})")
        return approval

    def respond_to_approval(self, approval_id: str, approved: bool, 
                           decided_by: str = "user") -> bool:
        """Respond to an approval request."""
        with self._lock:
            approval = self._pending_approvals.get(approval_id)
            if not approval:
                return False
            
            if approval.status != "pending":
                return False
            
            if datetime.now() > (approval.expires_at or datetime.max):
                approval.status = "expired"
                return False
            
            approval.status = "approved" if approved else "denied"
            approval.decided_at = datetime.now()
            approval.decided_by = decided_by
            
            self._approval_history.append(approval)
            del self._pending_approvals[approval_id]
        
        logger.info(f"Approval {approval_id} {'approved' if approved else 'denied'} by {decided_by}")
        return True

    def get_pending_approvals(self, task_id: str | None = None) -> List[ApprovalRequest]:
        """Get pending approval requests."""
        with self._lock:
            approvals = list(self._pending_approvals.values())
            if task_id:
                approvals = [a for a in approvals if a.task_id == task_id]
            return approvals

    def register_approval_callback(self, callback: Callable[[ApprovalRequest], None]) -> None:
        """Register a callback for new approval requests."""
        with self._lock:
            self._approval_callbacks.append(callback)

    def get_approval_history(self, task_id: str | None = None, limit: int = 100) -> List[ApprovalRequest]:
        """Get approval history."""
        with self._lock:
            history = self._approval_history
            if task_id:
                history = [a for a in history if a.task_id == task_id]
            return history[-limit:]

    def get_user_permissions(self, user_id: str = "default") -> Set[str]:
        """Get user's granted permissions (would integrate with user management)."""
        # In a real implementation, this would query the user management system
        return set()

    def grant_permission(self, user_id: str, permission: str) -> None:
        """Grant a permission to a user (would integrate with user management)."""
        # In a real implementation, this would update the user management system
        logger.info(f"Granted permission {permission} to user {user_id}")

    def revoke_permission(self, user_id: str, permission: str) -> None:
        """Revoke a permission from a user."""
        logger.info(f"Revoked permission {permission} from user {user_id}")


# Module-level instance
_permission_model_instance: Optional[PermissionModel] = None


def get_permission_model(config: Dict[str, Any] | None = None) -> PermissionModel:
    """Get the global permission model instance."""
    global _permission_model_instance
    if _permission_model_instance is None:
        _permission_model_instance = PermissionModel(config)
    return _permission_model_instance