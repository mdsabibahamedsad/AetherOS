"""Governance health (§116, §152-154, §237-238): subsystem checks,
startup self-test with restricted-mode degradation, trust doctor."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


class GovernanceHealthMonitor:
    SUBSYSTEMS = ("policy engine", "identity authority", "audit ledger",
                  "approval service", "revocation service",
                  "secret boundary", "action firewall",
                  "emergency controller",
                  "reality input pipelines", "reality output pipelines",
                  "reality fusion engine", "reality spatial memory")

    def __init__(self) -> None:
        self._checks: Dict[str, Callable[[], bool]] = {}

    def register(self, subsystem: str, fn: Callable[[], bool]) -> None:
        if subsystem not in self.SUBSYSTEMS:
            raise ValueError(f"unknown subsystem {subsystem}")
        self._checks[subsystem] = fn

    def self_test(self) -> Dict[str, Any]:
        results = {}
        for name in self.SUBSYSTEMS:
            fn = self._checks.get(name)
            try:
                results[name] = bool(fn()) if fn else False
            except Exception:
                results[name] = False
        unhealthy = [k for k, v in results.items() if not v]
        return {"checks": results,
                "mode": "RESTRICTED" if unhealthy else "NORMAL",
                "note": "unhealthy subsystems degrade to restricted, "
                        "never unrestricted (§238)",
                "unhealthy": unhealthy}


def trust_doctor(state: Dict[str, Any]) -> Dict[str, Any]:
    """`aetheros trust doctor` logic over real backend state (§152)."""
    lines = []
    critical, warnings = [], []
    checks = {}
    for name in ("identity", "policy", "audit", "revocation",
                 "emergency", "secrets"):
        ok = bool(state.get(name, {}).get("healthy", False))
        checks[name] = "PASS" if ok else "FAIL"
        if not ok:
            critical.append(f"{name} subsystem unhealthy")
    for agent in state.get("agents", []):
        if "unrestricted" in agent.get("network", ""):
            warnings.append(
                f"Agent {agent.get('id')} has unrestricted network access.")
    if state.get("development_mode"):
        critical.append("Development bypass enabled.")
    for ext in state.get("extensions", []):
        if ext.get("trust") in ("UNKNOWN", "QUARANTINED", "MALICIOUS"):
            warnings.append(
                f"Extension {ext.get('id')}: {ext.get('trust')}.")
    posture = ("CRITICAL" if critical else
               "MODERATE" if warnings else "GOOD")
    lines.append("AetherOS Trust Health")
    for k, v in checks.items():
        lines.append(f"{k:20s} {v}")
    for w in warnings:
        lines.append(f"WARNING {w}")
    for c in critical:
        lines.append(f"CRITICAL {c}")
    return {"report": "\n".join(lines), "posture": posture,
            "critical": critical, "warnings": warnings}
