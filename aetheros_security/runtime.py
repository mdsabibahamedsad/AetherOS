"""
Security Runtime Context for AetherOS
=====================================

Thread-local (ContextVar-bound) security context for zero-trust authorization.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class SecurityContext:
    """Security context bound to the current execution flow.

    Attributes:
        principal: The current principal (user/agent/etc.) making requests.
        user_id: The user ID if the principal is a user or agent acting on behalf.
        agent_id: The agent ID if the principal is an agent or subagent.
        session_token: Valid session token for the principal (if any).
        delegation_depth: Remaining delegation depth allowed (0 = no further delegation).
        mission: Current mission or workflow ID.
        task: Current task or goal ID.
        attributes: Additional context attributes.
    """
    principal: str = ""
    user_id: str = ""
    agent_id: str = ""
    session_token: str = ""
    delegation_depth: int = 0
    mission: str = ""
    task: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)


# Context variable holding the current security context.
# When unset, returns a default-constructed SecurityContext (empty values).
_SECURITY_CONTEXT: ContextVar[SecurityContext] = ContextVar(
    "AETHEROS_SECURITY_CONTEXT",
    default=SecurityContext(),
)


def get_security_context() -> SecurityContext:
    """Return the current security context."""
    return _SECURITY_CONTEXT.get()


def set_security_context(context: SecurityContext) -> None:
    """Set the current security context."""
    _SECURITY_CONTEXT.set(context)


def clear_security_context() -> None:
    """Clear the security context (reset to default empty values)."""
    _SECURITY_CONTEXT.set(SecurityContext())


def run_with_security_context(
    func: Any,
    *args: Any,
    context: SecurityContext | None = None,
    **kwargs: Any,
) -> Any:
    """Run a function with a temporary security context.

    Args:
        func: Function to call.
        context: Security context to set during the call.
        *args, **kwargs: Arguments to pass to func.

    Returns:
        The result of calling func.
    """
    token = _SECURITY_CONTEXT.set(context or SecurityContext())
    try:
        return func(*args, **kwargs)
    finally:
        _SECURITY_CONTEXT.reset(token)