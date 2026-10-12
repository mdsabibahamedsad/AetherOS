"""AetherOS Universal Reality Interface 1.0 — Multimodal Fusion & Intent Resolver (§46-50).

Unifies observations from all input pipelines into coherent intent hypotheses.
Implements cross-modal fusion, ambiguity detection, and clarification engine.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Set

from aetheros_reality.models import (
    InputModality,
    IntentHypothesis,
    MultimodalEvent,
    ClarificationRequest,
    ClarificationResponse,
    new_id,
)

logger = logging.getLogger(__name__)


def _now() -> float:
    return time.time()


def new_id(prefix: str = "intent") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# §46: Multimodal Intent Resolver
# ---------------------------------------------------------------------------

class FusionStrategy(str, Enum):
    """Strategies for fusing multimodal inputs."""
    EARLY_FUSION = "early_fusion"      # Fuse raw features
    LATE_FUSION = "late_fusion"        # Fuse high-level predictions
    HYBRID_FUSION = "hybrid_fusion"    # Combine early + late
    ATTENTION_BASED = "attention_based"  # Attention-weighted
    HIERARCHICAL = "hierarchical"       # Multi-level fusion


@dataclass
class ModalityEvidence:
    """Evidence from a single modality."""
    modality: str
    confidence: float
    features: Dict[str, Any] = field(default_factory=dict)
    raw_data: Any = None
    timestamp: float = field(default_factory=time.time)
    source: str = ""


@dataclass
class FusedIntent:
    """Result of multimodal fusion."""
    intent_hypotheses: List['IntentHypothesis'] = field(default_factory=list)
    fused_confidence: float = 0.0
    ambiguity_score: float = 0.0
    modality_contributions: Dict[str, float] = field(default_factory=dict)
    evidence_chain: List[str] = field(default_factory=list)
    fusion_strategy: str = ""
    timestamp: float = field(default_factory=time.time)


class MultimodalFusionEngine:
    """Core multimodal fusion engine (§46)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.fusion_strategy = FusionStrategy(self.config.get("fusion_strategy", "hybrid_fusion"))
        self.modality_weights = self.config.get("modality_weights", {
            "voice": 1.0,
            "vision": 1.0,
            "gaze": 0.8,
            "gesture": 0.7,
            "screen": 0.8,
            "text": 1.0,
        })
        self.confidence_threshold = self.config.get("confidence_threshold", 0.6)
        self.ambiguity_threshold = self.config.get("ambiguity_threshold", 0.15)

    def fuse(self, events: List[Dict[str, Any]], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fuse multimodal events into intent hypotheses."""
        if not events:
            return {"intent_hypotheses": [], "confidence": 0.0, "ambiguity": 1.0}

        # Group events by modality
        modality_events = {}
        for event in events:
            modality = event.get("modality", "unknown")
            if modality not in modality_events:
                modality_events[modality] = []
            modality_events[modality].append(event)

        # Extract features per modality
        modality_evidence = {}
        for modality, events in modality_events.items():
            weight = self.modality_weights.get(modality, 0.5)
            evidence = self._extract_modality_features(events, modality)
            modality_evidence[modality] = ModalityEvidence(
                modality=modality,
                confidence=evidence.get("confidence", 0.5) * weight,
                features=evidence,
                timestamp=time.time()
            )

        # Generate intent hypotheses from fused evidence
        hypotheses = self._generate_hypotheses(modality_evidence, context or {})

        # Calculate ambiguity
        ambiguity = self._calculate_ambiguity(hypotheses)

        # Apply fusion strategy
        fused = self._apply_fusion_strategy(hypotheses, modality_evidence)

        return {
            "intent_hypotheses": [h.__dict__ for h in fused.intent_hypotheses],
            "fused_confidence": fused.fused_confidence,
            "ambiguity_score": fused.ambiguity_score,
            "modality_contributions": fused.modality_contributions,
            "evidence_chain": fused.evidence_chain,
            "fusion_strategy": fused.fusion_strategy,
            "timestamp": fused.timestamp,
        }

    def _extract_modality_features(self, events: List[Dict], modality: str) -> Dict[str, Any]:
        """Extract features from modality-specific events."""
        if not events:
            return {"confidence": 0.0, "features": []}

        # Aggregate features from events
        features = []
        confidences = []

        for event in events:
            if "payload" in event:
                payload = event.get("payload", {})
                if "text" in payload:
                    features.append(("text", payload["text"]))
                if "objects" in payload:
                    features.append(("objects", payload["objects"]))
                if "text" in payload:
                    features.append(("transcript", payload["text"]))
            if "confidence" in event:
                confidences.append(event.get("confidence", 0.5))

        return {
            "confidence": sum(confidences) / len(confidences) if confidences else 0.5,
            "features": features,
            "event_count": len(events),
        }

    def _generate_hypotheses(self, modality_evidence: Dict, context: Dict) -> List:
        """Generate intent hypotheses from fused evidence."""
        from aetheros_reality.models import IntentHypothesis

        hypotheses = []

        # Simple rule-based hypothesis generation
        # In production, this would use an LLM or specialized model

        # Voice + Vision fusion
        if "voice" in modality_evidence and "vision" in modality_evidence:
            voice_feat = modality_evidence["vision"].features
            vision_feat = modality_evidence["vision"].features
            # Could fuse here

        # Create a default hypothesis if we have any evidence
        total_confidence = sum(e.confidence for e in modality_evidence.values())
        if total_confidence > 0:
            hypotheses.append(IntentHypothesis(
                intent="user_intent",
                confidence=min(total_confidence / len(modality_evidence), 1.0),
                evidence=["multimodal fusion"],
                ambiguity=0.3,
                modality_contributions={m: e.confidence for m, e in modality_evidence.items()},
            ))

        return hypotheses

    def _calculate_ambiguity(self, hypotheses: List) -> float:
        """Calculate ambiguity score from competing hypotheses."""
        if not hypotheses:
            return 1.0
        if len(hypotheses) == 1:
            return 0.0

        confidences = [h.confidence for h in hypotheses]
        max_conf = max(confidences)
        others = [c for c in confidences if c != max_conf]
        if not others:
            return 0.0
        second_best = max(others)
        return 1.0 - (max_conf - second_best)

    def _apply_fusion_strategy(self, hypotheses: List, modality_evidence: Dict) -> 'FusedIntent':
        """Apply fusion strategy to produce final result."""
        from aetheros_reality.fusion import FusedIntent

        if not hypotheses:
            return FusedIntent(
                intent_hypotheses=[],
                fused_confidence=0.0,
                ambiguity_score=1.0,
            )

        # Sort by confidence
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        top = hypotheses[0]

        # Calculate modality contributions
        modality_contributions = {}
        # In real implementation, would compute from modality_evidence

        return FusedIntent(
            intent_hypotheses=hypotheses,
            fused_confidence=top.confidence,
            ambiguity_score=self._calculate_ambiguity(hypotheses),
            modality_contributions=modality_contributions,
            evidence_chain=["multimodal_fusion"],
            fusion_strategy="hybrid",
            timestamp=time.time()
        )


# ---------------------------------------------------------------------------
# §49: Clarification Engine
# ---------------------------------------------------------------------------

class ClarificationEngine:
    """Generates minimal clarification questions to resolve ambiguity (§49)."""

    def __init__(self):
        self.templates = {
            "file_reference": "Which file do you mean: {options}?",
            "action_ambiguity": "Do you want to {action_a} or {action_b}?",
            "reference_resolution": "Which {object_type} do you mean: {options}?",
            "spatial_reference": "Do you mean the {object} on the {left/right} or {other}?",
        }

    def generate_clarification(self, hypotheses: List[Dict], context: Dict) -> Dict[str, Any]:
        """Generate a clarification request for ambiguous hypotheses."""
        if len(hypotheses) < 2:
            return {"needs_clarification": False}

        # Sort by confidence
        hypotheses.sort(key=lambda h: h.get("confidence", 0), reverse=True)

        top = hypotheses[0]
        second = hypotheses[1] if len(hypotheses) > 1 else None

        if not second:
            return {"needs_clarification": False}

        # Generate clarification based on hypothesis types
        intent_a = hypotheses[0].get("intent", "")
        intent_b = hypotheses[1].get("intent", "")

        clarification = {
            "needs_clarification": True,
            "question": f"Did you mean '{intent_a}' or '{intent_b}'?",
            "options": [
                {"id": 0, "text": intent_a, "confidence": hypotheses[0].get("confidence", 0)},
                {"id": 1, "text": intent_b, "confidence": hypotheses[1].get("confidence", 0)},
            ],
            "type": "intent_disambiguation",
        }

        return clarification

    def generate_spatial_clarification(self, objects: List[str], spatial_context: Dict) -> Dict:
        """Generate spatial disambiguation question."""
        if len(objects) < 2:
            return {"needs_clarification": False}

        return {
            "needs_clarification": True,
            "question": f"Which one do you mean: {', '.join(objects[:-1])} or {objects[-1]}?",
            "options": [{"id": i, "text": obj} for i, obj in enumerate(objects)],
            "type": "spatial_disambiguation",
        }


# ---------------------------------------------------------------------------
# §50: Minimal Interruption Policy
# ---------------------------------------------------------------------------

class InterruptionPolicy:
    """Controls when to interrupt user for clarification (§50)."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.min_confidence_for_action = self.config.get("min_confidence_for_action", 0.7)
        self.max_clarifications_per_task = self.config.get("max_clarifications", 3)
        self.clarification_history: List[Dict] = []

    def should_clarify(self, fused_result: Dict, context: Dict) -> bool:
        """Decide whether to ask for clarification."""
        ambiguity = fused_result.get("ambiguity_score", 1.0)
        top_confidence = fused_result.get("fused_confidence", 0.0)

        # Don't clarify if confidence is high enough
        if top_confidence >= self.min_confidence_for_action:
            return False

        # Don't clarify if ambiguity is low
        if fused_result.get("ambiguity_score", 1.0) < 0.15:
            return False

        # Check clarification budget
        task_id = context.get("task_id", "")
        recent_clarifications = sum(1 for c in self.clarification_history
                                    if c.get("task_id") == task_id)
        if recent_clarifications >= self.max_clarifications_per_task:
            return False

        return True

    def record_clarification(self, task_id: str, clarification: Dict) -> None:
        self.clarification_history.append({
            "task_id": task_id,
            "clarification": clarification,
            "timestamp": time.time(),
        })


# ---------------------------------------------------------------------------
# §47-50: Intent Resolution Integration
# ---------------------------------------------------------------------------

class IntentResolver:
    """High-level intent resolution orchestrating fusion and clarification."""

    def __init__(self, config: Optional[Dict] = None):
        self.fusion_engine = MultimodalFusionEngine(config)
        self.clarification_engine = ClarificationEngine()
        self.interruption_policy = InterruptionPolicy(config)
        self.pending_clarifications: Dict[str, Dict] = {}

    def resolve_intent(self, events: List[Dict], context: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point: resolve intent from multimodal events."""
        # Fuse multimodal events
        fused = self.fusion_engine.fuse(events, context)

        # Check if clarification needed
        if self.interruption_policy.should_clarify(fused, context):
            clarification = self.clarification_engine.generate_clarification(
                fused.get("intent_hypotheses", []), context
            )
            if clarification.get("needs_clarification"):
                return {
                    "status": "needs_clarification",
                    "clarification": clarification,
                    "fused_result": fused,
                }

        return {
            "status": "resolved",
            "intent": fused_result.get("intent_hypotheses", [{}])[0] if fused.get("intent_hypotheses") else {},
            "confidence": fused.get("fused_confidence", 0.0),
            "fused_result": fused,
        }

    def handle_clarification_response(self, response: Dict) -> Dict[str, Any]:
        """Process user's clarification response."""
        # Update hypothesis weights based on clarification
        # Re-run fusion with updated weights
        pass


# Missing imports
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple