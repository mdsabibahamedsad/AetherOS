"""
Tool Authorization Service for AetherOS
========================================

Deterministic authorization boundary for tool calls (master security spec
steps 14, 16, 34). Every tool call SHOULD pass through this service before
execution. It validates:

    - identity (user / session / agent / mission / task)
    - tool identity and trust level
    - the exact action (category:operation)
    - the resource scope
    - parameters (outside the model)
    - risk level
    - policy (declarative + manifest allowlists)

The service NEVER trusts model output, tool descriptions, or memory. All
decisions are deterministic and audited.

Usage::

    from aetheros_security.tool_authz import (
        ToolAuthorizationService, ToolAuthRequest, ToolAuthDecision,
    )

    service = ToolAuthorizationService()
    decision = service.check(
        ToolAuthRequest(
            principal="research-agent",
            session="<token>",
            tool="filesystem_read_file",
            action="filesystem:read",
            resource="/project/docs/notes.md",
            parameters={"path": "/project/docs/notes.md"},
        ),
    )
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolAuthOutcome(Enum):
    ALLOW = "allow"
    DENY = "deny"
    APPROVAL_REQUIRED = "approval_required"
    CHALLENGE = "challenge"


@dataclass
class ToolAuthRequest:
    """One tool-call authorization request."""
    principal: str
    tool: str
    action: str
    resource: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    session: str = ""
    mission: str = ""
    task: str = ""
    agent: str = ""
    risk: Optional[str] = None


@dataclass
class ToolAuthDecision:
    """Result of a tool authorization check."""
    outcome: ToolAuthOutcome
    principal: str
    tool: str
    action: str
    resource: str = ""
    reason: str = ""
    risk: str = "medium"
    requires_approval: bool = False
    approval_id: str = ""
    checked_at: float = 0.0

    @property
    def allowed(self) -> bool:
        return self.outcome == ToolAuthOutcome.ALLOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "principal": self.principal,
            "tool": self.tool,
            "action": self.action,
            "resource": self.resource,
            "reason": self.reason,
            "risk": self.risk,
            "requires_approval": self.requires_approval,
            "approval_id": self.approval_id,
            "checked_at": self.checked_at,
        }


class ToolAuthError(Exception):
    """Raised for invalid authorization requests."""


class ToolAuthorizationService:
    """Central tool authorization boundary (step 14).

    Order of checks (fail-closed):
        1. Emergency stop / lockdown (via authz engine state)
        2. Kill switch for tool execution
        3. Principal active
        4. Session valid + scope
        5. Manifest permission (tool allow/deny by operation + resource)
        6. Authorization-engine policy rules
        7. Risk-based approval requirement
        8. Default DENY

    The service is deterministic — it consults the security singletons, never
    the model.
    """

    def __init__(self) -> None:
        self._param_validators: Dict[str, Callable[[Dict[str, Any]], Optional[str]]] = {}
        self._tool_actions: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_tool_action(self, tool: str, action: str) -> None:
        """Map a tool name to its canonical action (``category:operation``)."""
        self._tool_actions[tool] = action

    def register_parameter_validator(
        self, tool: str, validator: Callable[[Dict[str, Any]], Optional[str]]) -> None:
        """Register a parameter validator for a tool.

        The validator receives the full parameters dict and returns ``None``
        when valid or an error string when invalid.
        """
        self._param_validators[tool] = validator

    def action_for(self, tool: str) -> str:
        return self._tool_actions.get(tool, tool)

    # ------------------------------------------------------------------
    # Parameter validation (step 16)
    # ------------------------------------------------------------------

    def validate_parameters(self, tool: str, parameters: Dict[str, Any]) -> Optional[str]:
        """Validate tool parameters outside the model.

        Returns an error string, or ``None`` if the parameters pass all
        registered validators plus the built-in checks.
        """
        if not isinstance(parameters, dict):
            return "parameters must be a mapping"
        validator = self._param_validators.get(tool)
        if validator is not None:
            try:
                error = validator(parameters)
            except Exception as exc:  # pragma: no cover - defensive
                return f"parameter validator error: {exc}"
            if error:
                return error
        return self._builtin_validation(tool, parameters)

    @staticmethod
    def _builtin_validation(tool: str, parameters: Dict[str, Any]) -> Optional[str]:
        """Built-in parameter hygiene checks (path, command, URL)."""
        for key in ("path", "file_path", "directory", "target"):
            value = parameters.get(key)
            if isinstance(value, str) and value:
                error = _validate_path(value)
                if error:
                    return f"invalid '{key}': {error}"
        if "command" in parameters and isinstance(parameters["command"], str):
            cmd = parameters["command"].strip()
            if not cmd:
                return "command must not be empty"
            if len(cmd) > 8192:
                return "command too long"
        if "url" in parameters and isinstance(parameters["url"], str):
            url = parameters["url"].strip().lower()
            if url.startswith(("file:", "gopher:", "dict:")):
                return "unsupported URL scheme"
        return None

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    def check(self, request: ToolAuthRequest) -> ToolAuthDecision:
        now = time.time()
        action = self.action_for(request.tool) or request.action
        risk = request.risk or self._classify_risk(action, request.resource)

        # 1. Kill switch for tool execution.
        try:
            from aetheros_security.kill_switch import (KillSwitch,
                                                       get_kill_switch_registry)
            if get_kill_switch_registry().is_active(KillSwitch.DISABLE_TOOL_EXECUTION):
                return ToolAuthDecision(ToolAuthOutcome.DENY, request.principal,
                                        request.tool, action, request.resource,
                                        "tool execution disabled by kill switch",
                                        risk, checked_at=now)
        except Exception:
            pass  # fail closed below via authz

        # 2. Parameter validation.
        param_error = self.validate_parameters(request.tool, request.parameters)
        if param_error:
            return ToolAuthDecision(ToolAuthOutcome.DENY, request.principal,
                                    request.tool, action, request.resource,
                                    f"invalid parameters: {param_error}",
                                    risk, checked_at=now)

        # 3. Manifest permission.
        manifest_decision = self._check_manifest(request.tool, action, request.resource)
        if manifest_decision is not None:
            return manifest_decision

        # 4. Authorization engine (policy, session, principal, risk, approval).
        return self._check_engine(request, action, risk, now)

    def _classify_risk(self, action: str, resource: str) -> str:
        try:
            from aetheros_security.authz import get_authorization_engine
            return get_authorization_engine().get_risk(action, resource).value
        except Exception:
            return "medium"

    def _check_manifest(self, tool: str, action: str, resource: str) -> Optional[ToolAuthDecision]:
        try:
            from aetheros_security.manifest import get_manifest_registry
            registry = get_manifest_registry()
            manifest = registry.get(tool)
            if manifest is None:
                return None  # no manifest → fall through to engine (default deny)
            operation = _action_operation(action)
            if not registry.allows(tool, operation, resource):
                return ToolAuthDecision(ToolAuthOutcome.DENY, "", tool, action,
                                        resource,
                                        "tool manifest denies this operation/resource",
                                        "medium")
            return None
        except Exception:
            return None

    def _check_engine(self, request: ToolAuthRequest, action: str, risk: str,
                      now: float) -> ToolAuthDecision:
        try:
            from aetheros_security.authz import (
                AuthorizationRequest as AuthzRequest, Decision,
                get_authorization_engine,
            )
            engine = get_authorization_engine()
            decision = engine.authorize(AuthzRequest(
                principal=request.principal,
                action=action,
                resource=request.resource,
                session=request.session,
                mission=request.mission,
                details={"tool": request.tool, "task": request.task,
                         "agent": request.agent},
            ))
            if decision.decision == Decision.ALLOW:
                return ToolAuthDecision(ToolAuthOutcome.ALLOW, request.principal,
                                        request.tool, action, request.resource,
                                        decision.reason, risk, checked_at=now)
            if decision.decision == Decision.REQUIRE_APPROVAL:
                return ToolAuthDecision(ToolAuthOutcome.APPROVAL_REQUIRED,
                                        request.principal, request.tool, action,
                                        request.resource, decision.reason, risk,
                                        requires_approval=True,
                                        approval_id=decision.approval_id,
                                        checked_at=now)
            if decision.decision == Decision.CHALLENGE:
                return ToolAuthDecision(ToolAuthOutcome.CHALLENGE, request.principal,
                                        request.tool, action, request.resource,
                                        decision.reason, risk, checked_at=now)
            return ToolAuthDecision(ToolAuthOutcome.DENY, request.principal,
                                    request.tool, action, request.resource,
                                    decision.reason, risk, checked_at=now)
        except Exception as exc:
            # Fail closed: if the engine is unavailable, deny.
            return ToolAuthDecision(ToolAuthOutcome.DENY, request.principal,
                                    request.tool, action, request.resource,
                                    f"authorization engine unavailable: {exc}",
                                    risk, checked_at=now)

    # ------------------------------------------------------------------
    # Audit / stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "tools_registered": len(self._tool_actions),
            "validators_registered": len(self._param_validators),
        }


def _action_operation(action: str) -> str:
    """Extract the operation from ``category:operation`` (e.g. 'read')."""
    if ":" in action:
        return action.split(":", 1)[1]
    return action


def _validate_path(path: str) -> Optional[str]:
    """Reject path traversal, UNC, and absolute-path tricks (step 17)."""
    if not path:
        return "empty path"
    lowered = path.replace("\\", "/").lower()
    if "\x00" in path:
        return "null byte in path"
    if lowered.startswith("//"):
        return "UNC path not allowed"
    if ":" in lowered and lowered.split(":", 1)[0].isalpha():
        return "absolute Windows path not allowed"
    # Any dot-run segment of length >= 2 ("..", "...", "....") is a traversal
    # trick once collapsed by the filesystem.
    if any(len(seg) >= 2 and set(seg) == {"."} for seg in lowered.split("/")):
        return "path traversal not allowed"
    if "%2f" in lowered or "%5c" in lowered:
        return "encoded separators not allowed"
    if lowered.endswith(":ads") or "::$" in lowered:
        return "NTFS alternate data stream not allowed"
    return None


# Global tool authorization service
_tool_authz_service: ToolAuthorizationService | None = None


def get_tool_authorization_service() -> ToolAuthorizationService:
    """Return the global ToolAuthorizationService singleton."""
    global _tool_authz_service
    if _tool_authz_service is None:
        _tool_authz_service = ToolAuthorizationService()
    return _tool_authz_service