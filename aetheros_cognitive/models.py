"""Cognitive Architecture 2.0 — shared models (§3-10, §15-17, §24,
§38, §40-41, §72, §79, §101).

Pure stdlib dataclasses/enums; no I/O, no inference. Every predicted
artifact is explicitly tagged PREDICTION, never FACT (§0.4).
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


class Provenance(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    PREDICTED = "predicted"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


class CognitiveMode(str, Enum):
    REACTIVE = "reactive"
    FORESIGHT = "foresight"
    CAUSAL = "causal"
    SIMULATIVE = "simulative"
    COUNTERFACTUAL = "counterfactual"
    DELIBERATIVE = "deliberative"


class BackendKind(str, Enum):
    RULE_BASED = "rule_based"
    STATE_TRANSITION = "state_transition"
    LLM_SIMULATOR = "llm_simulator"
    GRAPH_DYNAMICS = "graph_dynamics"
    NEURAL_WORLD_MODEL = "neural"
    EXTERNAL_SIMULATOR = "external"
    HYBRID = "hybrid"


class TwinMode(str, Enum):
    READ_ONLY = "read_only"
    SIMULATION = "simulation"
    SHADOW = "shadow"
    MIRROR = "mirror"
    CONTROLLED_EXECUTION = "controlled_execution"


class ErrorClass(str, Enum):
    STATE_ERROR = "state_error"
    ACTION_EFFECT_ERROR = "action_effect_error"
    TEMPORAL_ERROR = "temporal_error"
    CAUSAL_ERROR = "causal_error"
    ENTITY_ERROR = "entity_error"
    RELATIONSHIP_ERROR = "relationship_error"
    OBSERVATION_ERROR = "observation_error"
    MODEL_ERROR = "model_error"
    ENVIRONMENT_DRIFT = "environment_drift"


@dataclass
class Entity:
    id: str
    kind: str  # user, agent, file, browser, tab, task, ...
    attributes: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    confidence: float = 1.0
    provenance: str = "observed"
    observed_at: float = field(default_factory=_now)
    valid_until: Optional[float] = None

    def is_stale(self, at: Optional[float] = None) -> bool:
        if self.valid_until is None:
            return False
        return (at or _now()) > self.valid_until


@dataclass
class Relationship:
    src: str
    rel: str  # owns, contains, depends_on, causes, blocked_by, ...
    dst: str
    confidence: float = 1.0
    provenance: str = "observed"


@dataclass
class WorldState:
    state_id: str = field(default_factory=lambda: new_id("ws"))
    timestamp: float = field(default_factory=_now)
    version: int = 1
    entities: Dict[str, Entity] = field(default_factory=dict)
    relationships: List[Relationship] = field(default_factory=list)
    environment: Dict[str, Any] = field(default_factory=dict)
    goals: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    available_actions: List[str] = field(default_factory=list)
    known_unknowns: List[str] = field(default_factory=list)
    sources: Dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class ActionCandidate:
    action_id: str = field(default_factory=lambda: new_id("act"))
    type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    expected_effects: Dict[str, Any] = field(default_factory=dict)
    possible_effects: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    irreversible: bool = False
    risk: float = 0.0
    cost: float = 0.0
    latency_ms: float = 0.0
    reversibility: float = 1.0
    blast_radius: str = "single task"
    confidence: float = 0.5


@dataclass
class PredictedState:
    """Explicitly a PREDICTION (§0.4)."""
    state: Dict[str, Any] = field(default_factory=dict)
    confidence: PredictionConfidence | None = None  # noqa: F821
    horizon: int = 1
    model_version: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictionConfidence:
    model: float = 0.5
    data: float = 0.5
    state: float = 0.5
    causal: float = 0.5
    env_similarity: float = 0.5
    horizon_penalty: float = 0.0

    def combined(self) -> float:
        base = (self.model * self.data * self.state * self.causal
                * self.env_similarity)
        return max(0.0, min(1.0, base * (1.0 - self.horizon_penalty)))


@dataclass
class FutureBranch:
    branch_id: str = field(default_factory=lambda: new_id("br"))
    parent_state_id: str = ""
    actions: List[str] = field(default_factory=list)
    predicted_states: List[Dict[str, Any]] = field(default_factory=list)
    outcome: Dict[str, Any] = field(default_factory=dict)
    frequency: float = 0.0  # simulation frequency, NOT real-world prob
    confidence: float = 0.0
    risk: float = 0.0
    cost: float = 0.0
    score: float = 0.0


@dataclass
class PredictionError:
    prediction: Dict[str, Any] = field(default_factory=dict)
    observation: Dict[str, Any] = field(default_factory=dict)
    difference: Dict[str, Any] = field(default_factory=dict)
    severity: str = "minor"  # minor | moderate | major | critical
    error_class: str = "state_error"
    cause: str = ""
    model_version: str = ""
    at: float = field(default_factory=_now)


@dataclass
class CausalEdge:
    src: str
    dst: str
    strength: float = 0.0
    confidence: float = 0.0
    source: str = "hypothesis"  # rule | domain | experiment | intervention
    evidence: List[str] = field(default_factory=list)
    scope: str = ""
    status: str = "HYPOTHESIS"  # HYPOTHESIS | VALIDATED


@dataclass
class SimulationBudget:
    max_depth: int = 3
    max_branches: int = 8
    max_rollouts: int = 16
    max_time_s: float = 5.0
    max_cost: float = 1.0

    def exceeded(self, depth: int, branches: int, rollouts: int,
                 elapsed: float, cost: float) -> bool:
        return (depth > self.max_depth or branches > self.max_branches
                or rollouts > self.max_rollouts
                or elapsed > self.max_time_s or cost > self.max_cost)
