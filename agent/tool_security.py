"""Tool Security Enhancements for Zero-Trust Architecture.

Enhances the tool permission system with:
- Granular resource-based permissions
- Read/write/separate execution permissions
- Tool-specific security policies
- Permission inheritance and role-based access control
- Dynamic permission evaluation based on context
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

from .security_principal import Principal, PermissionAction
from .authorization_engine import AuthorizationEngine, AuthorizationRequest, AuthorizationDecision
from tools.registry import registry
from aetheros_constants import get_aetheros_home


class ToolSecurityLevel(Enum):
    """Security levels for tools."""
    PUBLIC = "public"          # Available to all authenticated agents
    RESTRICTED = "restricted"  # Requires specific authorization
    PRIVILEGED = "privileged"  # Requires elevated privileges
    SYSTEM = "system"          # System-level tools (limited availability)


class ToolPermissionType(Enum):
    """Types of tool permissions."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    MODIFY = "modify"
    ACCESS = "access"
    CALL = "call"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    DEVICE = "device"
    MEMORY = "memory"
    IPC = "ipc"


@dataclass
class ToolResourceSpec:
    """Specification for a tool-accessible resource."""
    resource_type: str  # file, network, device, memory, etc.
    resource_pattern: str  # e.g., "file:///tmp/**", "network://api.example.com/*"
    allowed_actions: Set[PermissionAction] = field(default_factory=set)
    denied_actions: Set[PermissionAction] = field(default_factory=set)
    requires_approval: bool = False
    max_frequency: Optional[int] = None  # Max calls per time period
    max_data_transfer: Optional[int] = None  # Max bytes transferred
    
    def allows_action(self, action: PermissionAction) -> bool:
        """Check if the specified action is allowed for this resource."""
        if action in self.denied_actions:
            return False
        if not self.allowed_actions or PermissionAction.READ in self.allowed_actions:
            # If no specific actions specified or read is allowed, check defaults
            return action in {PermissionAction.READ, PermissionAction.WRITE, PermissionAction.EXECUTE}
        return action in self.allowed_actions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "resource_type": self.resource_type,
            "resource_pattern": self.resource_pattern,
            "allowed_actions": [a.value for a in self.allowed_actions],
            "denied_actions": [a.value for a in self.denied_actions],
            "requires_approval": self.requires_approval,
            "max_frequency": self.max_frequency,
            "max_data_transfer": self.max_data_transfer
        }


