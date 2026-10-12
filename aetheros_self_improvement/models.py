"""Self-Evolving Intelligence Fabric — shared models (§3-8, §11-12, §20,
§45-46, §52, §83, §92, §109-110, §130, §178).

Pure stdlib dataclasses/enums; no I/O. Status vocabularies are
deliberately narrow: Observed / Inferred / Proposed / Experimented /
Validated / Deployed (§156) and UNVERIFIED / SUPPORTED / VALIDATED /
REJECTED / STALE / CONTRADICTED (§157).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


def _now() -> float:
    return time.time()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Traces (§3-4)
# ---------------------------------------------------------------------------

class TraceLevel(str, Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    DEBUG = "debug"
    FORENSIC = "forensic"


@dataclass
class AgentTrace:
    trace_id: str = field(default_factory=lambda: new_id("tr"))
    task_id: str = ""
    session_id: str = ""
    user_intent: str = ""
    normalized_intent: str = ""
    agent_identity: str = ""
    tenant: str = "default"
    model: str = ""
    model_version: str = ""
    system_configuration: Dict[str, Any] = field(default_factory=dict)
    policy_version: str = ""
    tools_available: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    delegations: List[str] = field(default_factory=list)
    approvals: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    retries: int = 0
    latency_ms: float = 0.0
    token_usage: Dict[str, int] = field(default_factory=dict)
    estimated_cost_usd: float = 0.0
    final_outcome: str = ""
    verification: Dict[str, Any] = field(default_factory=dict)
    user_feedback: str = ""
    level: str = "standard"
    redacted: bool = False
    timestamp: float = field(default_factory=_now)


# ---------------------------------------------------------------------------
# Experience (§6), failures (§7-8), lessons (§20-21)
# ---------------------------------------------------------------------------

class FailureClass(str, Enum):
    PLANNING_FAILURE = "planning"
    REASONING_FAILURE = "reasoning"
    TOOL_SELECTION_FAILURE = "tool_selection"
    TOOL_EXECUTION_FAILURE = "tool_execution"
    OBSERVATION_FAILURE = "observation"
    GROUNDING_FAILURE = "grounding"
    MEMORY_FAILURE = "memory"
    RETRIEVAL_FAILURE = "retrieval"
    MODEL_FAILURE = "model"
    ROUTING_FAILURE = "routing"
    POLICY_FAILURE = "policy"
    AUTHORIZATION_FAILURE = "authorization"
    ENVIRONMENT_FAILURE = "environment"
    NETWORK_FAILURE = "network"
    USER_INTENT_FAILURE = "user_intent"
    VERIFICATION_FAILURE = "verification"
    RECOVERY_FAILURE = "recovery"


class FailureSeverity(str, Enum):
    F0 = "F0"
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"
    F4 = "F4"
    F5 = "F5"


@dataclass
class FailureRecord:
    id: str = field(default_factory=lambda: new_id("fail"))
    trace_id: str = ""
    tenant: str = "default"
    failure_class: str = "tool_execution"
    severity: str = "F3"
    what_happened: str = ""
    what_expected: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    at: float = field(default_factory=_now)


@dataclass
class RootCauseHypothesis:
    failure_id: str
    root_cause: str = ""
    divergence_step: int = -1
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    could_detect_earlier: bool = False
    alternatives: List[str] = field(default_factory=list)


@dataclass
class ExperienceRecord:
    id: str = field(default_factory=lambda: new_id("exp"))
    task: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    approach: str = ""
    actions: List[str] = field(default_factory=list)
    outcome: str = ""
    verification: Dict[str, Any] = field(default_factory=dict)
    failure_id: str = ""
    lesson_id: str = ""
    confidence: float = 0.0
    provenance: Dict[str, Any] = field(default_factory=dict)
    tenant: str = "default"


class LessonScope(str, Enum):
    TASK_SPECIFIC = "task"
    PROJECT_SPECIFIC = "project"
    USER_SPECIFIC = "user"
    TOOL_SPECIFIC = "tool"
    MODEL_SPECIFIC = "model"
    DOMAIN_SPECIFIC = "domain"
    GLOBAL_CANDIDATE = "global_candidate"


class LessonStatus(str, Enum):
    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    VALIDATED = "validated"
    REJECTED = "rejected"
    STALE = "stale"
    CONTRADICTED = "contradicted"


@dataclass
class Lesson:
    id: str = field(default_factory=lambda: new_id("les"))
    observation: str = ""
    evidence: List[str] = field(default_factory=list)
    generalization: str = ""
    scope: str = "task"
    scope_id: str = ""
    confidence: float = 0.0
    status: str = "unverified"
    source_traces: List[str] = field(default_factory=list)
    model_scope: str = ""
    tool_scope: str = ""
    agent_scope: str = ""
    tenant: str = "default"
    expires_at: Optional[float] = None
    knowledge_state: str = "Observed"  # §156 vocabulary
    at: float = field(default_factory=_now)


# ---------------------------------------------------------------------------
# Eval tasks + trials (§11-12, §83)
# ---------------------------------------------------------------------------

@dataclass
class EvalTask:
    id: str = ""
    name: str = ""
    description: str = ""
    category: str = "capability"
    difficulty: str = "medium"
    inputs: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: Any = None
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    failure_criteria: List[str] = field(default_factory=list)
    graders: List[str] = field(default_factory=list)
    timeout_s: float = 60.0
    budget: Dict[str, float] = field(default_factory=dict)
    security_requirements: List[str] = field(default_factory=list)
    version: str = "v1"
    dataset: str = ""
    golden: bool = False
    holdout: bool = False
    platforms: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrialResult:
    trial_id: str = ""
    task_id: str = ""
    configuration: str = ""
    seed: int = 0
    outcome: Any = None
    grader_results: Dict[str, Any] = field(default_factory=dict)
    passed: bool = False
    hard_gate_failed: str = ""
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    tokens: int = 0
    tool_calls: int = 0
    status: str = "done"


# ---------------------------------------------------------------------------
# Experiments, proposals, deployments (§45-46, §92, §109, §130, §178)
# ---------------------------------------------------------------------------

class ProposalStatus(str, Enum):
    DRAFT = "draft"
    ANALYZING = "analyzing"
    EXPERIMENT = "experiment"
    EVALUATED = "evaluated"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ImprovementProposal:
    id: str = field(default_factory=lambda: new_id("prop"))
    title: str = ""
    problem: str = ""
    evidence: List[str] = field(default_factory=list)
    root_cause: str = ""
    hypothesis: str = ""
    candidate_change: Dict[str, Any] = field(default_factory=dict)
    expected_benefit: str = ""
    expected_risk: str = ""
    affected_systems: List[str] = field(default_factory=list)
    evaluation_plan: Dict[str, Any] = field(default_factory=dict)
    rollback_plan: str = ""
    blast_radius: str = "single task"
    required_permissions: List[str] = field(default_factory=list)
    author: str = ""
    status: str = "draft"
    tenant: str = "default"
    at: float = field(default_factory=_now)


@dataclass
class Experiment:
    id: str = field(default_factory=lambda: new_id("exp_run"))
    proposal_id: str = ""
    baseline_config: Dict[str, Any] = field(default_factory=dict)
    candidate_config: Dict[str, Any] = field(default_factory=dict)
    dataset_version: str = ""
    code_version: str = ""
    model_version: str = ""
    policy_version: str = ""
    seed: int = 0
    mode: str = "offline"  # offline | sandbox | shadow | ab | canary
    budgets: Dict[str, float] = field(default_factory=dict)
    status: str = "created"  # created|running|paused|done|cancelled|expired
    results: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)
    tenant: str = "default"
    at: float = field(default_factory=_now)


@dataclass
class Deployment:
    id: str = field(default_factory=lambda: new_id("dep"))
    proposal_id: str = ""
    stage: str = "offline"  # offline|sandbox|shadow|canary|limited|general
    traffic_pct: float = 0.0
    change_id: str = ""
    version: str = ""
    author: str = ""
    reviewer: str = ""
    approval_id: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    state: str = "staged"  # staged|active|demoted|rolled_back|disabled
    tenant: str = "default"
    at: float = field(default_factory=_now)


@dataclass
class DriftEvent:
    id: str = field(default_factory=lambda: new_id("drift"))
    kind: str = ""  # task|model|tool|latency|cost|failure|source|user
    metric: str = ""
    baseline: float = 0.0
    observed: float = 0.0
    threshold: float = 0.0
    at: float = field(default_factory=_now)


class AutonomyLevel(str, Enum):
    I0_OBSERVE = "I0"
    I1_ANALYZE = "I1"
    I2_PROPOSE = "I2"
    I3_EXPERIMENT = "I3"
    I4_CANARY = "I4"
    I5_AUTONOMOUS = "I5"
