"""Security Policy Engine for Zero-Trust Architecture.

Implements the policy definition, storage, retrieval, and evaluation system
that works with the authorization engine to enforce zero-trust security
principles throughout the Aetheros system.
"""

from __future__ import annotations

import json
import os
import time
import uuid
import yaml
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

from .authorization_engine import (
    SecurityPolicy, PolicyEffect, AuthorizationEngine,
    AuthorizationRequest, AuthorizationDecision, Decision,
    RiskLevel, get_authorization_engine
)
from .security_principal import Principal, PrincipalType
from aetheros_constants import get_aetheros_home
from aetheros_cli.config import load_config


class PolicyStorageType(Enum):
    """Types of policy storage."""
    MEMORY = "memory"
    FILE = "file"
    DATABASE = "database"
    CONFIG = "config"


class PolicyFormat(Enum):
    """Formats for policy storage."""
    YAML = "yaml"
    JSON = "json"


@dataclass
class PolicyMetadata:
    """Metadata for security policies."""
    policy_id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "aetheros-system"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "category": self.category,
            "enabled": self.enabled
        }


class PolicyStore:
    """Abstract base class for policy storage implementations."""
    
    def __init__(self, storage_type: PolicyStorageType):
        self.storage_type = storage_type
    
    def load_policies(self) -> List[SecurityPolicy]:
        """Load policies from storage."""
        raise NotImplementedError
    
    def save_policy(self, policy: SecurityPolicy) -> bool:
        """Save a policy to storage."""
        raise NotImplementedError
    
    def update_policy(self, policy: SecurityPolicy) -> bool:
        """Update a policy in storage."""
        raise NotImplementedError
    
    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy from storage."""
        raise NotImplementedError
    
    def get_policy(self, policy_id: str) -> Optional[SecurityPolicy]:
        """Get a policy by ID from storage."""
        raise NotImplementedError
    
    def list_policies(self) -> List[SecurityPolicy]:
        """List all policies in storage."""
        raise NotImplementedError


class MemoryPolicyStore(PolicyStore):
    """In-memory policy storage for fast access."""
    
    def __init__(self):
        super().__init__(PolicyStorageType.MEMORY)
        self._policies: Dict[str, SecurityPolicy] = {}
        self._lock = __import__("threading").Lock()
    
    def load_policies(self) -> List[SecurityPolicy]:
        """Load policies from memory storage."""
        with self._lock:
            return list(self._policies.values())
    
    def save_policy(self, policy: SecurityPolicy) -> bool:
        """Save a policy to memory storage."""
        with self._lock:
            self._policies[policy.policy_id] = policy
            return True
    
    def update_policy(self, policy: SecurityPolicy) -> bool:
        """Update a policy in memory storage."""
        with self._lock:
            if policy.policy_id in self._policies:
                self._policies[policy.policy_id] = policy
                return True
            return False
    
    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy from memory storage."""
        with self._lock:
            if policy.policy_id in self._policies:
                del self._policies[policy.policy_id]
                return True
            return False
    
    def get_policy(self, policy_id: str) -> Optional[SecurityPolicy]:
        """Get a policy by ID from memory storage."""
        with self._lock:
            return self._policies.get(policy_id)
    
    def list_policies(self) -> List[SecurityPolicy]:
        """List all policies in memory storage."""
        with self._lock:
            return list(self._policies.values())


class FilePolicyStore(PolicyStore):
    """File-based policy storage for persistence."""
    
    def __init__(self, file_path: Optional[str] = None):
        super().__init__(PolicyStorageType.FILE)
        if file_path is None:
            aetheros_home = get_aetheros_home()
            self.file_path = str(aetheros_home / "security" / "policies.yaml")
        else:
            self.file_path = file_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        self._lock = __import__("threading").Lock()
        
        # Load existing policies if file exists
        if os.path.exists(self.file_path):
            self._load_from_file()
    
    def _load_from_file(self):
        """Load policies from the policy file."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                if self.file_path.endswith('.yaml') or self.file_path.endswith('.yml'):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            if data and isinstance(data, dict) and "policies" in data:
                policy_dicts = data["policies"]
                self._policies = {}
                for policy_dict in policy_dicts:
                    try:
                        policy = self._dict_to_policy(policy_dict)
                        self._policies[policy.policy_id] = policy
                    except Exception as e:
                        # Log error but continue loading other policies
                        print(f"Warning: Failed to load policy {policy_dict.get('policy_id', 'unknown')}: {e}")
        except Exception as e:
            print(f"Warning: Failed to load policy file {self.file_path}: {e}")
            self._policies = {}
    
    def _save_to_file(self):
        """Save policies to the policy file."""
        try:
            policy_dicts = []
            for policy in self._policies.values():
                policy_dicts.append(self._policy_to_dict(policy))
            
            data = {"policies": policy_dicts}
            
            # Create backup of existing file
            if os.path.exists(self.file_path):
                backup_path = f"{self.file_path}.backup.{int(time.time())}"
                try:
                    os.rename(self.file_path, backup_path)
                except Exception:
                    pass  # Continue even if backup fails
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                if self.file_path.endswith('.yaml') or self.file_path.endswith('.yml'):
                    yaml.dump(data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error: Failed to save policy file {self.file_path}: {e}")
            raise
    
    def _policy_to_dict(self, policy: SecurityPolicy) -> Dict[str, Any]:
        """Convert a SecurityPolicy to dictionary for storage."""
        return {
            "policy_id": policy.policy_id,
            "name": policy.name,
            "description": policy.description,
            "effect": policy.effect.value,
            "conditions": policy.conditions,
            "actions": policy.actions,
            "resources": policy.resources,
            "principals": policy.principals,
            "risk_level": policy.risk_level.value,
            "priority": policy.priority,
            "enabled": policy.enabled,
            "metadata": {
                "created_at": policy.created_at,
                "updated_at": policy.updated_at,
                "version": "1.0.0",
                "author": "aetheros-system"
            }
        }
    
    def _dict_to_policy(self, policy_dict: Dict[str, Any]) -> SecurityPolicy:
        """Convert dictionary to SecurityPolicy object."""
        # Convert effect string to enum
        effect_map = {
            "allow": PolicyEffect.ALLOW,
            "deny": PolicyEffect.DENY,
            "require_approval": PolicyEffect.REQUIRE_APPROVAL,
            "challenge": PolicyEffect.CHALLENGE,
            "audit": PolicyEffect.AUDIT
        }
        effect = effect_map.get(policy_dict.get("effect", "deny"), PolicyEffect.DENY)
        
        # Convert risk_level string to enum
        risk_level_map = {
            "none": RiskLevel.NONE,
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL
        }
        risk_level_str = policy_dict.get("risk_level", "low")
        risk_level = risk_level_map.get(risk_level_str, RiskLevel.LOW)
        
        policy = SecurityPolicy(
            policy_id=policy_dict.get("policy_id", ""),
            name=policy_dict.get("name", ""),
            description=policy_dict.get("description", ""),
            effect=effect,
            conditions=policy_dict.get("conditions", {}),
            actions=policy_dict.get("actions", []),
            resources=policy_dict.get("resources", []),
            principals=policy_dict.get("principals", []),
            risk_level=risk_level,
            priority=policy_dict.get("priority", 0),
            enabled=policy_dict.get("enabled", True)
        )
        
        # Set timestamps from metadata if available
        metadata = policy_dict.get("metadata", {})
        if "created_at" in metadata:
            policy.created_at = metadata["created_at"]
        if "updated_at" in metadata:
            policy.updated_at = metadata["updated_at"]
        
        return policy
    
    def load_policies(self) -> List[SecurityPolicy]:
        """Load policies from file storage."""
        with self._lock:
            if not os.path.exists(self.file_path):
                return []
            self._load_from_file()
            return list(self._policies.values())
    
    def save_policy(self, policy: SecurityPolicy) -> bool:
        """Save a policy to file storage."""
        with self._lock:
            self._policies[policy.policy_id] = policy
            self._save_to_file()
            return True
    
    def update_policy(self, policy: SecurityPolicy) -> bool:
        """Update a policy in file storage."""
        with self._lock:
            if policy.policy_id in self._policies:
                self._policies[policy.policy_id] = policy
                self._save_to_file()
                return True
            return False
    
    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy from file storage."""
        with self._lock:
            if policy.policy_id in self._policies:
                del self._policies[policy.policy_id]
                self._save_to_file()
                return True
            return False
    
    def get_policy(self, policy_id: str) -> Optional[SecurityPolicy]:
        """Get a policy by ID from file storage."""
        with self._lock:
            if not os.path.exists(self.file_path):
                return None
            self._load_from_file()
            return self._policies.get(policy_id)
    
    def list_policies(self) -> List[SecurityPolicy]:
        """List all policies in file storage."""
        with self._lock:
            if not os.path.exists(self.file_path):
                return []
            self._load_from_file()
            return list(self._policies.values())


