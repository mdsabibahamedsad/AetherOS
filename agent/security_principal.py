"""Security Principal Identity System for Zero-Trust Architecture.

Defines the core identities and their relationships in the zero-trust model:
- USER: Human or service account interacting with the system
- AGENT: AI agent instance with specific capabilities and permissions
- TOOL: Individual tool function with defined permissions and scopes
- MCP_SERVER: External MCP server with trust status and permissions
- PLUGIN: Extensible module with declared capabilities and permissions
- SKILL: Domain-specific capability with permission requirements
- SESSION: Interactive context with user/agent binding and time limits
- WORKSPACE: File system and resource boundary for operations
- DEVICE: Physical or virtual device running the agent
- SERVICE: External service being accessed (API, database, etc.)

Each principal has explicit identity, scope, and trust level where applicable.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from aetheros_constants import get_aetheros_home


class PrincipalType(Enum):
    """Types of security principals in the zero-trust model."""
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"
    MCP_SERVER = "mcp_server"
    PLUGIN = "plugin"
    SKILL = "skill"
    SESSION = "session"
    WORKSPACE = "workspace"
    DEVICE = "device"
    SERVICE = "service"


class TrustLevel(Enum):
    """Trust levels for principals in the zero-trust model."""
    UNTRUSTED = "untrusted"      # Never trust, always verify
    LOW = "low"                  # Minimal trust, strict verification
    MEDIUM = "medium"            # Moderate trust, standard verification
    HIGH = "high"                # High trust, reduced verification
    ESSENTIAL = "essential"      # Critical system components


class PermissionAction(Enum):
    """Types of actions that can be permitted or denied."""
    READ = "read"
    WRITE = "write"
    CREATE = "create"
    DELETE = "delete"
    EXECUTE = "execute"
    MODIFY = "modify"
    ACCESS = "access"
    CALL = "call"
    CONNECT = "connect"


@dataclass
class Principal:
    """Base class for all security principals."""
    principal_id: str
    principal_type: PrincipalType
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.updated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert principal to dictionary representation."""
        return {
            "principal_id": self.principal_id,
            "principal_type": self.principal_type.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Principal":
        """Create principal from dictionary representation."""
        principal = cls(
            principal_id=data["principal_id"],
            principal_type=PrincipalType(data["principal_type"]),
            created_at=data.get("created_at", time.time()),
            metadata=data.get("metadata", {})
        )
        principal.updated_at = data.get("updated_at", time.time())
        return principal


@dataclass
class User(Principal):
    """Represents a human user or service account."""
    username: str = ""
    email: str = ""
    display_name: str = ""
    is_active: bool = True
    is_service_account: bool = False
    auth_methods: List[str] = field(default_factory=list)
    trusted_devices: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        super().__post_init__()
        if not self.principal_id:
            self.principal_id = f"user_{uuid.uuid4().hex[:8]}"


@dataclass
class Agent(Principal):
    """Represents an AI agent instance."""
    agent_type: str = "general"  # planner, developer, researcher, etc.
    version: str = "1.0.0"
    owner: Optional[str] = None  # User ID that owns this agent
    trust_level: TrustLevel = TrustLevel.LOW
    capabilities: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    workspace: Optional[str] = None  # Workspace ID this agent operates in
    session_scope: Optional[str] = None  # Current session ID
    status: str = "idle"  # idle, busy, error, terminated
    risk_score: float = 0.0  # Calculated risk based on behavior
    
    def __post_init__(self):
        super().__post_init__()
        if not self.principal_id:
            self.principal_id = f"agent_{uuid.uuid4().hex[:8]}"


@dataclass
class Tool(Principal):
    """Represents an individual tool function."""
    tool_name: str = ""
    toolset: str = ""  # file, terminal, web, etc.
    description: str = ""
    risk_level: str = "LOW_RISK"  # LOW_RISK, MEDIUM_RISK, HIGH_RISK, CRITICAL_RISK
    permissions: Dict[str, List[str]] = field(default_factory=dict)  # resource -> actions
    confirmation_required: bool = False
    sandbox_config: Optional[Dict[str, Any]] = None
    output_security_level: str = "NONE"  # NONE, LOW, MEDIUM, HIGH
    version: str = "1.0.0"
    provider: str = "aetheros"
    
    def __post_init__(self):
        super().__post_init__()
        if not self.principal_id:
            self.principal_id = f"tool_{self.toolname or uuid.uuid4().hex[:8]}"
    
    def has_permission(self, resource: str, action: PermissionAction) -> bool:
        """Check if tool has permission to perform action on resource."""
        resource_permissions = self.permissions.get(resource, [])
        return action.value in resource_permissions or "*" in resource_permissions


@dataclass
class MCPServer(Principal):
    """Represents an external MCP server."""
    server_url: str = ""
    trust_status: str = "unverified"  # unverified, trusted, blocked, quarantined
    version: str = "1.0.0"
    protocol_version: str = "2024-11-05"
    capabilities: List[str] = field(default_factory=list)
    permission_manifest: Dict[str, Any] = field(default_factory=dict)
    network_policy: Dict[str, Any] = field(default_factory=dict)
    filesystem_policy: Dict[str, Any] = field(default_factory=dict)
    credential_scope: List[str] = field(default_factory=list)
    audit_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        if not self.principal_id:
            # Generate ID based on server URL for consistency
            url_hash = hashlib.sha256(self.server_url.encode()).hexdigest()[:8]
            self.principal_id = f"mcp_{url_hash}"


@dataclass
class Plugin(Principal):
    """Represents an extensible plugin module."""
    plugin_name: str = ""
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    permissions: Dict[str, List[str]] = field(default_factory=dict)
    files: List[str] = field(default_factory=list)
    network_access: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    processes: List[str] = field(default_factory=list)
    credentials: List[str] = field(default_factory=list)
    ipc_access: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        if not self.principal_id:
            self.principal_id = f"plugin_{self.plugin_name or uuid.uuid4().hex[:8]}"


@dataclass
class Skill(Principal):
    """Represents a domain-specific skill."""
    skill_name: str = ""
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    permission_manifest: Dict[str, Any] = field(default_factory=dict)
    tool_dependencies: List[str] = field(default_factory=list)
    network_requirements: List[str] = field(default_factory=list)
    filesystem_requirements: List[str] = field(default_factory=list)
    risk_level: str = "LOW"
    platforms: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        if not self.principal_id:
            self.principal_id = f"skill_{self.skill_name or uuid.uuid4().hex[:8]}"


@dataclass
class Session(Principal):
    """Represents an interactive session."""
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    device_id: Optional[str] = None
    workspace_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)  # 1 hour default
    last_activity: float = field(default_factory=time.time)
    authentication_state: str = "unauthenticated"  # unauthenticated, authenticating, authenticated
    permission_context: Dict[str, Any] = field(default_factory=dict)
    agent_context: Dict[str, Any] = field(default_factory=dict)
    risk_state: str = "low"  # low, medium, high, critical
    
    def __post_init__(self):
        super().__post_init__()
        if not self.principal_id:
            self.principal_id = f"session_{uuid.uuid4().hex[:8]}"
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return time.time() > self.expires_at
    
    def refresh_expiry(self, extension_seconds: int = 3600):
        """Refresh session expiry time."""
        self.expires_at = time.time() + extension_seconds
        self.last_activity = time.time()
        self.updated_at = time.time()


