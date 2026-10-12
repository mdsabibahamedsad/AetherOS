"""Safety Engine.

Never execute destructive actions silently.
Always request approval for: delete, overwrite, format, shutdown, git push, credential changes.
Provides pattern-based detection of dangerous operations.
"""

from __future__ import annotations

import enum
import json
import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Pattern

from tool_runtime.interface import ToolMetadata, ToolRiskLevel

logger = logging.getLogger(__name__)


class SafetyVerdict(enum.Enum):
    SAFE = "safe"
    DESTRUCTIVE = "destructive"
    BLOCKED = "blocked"
    PENDING_APPROVAL = "pending_approval"


@dataclass
class SafetyCheck:
    result: SafetyVerdict
    reason: Optional[str] = None
    requires_approval: bool = False
    matched_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result.value,
            "reason": self.reason,
            "requires_approval": self.requires_approval,
            "matched_rules": self.matched_rules,
        }

    @classmethod
    def safe(cls) -> "SafetyCheck":
        return cls(result=SafetyVerdict.SAFE)

    @classmethod
    def destructive(cls, reason: str, rule: str = "") -> "SafetyCheck":
        return cls(
            result=SafetyVerdict.DESTRUCTIVE,
            reason=reason,
            requires_approval=True,
            matched_rules=[rule] if rule else [],
        )

    @classmethod
    def blocked(cls, reason: str) -> "SafetyCheck":
        return cls(result=SafetyVerdict.BLOCKED, reason=reason)


@dataclass
class DestructiveAction:
    """Describes a destructive action detected in params."""
    action_type: str
    target: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    safe_alternative: Optional[str] = None


class SafetyRule:
    """A safety rule that detects destructive patterns."""

    def __init__(
        self,
        name: str,
        description: str,
        pattern: Pattern,
        severity: str,
        param_key: Optional[str] = None,
        safe_alternative: Optional[str] = None,
        block: bool = False,
    ):
        self.name = name
        self.description = description
        self.pattern = pattern
        self.severity = severity
        self.param_key = param_key
        self.safe_alternative = safe_alternative
        self.block = block