@dataclass
class ToolPermissionManifest:
    """Complete permission specification for a tool."""
    tool_name: str
    toolset: str
    security_level: ToolSecurityLevel = ToolSecurityLevel.RESTRICTED
    description: str = ""
    version: str = "1.0.0"
    
    # Resource-specific permissions
    resources: Dict[str, ToolResourceSpec] = field(default_factory=dict)
    
    # Global tool properties
    requires_approval: bool = False
    confirmation_prompt: Optional[str] = None
    sandbox_required: bool = False
    network_access_required: bool = False
    filesystem_access_required: bool = False
    device_access_required: bool = False
    memory_access_required: bool = False
    
    # Risk assessment
    base_risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    risk_factors: List[str] = field(default_factory=list)
    
    # Usage limits
    rate_limit_per_minute: Optional[int] = None
    max_concurrent_calls: Optional[int] = None
    max_execution_time_seconds: Optional[int] = None
    
    def __post_init__(self):
        # Ensure we have at least a default resource spec if none provided
        if not self.resources:
            # Default to no access
            self.resources["none"] = ToolResourceSpec(
                resource_type="none",
                resource_pattern="none",
                allowed_actions=set(),
                denied_actions={PermissionAction.READ, PermissionAction.WRITE, PermissionAction.EXECUTE, PermissionAction.DELETE}
            )
    
    def get_resource_spec(self, resource_path: str) -> Optional[ToolResourceSpec]:
        """Get the resource spec for a given resource path."""
        # Check for exact match first
        if resource_path in self.resources:
            return self.resources[resource_path]
        
        # Check for pattern matches
        for pattern, spec in self.resources.items():
            if self._resource_matches_pattern(resource_path, pattern):
                return spec
        
        return None
    
    def _resource_matches_pattern(self, resource_path: str, pattern: str) -> bool:
        """Check if a resource path matches a pattern."""
        if pattern == "*":
            return True
        if pattern == resource_path:
            return True
        if pattern.endswith("*"):
            return resource_path.startswith(pattern[:-1])
        if "*" in pattern:
            # Simple wildcard matching - real implementation would be more robust
            import fnmatch
            return fnmatch.fnmatch(resource_path, pattern)
        
        # Path-based matching
        try:
            from pathlib import Path
            if "/" in pattern or "\\" in pattern:
                path_obj = Path(resource_path)
                pattern_obj = Path(pattern)
                # Check if resource is within pattern directory
                try:
                    path_obj.relative_to(pattern_obj)
                    return True
                except ValueError:
                    pass
                # Check if pattern is within resource directory (for reverse matching)
                try:
                    pattern_obj.relative_to(path_obj)
                    return True
                except ValueError:
                    pass
        except Exception:
            pass
        
        return False
    
    def allows_action(self, resource_path: str, action: PermissionAction) -> bool:
        """Check if the tool is allowed to perform an action on a resource."""
        resource_spec = self.get_resource_spec(resource_path)
        if resource_spec is None:
            # No matching resource spec - deny by default
            return False
        
        return resource_spec.allows_action(action)
    
    def requires_approval_for(self, resource_path: str, action: PermissionAction) -> bool:
        """Check if approval is required for an action on a resource."""
        resource_spec = self.get_resource_spec(resource_path)
        if resource_spec is None:
            # No matching resource spec - require approval by default for safety
            return True
        
        return resource_spec.requires_approval
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "toolset": self.toolset,
            "security_level": self.security_level.value,
            "description": self.description,
            "version": self.version,
            "resources": {
                path: spec.to_dict() for path, spec in self.resources.items()
            },
            "requires_approval": self.requires_approval,
            "confirmation_prompt": self.confirmation_prompt,
            "sandbox_required": self.sandbox_required,
            "network_access_required": self.network_access_required,
            "filesystem_access_required": self.filesystem_access_required,
            "device_access_required": self.device_access_required,
            "memory_access_required": self.memory_access_required,
            "base_risk_level": self.base_risk_level,
            "risk_factors": self.risk_factors,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "max_concurrent_calls": self.max_concurrent_calls,
            "max_execution_time_seconds": self.max_execution_time_seconds
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolPermissionManifest":
        """Create from dictionary."""
        # Convert resource specs
        resources = {}
        for path, spec_data in data.get("resources", {}).items():
            allowed_actions = {PermissionAction(a) for a in spec_data.get("allowed_actions", [])}
            denied_actions = {PermissionAction(a) for a in spec_data.get("denied_actions", [])}
            resources[path] = ToolResourceSpec(
                resource_type=spec_data.get("resource_type", "unknown"),
                resource_pattern=spec_data.get("resource_pattern", ""),
                allowed_actions=allowed_actions,
                denied_actions=denied_actions,
                requires_approval=spec_data.get("requires_approval", False),
                max_frequency=spec_data.get("max_frequency"),
                max_data_transfer=spec_data.get("max_data_transfer")
            )
        
        return cls(
            tool_name=data.get("tool_name", ""),
            toolset=data.get("toolset", ""),
            security_level=ToolSecurityLevel(data.get("security_level", "restricted")),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            resources=resources,
            requires_approval=data.get("requires_approval", False),
            confirmation_prompt=data.get("confirmation_prompt", None),
            sandbox_required=data.get("sandbox_required", False),
            network_access_required=data.get("network_access_required", False),
            filesystem_access_required=data.get("filesystem_access_required", False),
            device_access_required=data.get("device_access_required", False),
            memory_access_required=data.get("memory_access_required", False),
            base_risk_level=data.get("base_risk_level", "LOW"),
            risk_factors=data.get("risk_factors", []),
            rate_limit_per_minute=data.get("rate_limit_per_minute"),
            max_concurrent_calls=data.get("max_concurrent_calls"),
            max_execution_time_seconds=data.get("max_execution_time_seconds")
        )


