"""Permission System.

Every tool declares its risk level and permissions required.
The permission system evaluates access based on:
- Risk level (Read, Write, Execute, System, Network, Credential, Admin)
- User approval requirements
- Context-based authorization
- Granular allow/deny rules
"""

from __future__ import annotations

import enum
import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from tool_runtime.interface import ToolMetadata, ToolRiskLevel

logger = logging.getLogger(__name__)


class RiskLevel(enum.IntEnum):
    READ = 1
    WRITE = 2
    EXECUTE = 3
    NETWORK = 4
    SYSTEM = 5
    CREDENTIAL = 6
    ADMIN = 7


RISK_LEVEL_MAP = {
    ToolRiskLevel.READ: RiskLevel.READ,
    ToolRiskLevel.WRITE: RiskLevel.WRITE,
    ToolRiskLevel.EXECUTE: RiskLevel.EXECUTE,
    ToolRiskLevel.NETWORK: RiskLevel.NETWORK,
    ToolRiskLevel.SYSTEM: RiskLevel.SYSTEM,
    ToolRiskLevel.CREDENTIAL: RiskLevel.CREDENTIAL,
    ToolRiskLevel.ADMIN: RiskLevel.ADMIN,
}


@dataclass
class PermissionResult:
    allowed: bool
    reason: Optional[str] = None
    requires_approval: bool = False
    approval_request_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def grant(cls, reason: Optional[str] = None) -> "PermissionResult":
        return cls(allowed=True, reason=reason)

    @classmethod
    def deny(cls, reason: str) -> "PermissionResult":
        return cls(allowed=False, reason=reason)

    @classmethod
    def pending_approval(cls, request_id: str, reason: Optional[str] = None) -> "PermissionResult":
        return cls(
            allowed=False,
            reason=reason or "Pending user approval",
            requires_approval=True,
            approval_request_id=request_id,
        )


@dataclass
class PermissionRule:
    """A single permission rule."""
    effect: str  # "allow" or "deny"
    tool_pattern: str  # glob-style: "file.*", "terminal*"
    risk_level_max: Optional[RiskLevel] = None
    contexts: List[str] = field(default_factory=lambda: ["*"])
    reason: Optional[str] = None


class PermissionSystem:
    """Manages tool execution permissions with fine-grained rules.

    Features:
    - Risk-level-based access control
    - Tool name pattern matching
    - Context-aware rules
    - Approval workflow for high-risk operations
    - Granular allow/deny rules
    """

    def __init__(self):
        self._rules: List[PermissionRule] = []
        self._lock = threading.RLock()
        self._approval_handlers: List[Callable] = []
        self._approval_cache: Dict[str, bool] = {}
        self._max_risk_default = RiskLevel.EXECUTE
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        """Set up default security rules."""
        self.add_rule(PermissionRule(
            effect="allow",
            tool_pattern="*",
            risk_level_max=RiskLevel.READ,
            reason="Default allow for read operations",
        ))
        self.add_rule(PermissionRule(
            effect="allow",
            tool_pattern="*",
            risk_level_max=RiskLevel.WRITE,
            reason="Default allow for write with awareness",
        ))
        self.add_rule(PermissionRule(
            effect="allow",
            tool_pattern="*",
            risk_level_max=RiskLevel.EXECUTE,
            reason="Default allow for execution with approval",
        ))
        self.add_rule(PermissionRule(
            effect="deny",
            tool_pattern="credential*",
            reason="Credential access requires explicit approval",
        ))
        self.add_rule(PermissionRule(
            effect="deny",
            tool_pattern="admin*",
            reason="Admin operations require authorization",
        ))

    def add_rule(self, rule: PermissionRule) -> None:
        with self._lock:
            self._rules.append(rule)

    def remove_rule(self, tool_pattern: str) -> bool:
        with self._lock:
            before = len(self._rules)
            self._rules = [r for r in self._rules if r.tool_pattern != tool_pattern]
            return len(self._rules) < before

    def set_max_risk_level(self, level: RiskLevel) -> None:
        self._max_risk_default = level

    def check(
        self,
        tool_name: str,
        metadata: ToolMetadata,
        context: Dict[str, Any],
    ) -> PermissionResult:
        """Check if a tool execution is permitted."""
        risk_level = RISK_LEVEL_MAP.get(metadata.risk_level, RiskLevel.READ)

        with self._lock:
            for rule in self._rules:
                if self._match_pattern(tool_name, rule.tool_pattern):
                    if rule.risk_level_max is not None and risk_level > rule.risk_level_max:
                        continue
                    if rule.effect == "deny":
                        return PermissionResult.deny(rule.reason or f"Denied by rule: {rule.tool_pattern}")
                    elif rule.effect == "allow":
                        pass

        if risk_level > self._max_risk_default:
            return PermissionResult.pending_approval(
                request_id=f"approval_{tool_name}",
                reason=f"Risk level {risk_level.name} requires approval",
            )

        if metadata.requires_approval:
            return PermissionResult.pending_approval(
                request_id=f"approval_{tool_name}",
                reason=f"Tool {tool_name} requires user approval",
            )

        return PermissionResult.grant()

    def _match_pattern(self, name: str, pattern: str) -> bool:
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return name.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return name.endswith(pattern[1:])
        return name == pattern

    def register_approval_handler(self, handler: Callable) -> None:
        self._approval_handlers.append(handler)

    def request_approval(self, request_id: str, tool_name: str, reason: str) -> bool:
        for handler in self._approval_handlers:
            try:
                result = handler(request_id, tool_name, reason)
                if result is not None:
                    with self._lock:
                        self._approval_cache[request_id] = bool(result)
                    return bool(result)
            except Exception as e:
                logger.error("Approval handler error: %s", e)
        return False

    def get_rules(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "effect": r.effect,
                    "tool_pattern": r.tool_pattern,
                    "risk_level_max": r.risk_level_max.name if r.risk_level_max else None,
                    "contexts": r.contexts,
                    "reason": r.reason,
                }
                for r in self._rules
            ]

    def get_status(self) -> Dict[str, Any]:
        return {
            "max_risk_default": self._max_risk_default.name,
            "rules_count": len(self._rules),
            "approval_cache_size": len(self._approval_cache),
        }


# Global singleton
_permission_system_instance: Optional[PermissionSystem] = None


def get_permission_system() -> PermissionSystem:
    global _permission_system_instance
    if _permission_system_instance is None:
        _permission_system_instance = PermissionSystem()
    return _permission_system_instance
