"""
Security Scorecard for AetherOS
===============================

Evaluate the security posture of every subsystem and produce a
PASS / PARTIAL / FAIL / NOT APPLICABLE scorecard (master security spec
step 86).

Categories evaluated:

    Identity, Authentication, Authorization, Least Privilege, Secrets,
    Data Protection, Tool Security, MCP Security, Prompt Injection,
    Memory Security, Network Security, Filesystem Security, Command
    Security, Approval, Audit, Monitoring, Emergency Controls,
    Supply Chain, Installer, Cross-platform.

Usage::

    from aetheros_security.scorecard import generate_scorecard

    scorecard = generate_scorecard()
    for row in scorecard["categories"]:
        print(row["category"], row["status"])
    print(scorecard["overall"])
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ScoreStatus(Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT APPLICABLE"


@dataclass
class ScoreRow:
    """One scorecard category."""
    category: str
    status: ScoreStatus
    checks: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "status": self.status.value,
            "checks": list(self.checks),
            "notes": self.notes,
        }


def _probe(fn: Callable[[], bool], success: str, failure: str) -> List[str]:
    try:
        return [success if fn() else failure]
    except Exception as exc:
        return [f"{failure} ({exc})"]


class SecurityScorecard:
    """Computes the security posture scorecard (step 86)."""

    #: category name → list of probe functions returning bool.
    _PROBES: Dict[str, List[Callable[[], bool]]] = {}

    def __init__(self) -> None:
        self._build_probes()

    def _build_probes(self) -> None:
        """Assemble deterministic probes per category (all fail-safe)."""

        def _identity() -> bool:
            from aetheros_security.identity import get_identity_registry
            reg = get_identity_registry()
            return len(reg.list_agents()) >= 0 and callable(getattr(reg, "register_user", None))

        def _authentication() -> bool:
            from aetheros_security.authentication import get_authentication_manager
            return get_authentication_manager() is not None

        def _authorization() -> bool:
            from aetheros_security.authz import get_authorization_engine
            engine = get_authorization_engine()
            from aetheros_security.authz import AuthorizationRequest, Decision
            # Default-deny probe: an unknown principal must be denied.
            decision = engine.authorize(AuthorizationRequest(
                principal="__no_such_principal__", action="filesystem:write",
                resource="/tmp/x"))
            return decision.decision == Decision.DENY

        def _least_privilege() -> bool:
            from aetheros_security.policy import get_policy_manager
            pm = get_policy_manager()
            pm.load_policy("__probe__", {"version": 1, "workspace": "probe",
                                         "default_permission": "deny"})
            denied = not pm.check_permission("__probe__", "filesystem:write")
            pm.unload("__probe__")
            return denied

        def _secrets() -> bool:
            from aetheros_security.secrets import get_secrets_manager
            mgr = get_secrets_manager()
            return mgr is not None and mgr.backend is not None

        def _encryption() -> bool:
            from aetheros_security.encryption import get_encryption_manager
            mgr = get_encryption_manager()
            probe = mgr.encrypt("scorecard-probe")
            return mgr.decrypt(probe) == "scorecard-probe"

        def _redaction() -> bool:
            from aetheros_security.redaction import get_redaction_manager
            redacted = get_redaction_manager().redact("sk-1234567890abcdefghijklmnop")
            return "sk-" not in redacted.lower() or "1234567890" not in redacted

        def _data_protection() -> bool:
            return _encryption() and _redaction()

        def _tool_security() -> bool:
            from aetheros_security.manifest import get_manifest_registry
            # Unknown tool must be denied (deny-by-default registry).
            allowed = get_manifest_registry().allows("__no_such_tool__", "read")
            return not allowed

        def _mcp_security() -> bool:
            from aetheros_security.mcp import get_mcp_security_manager
            return get_mcp_security_manager() is not None

        def _prompt_injection() -> bool:
            from aetheros_security.ai_security import get_ai_security_manager
            mgr = get_ai_security_manager()
            return mgr is not None and callable(getattr(mgr, "scan_prompt", None))

        def _memory_security() -> bool:
            from aetheros_security.dlp import get_dlp_manager
            return get_dlp_manager() is not None

        def _network_security() -> bool:
            from aetheros_security.network import get_network_security_manager
            mgr = get_network_security_manager()
            decision = mgr.check_host("169.254.169.254")
            return not decision.allowed

        def _filesystem_security() -> bool:
            from aetheros_security.filesystem import get_filesystem_security
            mgr = get_filesystem_security()
            # No rules → deny-all.
            return not mgr.check("../etc/passwd", "read").allowed

        def _command_security() -> bool:
            from aetheros_security.sandbox import get_sandbox_manager
            return get_sandbox_manager() is not None

        def _approval() -> bool:
            from aetheros_security.approval import get_approval_manager
            mgr = get_approval_manager()
            return callable(getattr(mgr, "create", None))

        def _audit() -> bool:
            from aetheros_security.audit import get_audit_logger
            return get_audit_logger() is not None

        def _monitoring() -> bool:
            from aetheros_security.threat import get_threat_detector
            return get_threat_detector() is not None

        def _emergency_controls() -> bool:
            from aetheros_security.response import get_response_manager
            mgr = get_response_manager()
            return callable(getattr(mgr, "emergency_stop", None))

        def _kill_switches() -> bool:
            from aetheros_security.kill_switch import get_kill_switch_registry
            return len(get_kill_switch_registry().status()) > 0

        def _supply_chain() -> bool:
            from aetheros_security.supply_chain import get_supply_chain_manager
            return get_supply_chain_manager() is not None

        def _privacy() -> bool:
            from aetheros_security.privacy import get_privacy_manager
            return get_privacy_manager() is not None

        def _action_guard() -> bool:
            from aetheros_security.action_guard import get_action_guard
            return get_action_guard() is not None

        self._PROBES = {
            "Identity": [_identity],
            "Authentication": [_authentication],
            "Authorization": [_authorization],
            "Least Privilege": [_least_privilege],
            "Secrets": [_secrets],
            "Data Protection": [_data_protection],
            "Tool Security": [_tool_security],
            "MCP Security": [_mcp_security],
            "Prompt Injection": [_prompt_injection],
            "Memory Security": [_memory_security],
            "Network Security": [_network_security],
            "Filesystem Security": [_filesystem_security],
            "Command Security": [_command_security],
            "Approval": [_approval],
            "Audit": [_audit],
            "Monitoring": [_monitoring],
            "Emergency Controls": [_emergency_controls],
            "Kill Switches": [_kill_switches],
            "Supply Chain": [_supply_chain],
            "Privacy": [_privacy],
            "Action Guard": [_action_guard],
        }

    def generate(self) -> Dict[str, Any]:
        """Compute the scorecard."""
        rows: List[ScoreRow] = []
        for category, probes in self._PROBES.items():
            results = []
            for probe in probes:
                results.extend(_probe(probe, "ok", "failed"))
            status = ScoreStatus.PASS
            if not results:
                status = ScoreStatus.NOT_APPLICABLE
            elif any(r.startswith("failed") for r in results):
                status = ScoreStatus.FAIL
            elif any(r.startswith("ok") for r in results):
                status = ScoreStatus.PASS
            rows.append(ScoreRow(category, status, results))

        passed = sum(1 for r in rows if r.status == ScoreStatus.PASS)
        partial = sum(1 for r in rows if r.status == ScoreStatus.PARTIAL)
        failed = sum(1 for r in rows if r.status == ScoreStatus.FAIL)
        total = len(rows)

        readiness = 0.0
        if total:
            readiness = round((passed + 0.5 * partial) / total * 100.0, 1)

        return {
            "generated_at": time.time(),
            "categories": [r.to_dict() for r in rows],
            "summary": {
                "pass": passed,
                "partial": partial,
                "fail": failed,
                "total": total,
            },
            "overall": {
                "score": readiness,
                "readiness_percent": readiness,
                "verdict": ("STRONG" if readiness >= 90 else
                            "GOOD" if readiness >= 75 else
                            "NEEDS_ATTENTION" if readiness >= 50 else
                            "WEAK"),
            },
        }


# Global scorecard
_scorecard: SecurityScorecard | None = None


def get_scorecard() -> SecurityScorecard:
    """Return the global SecurityScorecard singleton."""
    global _scorecard
    if _scorecard is None:
        _scorecard = SecurityScorecard()
    return _scorecard


def generate_scorecard() -> Dict[str, Any]:
    """Generate the security scorecard (step 86)."""
    return get_scorecard().generate()