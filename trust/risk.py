"""Risk engine (§16-18): deterministic R0-R8 classification,
dynamic re-evaluation during execution, blast-radius accounting.
Extends M50's R0-R5 `classify_risk` (reused for the base mapping)."""
from __future__ import annotations

from typing import Dict, List, Optional

from aetheros_control_plane.policy_risk import (
    RiskLevel as M50Risk,
    classify_risk as m50_classify,
)

from .models import Risk, RiskAssessment, risk_at_least, risk_order

_BASE_MAP = {
    M50Risk.R0_READ_ONLY: Risk.R0_INFORMATIONAL,
    M50Risk.R1_LOCAL_REVERSIBLE: Risk.R2_REVERSIBLE_LOCAL,
    M50Risk.R2_EXTERNAL_SIDE_EFFECT: Risk.R3_EXTERNAL_COMM,
    M50Risk.R3_SENSITIVE_DATA: Risk.R4_CREDENTIAL_DATA,
    M50Risk.R4_HIGH_IMPACT: Risk.R5_FINANCIAL_LEGAL_ORG,
    M50Risk.R5_CRITICAL: Risk.R8_IRREVERSIBLE_CRITICAL,
}

_INFRA_HINTS = ("infra", "production", "database", "migrate", "deploy",
                "kubernetes", "terraform", "systemd", "kernel")
_PHYSICAL_HINTS = ("robot", "actuator", "motor", "drone", "arm ",
                   "gripper", "cobot", "plc", "physical")
_FINANCIAL_HINTS = ("payment", "charge", "refund", "invoice", "payroll",
                    "contract", "legal", "lawsuit", "insurance")
_IRREVERSIBLE_HINTS = ("delete production", "drop database", "rm -rf /",
                       "publish private key", "broadcast")


class RiskEngine:
    def classify(self, capability: str, resource: str = "",
                 data_class: str = "internal",
                 context: Optional[Dict] = None) -> RiskAssessment:
        ctx = context or {}
        cap, res = capability.lower(), resource.lower()
        text = f"{cap} {res}"
        base = m50_classify(capability, resource, data_class, ctx)
        level = _BASE_MAP[base]
        reasons = [f"m50-base={base.value}"]
        if any(h in text for h in _IRREVERSIBLE_HINTS):
            level, reasons = Risk.R8_IRREVERSIBLE_CRITICAL, reasons + [
                "irreversible/high-consequence marker"]
        elif any(h in text for h in _PHYSICAL_HINTS):
            if risk_at_least(level, Risk.R3_EXTERNAL_COMM) or \
                    "move" in text or "grasp" in text or "speed" in text:
                level = max(level, Risk.R7_PHYSICAL_WORLD,
                            key=lambda r: _order(r))
                reasons.append("physical-world action")
        elif any(h in text for h in _INFRA_HINTS):
            if risk_at_least(level, Risk.R2_REVERSIBLE_LOCAL):
                level = max(level, Risk.R6_INFRA_MODIFICATION,
                            key=lambda r: _order(r))
                reasons.append("infrastructure modification")
        elif any(h in text for h in _FINANCIAL_HINTS):
            level = max(level, Risk.R5_FINANCIAL_LEGAL_ORG,
                        key=lambda r: _order(r))
            reasons.append("financial/legal/organizational impact")
        # R1 read-only: explicit read markers stay low
        if cap.startswith(("read", "get", "list", "describe", "search")) \
                and level == Risk.R2_REVERSIBLE_LOCAL:
            level, reasons = Risk.R1_READ_ONLY, reasons + ["read-only"]
        blast = self.blast_radius(capability, resource, ctx)
        return RiskAssessment(
            level=level,
            irreversibility=(level == Risk.R8_IRREVERSIBLE_CRITICAL),
            blast_radius=blast, reasons=tuple(reasons))

    def blast_radius(self, capability: str, resource: str,
                     context: Optional[Dict] = None) -> Dict[str, int]:
        """Conservative counts from explicit scope hints (§18). Unknowns
        are reported as 0 with scope_unknown=1 — never invented."""
        ctx = context or {}
        out = {"files_affected": int(ctx.get("files_affected", 0)),
               "records_affected": int(ctx.get("records_affected", 0)),
               "users_affected": int(ctx.get("users_affected", 0)),
               "systems_affected": int(ctx.get("systems_affected", 0)),
               "agents_affected": int(ctx.get("agents_affected", 0)),
               "scope_unknown": 0}
        if resource.endswith(("**", "/*")) or resource in ("*", "/"):
            out["scope_unknown"] = 1
        return out

    def reevaluate(self, current: RiskAssessment,
                   discovered: Dict[str, str]) -> RiskAssessment:
        """Dynamic escalation mid-execution (§17): R1 -> R4/R6 on new
        discoveries. Never de-escalates without explicit reason."""
        level, reasons = current.level, list(current.reasons)
        for marker, target, why in (
                ("credential", Risk.R4_CREDENTIAL_DATA,
                 "credentialed endpoint discovered"),
                ("production", Risk.R6_INFRA_MODIFICATION,
                 "production system discovered"),
                ("secret", Risk.R4_CREDENTIAL_DATA,
                 "secret material discovered"),
                ("human-present", Risk.R7_PHYSICAL_WORLD,
                 "human entered physical scope")):
            if marker in " ".join(discovered.values()).lower():
                if _order(target) > _order(level):
                    level, reasons = target, reasons + [why]
        return RiskAssessment(
            level=level, impact=current.impact,
            likelihood=current.likelihood,
            irreversibility=current.irreversibility or
            level == Risk.R8_IRREVERSIBLE_CRITICAL,
            blast_radius=current.blast_radius, reasons=tuple(reasons))

    def gate_for(self, level: Risk) -> str:
        """fast/normal/full path routing (§230)."""
        if level in (Risk.R0_INFORMATIONAL, Risk.R1_READ_ONLY):
            return "fast"
        if level in (Risk.R2_REVERSIBLE_LOCAL, Risk.R3_EXTERNAL_COMM):
            return "normal"
        return "full"


def _order(level: Risk) -> int:
    return risk_order(level)
