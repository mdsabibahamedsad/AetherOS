"""
Unified Approval Engine (Master 15 Phases 3-5, 54-57).

Merges terminal approval (tools/approval.py) + MASTER 7 action_guard risk tiers
+ computer-use destructive actions into a single approval engine with:
- R0-R4 risk classification
- Plan preview for risky tasks
- Approval boundaries, expiration, context binding
- Plan preview for user review
"""

from __future__ import annotations

import enum
import json
import logging
import os
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from aetheros_computer.action import (
    ActionMetadata, ActionDomain, RiskTier, VerificationRequirement, ApprovalBinding,
    FieldClassification, SubmissionSummary, classify_field,
    get_action_risk, get_action_verification
)
from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)

# =============================================================================
# APPROVAL STATE
# =============================================================================

class ApprovalOutcome(enum.Enum):
    ONCE = "once"              # approve this one execution
    SESSION = "session"        # approve for this session
    ALWAYS = "always"          # permanent allowlist
    DENY = "deny"              # deny this execution
    ESCALATE = "escalate"      # requires higher authority


class ApprovalState(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    ESCALATED = "escalated"


@dataclass
class ApprovalRequest:
    """Unified approval request (Master 15 Phases 3-5, 54-57)."""

    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action_metadata: Any = None          # ActionMetadata
    plan_preview: Optional[Dict[str, Any]] = None  # Plan preview for risky tasks
    state: ApprovalState = ApprovalState.PENDING
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    resolved_at: Optional[float] = None
    outcome: Optional[ApprovalOutcome] = None
    resolver: str = ""                   # user, agent, system
    context: Dict[str, Any] = field(default_factory=dict)
    approval_bindings: List[str] = field(default_factory=list)  # ApprovalBinding values

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "action_metadata": self.action_metadata.to_dict() if self.action_metadata else None,
            "plan_preview": self.plan_preview,
            "state": self.state.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "resolved_at": self.resolved_at,
            "outcome": self.outcome.value if self.outcome else None,
            "resolver": self.resolver,
            "context": self.context,
            "approval_bindings": self.approval_bindings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalRequest":
        from aetheros_computer.action import ActionMetadata
        req = cls(
            request_id=data.get("request_id", uuid.uuid4().hex[:12]),
            action_metadata=ActionMetadata.from_dict(data["action_metadata"]) if data.get("action_metadata") else None,
            plan_preview=data.get("plan_preview"),
            state=ApprovalState(data.get("state", "pending")),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at"),
            resolved_at=data.get("resolved_at"),
            outcome=ApprovalOutcome(data["outcome"]) if data.get("outcome") else None,
            resolver=data.get("resolver", ""),
            context=data.get("context", {}),
            approval_bindings=data.get("approval_bindings", []),
        )
        return req


# =============================================================================
# HARDLINE BLOCKLIST (Unconditional - Phase 3)
# =============================================================================

HARDLINE_BLOCKLIST = [
    # Destructive filesystem
    r"rm\s+-rf\s+/",
    r"mkfs\.",
    r"dd\s+of=/dev/",
    r">\s*/dev/sd",
    r"fdisk",
    r"parted",

    # System destruction
    r"shutdown\s",
    r"reboot\s",
    r"halt\s",
    r"poweroff\s",
    r"init\s+0",
    r"init\s+6",
    r"telinit\s+0",
    r"telinit\s+6",
    r"systemctl\s+(poweroff|reboot|halt)",

    # Fork bomb
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\};:",

    # Kill all
    r"kill\s+-1\s*$",
    r"killall\s+-9\s*$",
    r"pkill\s+-9\s*$",

    # Credential destruction
    r"ssh-add\s+-D",
    r"gpg\s+--delete-secret-keys",
]


def check_hardline_block(command: str) -> Optional[str]:
    """Check if command matches hardline blocklist. Returns blocking reason or None."""
    import re
    normalized = command.strip()
    for pattern in HARDLINE_BLOCKLIST:
        if re.search(pattern, normalized, re.IGNORECASE):
            return f"Hardline block: '{pattern}' matched in command"
    return None


