"""Master 20 quality-object model layer (P2, P4-7, P11-12, P24, P61, P83-84).

Every object serializes via ``dataclasses.asdict`` (contract-tested). Risk
classification and gate semantics are enforced here so no other module can
quietly redefine them (P16: criteria never silently change — thresholds are
explicit constructor arguments).
"""

from __future__ import annotations

import dataclasses
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


def _now() -> float:
    return time.time()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


class GateStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ChangeRisk(str, Enum):
    TRIVIAL = "TRIVIAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


#: P7 — components whose modification is CRITICAL by definition.
CRITICAL_COMPONENTS = frozenset({
    "security", "authentication", "authorization", "installer",
    "credentials", "secrets", "data_migration", "permission_policy",
    "release", "sandbox",
})

#: P63 — the ONLY change kinds eligible for autonomous application.
SAFE_AUTO_FIX_KINDS = frozenset({
    "formatting", "regenerate_derived_index", "restart_failed_worker",
    "clear_safe_cache",
})


def classify_change_risk(components: List[str],
                         described_risk: str = "LOW") -> ChangeRisk:
    """P7 — risk from actual touched components, upgraded never downgraded
    below the author's own claim when components are critical."""
    risk = ChangeRisk(described_risk) if described_risk in {r.value for r in ChangeRisk} \
        else ChangeRisk.LOW
    order = {r: i for i, r in enumerate(ChangeRisk)}
    for comp in components:
        if comp.lower() in CRITICAL_COMPONENTS:
            if order[ChangeRisk.CRITICAL] > order[risk]:
                risk = ChangeRisk.CRITICAL
    return risk


# ---------------------------------------------------------------- P2/P3/P4

@dataclass
class Baseline:
    baseline_id: str
    label: str                    # previous-release | production | commit | known-good
    version: str
    metrics: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, label: str, version: str,
               metrics: Optional[Dict[str, float]] = None) -> "Baseline":
        return cls(baseline_id=_id("base"), label=label, version=version,
                   metrics=dict(metrics or {}))


@dataclass
class Candidate:
    candidate_id: str
    commit: str = "unknown"
    branch: str = ""
    version: str = ""
    configuration: Dict[str, Any] = field(default_factory=dict)
    model: str = ""
    agent: str = ""
    tool: str = ""
    dependency_changes: List[str] = field(default_factory=list)


@dataclass
class MetricResult:
    name: str
    value: float
    baseline_value: Optional[float] = None
    delta: Optional[float] = None
    direction: str = ""           # improved | regressed | unchanged | new
    threshold: Optional[float] = None
    blocked: bool = False


@dataclass
class EvaluationRun:
    """P2 — one evaluation execution with full reproducibility metadata."""

    target: str
    version: str
    environment: str
    dataset: str
    evaluation_id: str = field(default_factory=lambda: _id("eval"))
    config: Dict[str, Any] = field(default_factory=dict)
    baseline_id: str = ""
    candidate_id: str = ""
    metrics: List[MetricResult] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=_now)
    status: RunStatus = RunStatus.PENDING
    # P90 reproducibility
    code_commit: str = "unknown"
    python_version: str = ""
    platform: str = ""
    dependency_fingerprint: str = ""

    def executed(self) -> bool:
        """P17/P18 anti-fabrication: a run is only reportable when it actually
        executed its checks to completion."""
        return self.status is RunStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["status"] = self.status.value
        d["metrics"] = [dataclasses.asdict(m) for m in self.metrics]
        return d


# ---------------------------------------------------------------- P5/P61

@dataclass
class ChangeProposal:
    """P5/P61/P66 — every field below is mandatory for submission; the
    engine refuses proposals without evidence + rollback plan (P26-27)."""

    description: str
    reason: str
    components: List[str]
    expected_benefit: str
    evidence: List[str]
    rollback_plan: str
    author: str
    files: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)
    benchmarks: List[str] = field(default_factory=list)
    baseline_id: str = ""
    candidate_id: str = ""
    change_id: str = field(default_factory=lambda: _id("chg"))
    risk: ChangeRisk = ChangeRisk.LOW
    approval_status: str = "pending"   # pending|approved|rejected|rolled_back
    auto_applicable: bool = False      # P63: only SAFE_AUTO_FIX kinds
    timestamp: float = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.risk = classify_change_risk(self.components)
        missing = []
        if not self.evidence:
            missing.append("evidence")
        if not self.rollback_plan:
            missing.append("rollback_plan")
        if missing:
            raise ValueError(
                f"proposal rejected: mandatory field(s) missing: {missing}")

    @property
    def requires_human_approval(self) -> bool:
        """P8/P21/P62 — CRITICAL/HIGH always; anything not on the safe
        auto-fix allowlist as well."""
        if self.risk in (ChangeRisk.CRITICAL, ChangeRisk.HIGH):
            return True
        return not self.auto_applicable

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["risk"] = self.risk.value
        return d


