"""
Universal Computer Action Model (Master 15 Phases 1-2).

Single source of truth for all computer-use actions across:
  - Browser (navigate, click, type, form_fill, download, upload, etc.)
  - Desktop (click, type, drag, window/app mgmt, clipboard, OCR)
  - Terminal (execute, background, sudo, process control)
  - Vision (analyze, ocr, capture, understand)
  - Filesystem (read, write, patch, delete, search)

Every action carries metadata for risk classification, approval, verification, and audit.
"""

from __future__ import annotations

import enum
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from aetheros_constants import get_aetheros_home


class ActionDomain(enum.Enum):
    """High-level domain categorization."""

    BROWSER = "browser"
    DESKTOP = "desktop"
    TERMINAL = "terminal"
    VISION = "vision"
    FILESYSTEM = "filesystem"
    SYSTEM = "system"


class RiskTier(enum.Enum):
    """Unified risk tiers across all domains (Master 15 Phase 3, aligned with MASTER 7 action_guard)."""

    R0_INFORMATIONAL = 0  # read-only, no side effects
    R1_LOW = 1            # navigation, scroll, read, capture
    R2_MODERATE = 2       # type, click, execute command, write file
    R3_HIGH = 3           # form submit, download, delete file, terminal rm
    R4_CRITICAL = 4       # financial, credential change, privilege escalation, system config


class VerificationRequirement(enum.Enum):
    """Post-action verification requirement."""

    NONE = "none"                          # no verification needed
    STATE_MATCH = "state_match"            # verify expected state reached
    DOMAIN_CONFIRMATION = "domain_confirm" # verify destination domain
    IDEMPOTENCY_CHECK = "idempotency"      # verify action not duplicated
    INDEPENDENT_VERIFY = "independent"     # require separate verification agent


class ApprovalBinding(enum.Enum):
    """Approval context binding (Phase 57)."""

    TASK = "task"           # bound to specific task_id
    ACTION = "action"       # bound to specific action type
    TARGET = "target"       # bound to specific target (URL, file, window)
    SCOPE = "scope"         # bound to permission scope (project, user, system)


@dataclass
class ActionMetadata:
    """Complete metadata for any computer action (Master 15 Phase 2)."""

    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    task_id: str = ""
    timestamp: float = field(default_factory=time.time)
    domain: ActionDomain = ActionDomain.SYSTEM
    action_type: str = ""
    target: str = ""                    # URL, file path, window title, selector, command
    intent: str = ""                    # human-readable description
    risk_level: RiskTier = RiskTier.R0_INFORMATIONAL
    permission_scope: str = "user"      # user, project, system
    authorization_context: Dict[str, Any] = field(default_factory=dict)
    verification_requirement: VerificationRequirement = VerificationRequirement.NONE
    approval_bindings: List[ApprovalBinding] = field(default_factory=list)
    idempotency_key: Optional[str] = None
    dry_run: bool = False
    estimated_cost_usd: float = 0.0
    estimated_time_seconds: float = 0.0
    max_retries: int = 0
    timeout_seconds: float = 30.0
    depends_on: List[str] = field(default_factory=list)  # action_ids this depends on
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "domain": self.domain.value,
            "action_type": self.action_type,
            "target": self.target,
            "intent": self.intent,
            "risk_level": self.risk_level.name,
            "permission_scope": self.permission_scope,
            "authorization_context": self.authorization_context,
            "verification_requirement": self.verification_requirement.value,
            "approval_bindings": [b.value for b in self.approval_bindings],
            "idempotency_key": self.idempotency_key,
            "dry_run": self.dry_run,
            "estimated_cost_usd": self.estimated_cost_usd,
            "estimated_time_seconds": self.estimated_time_seconds,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "depends_on": self.depends_on,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionMetadata":
        return cls(
            action_id=data.get("action_id", uuid.uuid4().hex[:12]),
            agent_id=data.get("agent_id", ""),
            task_id=data.get("task_id", ""),
            timestamp=data.get("timestamp", time.time()),
            domain=ActionDomain(data.get("domain", "system")),
            action_type=data.get("action_type", ""),
            target=data.get("target", ""),
            intent=data.get("intent", ""),
            risk_level=RiskTier[data.get("risk_level", "R0_INFORMATIONAL")],
            permission_scope=data.get("permission_scope", "user"),
            authorization_context=data.get("authorization_context", {}),
            verification_requirement=VerificationRequirement(data.get("verification_requirement", "none")),
            approval_bindings=[ApprovalBinding(b) for b in data.get("approval_bindings", [])],
            idempotency_key=data.get("idempotency_key"),
            dry_run=data.get("dry_run", False),
            estimated_cost_usd=data.get("estimated_cost_usd", 0.0),
            estimated_time_seconds=data.get("estimated_time_seconds", 0.0),
            max_retries=data.get("max_retries", 0),
            timeout_seconds=data.get("timeout_seconds", 30.0),
            depends_on=data.get("depends_on", []),
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# ACTION DEFINITIONS
# =============================================================================

# Browser Actions
BROWSER_ACTIONS = {
    "BROWSER_NAVIGATE": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Navigate to URL",
    },
    "BROWSER_CLICK": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Click element by selector/ref",
    },
    "BROWSER_TYPE": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Type text into field",
    },
    "BROWSER_FORM_FILL": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Fill multiple form fields at once",
    },
    "BROWSER_SUBMIT": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R3_HIGH,
        "verification": VerificationRequirement.DOMAIN_CONFIRMATION,
        "description": "Submit form with confirmation",
    },
    "BROWSER_DOWNLOAD": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R3_HIGH,
        "verification": VerificationRequirement.IDEMPOTENCY_CHECK,
        "description": "Download file",
    },
    "BROWSER_UPLOAD": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R3_HIGH,
        "verification": VerificationRequirement.IDEMPOTENCY_CHECK,
        "description": "Upload file",
    },
    "BROWSER_SNAPSHOT": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Capture accessibility tree / screenshot",
    },
    "BROWSER_SCROLL": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Scroll page",
    },
    "BROWSER_BACK": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Navigate back in history",
    },
    "BROWSER_FORWARD": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Navigate forward in history",
    },
    "BROWSER_NEW_TAB": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Open new tab",
    },
    "BROWSER_CLOSE_TAB": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Close tab",
    },
    "BROWSER_SWITCH_TAB": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Switch to tab",
    },
    "BROWSER_WAIT": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Wait for condition",
    },
    "BROWSER_EXECUTE_JS": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Execute JavaScript in page context",
    },
    "BROWSER_DIALOG": {
        "domain": ActionDomain.BROWSER,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Handle JavaScript dialog (accept/dismiss)",
    },
}

