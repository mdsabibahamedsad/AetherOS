"""Policy-aware execution bridge (Master 62 §2, §10-11, §90).

Developer API -> Intent -> Policy Evaluation -> Capability Resolution ->
Approval -> Execution. SDK calls can NEVER reach raw privileged actions:
every intent is evaluated, decided (allowed/denied/approval_required/
sandbox_required/credential_required), and audited.

Integrates the real `aetheros_security.policy.PolicyManager` as one signal;
deny-by-default capability resolution is enforced in this module so a missing
policy file can never become an allow-all.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from aetheros_platform.errors import err

OUTCOMES = ("allowed", "denied", "approval_required", "sandbox_required",
            "credential_required")

# Risk level -> minimum handling.
RISK_HANDLING = {
    "LOW": "allowed",
    "MEDIUM": "allowed",
    "HIGH": "approval_required",
    "CRITICAL": "approval_required",
}

# Capability -> risk class for resolution when the tool manifest is silent.
CAPABILITY_RISK = {
    "filesystem.read": "LOW", "memory.read": "LOW", "browser.read": "LOW",
    "research.search": "LOW", "research.fetch": "MEDIUM",
    "filesystem.write": "HIGH", "terminal.execute": "HIGH",
    "browser.navigate": "MEDIUM", "browser.click": "MEDIUM",
    "browser.type": "MEDIUM", "network.http": "MEDIUM",
    "memory.write": "MEDIUM", "artifact.create": "LOW",
    "automation.create": "HIGH", "messaging.send": "HIGH",
    "email.send": "CRITICAL", "calendar.modify": "HIGH",
    "computer.input": "CRITICAL", "device.control": "CRITICAL",
    "robot.control": "CRITICAL",
}


def _platform_policy_signal(capability: str) -> Optional[bool]:
    """Consult the real platform PolicyManager; None = no opinion."""
    try:
        from aetheros_security.policy import get_policy_manager
        mgr = get_policy_manager()
        for policy in mgr.get_loaded_policies() or []:
            name = policy if isinstance(policy, str) else policy.get("name", "")
            if not name:
                continue
            verdict = mgr.check_permission(name, capability)
            if verdict is False:
                return False
        return None
    except Exception:
        return None


class PolicyBridge:
    def __init__(self, audit=None) -> None:
        self._audit = audit

    def evaluate(self, intent: Dict[str, Any],
                 grants: List[str]) -> Dict[str, Any]:
        """Evaluate an intent against grants. Never raises for denies."""
        capability = intent.get("capability", "")
        actor = intent.get("actor", "")
        now = time.time()
        decision: Dict[str, Any] = {
            "decision_id": f"pol_{uuid.uuid4().hex[:12]}",
            "capability": capability, "actor": actor,
            "outcome": "denied", "reason": "capability not granted",
            "evaluated_at": now,
        }
        if not capability:
            decision["reason"] = "no capability declared"
            self._record(decision, intent)
            return decision
        if capability not in grants:
            self._record(decision, intent)
            return decision
        if _platform_policy_signal(capability) is False:
            decision["reason"] = "platform policy denied"
            self._record(decision, intent)
            return decision
        risk = CAPABILITY_RISK.get(capability, "HIGH")
        handling = RISK_HANDLING.get(risk, "approval_required")
        if risk in ("CRITICAL",) or intent.get("side_effects_irreversible"):
            handling = "approval_required"
        decision["outcome"] = handling
        decision["reason"] = f"granted; risk={risk}"
        self._record(decision, intent)
        return decision

    def require_allowed(self, intent: Dict[str, Any], grants: List[str]) -> Dict[str, Any]:
        decision = self.evaluate(intent, grants)
        if decision["outcome"] != "allowed":
            raise err("POLICY_DENIED" if decision["outcome"] == "denied" else "APPROVAL_REQUIRED",
                      f"intent blocked: {decision['reason']}",
                      capability=intent.get("capability", ""),
                      policyDecision=decision["decision_id"],
                      remediation="request approval or narrow the capability")
        return decision

    def _record(self, decision: Dict[str, Any], intent: Dict[str, Any]) -> None:
        if self._audit is not None:
            try:
                self._audit("policy.decision", decision["actor"], decision["capability"],
                            decision["outcome"], {"decision_id": decision["decision_id"]})
            except Exception:
                pass