# =============================================================================
# DANGEROUS PATTERNS (Require Approval - Phase 3)
# =============================================================================

DANGEROUS_PATTERNS = [
    # Recursive deletion
    (r"rm\s+(-r|--recursive)", "Recursive file deletion"),
    (r"rm\s+.*\s+(-f|--force)", "Forced file deletion"),
    (r"find\s+.*\s+(-exec|-delete)\s+rm", "Find with delete"),

    # Filesystem modification
    (r"mkfs\.", "Filesystem creation"),
    (r"dd\s+of=/dev/", "Direct disk write"),
    (r">\s*/dev/sd", "Block device write"),
    (r"chmod\s+.*\s+777", "World-writable permissions"),
    (r"chown\s+.*\s+root:", "Recursive root ownership"),

    # SQL destruction
    (r"DROP\s+(TABLE|DATABASE|SCHEMA)", "SQL DROP"),
    (r"DELETE\s+FROM\s+\w+\s*(?!WHERE)", "DELETE without WHERE"),
    (r"TRUNCATE\s+TABLE", "TRUNCATE TABLE"),

    # System service modification
    (r"systemctl\s+(stop|restart|disable|mask)", "Service control"),
    (r"service\s+\w+\s+(stop|restart)", "Service control"),

    # Process killing
    (r"kill\s+-9\s+-1", "Kill all processes"),
    (r"pkill\s+-9", "Kill all by pattern"),
    (r"killall\s+-9", "Kill all by name"),

    # Fork bomb
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\};:", "Fork bomb"),

    # Shell exec
    (r"\b(sh|bash|zsh|python|perl|ruby|node)\s+(-c|-e)", "Shell code execution"),
    (r"curl\s+\|\s*(sh|bash)", "Pipe curl to shell"),
    (r"bash\s+<\(curl", "Process substitution curl"),
    (r"wget\s+.*\|\s*(sh|bash)", "Pipe wget to shell"),

    # Sensitive file writes
    (r">\s*(/etc/|/boot/|/usr/lib/systemd/|/private/etc/|/var/run/docker\.sock|~/\.aetheros/config\.yaml|\.env)", "Sensitive path write"),
    (r"tee\s+.*(/etc/|~/\.ssh/|~/\.aetheros/)", "Tee to sensitive path"),

    # Credential manipulation
    (r"ssh-add\s+-D", "Clear SSH keys"),
    (r"gpg\s+--delete-secret-keys", "Delete GPG keys"),
    (r"passwd\s", "Password change"),
    (r"chpasswd", "Batch password change"),

    # Self-termination
    (r"pkill\s+aetheros", "Kill Aetheros processes"),
    (r"kill\s+\$\(pgrep\s+aetheros\)", "Kill Aetheros by pgrep"),

    # Git destruction
    (r"git\s+reset\s+--hard", "Git hard reset"),
    (r"git\s+push\s+--force", "Git force push"),
    (r"git\s+clean\s+-f", "Git clean"),
    (r"git\s+branch\s+-D", "Git delete branch"),

    # Container orchestration
    (r"docker\s+compose\s+(restart|stop|kill|down)", "Docker compose control"),
    (r"docker\s+(restart|stop|kill)", "Docker container control"),

    # Network
    (r"iptables\s+-F", "Flush iptables"),
    (r"ufw\s+(disable|reset)", "Firewall disable"),

    # Aetheros self-modification
    (r"aetheros\s+(gateway\s+)?(stop|restart|update)", "Aetheros self-control"),
]


def check_dangerous_pattern(command: str) -> Optional[str]:
    """Check if command matches dangerous pattern. Returns description or None."""
    import re
    normalized = _normalize_command_for_detection(command)
    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return f"Dangerous pattern: {description}"
    return None