# Desktop Actions
DESKTOP_ACTIONS = {
    "DESKTOP_CLICK": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Click at coordinates or element",
    },
    "DESKTOP_DOUBLE_CLICK": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Double-click",
    },
    "DESKTOP_RIGHT_CLICK": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Right-click",
    },
    "DESKTOP_DRAG": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Drag from/to coordinates",
    },
    "DESKTOP_SCROLL": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Scroll window",
    },
    "DESKTOP_TYPE": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Type text",
    },
    "DESKTOP_KEY": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Press key combination",
    },
    "DESKTOP_SET_VALUE": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Set native value (slider, dropdown)",
    },
    "DESKTOP_MOVE_MOUSE": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.NONE,
        "description": "Move mouse to coordinates",
    },
    "DESKTOP_CAPTURE": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Capture screen/window/region",
    },
    "DESKTOP_OCR": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "OCR screen region",
    },
    "DESKTOP_FIND_TEXT": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Find text on screen",
    },
    "DESKTOP_LIST_WINDOWS": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "List open windows",
    },
    "DESKTOP_GET_ACTIVE_WINDOW": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Get active window info",
    },
    "DESKTOP_FOCUS_WINDOW": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Focus specific window",
    },
    "DESKTOP_MINIMIZE_WINDOW": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Minimize window",
    },
    "DESKTOP_MAXIMIZE_WINDOW": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Maximize window",
    },
    "DESKTOP_CLOSE_WINDOW": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R3_HIGH,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Close window",
    },
    "DESKTOP_LIST_APPS": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "List installed applications",
    },
    "DESKTOP_FOCUS_APP": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Focus application",
    },
    "DESKTOP_LAUNCH_APP": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R3_HIGH,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Launch application",
    },
    "DESKTOP_CLOSE_APP": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R3_HIGH,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Close application",
    },
    "DESKTOP_READ_CLIPBOARD": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.NONE,
        "description": "Read clipboard text",
    },
    "DESKTOP_COPY_CLIPBOARD": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.IDEMPOTENCY_CHECK,
        "description": "Copy to clipboard",
    },
    "DESKTOP_CLEAR_CLIPBOARD": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.IDEMPOTENCY_CHECK,
        "description": "Clear clipboard",
    },
    "DESKTOP_WAIT": {
        "domain": ActionDomain.DESKTOP,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Wait for condition",
    },
}

# Terminal Actions
TERMINAL_ACTIONS = {
    "TERMINAL_EXECUTE": {
        "domain": ActionDomain.TERMINAL,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Execute foreground command",
    },
    "TERMINAL_BACKGROUND": {
        "domain": ActionDomain.TERMINAL,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Start background process",
    },
    "TERMINAL_SUDO": {
        "domain": ActionDomain.TERMINAL,
        "risk": RiskTier.R3_HIGH,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Execute with sudo",
    },
    "TERMINAL_KILL": {
        "domain": ActionDomain.TERMINAL,
        "risk": RiskTier.R3_HIGH,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Kill process",
    },
    "TERMINAL_WAIT": {
        "domain": ActionDomain.TERMINAL,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Wait for background process",
    },
    "TERMINAL_POLL": {
        "domain": ActionDomain.TERMINAL,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Poll background process status",
    },
}

