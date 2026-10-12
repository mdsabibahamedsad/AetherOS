"""Master 53 core models: tasks, research, hypotheses, experiments,
evidence, discovery. All dataclasses with explicit status labels."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _now() -> float:
    return time.time()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------- tasks ---
class TaskStatus:
    CREATED = "CREATED"
    UNDERSTANDING = "UNDERSTANDING"
    RESEARCHING = "RESEARCHING"
    HYPOTHESIS_GENERATION = "HYPOTHESIS_GENERATION"
    HYPOTHESIS_REVIEW = "HYPOTHESIS_REVIEW"
    EXPERIMENT_DESIGN = "EXPERIMENT_DESIGN"
    SIMULATING = "SIMULATING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    ANALYZING = "ANALYZING"
    VALIDATING = "VALIDATING"
    REFINING = "REFINING"
    DISCOVERED = "DISCOVERED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ScientificTask:
    id: str = field(default_factory=lambda: new_id("sci"))
    title: str = ""
    question: str = ""
    domain: str = "general"
    subdomain: str = ""
    objective: str = ""
    background: str = ""
    known_facts: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    resources: Dict[str, float] = field(default_factory=dict)
    research_mode: str = "LOCAL_ONLY"  # LOCAL_ONLY | NETWORK | MIXED
    experiment_mode: str = "COMPUTATIONAL"  # COMPUTATIONAL | SIMULATION | PHYSICAL_LAB
    simulation_mode: str = "OFFLINE"
    autonomy_level: int = 1
    risk_level: str = "LOW"
    deadline: Optional[float] = None
    budget: Dict[str, float] = field(default_factory=dict)
    compute_budget: Dict[str, float] = field(default_factory=dict)
    evidence_threshold: str = "E3"
    reproducibility_requirement: int = 1
    human_approval_policy: str = "HIGH_RISK"
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    status: str = TaskStatus.CREATED
    history: List[Dict[str, Any]] = field(default_factory=list)
    owner: str = "default"
    team: str = "default"


# --------------------------------------------------------------- research ---
@dataclass
class ResearchSource:
    id: str = field(default_factory=lambda: new_id("src"))
    kind: str = "USER_PROVIDED"  # PAPER | DATASET | DOCS | BENCHMARK | USER_PROVIDED | ...
    title: str = ""
    authors: List[str] = field(default_factory=list)
    uri: str = ""
    doi: str = ""
    retrieved_at: float = field(default_factory=_now)
    published_at: Optional[float] = None
    content_excerpt: str = ""
    trust: str = "USER_PROVIDED"  # LOCAL | TRUSTED_REMOTE | UNTRUSTED_REMOTE | ...
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Claim:
    id: str = field(default_factory=lambda: new_id("clm"))
    text: str = ""
    source_id: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    confidence: str = "unknown"  # qualitative only: low | medium | high | unknown
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchLandscape:
    task_id: str = ""
    sources: List[ResearchSource] = field(default_factory=list)
    claims: List[Claim] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    datasets: List[str] = field(default_factory=list)
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    built_at: float = field(default_factory=_now)


@dataclass
class KnowledgeGap:
    id: str = field(default_factory=lambda: new_id("gap"))
    description: str = ""
    importance: float = 0.5
    uncertainty: float = 0.5
    affected_hypotheses: List[str] = field(default_factory=list)
    available_tests: List[str] = field(default_factory=list)
    expected_information_gain: float = 0.0
    cost: float = 1.0
    risk: float = 0.0
    priority: float = 0.0  # EIG * importance * feasibility / cost


# -------------------------------------------------------------- hypothesis ---
class HypothesisStatus:
    PROPOSED = "PROPOSED"  # == UNVALIDATED HYPOTHESIS
    SUPPORTED = "SUPPORTED"
    CONTESTED = "CONTESTED"
    WEAKENED = "WEAKENED"
    FALSIFIED = "FALSIFIED"
    VALIDATED = "VALIDATED"
    SUPERSEDED = "SUPERSEDED"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass
class Hypothesis:
    id: str = field(default_factory=lambda: new_id("hyp"))
    task_id: str = ""
    statement: str = ""
    mechanism: str = ""
    assumptions: List[str] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
    conflicting_evidence: List[str] = field(default_factory=list)
    predictions: List[str] = field(default_factory=list)
    variables: Dict[str, List[str]] = field(default_factory=dict)
    causal_claims: List[str] = field(default_factory=list)
    strategy: str = "EXPLANATORY"
    family: str = ""
    novelty: str = "UNCERTAIN"  # NOVEL | POTENTIALLY_NOVEL | KNOWN_VARIANT | KNOWN | DUPLICATE | UNCERTAIN
    novelty_confidence: str = "unknown"
    plausibility: str = "unknown"
    testability: str = "unknown"
    falsifiability: str = "unknown"
    evidence_strength: str = "E0"
    risk: str = "unknown"
    uncertainty: str = "high"
    status: str = HypothesisStatus.PROPOSED
    version: int = 1
    prior_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=_now)


@dataclass
class HypothesisReview:
    hypothesis_id: str = ""
    strongest_argument: str = ""
    strongest_counterargument: str = ""
    missing_evidence: List[str] = field(default_factory=list)
    confounders: List[str] = field(default_factory=list)
    alternative_explanations: List[str] = field(default_factory=list)
    falsification_test: str = ""
    reproducibility_concerns: List[str] = field(default_factory=list)
    safety_concerns: List[str] = field(default_factory=list)
    confidence: str = "unknown"
    reviewer: str = "SkepticAgent"


@dataclass
class FalsificationCriteria:
    hypothesis_id: str = ""
    weaken_observation: str = ""
    falsify_observation: str = ""
    support_observation: str = ""
    inconclusive_observation: str = ""


# -------------------------------------------------------------- experiment ---
class ExperimentType:
    COMPUTATIONAL = "COMPUTATIONAL"
    SIMULATION = "SIMULATION"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    STATISTICAL = "STATISTICAL"
    LITERATURE_REPLICATION = "LITERATURE_REPLICATION"
    SOFTWARE_EXPERIMENT = "SOFTWARE_EXPERIMENT"
    BENCHMARK = "BENCHMARK"
    AB_TEST = "AB_TEST"
    CONTROLLED_AUTOMATION = "CONTROLLED_AUTOMATION"
    DIGITAL_TWIN = "DIGITAL_TWIN"
    PHYSICAL_LAB = "PHYSICAL_LAB"
    HUMAN_APPROVED_EXTERNAL = "HUMAN_APPROVED_EXTERNAL"


class ExperimentStatus:
    DESIGNED = "DESIGNED"
    SIMULATED = "SIMULATED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REPRODUCTION_FAILED = "REPRODUCTION_FAILED"


@dataclass
class Experiment:
    id: str = field(default_factory=lambda: new_id("exp"))
    task_id: str = ""
    hypothesis_id: str = ""
    objective: str = ""
    design: str = ""
    experiment_type: str = ExperimentType.COMPUTATIONAL
    variables: Dict[str, List[str]] = field(default_factory=dict)
    controls: List[str] = field(default_factory=list)
    treatment_groups: List[str] = field(default_factory=list)
    control_groups: List[str] = field(default_factory=list)
    sample_plan: Dict[str, Any] = field(default_factory=dict)
    measurement_plan: List[str] = field(default_factory=list)
    protocol: List[str] = field(default_factory=list)
    expected_results: str = ""
    falsification_criteria_id: str = ""
    statistical_plan: str = ""
    simulation_plan: str = ""
    safety_class: str = "COMPUTATIONAL"
    approval_required: bool = False
    reproducibility_plan: str = ""
    seed: int = 0
    status: str = ExperimentStatus.DESIGNED
    branches: List[str] = field(default_factory=list)
    parent_id: str = ""
    created_at: float = field(default_factory=_now)


@dataclass
class ExperimentManifest:
    experiment_id: str = ""
    source_snapshot: str = ""
    environment: Dict[str, Any] = field(default_factory=dict)
    dependencies: Dict[str, str] = field(default_factory=dict)
    dataset_hashes: Dict[str, str] = field(default_factory=dict)
    model_identifiers: Dict[str, str] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    seeds: List[int] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    tool_versions: Dict[str, str] = field(default_factory=dict)
    hardware: Dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""
    created_at: float = field(default_factory=_now)


@dataclass
class ExperimentResult:
    experiment_id: str = ""
    execution_type: str = "REAL"  # REAL | SIMULATION — never mixed silently
    observations: List[str] = field(default_factory=list)
    raw_data_ref: str = ""
    raw_data_hash: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    statistical_analysis: Dict[str, Any] = field(default_factory=dict)
    uncertainty: Dict[str, Any] = field(default_factory=dict)
    anomalies: List[str] = field(default_factory=list)
    interpretation: str = ""
    interpretation_label: str = "EXPLORATORY"  # EXPLORATORY | CONFIRMATORY
    limitations: List[str] = field(default_factory=list)
    falsification_outcome: str = "INCONCLUSIVE"  # SUPPORTS|WEAKENS|FALSIFIES|INCONCLUSIVE|DISCOVERS_ANOMALY
    reproducibility: str = "NOT_REPLICATED"
    provenance: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    started_at: float = 0.0
    ended_at: float = 0.0


# ---------------------------------------------------------------- evidence ---
class EvidenceType:
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    EXPERIMENTAL_RESULT = "EXPERIMENTAL_RESULT"
    SIMULATION_RESULT = "SIMULATION_RESULT"
    DATASET = "DATASET"
    LITERATURE = "LITERATURE"
    META_ANALYSIS = "META_ANALYSIS"
    STATISTICAL_RESULT = "STATISTICAL_RESULT"
    COMPUTATIONAL_RESULT = "COMPUTATIONAL_RESULT"
    THEORETICAL_DERIVATION = "THEORETICAL_DERIVATION"
    EXPERT_ASSESSMENT = "EXPERT_ASSESSMENT"
    MODEL_PREDICTION = "MODEL_PREDICTION"
    USER_PROVIDED_DATA = "USER_PROVIDED_DATA"


@dataclass
class Evidence:
    id: str = field(default_factory=lambda: new_id("ev"))
    claim_id: str = ""
    type: str = EvidenceType.USER_PROVIDED_DATA
    source: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now)
    methodology: str = ""
    dataset: str = ""
    measurement: str = ""
    uncertainty: str = ""
    confidence: str = "unknown"
    reproducibility: str = "unknown"
    independence: str = "unknown"  # independent | derived-from:<id> | unknown
    limitations: List[str] = field(default_factory=list)
    strength: str = "E0"  # E0..E6 internal taxonomy


@dataclass
class DatasetVersion:
    id: str = field(default_factory=lambda: new_id("ds"))
    name: str = ""
    version: str = "v1"
    source: str = ""
    hash: str = ""
    license: str = "unknown"
    rows: int = 0
    schema: Dict[str, str] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)


# --------------------------------------------------------------- discovery ---
class DiscoveryStatus:
    POTENTIAL_DISCOVERY = "POTENTIAL_DISCOVERY"
    PRELIMINARY = "PRELIMINARY"
    REPLICATED = "REPLICATED"
    INDEPENDENTLY_REPLICATED = "INDEPENDENTLY_REPLICATED"
    VALIDATED = "VALIDATED"
    CONTESTED = "CONTESTED"
    REJECTED = "REJECTED"


@dataclass
class ScientificDiscovery:
    id: str = field(default_factory=lambda: new_id("disc"))
    task_id: str = ""
    title: str = ""
    claim: str = ""
    claim_id: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    supporting_experiments: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    novelty_assessment: str = "UNCERTAIN"
    confidence: Dict[str, str] = field(default_factory=dict)  # decomposed, never one number
    limitations: List[str] = field(default_factory=list)
    reproducibility: str = "NOT_REPLICATED"
    provenance: Dict[str, Any] = field(default_factory=dict)
    status: str = DiscoveryStatus.POTENTIAL_DISCOVERY
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=_now)


@dataclass
class ReplicationRecord:
    id: str = field(default_factory=lambda: new_id("rep"))
    experiment_id: str = ""
    original_result_ref: str = ""
    mode: str = "SAME_SETUP"  # SAME_SETUP|SEED|IMPLEMENTATION|MODEL|DATASET|AGENT|ENVIRONMENT
    outcome: str = "UNKNOWN"  # MATCHED | DIVERGED | FAILED
    details: Dict[str, Any] = field(default_factory=dict)
    independent: bool = False
    at: float = field(default_factory=_now)


@dataclass
class AnomalyRecord:
    id: str = field(default_factory=lambda: new_id("anom"))
    task_id: str = ""
    experiment_id: str = ""
    prediction: str = ""
    observation: str = ""
    questions: List[str] = field(default_factory=list)
    status: str = "OPEN"
    at: float = field(default_factory=_now)


@dataclass
class ScientificLesson:
    id: str = field(default_factory=lambda: new_id("sles"))
    text: str = ""
    kind: str = ""  # measurement | family | leakage | simulation | power | ...
    evidence: List[str] = field(default_factory=list)
    scope: str = "project"
    at: float = field(default_factory=_now)


@dataclass
class ResearchTraceEvent:
    at: float = field(default_factory=_now)
    kind: str = ""  # task/question/research/hypothesis/critique/experiment/...
    ref: str = ""
    detail: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    task_id: str = ""
    experiment_id: str = ""
    agent_id: str = "science-engine"


@dataclass
class ScientificBenchmark:
    id: str = ""
    domain: str = ""
    task: str = ""
    trials: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)
    baseline: Dict[str, Any] = field(default_factory=dict)
    candidate: Dict[str, Any] = field(default_factory=dict)
    reproducibility: str = ""
    confidence: str = ""
