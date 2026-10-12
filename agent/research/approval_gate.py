"""Consequential-action gate (P89).

Research itself must never send emails, publish, upload, purchase, or
modify accounts. This module makes that policy enforceable rather than
conventional: ANY future consequential external action MUST pass through
``request_consequential_action`` before executing.

Fail-closed by default: with no approver wired (CLI interactive prompt,
gateway approval round-trip via tools/approval.py, etc.) the action is
refused. "Silence is not consent" — same doctrine as the command-approval
system this composes with when the agent runtime provides one.
"""

from __future__ import annotations

from typing import Callable, Optional


Approver = Callable[[str, str], bool]

_ALLOWED_ACTION_PREFIXES = (
    # The only actions research performs today are read-only.
    "research.search",
    "research.fetch",
    "research.ingest_local",
)


class ConsequentialActionBlocked(Exception):
    def __init__(self, action: str, detail: str):
        self.action = action
        self.detail = detail
        super().__init__(f"blocked {action}: no approval for {detail}")


def is_readonly_research_action(action: str) -> bool:
    return any(action.startswith(p) for p in _ALLOWED_ACTION_PREFIXES)


def request_consequential_action(
    action: str,
    detail: str = "",
    approver: Optional[Approver] = None,
) -> bool:
    """Gate a potentially consequential external action.

    - Read-only research actions pass unconditionally.
    - Everything else requires an approver callback returning True.
    - No approver -> blocked (fail closed).
    """
    if is_readonly_research_action(action):
        return True
    if approver is None:
        raise ConsequentialActionBlocked(action, detail or "no approver configured")
    approved = bool(approver(action, detail))
    if not approved:
        raise ConsequentialActionBlocked(action, detail or "approver denied")
    return True
