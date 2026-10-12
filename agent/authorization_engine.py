"""Centralized Authorization Engine for Zero-Trust Security.

Implements the core authorization logic that makes access decisions based on:
- Principal identity and trust level
- Action being performed
- Target resource and its sensitivity
- Request context (session, time, location, etc.)
- Applicable security policies
- Risk assessment

Returns decisions: ALLOW, DENY, REQUIRE_APPROVAL, or CHALLENGE.
"""

from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from .security_principal import (
    Principal, PrincipalType, TrustLevel, PermissionAction,
    User, Agent, Tool, MCPServer, Plugin, Skill, Session, Workspace, Device, Service
)


class Decision(Enum):
    """Authorization decisions that can be returned by the engine."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    CHALLENGE = "challenge"


class RiskLevel(Enum):
    """Risk levels for authorization decisions."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuthorizationContext:
    """Context information for authorization decisions."""
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    device_id: Optional[str] = None
    workspace_id: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "device_id": self.device_id,
            "workspace_id": self.workspace_id,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "metadata": self.metadata
        }


@dataclass
class AuthorizationRequest:
    """Request for authorization decision."""
    principal: Principal
    action: str  # Action being performed (e.g., "tool.call", "file.read")
    resource: str  # Target resource (e.g., "file:/path/to/file", "tool:write_file")
    permission_action: PermissionAction  # Specific permission action (read, write, etc.)
    context: AuthorizationContext
    risk_assessment: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert request to dictionary."""
        return {
            "principal": self.principal.to_dict() if self.principal else None,
            "action": self.action,
            "resource": self.resource,
            "permission_action": self.permission_action.value,
            "context": self.context.to_dict() if self.context else None,
            "risk_assessment": self.risk_assessment
        }


@dataclass
class AuthorizationDecision:
    """Result of an authorization check."""
    decision: Decision
    reason: str = ""
    risk_level: RiskLevel = RiskLevel.NONE
    requires_approval_until: Optional[float] = None  # Timestamp for expiry
    constraints: Dict[str, Any] = field(default_factory=dict)  # Additional constraints
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary."""
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "risk_level": self.risk_level.value,
            "requires_approval_until": self.requires_approval_until,
            "constraints": self.constraints,
            "metadata": self.metadata
        }


