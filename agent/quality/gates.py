"""Release gates + scorecard (P82-84, P98).

Seven gates: FUNCTIONAL, SECURITY, PERFORMANCE, RELIABILITY, COMPATIBILITY,
INSTALLER, DOCUMENTATION. Each consumes measured facts; critical BLOCKs
prevent release. The scorecard is generated, never asserted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.quality.models import (
    GateResult,
    GateStatus,
    KnownIssue,
    ReleaseScorecard,
)


GATE_NAMES = (
    "FUNCTIONAL", "SECURITY", "PERFORMANCE", "RELIABILITY",
    "COMPATIBILITY", "INSTALLER", "DOCUMENTATION",
)


@dataclass
class GateInput:
    """Measured facts feeding one gate."""

    gate: str
    checks_passed: int = 0
    checks_failed: int = 0
    critical_failures: int = 0
    details: str = ""

    @property
    def result(self) -> GateResult:
        if self.critical_failures > 0 or (
                self.checks_failed > 0 and self.checks_passed == 0):
            return GateResult(
                gate=self.gate, status=GateStatus.BLOCK,
                details=self.details,
                blocking_reason=f"{self.critical_failures} critical failures"
                if self.critical_failures else "all checks failed",
            )
        if self.checks_failed > 0:
            return GateResult(
                gate=self.gate, status=GateStatus.WARN,
                details=f"{self.checks_failed} non-critical failures; "
                        f"{self.details}",
            )
        return GateResult(gate=self.gate, status=GateStatus.PASS,
                          details=self.details)


class ReleaseGateEngine:
    def evaluate(self, inputs: List[GateInput],
                 *, known_issues: Optional[List[KnownIssue]] = None,
                 benchmark_delta: Optional[Dict[str, float]] = None,
                 security_findings: Optional[List[str]] = None,
                 rollback_available: bool = False,
                 tests_passed: int = 0, tests_failed: int = 0,
                 version: str = "unknown") -> ReleaseScorecard:
        by_name = {i.gate.upper(): i for i in inputs}
        gates: List[GateResult] = []
        for name in GATE_NAMES:
            gi = by_name.get(name)
            if gi is None:
                # P98: a missing gate evaluation is a BLOCK, not a pass
                gates.append(GateResult(
                    gate=name, status=GateStatus.BLOCK,
                    blocking_reason="gate never evaluated",
                ))
            else:
                gates.append(gi.result)

        # security findings escalate the SECURITY gate
        if security_findings:
            for g in gates:
                if g.gate == "SECURITY":
                    g.status = GateStatus.BLOCK
                    g.blocking_reason = (
                        f"{len(security_findings)} open security findings")

        # P98: rollback must be available where required
        if not rollback_available:
            for g in gates:
                if g.status is GateStatus.PASS:
                    g.status = GateStatus.WARN
                    g.details = (g.details + " | rollback unavailable").strip(" |")

        critical_open = [k for k in (known_issues or [])
                         if k.severity == "critical" and k.status == "open"]
        if critical_open:
            for g in gates:
                if g.status is GateStatus.PASS:
                    g.status = GateStatus.WARN
                    g.details += f" | {len(critical_open)} critical known issues"

        return ReleaseScorecard(
            version=version,
            gates=gates,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            benchmark_delta=dict(benchmark_delta or {}),
            security_findings=list(security_findings or []),
            known_issues=[k.issue_id for k in (known_issues or [])
                          if k.status == "open"],
            rollback_available=rollback_available,
        )