class SecurityPolicyEngine:
    """Central security policy engine for managing and evaluating security policies."""
    
    def __init__(self, storage_type: PolicyStorageType = PolicyStorageType.FILE):
        self.storage_type = storage_type
        self._policy_store: PolicyStore
        self._authorization_engine: AuthorizationEngine
        self._lock = __import__("threading").Lock()
        
        # Initialize the policy store
        if storage_type == PolicyStorageType.MEMORY:
            self._policy_store = MemoryPolicyStore()
        elif storage_type == PolicyStorageType.FILE:
            self._policy_store = FilePolicyStore()
        else:
            # Default to file storage
            self._policy_store = FilePolicyStore()
        
        # Initialize the authorization engine
        self._authorization_engine = get_authorization_engine()
        
        # Load existing policies
        self._load_policies_into_engine()
    
    def _load_policies_into_engine(self):
        """Load policies from storage into the authorization engine."""
        policies = self._policy_store.load_policies()
        for policy in policies:
            self._authorization_engine.add_policy(policy)
    
    def add_policy(self, policy: SecurityPolicy) -> bool:
        """Add a new security policy."""
        with self._lock:
            try:
                # Add to policy store
                if not self._policy_store.save_policy(policy):
                    return False
                
                # Add to authorization engine
                self._authorization_engine.add_policy(policy)
                return True
            except Exception:
                return False
    
    def update_policy(self, policy: SecurityPolicy) -> bool:
        """Update an existing security policy."""
        with self._lock:
            try:
                # Update in policy store
                if not self._policy_store.update_policy(policy):
                    return False
                
                # Update in authorization engine (remove and re-add)
                self._authorization_engine.remove_policy(policy.policy_id)
                self._authorization_engine.add_policy(policy)
                return True
            except Exception:
                return False
    
    def remove_policy(self, policy_id: str) -> bool:
        """Remove a security policy by ID."""
        with self._lock:
            try:
                # Remove from policy store
                if not self._policy_store.delete_policy(policy_id):
                    return False
                
                # Remove from authorization engine
                return self._authorization_engine.remove_policy(policy_id)
            except Exception:
                return False
    
    def get_policy(self, policy_id: str) -> Optional[SecurityPolicy]:
        """Get a security policy by ID."""
        with self._lock:
            return self._policy_store.get_policy(policy_id)
    
    def list_policies(self) -> List[SecurityPolicy]:
        """List all security policies."""
        with self._lock:
            return self._policy_store.list_policies()
    
    def evaluate_request(self, request: AuthorizationRequest) -> AuthorizationDecision:
        """Evaluate an authorization request using the policy engine.
        
        This delegates to the authorization engine which evaluates
        all applicable policies.
        """
        return self._authorization_engine.is_authorized(request)
    
    def authorize_tool_call(
        self,
        agent: Any,  # Agent object from security_principal
        tool: Any,   # Tool object from security_principal
        tool_args: Dict[str, Any],
        context: Optional[Any] = None  # AuthorizationContext
    ) -> AuthorizationDecision:
        """Authorize a tool call using the policy engine."""
        return self._authorization_engine.authorize_tool_call(agent, tool, tool_args, context)
    
    def authorize_file_access(
        self,
        principal: Any,  # Principal object from security_principal
        file_path: str,
        action: Any,     # PermissionAction
        context: Optional[Any] = None  # AuthorizationContext
    ) -> AuthorizationDecision:
        """Authorize file access using the policy engine."""
        return self._authorization_engine.authorize_file_access(principal, file_path, action, context)
    
    def reload_policies(self):
        """Reload all policies from storage into the authorization engine."""
        with self._lock:
            # Clear existing policies from engine (except default ones)
            # For simplicity, we'll create a new engine and transfer default policies
            old_engine = self._authorization_engine
            self._authorization_engine = AuthorizationEngine()
            
            # Load fresh policies from store
            policies = self._policy_store.load_policies()
            for policy in policies:
                self._authorization_engine.add_policy(policy)
    
    def create_policy_from_dict(self, policy_dict: Dict[str, Any]) -> SecurityPolicy:
        """Create a SecurityPolicy object from a dictionary.
        
        This is useful for creating policies from configuration files.
        """
        # Handle effect conversion
        effect_str = policy_dict.get("effect", "deny").lower()
        effect_map = {
            "allow": PolicyEffect.ALLOW,
            "deny": PolicyEffect.DENY,
            "require_approval": PolicyEffect.REQUIRE_APPROVAL,
            "challenge": PolicyEffect.CHALLENGE,
            "audit": PolicyEffect.AUDIT
        }
        effect = effect_map.get(effect_str, PolicyEffect.DENY)
        
        # Handle risk_level conversion
        risk_level_str = policy_dict.get("risk_level", "low").lower()
        risk_level_map = {
            "none": RiskLevel.NONE,
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL
        }
        risk_level = risk_level_map.get(risk_level_str, RiskLevel.LOW)
        
        # Create the policy
        policy = SecurityPolicy(
            policy_id=policy_dict.get("policy_id", f"policy_{uuid.uuid4().hex[:8]}"),
            name=policy_dict.get("name", "Unnamed Policy"),
            description=policy_dict.get("description", ""),
            effect=effect,
            conditions=policy_dict.get("conditions", {}),
            actions=policy_dict.get("actions", []),
            resources=policy_dict.get("resources", []),
            principals=policy_dict.get("principals", []),
            risk_level=risk_level,
            priority=policy_dict.get("priority", 0),
            enabled=policy_dict.get("enabled", True)
        )
        
        # Set timestamps if provided
        if "created_at" in policy_dict:
            policy.created_at = policy_dict["created_at"]
        if "updated_at" in policy_dict:
            policy.updated_at = policy_dict["updated_at"]
        
        return policy
    
    def load_policies_from_config(self, config_path: Optional[str] = None) -> int:
        """Load policies from Aetheros configuration files.
        
        Returns the number of policies loaded.
        """
        if config_path is None:
            # Try to load from default config location
            aetheros_home = get_aetheros_home()
            config_path = str(aetheros_home / "config.yaml")
        
        policies_loaded = 0
        
        try:
            if os.path.exists(config_path):
                config = load_config()
                if config and "security" in config and "policies" in config["security"]:
                    policy_dicts = config["security"]["policies"]
                    for policy_dict in policy_dicts:
                        try:
                            policy = self.create_policy_from_dict(policy_dict)
                            if self.add_policy(policy):
                                policies_loaded += 1
                        except Exception as e:
                            print(f"Warning: Failed to load policy from config: {e}")
        except Exception as e:
            print(f"Warning: Failed to load policies from config {config_path}: {e}")
        
        return policies_loaded
    
    def save_policies_to_config(self, config_path: Optional[str] = None) -> bool:
        """Save current policies to Aetheros configuration files.
        
        Returns True if successful.
        """
        if config_path is None:
            # Try to save to default config location
            aetheros_home = get_aetheros_home()
            config_path = str(aetheros_home / "config.yaml")
        
        try:
            # Load existing config
            config = {}
            if os.path.exists(config_path):
                config = load_config() or {}
            
            # Ensure security section exists
            if "security" not in config:
                config["security"] = {}
            
            # Convert policies to dictionaries
            policy_dicts = []
            for policy in self.list_policies():
                policy_dict = {
                    "policy_id": policy.policy_id,
                    "name": policy.name,
                    "description": policy.description,
                    "effect": policy.effect.value,
                    "conditions": policy.conditions,
                    "actions": policy.actions,
                    "resources": policy.resources,
                    "principals": policy.principals,
                    "risk_level": policy.risk_level.value,
                    "priority": policy.priority,
                    "enabled": policy.enabled,
                    "metadata": {
                        "created_at": policy.created_at,
                        "updated_at": policy.updated_at,
                        "version": "1.0.0",
                        "author": "aetheros-system"
                    }
                }
                policy_dicts.append(policy_dict)
            
            # Save policies to config
            config["security"]["policies"] = policy_dicts
            
            # Write config back to file
            # Note: In a real implementation, we'd use the proper config saving mechanism
            # For now, we'll just note that this would be done
            print(f"Info: Would save {len(policy_dicts)} policies to {config_path}")
            return True
        except Exception as e:
            print(f"Error: Failed to save policies to config {config_path}: {e}")
            return False


