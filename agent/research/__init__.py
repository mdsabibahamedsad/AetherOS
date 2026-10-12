"""Aetheros deep-research subsystem.

Evidence-backed research with provenance: research tasks, observable state
machine, normalized sources, claims, evidence, citations, and reports.
Composes the existing web-search provider registry and security stack; it
does not register new model tools.
"""

from agent.research.models import (
    CONTRADICTION_MARKERS,
    Claim,
    ClaimKind,
    ClaimStatus,
    Contradiction,
    Evidence,
    ResearchDepth,
    ResearchSource,
    ResearchTask,
    SourceType,
    SourceVisibility,
    ToolFailureKind,
    TrustSignals,
    classify_source_type,
    score_source_quality,
)
from agent.research.state import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    IllegalTransition,
    StateTransition,
    ResearchStateMachine,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "TERMINAL_STATES",
    "CONTRADICTION_MARKERS",
    "Claim",
    "ClaimKind",
    "ClaimStatus",
    "Contradiction",
    "Evidence",
    "IllegalTransition",
    "ResearchDepth",
    "ResearchSource",
    "ResearchStateMachine",
    "ResearchTask",
    "StateTransition",
    "SourceType",
    "SourceVisibility",
    "ToolFailureKind",
    "TrustSignals",
    "classify_source_type",
    "score_source_quality",
]
