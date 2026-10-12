"""
Permission Manager — centralized permission checking for the AetherOS Kernel.

Provides a unified permission system used by:
  - Tools (file access, shell execution, browser)
  - Plugins
  - Filesystem operations
  - MCP servers
  - Network access
  - Future mobile support

Integrates with the existing file_safety.py and tool approval systems.
"""

from __future__ import annotations

import enum
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class PermissionAction(enum.Enum):
    """Actions that can be permission-checked."""
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EXECUTE_COMMAND = "execute_command"
    EXECUTE_CODE = "execute_code"
    BROWSER_NAVIGATE = "browser_navigate"
    NETWORK_REQUEST = "network_request"
    SEND_MESSAGE = "send_message"
    ACCESS_ENV = "access_env"
    ACCESS_CREDENTIALS = "access_credentials"
    MODIFY_CONFIG = "modify_config"
    INSTALL_PACKAGE = "install_package"
    MANAGE_PLUGIN = "manage_plugin"
    MANAGE_SKILL = "manage_skill"
    MANAGE_CRON = "manage_cron"


class PermissionLevel(enum.IntEnum):
    """Permission levels from most to least restrictive."""
    DENY = 0       # Always denied
    CONFIRM = 10   # Requires user confirmation
    ALLOW_WARN = 20  # Allowed but with a warning
    ALLOW = 30     # Always allowed
    ELEVATED = 40  # Allowed with elevated privileges


@dataclass
class PermissionCheck:
    """Result of a permission check.

    Attributes:
        allowed: Whether the action is permitted
        level: Permission level that was applied
        reason: Human-readable explanation
        require_approval: Whether user approval is needed
        warnings: List of warning messages
        rule: Name of the matching rule
    """
    allowed: bool = True
    level: PermissionLevel = PermissionLevel.ALLOW
    reason: str = ""
    require_approval: bool = False
    warnings: List[str] = field(default_factory=list)
    rule: str = "default"


@dataclass
class PermissionRule:
    """A permission rule definition.

    Attributes:
        name: Rule name
        action: The action this rule applies to
        level: Permission level
        condition: Optional callable(context) -> bool predicate
        description: Human-readable description
        target_pattern: Optional glob-style target pattern
    """
    name: str
    action: PermissionAction
    level: PermissionLevel = PermissionLevel.ALLOW
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    description: str = ""
    target_pattern: str = "*"