@dataclass
class Workspace(Principal):
    """Represents a file system and resource workspace."""
    path: str = ""  # Path to workspace root
    is_read_only: bool = False
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)
    max_size_mb: int = 1024  # 1GB default limit
    current_size_mb: float = 0.0
    file_count: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        if not self.principal_id:
            # Generate ID based on workspace path
            path_hash = hashlib.sha256(self.path.encode()).hexdigest()[:8]
            self.principal_id = f"workspace_{path_hash}"
    
    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is within workspace boundaries."""
        try:
            # Normalize path
            normalized_path = str(urlparse(path).path) if "://" in path else path
            from pathlib import Path
            path_obj = Path(normalized_path).resolve()
            workspace_path = Path(self.path).resolve()
            
            # Check if path is within workspace
            path_obj.relative_to(workspace_path)
            return True
        except ValueError:
            # Path is not within workspace
            return False
        except Exception:
            # Error in path resolution
            return False


@dataclass
class Device(Principal):
    """Represents a physical or virtual device."""
    device_name: str = ""
    device_type: str = ""  # laptop, desktop, mobile, server, etc.
    os_name: str = ""
    os_version: str = ""
    hardware_id: str = ""  # Unique hardware identifier
    is_trusted: bool = False
    security_patch_level: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        if not self.principal_id:
            self.principal_id = f"device_{self.hardware_id or uuid.uuid4().hex[:8]}"


@dataclass
class Service(Principal):
    """Represents an external service being accessed."""
    service_name: str = ""
    service_type: str = ""  # api, database, storage, etc.
    endpoint_url: str = ""
    api_version: str = ""
    authentication_required: bool = True
    trust_level: TrustLevel = TrustLevel.UNTRUSTED
    rate_limits: Dict[str, int] = field(default_factory=dict)
    quota_used: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__post_init__()
        if not self.principal_id:
            # Generate ID based on service endpoint
            url_hash = hashlib.sha256(self.endpoint_url.encode()).hexdigest()[:8]
            self.principal_id = f"service_{url_hash}"


# Global registry for tracking principals
_PRINCIPAL_REGISTRY: Dict[str, Principal] = {}
_PRINCIPAL_LOCK = __import__("threading").Lock()


def register_principal(principal: Principal) -> None:
    """Register a principal in the global registry."""
    with _PRINCIPAL_LOCK:
        _PRINCIPAL_REGISTRY[principal.principal_id] = principal
        principal.updated_at = time.time()


def get_principal(principal_id: str) -> Optional[Principal]:
    """Get a principal by ID from the registry."""
    with _PRINCIPAL_LOCK:
        return _PRINCIPAL_REGISTRY.get(principal_id)


def unregister_principal(principal_id: str) -> bool:
    """Remove a principal from the registry."""
    with _PRINCIPAL_LOCK:
        if principal_id in _PRINCIPAL_REGISTRY:
            del _PRINCIPAL_REGISTRY[principal_id]
            return True
        return False


def list_principals(principal_type: Optional[PrincipalType] = None) -> List[Principal]:
    """List all principals, optionally filtered by type."""
    with _PRINCIPAL_LOCK:
        principals = list(_PRINCIPAL_REGISTRY.values())
        if principal_type:
            principals = [p for p in principals if p.principal_type == principal_type]
        return principals


def create_default_user(username: str = "default_user") -> User:
    """Create a default user principal."""
    user = User(
        principal_id=f"user_{username}",
        principal_type=PrincipalType.USER,
        username=username,
        display_name=username.replace("_", " ").title(),
        is_active=True,
        auth_methods=["password", "token"]
    )
    register_principal(user)
    return user


def create_system_agent(agent_type: str = "system") -> Agent:
    """Create a system agent with elevated privileges."""
    agent = Agent(
        principal_id=f"agent_{agent_type}_system",
        principal_type=PrincipalType.AGENT,
        agent_type=agent_type,
        owner="system",
        trust_level=TrustLevel.ESSENTIAL,
        capabilities=["*"],
        permissions=["*"],
        status="idle"
    )
    register_principal(agent)
    return agent


def get_current_user() -> Optional[User]:
    """Get the current user from context or environment."""
    # In a real implementation, this would come from session or auth context
    # For now, return a default user if none exists
    users = list_principals(PrincipalType.USER)
    if users:
        return users[0]
    return create_default_user()


def get_aetheros_principal() -> Principal:
    """Get or create the Aetheros system principal."""
    principal_id = "aetheros_system"
    principal = get_principal(principal_id)
    if principal is None:
        principal = Principal(
            principal_id=principal_id,
            principal_type=PrincipalType.AGENT,  # Using AGENT type for system
            metadata={"system": True, "component": "aetheros"}
        )
        register_principal(principal)
    return principal


def generate_principal_id(principal_type: PrincipalType, seed: str = "") -> str:
    """Generate a deterministic principal ID based on type and seed."""
    if seed:
        hash_input = f"{principal_type.value}:{seed}"
    else:
        hash_input = f"{principal_type.value}:{uuid.uuid4()}"
    
    hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
    return f"{principal_type.value}_{hash_value}"


def validate_principal_relationship(
    requester: Principal,
    target: Principal,
    action: str,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """Validate if a principal relationship is allowed based on basic rules.
    
    This is a basic implementation - the authorization engine will provide
    more sophisticated validation.
    """
    # Basic validation: principals must be registered
    if not get_principal(requester.principal_id) or not get_principal(target.principal_id):
        return False
    
    # Prevent principals from acting on themselves inappropriately
    if requester.principal_id == target.principal_id and action in ["delete", "terminate"]:
        # Allow self-termination for sessions and agents in some cases
        if requester.principal_type in [PrincipalType.SESSION, PrincipalType.AGENT]:
            return True
        return False
    
    return True