def _normalize_command_for_detection(command: str) -> str:
    """Normalize command for pattern matching (prevent bypass)."""
    import re
    # Strip ANSI
    cmd = re.sub(r'\x1b\[[0-9;]*m', '', command)
    # Remove null bytes
    cmd = cmd.replace('\x00', '')
    # NFKC Unicode normalization
    import unicodedata
    cmd = unicodedata.normalize('NFKC', cmd)
    # Resolve backslash escapes
    cmd = cmd.replace('\\ ', ' ').replace('\\t', '\t').replace('\\n', '\n')
    # Remove empty string concatenation
    cmd = re.sub(r'""\s*', '', cmd)
    cmd = re.sub(r"''\s*", '', cmd)
    # Rewrite resolved AETHEROS_HOME
    try:
        from aetheros_constants import get_aetheros_home
        home = str(get_aetheros_home())
        cmd = cmd.replace(home, "~/.aetheros")
    except Exception:
        pass
    return cmd


# =============================================================================
# PLAN PREVIEW (Phase 5)
# =============================================================================

@dataclass
class PlanStep:
    """Single step in an execution plan."""
    step_id: str
    action: str                    # action name (e.g., 'browser.navigate')
    intent: str                    # human-readable intent
    target: str                    # target (URL, file, selector, command)
    risk: str                      # RiskTier name
    estimated_time: float = 0.0
    estimated_cost: float = 0.0
    requires_approval: bool = False
    verification: str = "none"     # VerificationRequirement name
    depends_on: List[str] = field(default_factory=list)  # step_ids


@dataclass
class ExecutionPlan:
    """Complete execution plan for user review (Phase 5)."""

    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str = ""
    goal: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    total_estimated_time: float = 0.0
    total_estimated_cost: float = 0.0
    max_risk: str = "R0_INFORMATIONAL"
    approval_required: bool = False
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_user_preview(self) -> str:
        """Generate human-readable preview for user (Phase 5). ASCII-safe."""
        lines = [
            "Execution Plan Preview",
            "======================",
            f"Goal: {self.goal}",
            f"Plan ID: {self.plan_id}",
            f"Steps: {len(self.steps)}",
            f"Est. Time: {self.total_estimated_time:.0f}s",
            f"Est. Cost: ${self.total_estimated_cost:.4f}",
            f"Max Risk: {self.max_risk}",
            f"Approval Required: {'Yes' if self.approval_required else 'No'}",
            "",
            "Steps:",
        ]

        risk_order = {"R0_INFORMATIONAL": 0, "R1_LOW": 1, "R2_MODERATE": 2, "R3_HIGH": 3, "R4_CRITICAL": 4}
        for i, step in enumerate(self.steps, 1):
            if step.risk in ("R3_HIGH", "R4_CRITICAL"):
                marker = "[HIGH]"
            elif step.risk == "R2_MODERATE":
                marker = "[MED] "
            else:
                marker = "[LOW] "
            approve_flag = " << APPROVAL REQUIRED" if step.requires_approval else ""
            lines.append(f"  {i}. {marker} {step.action}{approve_flag}")
            lines.append(f"     Intent: {step.intent}")
            lines.append(f"     Target: {step.target[:80]}")
            lines.append(f"     Risk: {step.risk} | Verify: {step.verification} | Est: {step.estimated_time:.0f}s")

        if self.approval_required:
            lines.extend(["", "NOTE: This plan requires your approval before execution.",
                          "Review the steps above, then approve or deny."])

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "goal": self.goal,
            "steps": [
                {
                    "step_id": s.step_id,
                    "action": s.action,
                    "intent": s.intent,
                    "target": s.target,
                    "risk": s.risk,
                    "estimated_time": s.estimated_time,
                    "estimated_cost": s.estimated_cost,
                    "requires_approval": s.requires_approval,
                    "verification": s.verification,
                    "depends_on": s.depends_on,
                }
                for s in self.steps
            ],
            "total_estimated_time": self.total_estimated_time,
            "total_estimated_cost": self.total_estimated_cost,
            "max_risk": self.max_risk,
            "approval_required": self.approval_required,
            "created_at": self.created_at,
        }