class PermissionManager:
    """Centralized permission manager.

    Provides permission checking that integrates with existing Aetheros
    security mechanisms (file_safety, tool approval, guardrails).

    Usage:
        pm = PermissionManager(event_bus)

        # Check a permission
        result = pm.check(PermissionAction.WRITE_FILE, {
            "path": "/etc/passwd",
        })

        # Register a custom rule
        pm.add_rule(PermissionRule(
            name="block-etc-write",
            action=PermissionAction.WRITE_FILE,
            level=PermissionLevel.DENY,
            target_pattern="/etc/**",
        ))
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._rules: Dict[PermissionAction, List[PermissionRule]] = {
            action: [] for action in PermissionAction
        }
        self._default_levels: Dict[PermissionAction, PermissionLevel] = {
            action: PermissionLevel.ALLOW for action in PermissionAction
        }
        # Track pending approvals
        self._approval_callbacks: Dict[str, Callable[[bool], None]] = {}

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, rule: PermissionRule) -> None:
        """Add a permission rule.

        Rules are evaluated in order; the first matching rule wins.
        """
        with self._lock:
            self._rules[rule.action].append(rule)
            self._rules[rule.action].sort(
                key=lambda r: r.level.value,
            )
        logger.debug(
            "Permissions: added rule '%s' for %s (%s)",
            rule.name, rule.action.value, rule.level.name,
        )

    def add_rules(self, rules: List[PermissionRule]) -> None:
        """Add multiple permission rules at once."""
        for rule in rules:
            self.add_rule(rule)

    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name."""
        with self._lock:
            for action, rules in self._rules.items():
                before = len(rules)
                rules[:] = [r for r in rules if r.name != name]
                if len(rules) < before:
                    return True
        return False

    def set_default_level(self, action: PermissionAction,
                          level: PermissionLevel) -> None:
        """Set the default permission level for an action."""
        with self._lock:
            self._default_levels[action] = level

    def set_default_levels(self, defaults: Dict[PermissionAction,
                                                 PermissionLevel]) -> None:
        """Set multiple default permission levels at once."""
        with self._lock:
            self._default_levels.update(defaults)

    # ------------------------------------------------------------------
    # Permission checking
    # ------------------------------------------------------------------

    def check(self, action: PermissionAction,
              context: Dict[str, Any] = None) -> PermissionCheck:
        """Check if an action is permitted given the context.

        Args:
            action: The action to check
            context: Context dict with relevant information (path, target, etc.)

        Returns:
            PermissionCheck with the result
        """
        context = context or {}

        # Evaluate rules in order
        with self._lock:
            rules = list(self._rules.get(action, []))

        for rule in rules:
            if not self._target_matches(rule.target_pattern,
                                        context.get("target", "")):
                continue
            if rule.condition and not rule.condition(context):
                continue

            # Rule matched
            if rule.level == PermissionLevel.DENY:
                return PermissionCheck(
                    allowed=False,
                    level=PermissionLevel.DENY,
                    reason=rule.description or f"Denied by rule '{rule.name}'",
                    rule=rule.name,
                )

            if rule.level == PermissionLevel.CONFIRM:
                return PermissionCheck(
                    allowed=True,
                    level=PermissionLevel.CONFIRM,
                    reason=rule.description or f"Requires confirmation: {rule.name}",
                    require_approval=True,
                    rule=rule.name,
                )

            if rule.level == PermissionLevel.ALLOW_WARN:
                return PermissionCheck(
                    allowed=True,
                    level=PermissionLevel.ALLOW_WARN,
                    reason=rule.description or f"Allowed with warning: {rule.name}",
                    warnings=[f"Action permitted by rule '{rule.name}'"],
                    rule=rule.name,
                )

            if rule.level == PermissionLevel.ALLOW:
                return PermissionCheck(
                    allowed=True,
                    level=PermissionLevel.ALLOW,
                    reason=f"Allowed by rule '{rule.name}'",
                    rule=rule.name,
                )

        # No rule matched — use default
        default_level = self._default_levels.get(action, PermissionLevel.ALLOW)
        return PermissionCheck(
            allowed=default_level >= PermissionLevel.ALLOW,
            level=default_level,
            reason=f"Default permission: {default_level.name}",
            require_approval=(default_level == PermissionLevel.CONFIRM),
            rule="default",
        )

    def check_or_raise(self, action: PermissionAction,
                       context: Dict[str, Any] = None) -> None:
        """Check permission and raise PermissionError if denied."""
        result = self.check(action, context)
        if not result.allowed:
            raise PermissionError(
                f"Permission denied: {action.value} - {result.reason}"
            )

    # ------------------------------------------------------------------
    # Integration with existing systems
    # ------------------------------------------------------------------

    def integrate_file_safety(self) -> None:
        """Add rules that wrap the existing file_safety module."""
        try:
            from agent.file_safety import is_write_denied, get_read_block_error

            # Deny writes to blocked paths
            self.add_rule(PermissionRule(
                name="file-safety-deny-path",
                action=PermissionAction.WRITE_FILE,
                level=PermissionLevel.DENY,
                description="Blocked by file safety module",
                condition=lambda ctx: (
                    is_write_denied(ctx.get("path", ""))
                    if ctx.get("path") else False
                ),
            ))

            # Deny reads to blocked paths
            self.add_rule(PermissionRule(
                name="file-safety-deny-read",
                action=PermissionAction.READ_FILE,
                level=PermissionLevel.DENY,
                description="Blocked by file safety module",
                condition=lambda ctx: bool(
                    get_read_block_error(ctx.get("path", ""))
                    if ctx.get("path") else None
                ),
            ))

            logger.info("Permissions: integrated file_safety rules")
        except Exception as exc:
            logger.warning("Permissions: file_safety integration failed: %s", exc)

    # ------------------------------------------------------------------
    # Target pattern matching (simple glob)
    # ------------------------------------------------------------------

    @staticmethod
    def _target_matches(pattern: str, target: str) -> bool:
        """Simple glob-style target matching."""
        if pattern == "*" or pattern == "**":
            return True
        if not target:
            return pattern == "*"

        # Convert simple glob to regex
        import re as _re
        regex = _re.escape(pattern).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
        return bool(_re.match(regex, target))

    # ------------------------------------------------------------------
    # Approval workflow
    # ------------------------------------------------------------------

    def request_approval(self, action: PermissionAction,
                         context: Dict[str, Any],
                         approval_id: str = None) -> str:
        """Request user approval for an action.

        Returns the approval ID that can be used to resolve the request.
        """
        import uuid as _uuid
        aid = approval_id or _uuid.uuid4().hex[:12]

        if self._event_bus:
            self._event_bus.emit("permission.approval_requested", {
                "approval_id": aid,
                "action": action.value,
                "context": context,
            })

        return aid

    def resolve_approval(self, approval_id: str, granted: bool) -> bool:
        """Resolve a pending approval request.

        Returns True if the approval was found and resolved.
        """
        callback = self._approval_callbacks.pop(approval_id, None)
        if callback:
            callback(granted)
            if self._event_bus:
                self._event_bus.emit("permission.approval_resolved", {
                    "approval_id": approval_id,
                    "granted": granted,
                })
            return True
        return False

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def list_rules(self, action: PermissionAction = None) -> List[Dict[str, Any]]:
        """List all registered permission rules."""
        with self._lock:
            if action:
                rules = [
                    {"action": action.value, "name": r.name,
                     "level": r.level.name, "description": r.description}
                    for r in self._rules.get(action, [])
                ]
            else:
                rules = [
                    {"action": a.value, "name": r.name,
                     "level": r.level.name, "description": r.description}
                    for a, rl in self._rules.items()
                    for r in rl
                ]
        return rules

    def get_stats(self) -> Dict[str, Any]:
        """Return permission manager statistics."""
        total_rules = sum(len(rules) for rules in self._rules.values())
        return {
            "total_rules": total_rules,
            "actions_with_rules": sum(
                1 for rules in self._rules.values() if rules
            ),
            "pending_approvals": len(self._approval_callbacks),
        }