class PolicyEffect(Enum):
    """Effects that a policy can have."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    CHALLENGE = "challenge"
    AUDIT = "audit"


@dataclass
class SecurityPolicy:
    """Represents a security policy rule."""
    policy_id: str
    name: str
    description: str
    effect: PolicyEffect
    conditions: Dict[str, Any] = field(default_factory=dict)  # When policy applies
    actions: List[str] = field(default_factory=list)  # Actions this policy covers
    resources: List[str] = field(default_factory=list)  # Resources this policy covers
    principals: List[str] = field(default_factory=list)  # Principals this policy applies to
    risk_level: RiskLevel = RiskLevel.LOW
    priority: int = 0  # Higher priority policies override lower ones
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.updated_at = time.time()
    
    def applies_to(self, request: AuthorizationRequest) -> bool:
        """Check if this policy applies to the given request."""
        if not self.enabled:
            return False
        
        # Check principal
        if self.principals and request.principal.principal_id not in self.principals:
            # Check if it's a wildcard or type match
            if "*" not in self.principals and request.principal.principal_type.value not in self.principals:
                return False
        
        # Check action
        if self.actions and request.action not in self.actions:
            # Check for wildcards
            if "*" not in self.actions and not any(
                pattern.endswith("*") and request.action.startswith(pattern[:-1])
                for pattern in self.actions
            ):
                return False
        
        # Check resource
        if self.resources and not self._resource_matches(request.resource):
            return False
        
        # Check conditions
        if not self._conditions_match(request):
            return False
        
        return True
    
    def _resource_matches(self, resource: str) -> bool:
        """Check if resource matches policy resource patterns."""
        if not self.resources:
            return True  # No resource restrictions means applies to all
        
        for pattern in self.resources:
            if pattern == "*":
                return True
            elif pattern.endswith("*"):
                if resource.startswith(pattern[:-1]):
                    return True
            elif pattern == resource:
                return True
            elif self._is_path_pattern(pattern) and self._path_matches(pattern, resource):
                return True
        
        return False
    
    def _is_path_pattern(self, pattern: str) -> bool:
        """Check if pattern is a path pattern."""
        return "/" in pattern or "\\" in pattern or pattern.startswith("~/")
    
    def _path_matches(self, pattern: str, resource: str) -> bool:
        """Check if resource matches path pattern."""
        try:
            from pathlib import Path
            # Normalize both paths
            path_obj = Path(resource).resolve()
            pattern_path = Path(pattern).resolve()
            
            # Check if resource path is within pattern path (for allow patterns)
            # or if pattern path is within resource path (for deny patterns)
            # This is simplified - real implementation would be more sophisticated
            return str(path_obj).startswith(str(pattern_path))
        except Exception:
            # Fallback to string matching
            return pattern in resource
    
    def _conditions_match(self, request: AuthorizationRequest) -> bool:
        """Check if request meets policy conditions."""
        # Simplified condition matching - real implementation would be more robust
        for key, value in self.conditions.items():
            if key == "risk_level" and request.risk_assessment:
                # Check risk level condition
                request_risk = request.risk_assessment.get("level", "none")
                if isinstance(value, str) and request_risk != value:
                    return False
            elif key == "time_of_day":
                # Time-based conditions
                pass
            elif key == "location":
                # Location-based conditions
                pass
            # Add more condition types as needed
        
        return True


class AuthorizationEngine:
    """Centralized authorization engine for zero-trust security."""
    
    def __init__(self):
        self._policies: List[SecurityPolicy] = []
        self._policy_lock = __import__("threading").Lock()
        self._default_decision = Decision.DENY  # Default to deny
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Initialize default security policies."""
        # Default deny all policy (applies when no other policy matches)
        default_deny = SecurityPolicy(
            policy_id="default_deny_all",
            name="Default Deny All",
            description="Default deny all access when no other policy matches",
            effect=PolicyEffect.DENY,
            actions=["*"],
            resources=["*"],
            principals=["*"],
            priority=-1000  # Lowest priority
        )
        self.add_policy(default_deny)
        
        # Allow basic agent operations for authenticated agents
        basic_agent_ops = SecurityPolicy(
            policy_id="basic_agent_operations",
            name="Basic Agent Operations",
            description="Allow basic operations for authenticated agents",
            effect=PolicyEffect.ALLOW,
            actions=["tool.call", "message.send", "message.receive"],
            resources=["tool:*", "session:*"],
            principals=["agent:*"],
            conditions={"risk_level": "low"},
            priority=0
        )
        self.add_policy(basic_agent_ops)
        
        # Allow file operations within workspace
        workspace_file_ops = SecurityPolicy(
            policy_id="workspace_file_operations",
            name="Workspace File Operations",
            description="Allow file operations within assigned workspace",
            effect=PolicyEffect.ALLOW,
            actions=["file.read", "file.write", "file.delete"],
            resources=["file://workspace/**"],
            principals=["agent:*"],
            priority=10
        )
        self.add_policy(workspace_file_ops)
        
        # Require approval for sensitive operations
        sensitive_ops = SecurityPolicy(
            policy_id="sensitive_operations_approval",
            name="Sensitive Operations Require Approval",
            description="Require approval for sensitive operations",
            effect=PolicyEffect.REQUIRE_APPROVAL,
            actions=["tool.call"],
            resources=[
                "tool:write_file", 
                "tool:delete", 
                "tool:execute_code",
                "tool:send_message",
                "tool:delegate_task"
            ],
            principals=["agent:*"],
            priority=20
        )
        self.add_policy(sensitive_ops)
        
        # Deny access to system files
        system_file_protection = SecurityPolicy(
            policy_id="system_file_protection",
            name="System File Protection",
            description="Deny access to sensitive system files",
            effect=PolicyEffect.DENY,
            actions=["file.read", "file.write", "file.delete"],
            resources=[
                "file:///etc/passwd",
                "file:///etc/shadow",
                "file:///etc/sudoers",
                "file://~/.ssh/**",
                "file://~/.aws/**",
                "file://~/.aetheros/auth.json",
                "file://~/.aetheros/.env"
            ],
            principals=["agent:*"],
            priority=100  # High priority to override allows
        )
        self.add_policy(system_file_protection)
    
    def add_policy(self, policy: SecurityPolicy) -> None:
        """Add a security policy to the engine."""
        with self._policy_lock:
            self._policies.append(policy)
            # Sort by priority (higher priority first)
            self._policies.sort(key=lambda p: p.priority, reverse=True)
    
    def remove_policy(self, policy_id: str) -> bool:
        """Remove a security policy by ID."""
        with self._policy_lock:
            for i, policy in enumerate(self._policies):
                if policy.policy_id == policy_id:
                    del self._policies[i]
                    return True
            return False
    
    def get_policy(self, policy_id: str) -> Optional[SecurityPolicy]:
        """Get a security policy by ID."""
        with self._policy_lock:
            for policy in self._policies:
                if policy.policy_id == policy_id:
                    return policy
            return None
    
    def list_policies(self) -> List[SecurityPolicy]:
        """List all security policies."""
        with self._policy_lock:
            return self._policies.copy()
    
    def is_authorized(self, request: AuthorizationRequest) -> AuthorizationDecision:
        """Make an authorization decision for the given request.
        
        This is the main entry point for authorization checks.
        Evaluates all applicable policies and returns a decision.
        """
        # Collect all applicable policies
        applicable_policies = []
        with self._policy_lock:
            for policy in self._policies:
                if policy.applies_to(request):
                    applicable_policies.append(policy)
        
        if not applicable_policies:
            # No policies apply - use default decision
            return AuthorizationDecision(
                decision=self._default_decision,
                reason="No applicable policies found",
                risk_level=RiskLevel.MEDIUM
            )
        
        # Process policies in priority order
        # For simplicity, we'll use the highest priority policy that makes a definitive decision
        # In a more complex implementation, we'd combine policies or use more sophisticated logic
        final_decision = None
        final_reason = ""
        final_risk_level = RiskLevel.LOW
        
        for policy in applicable_policies:
            # Skip audit-only policies for decision making
            if policy.effect == PolicyEffect.AUDIT:
                continue
            
            # Determine the decision based on policy effect
            if policy.effect == PolicyEffect.ALLOW:
                final_decision = Decision.ALLOW
                final_reason = f"Allowed by policy: {policy.name}"
                final_risk_level = policy.risk_level
                break  # Allow takes precedence unless overridden by higher priority deny
            elif policy.effect == PolicyEffect.DENY:
                final_decision = Decision.DENY
                final_reason = f"Denied by policy: {policy.name}"
                final_risk_level = policy.risk_level
                # Deny is final - no need to check lower priority policies
                break
            elif policy.effect == PolicyEffect.REQUIRE_APPROVAL:
                final_decision = Decision.REQUIRE_APPROVAL
                final_reason = f"Approval required by policy: {policy.name}"
                final_risk_level = policy.risk_level
                # Continue checking for higher priority denies that might override
            elif policy.effect == PolicyEffect.CHALLENGE:
                final_decision = Decision.CHALLENGE
                final_reason = f"Challenge required by policy: {policy.name}"
                final_risk_level = policy.risk_level
                # Continue checking for higher priority denies/requires_approval
        
        # If we didn't get a definitive allow/deny, use what we have
        if final_decision is None:
            # Look for the highest priority require_approval or challenge
            for policy in applicable_policies:
                if policy.effect == PolicyEffect.REQUIRE_APPROVAL:
                    final_decision = Decision.REQUIRE_APPROVAL
                    final_reason = f"Approval required by policy: {policy.name}"
                    final_risk_level = policy.risk_level
                    break
                elif policy.effect == PolicyEffect.CHALLENGE:
                    final_decision = Decision.CHALLENGE
                    final_reason = f"Challenge required by policy: {policy.name}"
                    final_risk_level = policy.risk_level
                    break
            
            # If still nothing, default to deny
            if final_decision is None:
                final_decision = Decision.DENY
                final_reason = "No granting policy found"
                final_risk_level = RiskLevel.MEDIUM
        
        # Calculate final risk level based on request context and policies
        final_risk_level = self._calculate_risk_level(request, applicable_policies)
        
        return AuthorizationDecision(
            decision=final_decision,
            reason=final_reason,
            risk_level=final_risk_level,
            metadata={
                "applicable_policies_count": len(applicable_policies),
                "evaluated_policies": [p.policy_id for p in applicable_policies[:5]]  # First 5
            }
        )
    
    def _calculate_risk_level(
        self, 
        request: AuthorizationRequest, 
        policies: List[SecurityPolicy]
    ) -> RiskLevel:
        """Calculate risk level for the authorization decision."""
        # Start with base risk from request
        base_risk = request.risk_assessment.get("level", "low") if request.risk_assessment else "low"
        risk_level = RiskLevel(base_risk) if base_risk in [r.value for r in RiskLevel] else RiskLevel.LOW
        
        # Increase risk based on policy risk levels
        policy_risks = [p.risk_level for p in policies if p.enabled]
        if policy_risks:
            # Use the highest risk level from applicable policies
            max_policy_risk = max(policy_risks, key=lambda r: list(RiskLevel).index(r))
            if list(RiskLevel).index(max_policy_risk) > list(RiskLevel).index(risk_level):
                risk_level = max_policy_risk
        
        # Increase risk for sensitive actions
        sensitive_actions = {
            PermissionAction.DELETE, PermissionAction.WRITE, 
            PermissionAction.EXECUTE, PermissionAction.MODIFY
        }
        if request.permission_action in sensitive_actions:
            current_index = list(RiskLevel).index(risk_level)
            if current_index < len(RiskLevel) - 1:  # Not already at maximum
                risk_level = list(RiskLevel)[current_index + 1]
        
        # Increase risk for system resources
        if any(s in request.resource.lower() for s in ["/etc/", "/.ssh/", "/.aws/", "auth.json", ".env"]):
            current_index = list(RiskLevel).index(risk_level)
            if current_index < len(RiskLevel) - 1:  # Not already at maximum
                risk_level = list(RiskLevel)[current_index + 1]
        
        return risk_level
    
    def authorize_tool_call(
        self,
        agent: Agent,
        tool: Tool,
        tool_args: Dict[str, Any],
        context: Optional[AuthorizationContext] = None
    ) -> AuthorizationDecision:
        """Authorize a tool call request.
        
        Convenience method for authorizing tool executions.
        """
        if context is None:
            context = AuthorizationContext()
        
        # Extract agent and session info from context if not provided
        if not context.agent_id and agent.principal_id:
            context.agent_id = agent.principal_id
        if not context.user_id and agent.owner:
            context.user_id = agent.owner
        
        # Build the resource identifier for the tool
        resource = f"tool:{tool.tool_name}"
        
        # Determine the permission action based on tool type and args
        permission_action = self._determine_tool_permission_action(tool, tool_args)
        
        # Create the authorization request
        request = AuthorizationRequest(
            principal=agent,
            action="tool.call",
            resource=resource,
            permission_action=permission_action,
            context=context,
            risk_assessment=self._assess_tool_call_risk(tool, tool_args, context)
        )
        
        return self.is_authorized(request)
    
    def authorize_file_access(
        self,
        principal: Principal,
        file_path: str,
        action: PermissionAction,
        context: Optional[AuthorizationContext] = None
    ) -> AuthorizationDecision:
        """Authorize file access request.
        
        Convenience method for authorizing file operations.
        """
        if context is None:
            context = AuthorizationContext()
        
        # Build resource identifier
        resource = f"file:{file_path}"
        
        # Create the authorization request
        request = AuthorizationRequest(
            principal=principal,
            action=f"file.{action.value}",
            resource=resource,
            permission_action=action,
            context=context,
            risk_assessment=self._assess_file_access_risk(file_path, action, context)
        )
        
        return self.is_authorized(request)
    
    def _determine_tool_permission_action(
        self, 
        tool: Tool, 
        tool_args: Dict[str, Any]
    ) -> PermissionAction:
        """Determine the permission action for a tool call based on tool and arguments."""
        # Map common tools to their permission actions
        tool_action_map = {
            "read_file": PermissionAction.READ,
            "write_file": PermissionAction.WRITE,
            "patch": PermissionAction.WRITE,  # patch modifies files
            "delete_file": PermissionAction.DELETE,
            "execute_code": PermissionAction.EXECUTE,
            "send_message": PermissionAction.CREATE,  # creates a message
            "delegate_task": PermissionAction.EXECUTE,  # executes a task
            "memory": PermissionAction.WRITE,  # writes to memory
            "web_search": PermissionAction.READ,  # reads from web
            "browser_navigate": PermissionAction.ACCESS,  # accesses a resource
        }
        
        # Default to execute if not mapped
        return tool_action_map.get(tool.tool_name, PermissionAction.EXECUTE)
    
    def _assess_tool_call_risk(
        self, 
        tool: Tool, 
        tool_args: Dict[str, Any], 
        context: AuthorizationContext
    ) -> Dict[str, Any]:
        """Assess risk level for a tool call."""
        risk_factors = []
        risk_level = "low"
        
        # Tool-based risk factors
        if tool.risk_level == "HIGH_RISK":
            risk_factors.append("high_risk_tool")
            risk_level = "high"
        elif tool.risk_level == "CRITICAL_RISK":
            risk_factors.append("critical_risk_tool")
            risk_level = "critical"
        
        # Argument-based risk factors
        if tool.tool_name in ["write_file", "patch"]:
            file_path = tool_args.get("path", "")
            if any(s in file_path.lower() for s in ["/etc/", "/.ssh/", "/.aws/"]):
                risk_factors.append("sensitive_file_access")
                if risk_level == "low":
                    risk_level = "medium"
                elif risk_level == "medium":
                    risk_level = "high"
        
        if tool.tool_name == "execute_code":
            code = tool_args.get("code", "")
            if any(dangerous in code.lower() for dangerous in ["rm ", "del ", "format ", "mkfs"]):
                risk_factors.append("dangerous_code")
                risk_level = "high"
        
        if tool.tool_name == "send_message":
            # Check if sending to external recipients
            if tool_args.get("channel_type") in ["email", "sms"] and tool_args.get("to", "").startswith("+"):
                risk_factors.append("external_communication")
                if risk_level == "low":
                    risk_level = "medium"
        
        # Context-based risk factors
        if context and context.session_id:
            # Check if this is a new or unusual session
            pass  # Would integrate with session monitoring in practice
        
        return {
            "level": risk_level,
            "factors": risk_factors,
            "assessment_time": time.time(),
            "tool_id": tool.principal_id,
            "action": tool.tool_name
        }
    
    def _assess_file_access_risk(
        self, 
        file_path: str, 
        action: PermissionAction, 
        context: AuthorizationContext
    ) -> Dict[str, Any]:
        """Assess risk level for file access."""
        risk_factors = []
        risk_level = "low"
        
        # Path-based risk factors
        sensitive_paths = [
            "/etc/passwd", "/etc/shadow", "/etc/sudoers",
            "/.ssh/", "/.aws/", "/.git/", "/.env",
            "auth.json", ".env", "credentials", "secrets"
        ]
        
        if any(sensitive in file_path.lower() for sensitive in sensitive_paths):
            risk_factors.append("sensitive_file_path")
            if action in [PermissionAction.WRITE, PermissionAction.DELETE]:
                risk_level = "high"
            elif action == PermissionAction.READ:
                risk_level = "medium"
        
        # Action-based risk factors
        if action == PermissionAction.DELETE:
            risk_factors.append("file_deletion")
            if risk_level == "low":
                risk_level = "medium"
        
        # Context-based risk factors would go here
        
        return {
            "level": risk_level,
            "factors": risk_factors,
            "assessment_time": time.time(),
            "file_path": file_path,
            "action": action.value
        }


