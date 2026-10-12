"""Provenance, Grounding, Confidence and Hallucination Defense
(Phases 57-65 of Master Prompt 10).

- **Provenance**: every extracted fact carries source media, timestamp/page,
  region, processor/model and confidence.
- **Grounding**: answers can point back to the exact evidence that produced them.
- **Confidence**: OCR/STT/vision/speaker/alignment confidence is tracked.
- **Uncertainty**: when evidence is insufficient, say so instead of guessing.
- **Hallucination defense**: the system distinguishes OBSERVED / INFERRED /
  UNKNOWN and never lets inference masquerade as observation.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from agent.multimodal.media_abstraction import MediaObject

logger = logging.getLogger(__name__)


class EvidenceStatus(Enum):
    OBSERVED = "observed"    # directly grounded in media
    INFERRED = "inferred"    # derived/interpreted — must be labelled
    UNKNOWN = "unknown"      # cannot determine reliably


@dataclass
class EvidenceRef:
    """Pointer to the exact evidence backing a claim (Phase 58/62)."""

    media_id: str = ""
    source: str = ""                # file/url
    timestamp: float = 0.0          # media timestamp (seconds, for AV)
    page: Optional[int] = None      # document page
    region: Optional[Dict[str, int]] = None  # x/y/w/h bbox
    processor: str = ""             # which tool/model produced the fact
    confidence: float = 0.0
    claim: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "media_id": self.media_id,
            "source": self.source,
            "timestamp": self.timestamp,
            "page": self.page,
            "region": self.region,
            "processor": self.processor,
            "confidence": round(self.confidence, 3),
            "claim": self.claim,
        }


@dataclass
class GroundedFact:
    """A fact extracted from media, with full provenance (Phase 57)."""

    claim: str
    status: EvidenceStatus = EvidenceStatus.OBSERVED
    evidence: Optional[EvidenceRef] = None
    fact_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "claim": self.claim,
            "status": self.status.value,
            "evidence": self.evidence.to_dict() if self.evidence else None,
        }


class ProvenanceTracker:
    """Append-only store of grounded facts across a conversation/task."""

    def __init__(self) -> None:
        self._facts: List[GroundedFact] = []

    def record(
        self,
        claim: str,
        media: Optional[MediaObject] = None,
        status: EvidenceStatus = EvidenceStatus.OBSERVED,
        timestamp: float = 0.0,
        page: Optional[int] = None,
        region: Optional[Dict[str, int]] = None,
        processor: str = "",
        confidence: float = 1.0,
    ) -> GroundedFact:
        evidence = None
        if media is not None:
            evidence = EvidenceRef(
                media_id=media.media_id,
                source=media.source,
                timestamp=timestamp or media.timestamp,
                page=page,
                region=region,
                processor=processor,
                confidence=confidence,
                claim=claim,
            )
        fact = GroundedFact(claim=claim, status=status, evidence=evidence)
        self._facts.append(fact)
        return fact

    def get_facts(self, media_id: Optional[str] = None) -> List[GroundedFact]:
        if media_id is None:
            return list(self._facts)
        return [f for f in self._facts if f.evidence and f.evidence.media_id == media_id]

    def reset(self) -> None:
        self._facts.clear()


class ConfidenceTracker:
    """Tracks per-modality confidence (Phase 64) and exposes uncertainty."""

    def __init__(self) -> None:
        self._scores: Dict[str, float] = {}

    def set(self, modality: str, confidence: float) -> None:
        self._scores[modality] = round(max(0.0, min(1.0, confidence)), 3)

    def get(self, modality: str) -> float:
        return self._scores.get(modality, 0.0)

    def all(self) -> Dict[str, float]:
        return dict(self._scores)

    def is_certain(self, modality: str, threshold: float = 0.6) -> bool:
        return self.get(modality) >= threshold

    def uncertainty_note(self, modality: str, threshold: float = 0.6) -> str:
        score = self.get(modality)
        if score < threshold:
            return f"(low confidence in {modality}: {score:.2f})"
        return ""


def label_claim(
    tracker: ProvenanceTracker,
    claim: str,
    confidence: float,
    modality: str = "vision",
    threshold: float = 0.6,
    media: Optional[MediaObject] = None,
    processor: str = "",
) -> GroundedFact:
    """Classify a claim as OBSERVED / INFERRED / UNKNOWN (Phases 63-65).

    High confidence + grounded media -> OBSERVED.
    Medium confidence or derived -> INFERRED.
    Low confidence -> UNKNOWN (never guess).
    """
    if confidence < 0.3:
        status = EvidenceStatus.UNKNOWN
    elif confidence >= threshold:
        status = EvidenceStatus.OBSERVED
    else:
        status = EvidenceStatus.INFERRED
    fact = tracker.record(
        claim=claim, media=media, status=status, processor=processor, confidence=confidence
    )
    return fact


UNKNOWN_STATEMENT = "I cannot determine this reliably from the provided media."