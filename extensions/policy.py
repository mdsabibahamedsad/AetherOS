"""
Extension Security Policy
=========================

Defines and enforces security policies for extensions. Policies control
what extensions can do, what permissions they need, and how they are
audited.

Supports:
    - Allow/deny rules for specific extensions
    - Global default policies
    - Per-extension overrides
    - Signed extension requirements
    - Audit logging requirements
"""

from __future__ import annotations

import enum
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from sdk.permissions import Permission, PermissionSet

logger = logging.getLogger(__name__)


class PolicyAction(enum.Enum):
    """Action to take when a policy rule matches."""
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    REQUIRE_APPROVAL = "require_approval"
    AUDIT = "audit"


@dataclass
class PolicyRule:
    """A single policy rule."""
    action: PolicyAction
    description: str = ""
    extensions: Optional[List[str]] = None      # Apply to specific extensions
    permissions: Optional[List[str]] = None      # Match on permissions
    capabilities: Optional[List[str]] = None     # Match on capabilities
    signed_only: bool = False                    # Only apply to signed extensions
    priority: int = 0                            # Higher priority wins

    def matches(self, extension: str, permission: Optional[str] = None) -> bool:
        """Check if this rule matches an extension/permission."""
        if self.extensions and extension not in self.extensions:
            return False
        if self.permissions and permission and permission not in self.permissions:
            return False
        return True


@dataclass
class ExtensionPolicy:
    """Complete policy configuration for extensions."""
    default_action: PolicyAction = PolicyAction.ALLOW
    rules: List[PolicyRule] = field(default_factory=list)
    require_signing: bool = False
    audit_all_permissions: bool = False
    allow_undeclared_permissions: bool = False
    max_per_extensions: int = -1  # -1 = unlimited


# Default policy — permissive for trusted extensions
DEFAULT_POLICY = ExtensionPolicy(
    default_action=PolicyAction.ALLOW,
    rules=[],
    require_signing=False,
    audit_all_permissions=False,
    allow_undeclared_permissions=True,
)


class PolicyEngine:
    """Engine for evaluating and enforcing extension policies.

    Usage::

        engine = PolicyEngine()
        engine.set_policy("my-plugin", custom_policy)
        result = engine.evaluate("my-plugin", "filesystem:read")
    """

    def __init__(self) -> None:
        self._policies: Dict[str, ExtensionPolicy] = {}
        self._global_policy: ExtensionPolicy = DEFAULT_POLICY

    def set_global_policy(self, policy: ExtensionPolicy) -> None:
        """Set the global default policy."""
        self._global_policy = policy

    def set_policy(self, extension: str, policy: ExtensionPolicy) -> None:
        """Set a policy for a specific extension."""
        self._policies[extension] = policy

    def get_policy(self, extension: str) -> ExtensionPolicy:
        """Get the effective policy for an extension."""
        return self._policies.get(extension, self._global_policy)

    def evaluate(
        self,
        extension: str,
        permission: str,
        *,
        signed: bool = False,
    ) -> bool:
        """Evaluate whether a permission is allowed for an extension.

        Args:
            extension: Extension name.
            permission: Permission string (e.g. ``"filesystem:read"``).
            signed: Whether the extension is cryptographically signed.

        Returns:
            True if the action is allowed.
        """
        policy = self.get_policy(extension)

        # Check signing requirement
        if policy.require_signing and not signed:
            logger.warning("Extension '%s' blocked: signing required", extension)
            return False

        # Check per-extension limit
        if policy.max_per_extensions >= 0:
            try:
                from extensions.manager import get_extension_manager
                mgr = get_extension_manager()
                count = len(mgr.list_extensions())
                if count > policy.max_per_extensions:
                    logger.warning(
                        "Extension limit reached: %d/%d", count, policy.max_per_extensions
                    )
                    return False
            except Exception:
                pass

        # Evaluate rules
        for rule in sorted(policy.rules, key=lambda r: -r.priority):
            if rule.matches(extension, permission):
                if rule.action == PolicyAction.DENY:
                    logger.info("Policy DENY: %s/%s", extension, permission)
                    return False
                if rule.action == PolicyAction.ALLOW:
                    return True
                if rule.action == PolicyAction.AUDIT:
                    logger.info("Policy AUDIT: %s/%s", extension, permission)
                    # Audit then allow
                    continue

        # Default action
        if policy.default_action == PolicyAction.DENY:
            return False

        # Check undeclared permissions
        if not policy.allow_undeclared_permissions:
            perm = Permission(permission)
            try:
                from extensions.manager import get_extension_manager
                mgr = get_extension_manager()
                ext = mgr.get_extension(extension)
                if ext and perm.name not in (ext.manifest.permissions or []):
                    logger.warning(
                        "Extension '%s' using undeclared permission '%s'",
                        extension, permission,
                    )
                    if policy.audit_all_permissions:
                        return False
            except Exception:
                pass

        return True

    def audit_check(
        self,
        extension: str,
        permission: str,
        allowed: bool,
    ) -> None:
        """Log a permission check for audit trail."""
        if self.get_policy(extension).audit_all_permissions:
            logger.info("AUDIT: %s requested %s → allowed=%s", extension, permission, allowed)

    def load_from_config(self, config: Dict[str, Any]) -> None:
        """Load policy rules from a configuration dict.

        Expected format::

            {
                "extensions": {
                    "policies": {
                        "global": {
                            "default_action": "allow",
                            "require_signing": false
                        },
                        "overrides": {
                            "some-plugin": {
                                "default_action": "deny"
                            }
                        }
                    }
                }
            }
        """
        policies = config.get("extensions", {}).get("policies", {})
        global_cfg = policies.get("global", {})
        if global_cfg:
            action_str = global_cfg.get("default_action", "allow")
            action = PolicyAction(action_str)
            self.set_global_policy(ExtensionPolicy(
                default_action=action,
                require_signing=global_cfg.get("require_signing", False),
                audit_all_permissions=global_cfg.get("audit_all", False),
            ))

        overrides = policies.get("overrides", {})
        for ext_name, ext_cfg in overrides.items():
            action_str = ext_cfg.get("default_action", "")
            if action_str:
                action = PolicyAction(action_str)
                self._policies[ext_name] = ExtensionPolicy(default_action=action)


def load_policy_from_config(config: Dict[str, Any]) -> PolicyEngine:
    """Load a PolicyEngine from config."""
    engine = PolicyEngine()
    engine.load_from_config(config)
    return engine