# Global authorization engine instance
_AUTHORIZATION_ENGINE = None
_ENGINE_LOCK = __import__("threading").Lock()


def get_authorization_engine() -> AuthorizationEngine:
    """Get the global authorization engine instance."""
    global _AUTHORIZATION_ENGINE
    with _ENGINE_LOCK:
        if _AUTHORIZATION_ENGINE is None:
            _AUTHORIZATION_ENGINE = AuthorizationEngine()
        return _AUTHORIZATION_ENGINE


def authorize(
    principal: Principal,
    action: str,
    resource: str,
    permission_action: PermissionAction,
    context: Optional[AuthorizationContext] = None,
    risk_assessment: Optional[Dict[str, Any]] = None
) -> AuthorizationDecision:
    """Convenience function for making authorization decisions."""
    engine = get_authorization_engine()
    request = AuthorizationRequest(
        principal=principal,
        action=action,
        resource=resource,
        permission_action=permission_action,
        context=context or AuthorizationContext(),
        risk_assessment=risk_assessment
    )
    return engine.is_authorized(request)


def authorize_tool_call(
    agent: Agent,
    tool: Tool,
    tool_args: Dict[str, Any],
    context: Optional[AuthorizationContext] = None
) -> AuthorizationDecision:
    """Convenience function for authorizing tool calls."""
    engine = get_authorization_engine()
    return engine.authorize_tool_call(agent, tool, tool_args, context)


def authorize_file_access(
    principal: Principal,
    file_path: str,
    action: PermissionAction,
    context: Optional[AuthorizationContext] = None
) -> AuthorizationDecision:
    """Convenience function for authorizing file access."""
    engine = get_authorization_engine()
    return engine.authorize_file_access(principal, file_path, action, context)


# Helper functions for creating common authorization requests
def create_agent_context(
    agent_id: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    workspace_id: Optional[str] = None
) -> AuthorizationContext:
    """Create an authorization context for an agent."""
    return AuthorizationContext(
        agent_id=agent_id,
        session_id=session_id,
        user_id=user_id,
        workspace_id=workspace_id,
        timestamp=time.time()
    )


def create_system_context() -> AuthorizationContext:
    """Create an authorization context for system operations."""
    return AuthorizationContext(
        agent_id="aetheros_system",
        user_id="system",
        timestamp=time.time(),
        metadata={"system_operation": True}
    )