class ToolSecurityManager:
    """Manages tool permissions and security policies."""
    
    def __init__(self):
        self._tool_manifests: Dict[str, ToolPermissionManifest] = {}
        self._authorization_engine = AuthorizationEngine()
        self._lock = __import__("threading").Lock()
        
        # Load default tool manifests
        self._load_default_tool_manifests()
    
    def _load_default_tool_manifests(self):
        """Load default permission manifests for common tools."""
        
        # File read tool - restricted to workspace and temp directories
        read_file_manifest = ToolPermissionManifest(
            tool_name="read_file",
            toolset="file",
            description="Read text files with line numbers and pagination",
            security_level=ToolSecurityLevel.RESTRICTED,
            resources={
                "file://workspace/**": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file://workspace/**",
                    allowed_actions={PermissionAction.READ},
                    denied_actions=set()
                ),
                "file:///tmp/**": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file:///tmp/**",
                    allowed_actions={PermissionAction.READ},
                    denied_actions=set()
                ),
                "file:///var/tmp/**": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file:///var/tmp/**",
                    allowed_actions={PermissionAction.READ},
                    denied_actions=set()
                )
            },
            base_risk_level="LOW",
            requires_approval=False
        )
        self.register_tool_manifest(read_file_manifest)
        
        # File write tool - restricted to workspace with approval for sensitive locations
        write_file_manifest = ToolPermissionManifest(
            tool_name="write_file",
            toolset="file",
            description="Write content to a file, completely replacing existing content",
            security_level=ToolSecurityLevel.RESTRICTED,
            resources={
                "file://workspace/**": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file://workspace/**",
                    allowed_actions={PermissionAction.WRITE, PermissionAction.CREATE},
                    denied_actions=set(),
                    requires_approval=False
                ),
                "file:///tmp/**": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file:///tmp/**",
                    allowed_actions={PermissionAction.WRITE, PermissionAction.CREATE},
                    denied_actions=set(),
                    requires_approval=False
                ),
                "file:///etc/**": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file:///etc/**",
                    allowed_actions=set(),
                    denied_actions={PermissionAction.WRITE, PermissionAction.DELETE},
                    requires_approval=True
                ),
                "file:///home/**/.ssh/**": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file:///home/**/.ssh/**",
                    allowed_actions=set(),
                    denied_actions={PermissionAction.WRITE, PermissionAction.DELETE},
                    requires_approval=True
                ),
                "file:///home/**/.aws/**": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file:///home/**/.aws/**",
                    allowed_actions=set(),
                    denied_actions={PermissionAction.WRITE, PermissionAction.DELETE},
                    requires_approval=True
                ),
                "file:///**/auth.json": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file:///**/auth.json",
                    allowed_actions=set(),
                    denied_actions={PermissionAction.WRITE, PermissionAction.DELETE},
                    requires_approval=True
                ),
                "file:///**/.env": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file:///**/.env",
                    allowed_actions=set(),
                    denied_actions={PermissionAction.WRITE, PermissionAction.DELETE},
                    requires_approval=True
                )
            },
            base_risk_level="MEDIUM",
            requires_approval=False
        )
        self.register_tool_manifest(write_file_manifest)
        
        # Patch tool - similar to write_file
        patch_manifest = ToolPermissionManifest(
            tool_name="patch",
            toolset="file",
            description="Apply a patch to a file",
            security_level=ToolSecurityLevel.RESTRICTED,
            resources={
                "file://workspace/**": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file://workspace/**",
                    allowed_actions={PermissionAction.WRITE, PermissionAction.MODIFY},
                    denied_actions=set(),
                    requires_approval=False
                ),
                "file:///tmp/**": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file:///tmp/**",
                    allowed_actions={PermissionAction.WRITE, PermissionAction.MODIFY},
                    denied_actions=set(),
                    requires_approval=False
                ),
                "file:///etc/**": ToolResourceSpec(
                    resource_type="file",
                    resource_pattern="file:///etc/**",
                    allowed_actions=set(),
                    denied_actions={PermissionAction.WRITE, PermissionAction.DELETE},
                    requires_approval=True
                )
            },
            base_risk_level="MEDIUM",
            requires_approval=False
        )
        self.register_tool_manifest(patch_manifest)
        
        # Execute code tool - highly restricted
        execute_code_manifest = ToolPermissionManifest(
            tool_name="execute_code",
            toolset="code_execution",
            description="Execute code in a sandboxed environment",
            security_level=ToolSecurityLevel.PRIVILEGED,
            resources={
                "code://localhost/**": ToolResourceSpec(
                    resource_type="code",
                    resource_pattern="code://localhost/**",
                    allowed_actions={PermissionAction.EXECUTE},
                    denied_actions=set(),
                    requires_approval=True  # Always require approval for code execution
                ),
                "code://sandbox/**": ToolResourceSpec(
                    resource_type="code",
                    resource_pattern="code://sandbox/**",
                    allowed_actions={PermissionAction.EXECUTE},
                    denied_actions=set(),
                    requires_approval=False  # Pre-approved sandbox
                )
            },
            base_risk_level="HIGH",
            risk_factors=["arbitrary_code_execution", "system_access"],
            requires_approval=True,
            max_execution_time_seconds=30,
            max_concurrent_calls=1
        )
        self.register_tool_manifest(execute_code_manifest)
        
        # Send message tool - restricted to approved channels
        send_message_manifest = ToolPermissionManifest(
            tool_name="send_message",
            toolset="messaging",
            description="Send a message via configured messaging channels",
            security_level=ToolSecurityLevel.RESTRICTED,
            resources={
                "message://internal/**": ToolResourceSpec(
                    resource_type="message",
                    resource_pattern="message://internal/**",
                    allowed_actions={PermissionAction.CREATE, PermissionAction.SEND},
                    denied_actions=set(),
                    requires_approval=False
                ),
                "message://external/**": ToolResourceSpec(
                    resource_type="message",
                    resource_pattern="message://external/**",
                    allowed_actions={PermissionAction.CREATE, PermissionAction.SEND},
                    denied_actions=set(),
                    requires_approval=True  # Require approval for external messages
                )
            },
            base_risk_level="MEDIUM",
            requires_approval=False
        )
        self.register_tool_manifest(send_message_manifest)
        
        # Web search tool - with URL restrictions
        web_search_manifest = ToolPermissionManifest(
            tool_name="web_search",
            toolset="web",
            description="Search the web for information",
            security_level=ToolSecurityLevel.RESTRICTED,
            resources={
                "web://*/**": ToolResourceSpec(
                    resource_type="web",
                    resource_pattern="web://*/**",
                    allowed_actions={PermissionAction.READ, PermissionAction.ACCESS},
                    denied_actions=set(),
                    requires_approval=False
                ),
                "web://169.254.169.254/**": ToolResourceSpec(
                    resource_type="web",
                    resource_pattern="web://169.254.169.254/**",
                    allowed_actions=set(),
                    denied_actions={PermissionAction.READ, PermissionAction.ACCESS},
                    requires_approval=True
                ),
                "web://metadata.google.internal/**": ToolResourceSpec(
                    resource_type="web",
                    resource_pattern="web://metadata.google.internal/**",
                    allowed_actions=set(),
                    denied_actions={PermissionAction.READ, PermissionAction.ACCESS},
                    requires_approval=True
                ),
                "web://localhost/**": ToolResourceSpec(
                    resource_type="web",
                    resource_pattern="web://localhost/**",
                    allowed_actions={PermissionAction.READ, PermissionAction.ACCESS},
                    denied_actions=set(),
                    requires_approval=True  # Localhost access requires approval
                )
            },
            base_risk_level="LOW",
            requires_approval=False
        )
        self.register_tool_manifest(web_search_manifest)
        
        # Memory tool - restricted to agent's own memory
        memory_manifest = ToolPermissionManifest(
            tool_name="memory",
            toolset="memory",
            description="Read and write agent memory",
            security_level=ToolSecurityLevel.RESTRICTED,
            resources={
                "memory://agent/**": ToolResourceSpec(
                    resource_type="memory",
                    resource_pattern="memory://agent/**",
                    allowed_actions={PermissionAction.READ, PermissionAction.WRITE},
                    denied_actions=set(),
                    requires_approval=False
                ),
                "memory://system/**": ToolResourceSpec(
                    resource_type="memory",
                    resource_pattern="memory://system/**",
                    allowed_actions=set(),
                    denied_actions={PermissionAction.READ, PermissionAction.WRITE},
                    requires_approval=True
                )
            },
            base_risk_level="LOW",
            requires_approval=False
        )
        self.register_tool_manifest(memory_manifest)
    
    def register_tool_manifest(self, manifest: ToolPermissionManifest) -> bool:
        """Register a tool permission manifest."""
        with self._lock:
            self._tool_manifests[manifest.tool_name] = manifest
            return True
    
    def get_tool_manifest(self, tool_name: str) -> Optional[ToolPermissionManifest]:
        """Get the permission manifest for a tool."""
        with self._lock:
            return self._tool_manifests.get(tool_name)
    
    def list_tool_manifests(self) -> List[ToolPermissionManifest]:
        """List all registered tool permission manifests."""
        with self._lock:
            return list(self._tool_manifests.values())
    
    def remove_tool_manifest(self, tool_name: str) -> bool:
        """Remove a tool permission manifest."""
        with self._lock:
            if tool_name in self._tool_manifests:
                del self._tool_manifests[tool_name]
                return True
            return False
    
    def authorize_tool_execution(
        self,
        agent_principal: Any,  # Agent object
        tool_name: str,
        tool_args: Dict[str, Any],
        context: Any = None  # AuthorizationContext
    ) -> AuthorizationDecision:
        """Authorize tool execution based on the tool's permission manifest.
        
        This integrates tool-specific permissions with the general authorization engine.
        """
        manifest = self.get_tool_manifest(tool_name)
        if manifest is None:
            # No specific manifest - use restrictive default
            from .authorization_engine import AuthorizationRequest, PermissionAction
            
            # Create a basic request to the authorization engine
            request = AuthorizationRequest(
                principal=agent_principal,
                action="tool.call",
                resource=f"tool:{tool_name}",
                permission_action=PermissionAction.EXECUTE,  # Conservative default
                context=context or AuthorizationEngine().create_system_context() if hasattr(AuthorizationEngine, 'create_system_context') else AuthorizationEngine().AuthorizationContext(),
                risk_assessment={"level": "high", "reason": "No specific tool manifest found"}
            )
            
            engine = AuthorizationEngine()
            return engine.is_authorized(request)
        
        # Check if the tool requires approval based on arguments
        requires_approval = False
        approval_context = {}
        
        # Check each argument that might represent a resource
        for arg_name, arg_value in tool_args.items():
            if isinstance(arg_value, str):
                # Check if this argument represents a file path, URL, etc.
                if arg_name in ["path", "file", "url", "uri", "endpoint", "destination"]:
                    if manifest.requires_approval_for(arg_value, PermissionAction.WRITE if "write" in tool_name.lower() or "patch" in tool_name.lower() else PermissionAction.READ):
                        requires_approval = True
                        approval_context["resource"] = arg_value
                        approval_context["action"] = arg_name
                        break
        
        # Use the authorization engine for the final decision
        from .authorization_engine import AuthorizationRequest, PermissionAction
        
        # Determine the appropriate permission action
        permission_action = PermissionAction.EXECUTE  # Default
        if "read" in tool_name.lower() or "search" in tool_name.lower():
            permission_action = PermissionAction.READ
        elif "write" in tool_name.lower() or "patch" in tool_name.lower():
            permission_action = PermissionAction.WRITE
        elif "delete" in tool_name.lower():
            permission_action = PermissionAction.DELETE
        
        # Create authorization request
        request = AuthorizationRequest(
            principal=agent_principal,
            action="tool.call",
            resource=f"tool:{tool_name}",
            permission_action=permission_action,
            context=context or AuthorizationEngine().AuthorizationContext() if hasattr(AuthorizationEngine, 'AuthorizationContext') else None,
            risk_assessment={
                "level": manifest.base_risk_level.lower(),
                "factors": manifest.risk_factors,
                "tool_name": tool_name,
                "requires_manifest_approval": requires_approval
            }
        )
        
        engine = AuthorizationEngine()
        decision = engine.is_authorized(request)
        
        # If the tool's manifest requires approval and the engine didn't already require it,
        # upgrade the decision to require approval
        if requires_approval and decision.decision != AuthorizationEngine().Decision.REQUIRE_APPROVAL:
            # Create a new decision requiring approval
            from .authorization_engine import AuthorizationDecision, Decision, RiskLevel
            
            decision = AuthorizationDecision(
                decision=Decision.REQUIRE_APPROVAL,
                reason=f"Tool {tool_name} requires approval for resource access",
                risk_level=RiskLevel.MEDIUM,
                metadata={
                    "tool_manifest_required_approval": True,
                    "original_decision": decision.to_dict() if hasattr(decision, 'to_dict') else str(decision)
                }
            )
        
        return decision
    
    def validate_tool_usage(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        context: Any = None  # AuthorizationContext
    ) -> Tuple[bool, List[str]]:
        """Validate tool usage against its permission manifest.
        
        Returns (is_valid, list_of_violations).
        """
        violations = []
        manifest = self.get_tool_manifest(tool_name)
        
        if manifest is None:
            violations.append(f"No permission manifest found for tool: {tool_name}")
            return False, violations
        
        # Check each argument that represents a resource
        for arg_name, arg_value in tool_args.items():
            if isinstance(arg_value, str) and arg_name in ["path", "file", "url", "uri", "endpoint", "destination"]:
                # Determine the likely action based on tool name and arg name
                action = PermissionAction.READ  # Default
                if "write" in tool_name.lower() or "patch" in tool_name.lower() or "delete" in tool_name.lower():
                    action = PermissionAction.WRITE
                elif "read" in tool_name.lower() or "search" in tool_name.lower() or "get" in tool_name.lower():
                    action = PermissionAction.READ
                elif "execute" in tool_name.lower() or "run" in tool_name.lower():
                    action = PermissionAction.EXECUTE
                
                # Check if action is allowed
                if not manifest.allows_action(arg_value, action):
                    violations.append(f"Tool {tool_name} not allowed to perform {action.value} on {arg_value}")
                
                # Check if approval is required
                if manifest.requires_approval_for(arg_value, action):
                    violations.append(f"Tool {tool_name} requires approval for {action.value} on {arg_value}")
        
        return len(violations) == 0, violations
    
    def get_tool_security_info(self, tool_name: str) -> Dict[str, Any]:
        """Get security information for a tool."""
        manifest = self.get_tool_manifest(tool_name)
        if manifest is None:
            return {"error": f"No security information found for tool: {tool_name}"}
        
        return {
            "tool_name": manifest.tool_name,
            "toolset": manifest.toolset,
            "security_level": manifest.security_level.value,
            "description": manifest.description,
            "version": manifest.version,
            "base_risk_level": manifest.base_risk_level,
            "risk_factors": manifest.risk_factors,
            "requires_approval": manifest.requires_approval,
            "resources": {
                path: {
                    "type": spec.resource_type,
                    "pattern": spec.resource_pattern,
                    "allowed_actions": [a.value for a in spec.allowed_actions],
                    "denied_actions": [a.value for a in spec.denied_actions],
                    "requires_approval": spec.requires_approval
                }
                for path, spec in manifest.resources.items()
            },
            "limits": {
                "rate_limit_per_minute": manifest.rate_limit_per_minute,
                "max_concurrent_calls": manifest.max_concurrent_calls,
                "max_execution_time_seconds": manifest.max_execution_time_seconds
            }
        }