# Vision Actions
VISION_ACTIONS = {
    "VISION_ANALYZE": {
        "domain": ActionDomain.VISION,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.NONE,
        "description": "Analyze image with vision model",
    },
    "VISION_OCR": {
        "domain": ActionDomain.VISION,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "OCR image",
    },
    "VISION_CAPTURE": {
        "domain": ActionDomain.VISION,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Capture screen/window/region",
    },
    "VISION_DOCUMENT_EXTRACT": {
        "domain": ActionDomain.VISION,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.NONE,
        "description": "Extract document structure",
    },
    "VISION_UNDERSTAND": {
        "domain": ActionDomain.VISION,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.STATE_MATCH,
        "description": "Screen understanding (OCR + UI detection)",
    },
    "VIDEO_ANALYZE": {
        "domain": ActionDomain.VISION,
        "risk": RiskTier.R1_LOW,
        "verification": VerificationRequirement.NONE,
        "description": "Analyze video",
    },
}

# Filesystem Actions
FILESYSTEM_ACTIONS = {
    "FS_READ": {
        "domain": ActionDomain.FILESYSTEM,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Read file",
    },
    "FS_WRITE": {
        "domain": ActionDomain.FILESYSTEM,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.IDEMPOTENCY_CHECK,
        "description": "Write file",
    },
    "FS_PATCH": {
        "domain": ActionDomain.FILESYSTEM,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.IDEMPOTENCY_CHECK,
        "description": "Patch file",
    },
    "FS_DELETE": {
        "domain": ActionDomain.FILESYSTEM,
        "risk": RiskTier.R3_HIGH,
        "verification": VerificationRequirement.IDEMPOTENCY_CHECK,
        "description": "Delete file/directory",
    },
    "FS_MOVE": {
        "domain": ActionDomain.FILESYSTEM,
        "risk": RiskTier.R2_MODERATE,
        "verification": VerificationRequirement.IDEMPOTENCY_CHECK,
        "description": "Move/rename file",
    },
    "FS_SEARCH": {
        "domain": ActionDomain.FILESYSTEM,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Search files",
    },
}

# System Actions
SYSTEM_ACTIONS = {
    "SYSTEM_WAIT": {
        "domain": ActionDomain.SYSTEM,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Wait",
    },
    "SYSTEM_GET_CAPABILITIES": {
        "domain": ActionDomain.SYSTEM,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Get system capabilities",
    },
    "SYSTEM_INFO": {
        "domain": ActionDomain.SYSTEM,
        "risk": RiskTier.R0_INFORMATIONAL,
        "verification": VerificationRequirement.NONE,
        "description": "Get system info",
    },
}


# Combined action registry.
# Keys are canonical dotted names: "<domain>.<short>" (e.g. "browser.navigate",
# "terminal.execute", "filesystem.read") — matching how callers reference actions.
_DOMAIN_PREFIX_STRIP = {
    ActionDomain.BROWSER.value: "browser_",
    ActionDomain.DESKTOP.value: "desktop_",
    ActionDomain.TERMINAL.value: "terminal_",
    ActionDomain.VISION.value: "vision_",
    ActionDomain.FILESYSTEM.value: "fs_",
    ActionDomain.SYSTEM.value: "system_",
}

_ALL_ACTION_DICTS = (
    (ActionDomain.BROWSER, BROWSER_ACTIONS),
    (ActionDomain.DESKTOP, DESKTOP_ACTIONS),
    (ActionDomain.TERMINAL, TERMINAL_ACTIONS),
    (ActionDomain.VISION, VISION_ACTIONS),
    (ActionDomain.FILESYSTEM, FILESYSTEM_ACTIONS),
    (ActionDomain.SYSTEM, SYSTEM_ACTIONS),
)

ALL_ACTIONS: Dict[str, Dict[str, Any]] = {}
for _domain, _actions in _ALL_ACTION_DICTS:
    _strip = _DOMAIN_PREFIX_STRIP[_domain.value]
    for _key, _defn in _actions.items():
        _short = _key.lower()
        if _short.startswith(_strip):
            _short = _short[len(_strip):]
        ALL_ACTIONS[f"{_domain.value}.{_short}"] = _defn


def get_action_definition(action_name: str) -> Optional[Dict[str, Any]]:
    """Get action definition by name (e.g., 'browser.navigate')."""
    return ALL_ACTIONS.get(action_name.lower())