def build_execution_plan(
    goal: str,
    actions: List[Dict[str, Any]],
    task_id: str = "",
) -> ExecutionPlan:
    """Build execution plan from action list (Phase 4)."""
    plan = ExecutionPlan(goal=goal, task_id=task_id)
    risk_order = {"R0_INFORMATIONAL": 0, "R1_LOW": 1, "R2_MODERATE": 2, "R3_HIGH": 3, "R4_CRITICAL": 4}
    max_risk_val = 0

    for i, action in enumerate(actions):
        action_name = action.get("action", "")
        risk = get_action_risk(action_name)
        verification = get_action_verification(action_name)

        step = PlanStep(
            step_id=f"step_{i+1}",
            action=action_name,
            intent=action.get("intent", ""),
            target=action.get("target", ""),
            risk=risk.name,
            estimated_time=action.get("estimated_time", 0.0),
            estimated_cost=action.get("estimated_cost", 0.0),
            requires_approval=risk.value >= RiskTier.R3_HIGH.value,
            verification=verification.value,
            depends_on=action.get("depends_on", []),
        )
        plan.steps.append(step)

        # Update totals
        plan.total_estimated_time += step.estimated_time
        plan.total_estimated_cost += step.estimated_cost
        if step.requires_approval:
            plan.approval_required = True
        if risk_order.get(step.risk, 0) > max_risk_val:
            max_risk_val = risk_order.get(step.risk, 0)
            plan.max_risk = step.risk

    return plan


# =============================================================================
# UNIFIED APPROVAL ENGINE
# =============================================================================