# Global tool security manager instance
_TOOL_SECURITY_MANAGER = None
_TOOL_SECURITY_LOCK = __import__("threading").Lock()


def get_tool_security_manager() -> ToolSecurityManager:
    """Get the global tool security manager instance."""
    global _TOOL_SECURITY_MANAGER
    with _TOOL_SECURITY_LOCK:
        if _TOOL_SECURITY_MANAGER is None:
            _TOOL_SECURITY_MANAGER = ToolSecurityManager()
        return _TOOL_SECURITY_MANAGER


def authorize_tool_execution(
    agent_principal: Any,  # Agent object
    tool_name: str,
    tool_args: Dict[str, Any],
    context: Any = None  # AuthorizationContext
) -> AuthorizationDecision:
    """Convenience function for authorizing tool execution."""
    manager = get_tool_security_manager()
    return manager.authorize_tool_execution(agent_principal, tool_name, tool_args, context)


def validate_tool_usage(
    tool_name: str,
    tool_args: Dict[str, Any],
    context: Any = None  # AuthorizationContext
) -> Tuple[bool, List[str]]:
    """Convenience function for validating tool usage."""
    manager = get_tool_security_manager()
    return manager.validate_tool_usage(tool_name, tool_args, context)


def get_tool_security_info(tool_name: str) -> Dict[str, Any]:
    """Convenience function for getting tool security information."""
    manager = get_tool_security_manager()
    return manager.get_tool_security_info(tool_name)