class SafetyEngine:
    """Safety Engine for detecting and preventing destructive operations.

    Features:
    - Pattern-based destructive action detection
    - Risk-level gating
    - Required approval for high-risk operations
    - Action blocking for critical severity
    - Safe alternative suggestions
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._rules: List[SafetyRule] = []
        self._approval_callbacks: List[Callable] = []
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        self.add_rule(SafetyRule(
            name="file_delete",
            description="File or directory deletion",
            pattern=re.compile(r'rm\s+(-rf?\s+)?[/\\]?(?:[^/\\]+[/\\]?)*|delete|remove\s+file'),
            severity="high",
            safe_alternative="Use --dry-run or move to trash instead of permanent delete",
        ))
        self.add_rule(SafetyRule(
            name="file_overwrite",
            description="Overwriting existing files",
            pattern=re.compile(r'write|overwrite|replace\s+file'),
            severity="medium",
            safe_alternative="Verify content before overwriting",
        ))
        self.add_rule(SafetyRule(
            name="format_disk",
            description="Disk/volume formatting",
            pattern=re.compile(r'format|mkfs|fdisk|parted|dd\s+if='),
            severity="critical",
            block=True,
        ))
        self.add_rule(SafetyRule(
            name="shutdown_restart",
            description="System shutdown or restart",
            pattern=re.compile(r'shutdown|reboot|poweroff|halt|init\s+0|init\s+6'),
            severity="critical",
            block=True,
        ))
        self.add_rule(SafetyRule(
            name="git_push_force",
            description="Force push to git",
            pattern=re.compile(r'git\s+push\s+.*--force|git\s+push\s+-f'),
            severity="high",
            safe_alternative="Use `git push --force-with-lease` instead of `--force`",
        ))
        self.add_rule(SafetyRule(
            name="credential_change",
            description="Credential or password change",
            pattern=re.compile(r'password|credential|token|api_key|secret.*\s*=|chmod\s+777|passwd'),
            severity="critical",
            block=True,
        ))
        self.add_rule(SafetyRule(
            name="data_drop",
            description="Database table/schema drop",
            pattern=re.compile(r'drop\s+(table|database|schema|index|view)|truncate\s+table'),
            severity="critical",
            block=True,
        ))
        self.add_rule(SafetyRule(
            name="data_delete",
            description="Database row deletion without WHERE",
            pattern=re.compile(r'delete\s+from\s+\w+\s*(?:;|$|\s+--|\s+/\*)'),
            severity="high",
            safe_alternative="Always use a WHERE clause with DELETE",
        ))
        self.add_rule(SafetyRule(
            name="mass_rename_move",
            description="Bulk rename or move operations",
            pattern=re.compile(r'mv\s+.*\*|rename\s+.*\*|move\s+.*\*'),
            severity="medium",
        ))
        self.add_rule(SafetyRule(
            name="package_install",
            description="System package installation",
            pattern=re.compile(r'(apt|yum|dnf|pacman|brew)\s+install|pip\s+install|npm\s+install\s+-g'),
            severity="medium",
        ))

    def add_rule(self, rule: SafetyRule) -> None:
        with self._lock:
            self._rules.append(rule)

    def check(
        self,
        tool_name: str,
        params: Dict[str, Any],
        metadata: ToolMetadata,
    ) -> SafetyCheck:
        """Check tool execution against safety rules."""
        if metadata.risk_level in (ToolRiskLevel.ADMIN, ToolRiskLevel.CREDENTIAL):
            return SafetyCheck.destructive(
                f"Tool '{tool_name}' has {metadata.risk_level.value} risk level",
                rule="risk_level_gate",
            )

        matched = []
        params_str = json.dumps(params, default=str).lower()

        with self._lock:
            for rule in self._rules:
                if rule.pattern.search(params_str):
                    matched.append(rule)

        if not matched:
            return SafetyCheck.safe()

        destructive_matches = [m for m in matched if not m.block]
        blocked_matches = [m for m in matched if m.block]

        if blocked_matches:
            reasons = []
            for bm in blocked_matches:
                reasons.append(f"[BLOCKED] {bm.description}")
                logger.warning(
                    "Safety block on %s: %s (params: %s)",
                    tool_name, bm.description, params_str[:200],
                )
            return SafetyCheck.blocked("; ".join(reasons))

        if destructive_matches:
            reasons = []
            rules_triggered = []
            for dm in destructive_matches:
                reasons.append(dm.description)
                rules_triggered.append(dm.name)
            return SafetyCheck.destructive(
                reason="; ".join(reasons),
                rule=", ".join(rules_triggered),
            )

        return SafetyCheck.safe()

    def detect_destructive_actions(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> List[DestructiveAction]:
        """Scan parameters for destructive actions without blocking."""
        actions = []
        params_str = json.dumps(params, default=str).lower()

        with self._lock:
            for rule in self._rules:
                if rule.pattern.search(params_str):
                    actions.append(DestructiveAction(
                        action_type=rule.name,
                        target=params_str[:100],
                        severity=rule.severity,
                        description=rule.description,
                        safe_alternative=rule.safe_alternative,
                    ))

        return actions

    def get_rules_summary(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "name": r.name,
                    "description": r.description,
                    "severity": r.severity,
                    "block": r.block,
                    "safe_alternative": r.safe_alternative,
                }
                for r in self._rules
            ]


# Global singleton
_safety_engine_instance: Optional[SafetyEngine] = None


def get_safety_engine() -> SafetyEngine:
    global _safety_engine_instance
    if _safety_engine_instance is None:
        _safety_engine_instance = SafetyEngine()
    return _safety_engine_instance