class UnifiedApprovalEngine:
    """
    Unified approval engine merging:
    - Terminal approval (tools/approval.py)
    - MASTER 7 action_guard risk tiers (R0-R4)
    - Computer-use destructive actions
    - Plan preview for risky tasks
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._lock = threading.Lock()

        # State
        self._pending: Dict[str, ApprovalRequest] = {}
        self._session_approved: Dict[str, Set[str]] = {}  # session_id -> set of action_ids
        self._session_yolo: Set[str] = set()              # session_ids with YOLO mode
        self._permanent_allowed: Set[str] = set()         # action_ids permanently allowed

        # Callbacks
        self._gateway_notify: Optional[Callable[[str, Dict], None]] = None
        self._cli_prompt: Optional[Callable[[str], str]] = None

        # Config
        self._approval_timeout = self.config.get("approval_timeout_seconds", 300)
        self._yolo_mode = self.config.get("yolo_mode", False)
        self._smart_approval = self.config.get("smart_approval", False)

        # Load permanent allowlist
        self._load_permanent_allowlist()

    def set_gateway_notify(self, callback: Callable[[str, Dict], None]) -> None:
        """Register gateway notification callback."""
        self._gateway_notify = callback

    def set_cli_prompt(self, callback: Callable[[str], str]) -> None:
        """Register CLI prompt callback."""
        self._cli_prompt = callback

    def _load_permanent_allowlist(self) -> None:
        """Load permanent allowlist from config."""
        allowlist = self.config.get("command_allowlist", [])
        for action in allowlist:
            self._permanent_allowed.add(action)

    def _save_permanent_allowlist(self) -> None:
        """Save permanent allowlist to config."""
        # In practice, this would update config.yaml
        pass

    # -------------------------------------------------------------------------
    # MAIN APPROVAL INTERFACE
    # -------------------------------------------------------------------------

    def check_and_request_approval(
        self,
        action_metadata: ActionMetadata,
        session_key: str = "",
        context: Dict[str, Any] = None,
        wait: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if action requires approval and request if needed.

        Args:
            wait: When True (default), block until the gateway/CLI decision
                arrives. When False, queue the request, notify, and return
                immediately with ``(False, "PENDING:<request_id>")`` so async
                UIs can resolve later via :meth:`resolve_gateway_approval`.

        Returns:
            (allowed: bool, reason: Optional[str])
            - allowed=True: action can proceed
            - allowed=False: action blocked; reason explains why. Reasons
              beginning with ``PENDING:`` mean the request is queued and the
              remainder is the request id.
        """
        context = context or {}
        action_name = action_metadata.action_type
        risk = action_metadata.risk_level

        # 1. Hardline block (unconditional)
        if action_metadata.domain == ActionDomain.TERMINAL:
            target = action_metadata.target or ""
            hardline_reason = check_hardline_block(action_metadata.target or "")
            if hardline_reason:
                return False, hardline_reason

        # 2. Check permanent allowlist
        if action_name in self._permanent_allowed:
            return True, ""

        # 3. Check session allowlist (session-scoped approval)
        if session_key and action_name in self._session_approved.get(session_key, set()):
            return True, ""

        # 3.5 Check session YOLO mode
        if session_key and session_key in self._session_yolo:
            return True, ""

        # 4. Check if approval required based on risk
        requires_approval = self._requires_approval(action_metadata)
        if not requires_approval:
            return True, ""

        # 6. Build plan preview for risky tasks (Phase 5)
        plan_preview = self._build_plan_preview(action_metadata)

        # 7. Create approval request (target-hash bound for Phase 57)
        import hashlib as _hashlib

        request = ApprovalRequest(
            action_metadata=action_metadata,
            plan_preview=plan_preview.to_dict() if plan_preview else None,
            expires_at=time.time() + self._approval_timeout,
            context={
                "session_key": session_key,
                "target_hash": _hashlib.sha256(
                    str(action_metadata.target or "").encode("utf-8", "replace")
                ).hexdigest()[:16],
            },
        )

        # 8. Determine approval path
        if self._yolo_mode:
            # YOLO mode: auto-approve with warning
            logger.warning(f"YOLO mode: auto-approving {action_name} (risk: {risk.name})")
            self._session_approved.setdefault(session_key, set()).add(action_name)
            return True, ""

        if self._is_gateway_context():
            # Gateway: queue for async approval
            return self._request_gateway_approval(request, session_key, wait=wait)
        elif self._is_cli_context():
            # CLI: inline prompt
            return self._request_cli_approval(request, session_key)
        else:
            # Background/non-interactive: deny by default for safety
            return False, f"Approval required for {action_name} (risk: {risk.name}) but no interactive context available"

    def _requires_approval(self, metadata: ActionMetadata) -> bool:
        """Determine if action requires approval based on risk tier.

        Phase 53: effect-class routing — SEND/PUBLISH/PURCHASE/DEPLOY/
        PERMISSION_CHANGE/ACCOUNT_CHANGE always confirm regardless of tier.
        """
        from aetheros_computer.side_effects import requires_confirmation

        if metadata.risk_level.value >= RiskTier.R3_HIGH.value:
            return True
        if requires_confirmation(metadata.action_type):
            return True
        # Check for dangerous patterns in terminal commands
        if metadata.domain == ActionDomain.TERMINAL:
            target = metadata.target or ""
            if check_dangerous_pattern(target):
                return True
        return False

    def _build_plan_preview(self, action_metadata: ActionMetadata) -> Optional[ExecutionPlan]:
        """Build plan preview for user review (Phase 5)."""
        # For single actions, create minimal plan
        if action_metadata.risk_level.value < RiskTier.R3_HIGH.value:
            return None

        plan = ExecutionPlan(
            goal=f"Execute {action_metadata.action_type}",
            task_id=action_metadata.task_id,
        )
        step = PlanStep(
            step_id="step_1",
            action=action_metadata.action_type,
            intent=action_metadata.intent or action_metadata.action_type,
            target=action_metadata.target,
            risk=action_metadata.risk_level.name,
            estimated_time=action_metadata.estimated_time_seconds,
            estimated_cost=action_metadata.estimated_cost_usd,
            requires_approval=True,
            verification=get_action_verification(action_metadata.action_type).value,
        )
        plan.steps.append(step)
        plan.total_estimated_time = step.estimated_time
        plan.total_estimated_cost = step.estimated_cost
        plan.max_risk = step.risk
        plan.approval_required = True
        return plan

    def _request_gateway_approval(self, request: ApprovalRequest, session_key: str, wait: bool = True) -> Tuple[bool, str]:
        """Request approval via gateway queue."""
        with self._lock:
            self._pending[request.request_id] = request

        if self._gateway_notify:
            self._gateway_notify(session_key, {
                "type": "approval_request",
                "request_id": request.request_id,
                "action": request.action_metadata.action_type,
                "target": request.action_metadata.target,
                "risk": request.action_metadata.risk_level.name,
                "plan_preview": request.plan_preview,
                "expires_at": request.expires_at,
            })

        if not wait:
            # Queue-and-return for async UI flows; resolve later via
            # resolve_gateway_approval(request_id, approve).
            return False, f"PENDING:{request.request_id}"

        # Wait for resolution (with heartbeat to prevent watchdog kill)
        return self._await_gateway_decision(request.request_id)

    def _request_cli_approval(self, request: ApprovalRequest, session_key: str) -> Tuple[bool, str]:
        """Request approval via CLI inline prompt."""
        if not self._cli_prompt:
            return False, "No CLI prompt callback registered"

        preview = f"Approve {request.action_metadata.action_type}?"
        if request.plan_preview:
            plan = build_execution_plan(
                goal=request.plan_preview.get("goal", ""),
                actions=[],
                task_id=request.plan_preview.get("task_id", ""),
            )
            plan.max_risk = request.plan_preview.get("max_risk", plan.max_risk)
            plan.approval_required = True
            preview = plan.to_user_preview()

        try:
            response = self._cli_prompt(f"{preview}\nApprove? (once/session/always/deny): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            response = "deny"

        return self._resolve_approval(request.request_id, response, session_key)

    def _await_gateway_decision(self, request_id: str, timeout: float = None) -> Tuple[bool, str]:
        """Wait for gateway approval decision with heartbeat."""
        timeout = timeout or self._approval_timeout
        start = time.time()

        while time.time() - start < timeout:
            with self._lock:
                request = self._pending.get(request_id)
                if not request:
                    return False, "Request not found"
                if request.state != ApprovalState.PENDING:
                    return self._resolve_result(request)

            # Heartbeat to prevent watchdog
            time.sleep(1)

        # Timeout - deny by default
        return self._timeout_request(request_id)

    def _resolve_approval(self, request_id: str, response: str, session_key: str) -> Tuple[bool, str]:
        """Resolve approval from user response."""
        mapping = {
            "once": ApprovalOutcome.ONCE,
            "session": ApprovalOutcome.SESSION,
            "always": ApprovalOutcome.ALWAYS,
            "deny": ApprovalOutcome.DENY,
            "y": ApprovalOutcome.ONCE,
            "n": ApprovalOutcome.DENY,
        }

        outcome = mapping.get(response, ApprovalOutcome.DENY)

        with self._lock:
            request = self._pending.get(request_id)
            if not request:
                return False, "Request not found"

            request.state = ApprovalState.APPROVED if outcome != ApprovalOutcome.DENY else ApprovalState.DENIED
            request.outcome = outcome
            request.resolved_at = time.time()
            request.resolver = "user"

            if outcome == ApprovalOutcome.SESSION:
                self._session_approved.setdefault(session_key, set()).add(request.action_metadata.action_type)
            elif outcome == ApprovalOutcome.ALWAYS:
                self._permanent_allowed.add(request.action_metadata.action_type)
                self._save_permanent_allowlist()

        return self._resolve_result(request)

    def _resolve_result(self, request: ApprovalRequest) -> Tuple[bool, str]:
        """Return final result from resolved request."""
        if request.outcome == ApprovalOutcome.DENY:
            return False, f"Denied: {request.action_metadata.action_type}"
        return True, ""

    def _timeout_request(self, request_id: str) -> Tuple[bool, str]:
        """Handle approval timeout."""
        with self._lock:
            request = self._pending.get(request_id)
            if request and request.state == ApprovalState.PENDING:
                request.state = ApprovalState.EXPIRED
                request.outcome = ApprovalOutcome.DENY
                request.resolved_at = time.time()
        return False, "Approval timed out"

    def resolve_gateway_approval(self, request_id: str, approve: bool,
                                 target_hint: str = None) -> bool:
        """Resolve gateway approval (called from gateway /approve /deny).

        Phase 57 binding: when ``target_hint`` is provided it must hash-match
        the target the request was created for — an approval cannot be
        transplanted onto a different target. Late resolution of an expired
        request is REFUSED (Phases 23/56).
        """
        with self._lock:
            request = self._pending.get(request_id)
            if not request or request.state != ApprovalState.PENDING:
                return False
            if request.is_expired():
                request.state = ApprovalState.EXPIRED
                request.outcome = ApprovalOutcome.DENY
                request.resolved_at = time.time()
                return False

            if approve and target_hint is not None:
                import hashlib as _hashlib

                bound = (request.context or {}).get("target_hash")
                hint_hash = _hashlib.sha256(
                    str(target_hint).encode("utf-8", "replace")
                ).hexdigest()[:16]
                if bound and hint_hash != bound:
                    logger.warning(
                        "Approval %s refused: target binding mismatch", request_id
                    )
                    return False

            request.state = ApprovalState.APPROVED if approve else ApprovalState.DENIED
            request.outcome = ApprovalOutcome.SESSION if approve else ApprovalOutcome.DENY
            request.resolved_at = time.time()
            request.resolver = "gateway_user"

            if approve:
                session_key = request.context.get("session_key", "")
                self._session_approved.setdefault(session_key, set()).add(request.action_metadata.action_type)

        return True

    def _is_gateway_context(self) -> bool:
        """Check if running in gateway context."""
        return os.getenv("HERMES_GATEWAY_SESSION") == "1"

    def _is_cli_context(self) -> bool:
        """Check if running in interactive CLI context."""
        return os.getenv("AETHEROS_INTERACTIVE") == "1"

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def set_session_yolo(self, session_key: str, enabled: bool = True) -> None:
        """Enable/disable YOLO mode for session."""
        if enabled:
            self._session_yolo.add(session_key)
        else:
            self._session_yolo.discard(session_key)

    def is_session_yolo(self, session_key: str) -> bool:
        return session_key in self._session_yolo

    def add_permanent_allow(self, action: str) -> None:
        """Add action to permanent allowlist."""
        self._permanent_allowed.add(action)
        self._save_permanent_allowlist()

    def remove_permanent_allow(self, action: str) -> None:
        """Remove action from permanent allowlist."""
        self._permanent_allowed.discard(action)
        self._save_permanent_allowlist()

    def get_pending_approvals(self, session_key: str = None) -> List[ApprovalRequest]:
        """Get pending approvals, optionally filtered by session."""
        with self._lock:
            requests = list(self._pending.values())
            if session_key:
                requests = [r for r in requests if r.context.get("session_key") == session_key]
            return requests

    def cleanup_expired(self) -> int:
        """Sweep expired approvals: transition stale PENDING entries to
        EXPIRED and remove every EXPIRED entry from the pending map.
        Returns the number of entries removed."""
        removed = 0
        with self._lock:
            for rid in list(self._pending.keys()):
                req = self._pending[rid]
                if req.state == ApprovalState.PENDING and req.is_expired():
                    req.state = ApprovalState.EXPIRED
                    req.outcome = ApprovalOutcome.DENY
                    req.resolved_at = time.time()
                if req.state == ApprovalState.EXPIRED:
                    del self._pending[rid]
                    removed += 1
        return removed

    # -------------------------------------------------------------------------
    # CONFIRMATION BOUNDARIES (Phase 55)
    # -------------------------------------------------------------------------

    def create_batch_approval(self, items: List[ActionMetadata]) -> Dict[str, Any]:
        """Phase 55: unrelated high-impact actions may NOT share one approval.

        A batch is accepted only when every item shares the same task_id AND
        the same action_type AND the same target — i.e. genuinely identical
        work. Anything else is split into per-item requests by the caller.
        """
        from aetheros_computer.side_effects import classify_effect

        if not items:
            return {"accepted": False, "reason": "empty batch"}
        if len(items) == 1:
            return {"accepted": True, "single": True}
        first = items[0]
        same_shape = all(
            it.task_id == first.task_id
            and it.action_type == first.action_type
            and it.target == first.target
            for it in items[1:]
        )
        risky = any(classify_effect(it.action_type).value in (
            "SEND", "PUBLISH", "PURCHASE", "DEPLOY",
            "PERMISSION_CHANGE", "ACCOUNT_CHANGE", "DELETE",
        ) or it.risk_level.value >= RiskTier.R3_HIGH.value for it in items)
        if risky and not same_shape:
            return {
                "accepted": False,
                "reason": "refused: heterogeneous high-impact batch — "
                          "approve each item individually (Phase 55)",
                "split_required": True,
                "count": len(items),
            }
        return {"accepted": True, "count": len(items), "uniform": same_shape}

    # -------------------------------------------------------------------------
    # SUBMISSION CONFIRMATION (Phase 20)
    # -------------------------------------------------------------------------

    def create_submission_confirmation(
        self,
        action_metadata: ActionMetadata,
        form_data: Dict[str, Any],
        account: str = "",
        destination: str = "",
    ) -> SubmissionSummary:
        """Create submission confirmation for form submits (Phase 20)."""
        # Classify fields
        classified = {}
        for k, v in form_data.items():
            cls = classify_field(k)
            classified[k] = {"value": v, "classification": cls.value}

        # Check for sensitive data
        has_sensitive = any(c["classification"] in ("credential", "financial", "sensitive")
                           for c in classified.values())

        consequence = "Form will be submitted"
        if has_sensitive:
            consequence = "SENSITIVE DATA will be transmitted"

        return SubmissionSummary(
            action="form_submit",
            target=action_metadata.target,
            data_summary=classified,
            risk_level=RiskTier.R3_HIGH,
            account=account,
            destination=destination,
            consequence=consequence,
            requires_approval=True,
        )

    # -------------------------------------------------------------------------
    # LOGIN HANDOFF (Phase 21)
    # -------------------------------------------------------------------------

    def create_login_handoff(
        self,
        session_key: str,
        reason: str,
        auth_type: str,  # "password", "mfa", "captcha", "security_key"
    ) -> Dict[str, Any]:
        """Create login handoff request (Phase 21)."""
        handoff = {
            "type": "login_handoff",
            "session_key": session_key,
            "reason": reason,
            "auth_type": auth_type,
            "created_at": time.time(),
            "expires_at": time.time() + 300,  # 5 min for user to respond
        }
        return handoff

    def wait_for_handoff(self, handoff_id: str, timeout: float = 300) -> bool:
        """Wait for user to complete handoff."""
        # In practice, this would be implemented via gateway websocket
        # For now, return True (placeholder)
        return True


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_approval_engine: Optional[UnifiedApprovalEngine] = None


def get_approval_engine(config: Dict[str, Any] = None) -> UnifiedApprovalEngine:
    global _approval_engine
    if _approval_engine is None:
        _approval_engine = UnifiedApprovalEngine(config)
    return _approval_engine


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ApprovalOutcome",
    "ApprovalState",
    "ApprovalRequest",
    "PlanStep",
    "ExecutionPlan",
    "SubmissionSummary",
    "HARDLINE_BLOCKLIST",
    "DANGEROUS_PATTERNS",
    "check_hardline_block",
    "check_dangerous_pattern",
    "build_execution_plan",
    "UnifiedApprovalEngine",
    "get_approval_engine",
]