def register_tool_manifest(manifest: ToolPermissionManifest) -> bool:
    """Convenience function for registering a tool permission manifest."""
    manager = get_tool_security_manager()
    return manager.register_tool_manifest(manifest)


# Integration with the existing tool registry
def enhance_tool_registry_with_security():
    """Enhance the existing tool registry with security information.
    
    This function adds security metadata to existing tool registrations
    based on the tool permission manifests.
    """
    manager = get_tool_security_manager()
    
    # Iterate through all registered tools in the registry
    for tool_name in registry.get_all_tool_names():
        try:
            # Get the tool entry from the registry
            tool_entry = registry._tools.get(tool_name)
            if tool_entry is None:
                continue
            
        # Get the security manifest for this tool
        manifest = manager.get_tool_manifest(tool_name)
            if manifest is not None:
                # Enhance the tool entry with security information
                # We'll add this as metadata that can be accessed by the authorization engine
                if not hasattr(tool_entry, 'security_metadata'):
                    tool_entry.security_metadata = {}
                
                tool_entry.security_metadata.update({
                    "tool_manifest": manifest.to_dict(),
                    "security_level": manifest.security_level.value,
                    "base_risk_level": manifest.base_risk_level,
                    "requires_approval": manifest.requires_approval,
                    "resources_count": len(manifest.resources)
                })
        except Exception:
            # Continue processing other tools if one fails
            continue


def get_tool_manifest(self, tool_name: str) -> Optional[ToolPermissionManifest]:
    """Get the permission manifest for a tool."""
    with self._lock:
        return self._tool_manifests.get(tool_name)