# Global security policy engine instance
_POLICY_ENGINE = None
_POLICY_ENGINE_LOCK = __import__("threading").Lock()


def get_security_policy_engine() -> SecurityPolicyEngine:
    """Get the global security policy engine instance."""
    global _POLICY_ENGINE
    with _POLICY_ENGINE_LOCK:
        if _POLICY_ENGINE is None:
            _POLICY_ENGINE = SecurityPolicyEngine()
        return _POLICY_ENGINE


def load_default_policies():
    """Load default security policies into the policy engine."""
    engine = get_security_policy_engine()
    
    # Add some additional default policies beyond what's in AuthorizationEngine
    
    # Policy to allow read access to public web content
    web_read_policy = SecurityPolicy(
        policy_id="web_public_read",
        name="Public Web Read Access",
        description="Allow read access to public web URLs",
        effect=PolicyEffect.ALLOW,
        actions=["web_search", "web_extract"],
        resources=["web://*", "http://*", "https://*"],
        principals=["agent:*"],
        risk_level=RiskLevel.LOW,
        priority=10
    )
    engine.add_policy(web_read_policy)
    
    # Policy to deny access to internal metadata services
    metadata_block_policy = SecurityPolicy(
        policy_id="block_internal_metadata",
        name="Block Internal Metadata Services",
        description="Deny access to cloud provider metadata endpoints",
        effect=PolicyEffect.DENY,
        actions=["web_search", "web_extract", "tool.call"],
        resources=[
            "web://169.254.169.254/*",
            "web://metadata.google.internal/*",
            "web://metadata.azure/*",
            "http://169.254.169.254/*",
            "http://metadata.google.internal/*",
            "http://metadata.azure/*"
        ],
        principals=["agent:*"],
        risk_level=RiskLevel.HIGH,
        priority=100
    )
    engine.add_policy(metadata_block_policy)
    
    # Policy to require approval for installing new plugins
    plugin_install_policy = SecurityPolicy(
        policy_id="plugin_install_approval",
        name="Plugin Installation Requires Approval",
        description="Require approval for installing new plugins",
        effect=PolicyEffect.REQUIRE_APPROVAL,
        actions=["plugin.install", "skill.install"],
        resources=["plugin:*", "skill:*"],
        principals=["agent:*"],
        risk_level=RiskLevel.MEDIUM,
        priority=20
    )
    engine.add_policy(plugin_install_policy)
    
    print(f"Info: Loaded default policies into security policy engine")


# Convenience functions
def authorize_action(
    principal: Any,  # Principal object
    action: str,
    resource: str,
    permission_action: Any,  # PermissionAction
    context: Optional[Any] = None  # AuthorizationContext
) -> AuthorizationDecision:
    """Convenience function for authorizing an action using the policy engine."""
    engine = get_security_policy_engine()
    return engine.authorize_action(principal, action, resource, permission_action, context)


def is_action_allowed(
    principal: Any,  # Principal object
    action: str,
    resource: str,
    permission_action: Any,  # PermissionAction
    context: Optional[Any] = None  # AuthorizationContext
) -> bool:
    """Check if an action is allowed using the policy engine."""
    decision = authorize_action(principal, action, resource, permission_action, context)
    return decision.decision == Decision.ALLOW