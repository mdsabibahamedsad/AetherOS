"""Aetheros quality engine — Master 20 evaluation/reliability layer.

Composes ``aetheros_observability`` and ``aetheros_reliability`` primitives.
The layer observes, measures, evaluates, gates and proposes; it never
autonomously modifies product code beyond the SAFE_AUTO_FIX allowlist.
"""

from agent.quality.benchmarks import (
    BaselineStore,
    BenchmarkCheck,
    BenchmarkEngine,
    ComparisonPolicy,
    artifact_hash,
    compare_to_baseline,
    reproducibility_metadata,
)
from agent.quality.datasets import (
    DatasetIntegrityError,
    DatasetRegistry,
    DatasetVersion,
)
from agent.quality.diagnostics import (
    ChangeRecord,
    DiagnosticEngine,
    FailureRecord,
)
from agent.quality.gates import GATE_NAMES, GateInput, ReleaseGateEngine
from agent.quality.improvement import (
    FailureSignal,
    ProposalEngine,
    UnsafeAutoApply,
)
from agent.quality.knowledge import (
    KnownIssuesDatabase,
    RegressionKnowledgeBase,
    seed_documented_issues,
)
from agent.quality.metrics import (
    ErrorBudget,
    QualityMetrics,
    SLO,
    TaskRecord,
    cost_summary,
    recovery_score,
)
from agent.quality.models import (
    CRITICAL_COMPONENTS,
    SAFE_AUTO_FIX_KINDS,
    Baseline,
    Candidate,
    ChangeProposal,
    ChangeRisk,
    Diagnosis,
    EvaluationRun,
    Experiment,
    FailureClassification,
    GateResult,
    GateStatus,
    Hypothesis,
    KnownIssue,
    KnowledgeEntry,
    MetricResult,
    QuarantineEntry,
    ReleaseScorecard,
    RolloutStage,
    RolloutState,
    RunStatus,
    classify_change_risk,
)
from agent.quality.regression import (
    SuiteResult,
    QuarantineRegistry,
    FlakyTracker,
    classify_regressions,
    prioritize,
)
from agent.quality.rollout import RolloutController, RolloutPolicy
from agent.quality.trends import TrendAlert, TrendTracker

__all__ = [
    "CRITICAL_COMPONENTS",
    "SAFE_AUTO_FIX_KINDS",
    "Baseline",
    "BaselineStore",
    "BenchmarkCheck",
    "BenchmarkEngine",
    "Candidate",
    "ChangeProposal",
    "ChangeRecord",
    "ChangeRisk",
    "ComparisonPolicy",
    "DatasetIntegrityError",
    "DatasetRegistry",
    "DatasetVersion",
    "Diagnosis",
    "DiagnosticEngine",
    "ErrorBudget",
    "EvaluationRun",
    "Experiment",
    "FailureClassification",
    "FailureRecord",
    "FailureSignal",
    "FlakyTracker",
    "GATE_NAMES",
    "GateInput",
    "GateResult",
    "GateStatus",
    "Hypothesis",
    "KnownIssue",
    "KnownIssuesDatabase",
    "KnowledgeEntry",
    "MetricResult",
    "ProposalEngine",
    "QualityMetrics",
    "QuarantineEntry",
    "QuarantineRegistry",
    "ReleaseGateEngine",
    "ReleaseScorecard",
    "RolloutController",
    "RolloutPolicy",
    "RolloutStage",
    "RolloutState",
    "RunStatus",
    "SLO",
    "SuiteResult",
    "TaskRecord",
    "TrendAlert",
    "TrendTracker",
    "UnsafeAutoApply",
    "artifact_hash",
    "classify_change_risk",
    "classify_regressions",
    "compare_to_baseline",
    "cost_summary",
    "prioritize",
    "recovery_score",
    "reproducibility_metadata",
    "seed_documented_issues",
]