# ---------------------------------------------------------------- P11/P12

@dataclass
class Hypothesis:
    """P12 — every optimization states its contract upfront."""

    problem: str
    statement: str
    expected_improvement: str
    metric: str
    risk: str
    measurement_method: str
    rollback_condition: str


@dataclass
class Experiment:
    """P11 — baseline vs candidate under identical criteria."""

    hypothesis: Hypothesis
    baseline_id: str
    candidate_id: str
    environment: str
    experiment_id: str = field(default_factory=lambda: _id("exp"))
    metrics: Dict[str, float] = field(default_factory=dict)
    duration_seconds: float = 0.0
    sample_size: int = 0
    status: RunStatus = RunStatus.PENDING
    result: str = ""               # improved|regressed|neutral|inconclusive
    decision: str = ""             # accept|reject|rollback|escalate

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["hypothesis"] = dataclasses.asdict(self.hypothesis)
        d["status"] = self.status.value
        return d


# ---------------------------------------------------------------- P24/P80/P81

class FailureClassification(str, Enum):
    NEW_FAILURE = "NEW_FAILURE"
    FIXED_FAILURE = "FIXED_FAILURE"
    PRE_EXISTING_FAILURE = "PRE_EXISTING_FAILURE"
    FLAKY = "FLAKY"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    EXPECTED_CHANGE = "EXPECTED_CHANGE"


@dataclass
class QuarantineEntry:
    test_id: str
    reason: str
    quarantined_at: float = field(default_factory=_now)
    failure_history: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.reason or not self.reason.strip():
            # P26: quarantine without explicit reason is refused
            raise ValueError("quarantine requires an explicit reason")


@dataclass
class KnownIssue:
    """P81."""

    issue_id: str
    title: str
    severity: str                  # critical|high|medium|low
    workaround: str
    status: str = "open"           # open|tracked|fixed|wontfix
    owner: str = ""
    affected_versions: List[str] = field(default_factory=list)
    first_seen: float = field(default_factory=_now)


@dataclass
class KnowledgeEntry:
    """P80 — regression knowledge base row."""

    failure: str
    cause: str
    fix: str
    test: str
    version: str
    component: str
    entry_id: str = field(default_factory=lambda: _id("kb"))


# ---------------------------------------------------------------- P83-84

@dataclass
class GateResult:
    gate: str                      # FUNCTIONAL|SECURITY|...
    status: GateStatus
    details: str = ""
    blocking_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class ReleaseScorecard:
    """P83."""

    version: str
    gates: List[GateResult] = field(default_factory=list)
    tests_passed: int = 0
    tests_failed: int = 0
    benchmark_delta: Dict[str, float] = field(default_factory=dict)
    security_findings: List[str] = field(default_factory=list)
    known_issues: List[str] = field(default_factory=list)
    rollback_available: bool = False
    generated_at: float = field(default_factory=_now)

    @property
    def ready(self) -> bool:
        """P84/P98 — any critical BLOCK prevents release."""
        return not any(g.status is GateStatus.BLOCK for g in self.gates)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "gates": [g.to_dict() for g in self.gates],
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "benchmark_delta": dict(self.benchmark_delta),
            "security_findings": list(self.security_findings),
            "known_issues": list(self.known_issues),
            "rollback_available": self.rollback_available,
            "ready": self.ready,
            "generated_at": self.generated_at,
        }


# ---------------------------------------------------------------- P55-56

@dataclass
class Diagnosis:
    """P55 — what/where/when/why/impact/cause/confidence/action."""

    what: str
    where: str
    when: float
    impact: str
    likely_cause: str
    confidence: str                # CONFIRMED|LIKELY|POSSIBLE|UNKNOWN (rca.py)
    recommended_action: str
    evidence: List[str] = field(default_factory=list)
    correlated: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


# ---------------------------------------------------------------- P68-71

class RolloutStage(str, Enum):
    NONE = "0%"
    CANARY = "canary"
    MEDIUM = "medium"
    FULL = "full"


@dataclass
class RolloutState:
    version: str
    stage: RolloutStage = RolloutStage.NONE
    started_at: float = field(default_factory=_now)
    breached: bool = False
    rolled_back: bool = False
    validation: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["stage"] = self.stage.value
        return d