def get_actions_by_domain(domain: ActionDomain) -> Dict[str, Dict[str, Any]]:
    """Get all actions for a domain."""
    prefix = f"{domain.value}."
    return {k: v for k, v in ALL_ACTIONS.items() if k.startswith(prefix)}


def get_action_risk(action_name: str) -> RiskTier:
    """Get risk tier for an action."""
    defn = get_action_definition(action_name)
    return defn["risk"] if defn else RiskTier.R0_INFORMATIONAL


def get_action_verification(action_name: str) -> VerificationRequirement:
    """Get verification requirement for an action."""
    defn = get_action_definition(action_name)
    return defn["verification"] if defn else VerificationRequirement.NONE


# =============================================================================
# RISK CLASSIFICATION HELPERS
# =============================================================================

# Form field classification (Phase 19)
class FieldClassification(enum.Enum):
    PUBLIC = "public"           # public info (search query, public form)
    PERSONAL = "personal"       # name, email, phone, address
    SENSITIVE = "sensitive"     # SSN, DOB, medical, financial
    CREDENTIAL = "credential"   # password, API key, token, secret
    FINANCIAL = "financial"     # credit card, bank account, payment

FIELD_CLASSIFICATION_PATTERNS = {
    FieldClassification.CREDENTIAL: [
        r"password", r"passwd", r"secret", r"token", r"api[_-]?key",
        r"auth", r"credential", r"private[_-]?key", r"access[_-]?token"
    ],
    FieldClassification.FINANCIAL: [
        r"credit[_-]?card", r"card[_-]?number", r"cvv", r"expiry",
        r"bank[_-]?account", r"routing", r"iban", r"swift"
    ],
    FieldClassification.SENSITIVE: [
        r"ssn", r"social[_-]?security", r"dob", r"date[_-]?of[_-]?birth",
        r"medical", r"health", r"diagnosis", r"prescription"
    ],
    FieldClassification.PERSONAL: [
        r"name", r"email", r"phone", r"address", r"zip", r"postal",
        r"city", r"state", r"country", r"gender", r"age"
    ],
    FieldClassification.PUBLIC: [
        r"search", r"query", r"filter", r"sort", r"page", r"limit",
        r"category", r"tag", r"filter", r"order"
    ],
}


def classify_field(field_name: str, field_type: str = "") -> FieldClassification:
    """Classify a form field by name/type (Phase 19)."""
    text = (field_name + " " + field_type).lower()
    for classification, patterns in FIELD_CLASSIFICATION_PATTERNS.items():
        for pattern in patterns:
            import re
            if re.search(pattern, text):
                return classification
    return FieldClassification.PUBLIC


# Submission confirmation data (Phase 20)
@dataclass
class SubmissionSummary:
    """Summary presented to user before consequential submission (Phase 20)."""
    action: str
    target: str
    data_summary: Dict[str, Any]
    risk_level: RiskTier
    account: str = ""
    destination: str = ""
    consequence: str = ""
    requires_approval: bool = True
    idempotency_key: Optional[str] = None

    def to_user_message(self) -> str:
        lines = [
            "CONFIRM SUBMISSION",
            "",
            f"Action:     {self.action}",
            f"Target:     {self.target}",
            f"Risk:       {self.risk_level.name}",
        ]
        if self.account:
            lines.append(f"Account:    {self.account}")
        if self.destination:
            lines.append(f"Destination: {self.destination}")
        if self.consequence:
            lines.append(f"Consequence: {self.consequence}")
        lines.append("")
        lines.append("Data to be sent:")
        for k, v in self.data_summary.items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append("Approve? (yes/no)")
        return "\n".join(lines)


# =============================================================================
# PERSISTENCE
# =============================================================================

ACTION_LOG_DIR = get_aetheros_home() / "computer_actions"


def _ensure_action_log_dir() -> None:
    ACTION_LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_action(metadata: ActionMetadata, result: Dict[str, Any]) -> None:
    """Log action execution for audit trail (Phase 60)."""
    _ensure_action_log_dir()
    log_entry = {
        "metadata": metadata.to_dict(),
        "result": result,
        "completed_at": time.time(),
    }
    log_file = ACTION_LOG_DIR / f"{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ActionDomain",
    "RiskTier",
    "VerificationRequirement",
    "ApprovalBinding",
    "ActionMetadata",
    "FieldClassification",
    "SubmissionSummary",
    "BROWSER_ACTIONS",
    "DESKTOP_ACTIONS",
    "TERMINAL_ACTIONS",
    "VISION_ACTIONS",
    "FILESYSTEM_ACTIONS",
    "SYSTEM_ACTIONS",
    "ALL_ACTIONS",
    "get_action_definition",
    "get_actions_by_domain",
    "get_action_risk",
    "get_action_verification",
    "classify_field",
    "SubmissionSummary",
    "log_action",
    "ACTION_LOG_DIR",
]