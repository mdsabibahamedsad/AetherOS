"""Semantic Fusion Engine (Phase 25 of Master Prompt 10).

Aligns and fuses multi-modal semantic representations:
- Text + Image alignment (CLIP-style)
- Video + Text alignment (Video-Language)
- Cross-modal retrieval and grounding
- Semantic grounding and hallucination detection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from agent.multimodal.media_abstraction import MediaObject, MediaType
from agent.multimodal.provenance import ProvenanceTracker

logger = logging.getLogger(__name__)


class GroundingStrategy(Enum):
    """Strategies for semantic grounding."""

    CLIP_STYLE = "clip_style"  # Contrastive image-text alignment
    CROSS_ATTENTION = "cross_attention"  # Cross-modal attention
    RETRIEVAL_AUGMENTED = "retrieval_augmented"  # Retrieval-augmented grounding
    PROGRAMMATIC = "programmatic"  # Programmatic verification (code execution)
    HUMAN_IN_THE_LOOP = "human_in_the_loop"  # Human verification


@dataclass
class GroundingConfig:
    """Configuration for semantic grounding."""

    strategy: str = "clip_style"
    similarity_threshold: float = 0.3  # Minimum similarity for grounding
    max_candidates: int = 5  # Max candidates for retrieval
    verification_enabled: bool = True  # Enable verification step
    hallucination_threshold: float = 0.7  # Threshold for hallucination detection


@dataclass
class GroundingEvidence:
    """Evidence for a grounded claim."""

    claim: str
    modality: str
    source_id: str
    confidence: float
    evidence_text: str
    source_location: Optional[str] = None  # Page, timestamp, bbox, etc.
    verification_status: str = "unverified"  # verified, refuted, unverified


@dataclass
class GroundingResult:
    """Result of semantic grounding."""

    claim: str
    grounded: bool
    confidence: float
    evidence: List[GroundingEvidence] = field(default_factory=list)
    hallucination_risk: float = 0.0
    verification_status: str = "unverified"
    metadata: Dict = field(default_factory=dict)


class SemanticFusionEngine:
    """Engine for semantic fusion and grounding (Phase 25)."""

    def __init__(
        self,
        config: Optional[Dict] = None,
        tracker: Optional[ProvenanceTracker] = None,
    ):
        self.config = config or {}
        self.tracker = tracker
        self._embeddings_cache: Dict[str, np.ndarray] = {}

    def ground_claim(
        self,
        claim: str,
        evidence_media: List[Any],  # List of MediaObjects
        strategy: str = "clip_style",
    ) -> Dict[str, Any]:
        """Ground a textual claim in multi-modal evidence."""
        # In production, this would use CLIP-style embeddings
        # For now, use text-based matching

        evidence_list = []
        for media in evidence_media:
            # Extract text content from media
            text_content = self._extract_text(media)
            if text_content:
                # Simple text overlap scoring
                score = self._compute_overlap(claim, text_content)
                if score >= 0.3:
                    evidence_list.append({
                        "modality": media.type.value,
                        "source_id": media.media_id,
                        "confidence": score,
                        "evidence_text": text_content[:200],
                    })

        # Overall grounding confidence
        if evidence_list:
            max_conf = max(e["confidence"] for e in evidence_list)
            grounded = max_conf >= 0.3
            confidence = max_conf
        else:
            grounded = False
            confidence = 0.0

        result = {
            "claim": claim,
            "grounded": grounded,
            "confidence": confidence,
            "evidence": evidence_list,
            "metadata": {"strategy": "text_overlap_fallback"},
        }

        return result

    def _extract_text(self, media: Any) -> str:
        """Extract text content from media."""
        if hasattr(media, 'metadata') and media.metadata:
            return str(media.metadata.get("content", "") or media.metadata.get("data", "") or "")
        return str(media) if media else ""

    def _compute_overlap(self, text1: str, text2: str) -> float:
        """Compute text overlap score (simplified)."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    def cross_modal_retrieval(
        self,
        query: str,
        candidates: List[Any],  # List of MediaObjects
        top_k: int = 5,
    ) -> List[Dict]:
        """Retrieve relevant media for a text query (cross-modal retrieval)."""
        scored = []
        for media in candidates:
            text = self._extract_text(media)
            if text:
                score = self._compute_overlap(query, text)
                scored.append({
                    "media_id": media.media_id,
                    "modality": media.type.value,
                    "score": score,
                    "preview": text[:100],
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:5]

    def detect_hallucination(
        self,
        generated_text: str,
        evidence_media: List[Any],
    ) -> Dict[str, Any]:
        """Detect potential hallucinations in generated text.

        Compares generated claims against evidence media.
        """
        # Split generated text into claims (simplified: sentences)
        import re
        sentences = re.split(r'[.!?]+', generated_text)
        claims = [s.strip() for s in sentences if s.strip()]

        results = []
        for claim in claims:
            grounded_result = self.ground_claim(claim, evidence_media)
            risk = 1.0 - grounded_result["confidence"] if grounded_result["grounded"] else 1.0
            results.append({
                "claim": claim,
                "grounded": grounded_result["grounded"],
                "confidence": grounded_result["confidence"],
                "hallucination_risk": risk,
            })

        overall_risk = np.mean([r["hallucination_risk"] for r in results]) if results else 0.0

        return {
            "overall_hallucination_risk": overall_risk,
            "claims": results,
            "flagged_claims": [r for r in results if r["hallucination_risk"] > 0.7],
        }

    def verify_generation(
        self,
        generated_text: str,
        evidence_media: List[Any],
        verification_mode: str = "auto",
    ) -> Dict[str, Any]:
        """Verify generated text against evidence."""
        hallucination = self.detect_hallucination(generated_text, evidence_media)
        retrieval = self.cross_modal_retrieval(generated_text, evidence_media)

        return {
            "verified": hallucination["overall_hallucination_risk"] < 0.5,
            "hallucination_analysis": hallucination,
            "retrieval_candidates": retrieval,
            "summary": f"Risk: {hallucination['overall_hallucination_risk']:.2f}, "
                       f"Flagged: {len(hallucination['flagged_claims'])} claims",
        }


def ground_text_in_media(
    text: str,
    *medias: MediaObject,
    threshold: float = 0.3,
) -> Dict[str, Any]:
    """Convenience function to ground text in media evidence."""
    engine = SemanticFusionEngine()
    return engine.ground_claim(text, list(medias))


def verify_generation_against_evidence(
    generated: str,
    *evidence: MediaObject,
) -> Dict[str, Any]:
    """Verify generated text against evidence media."""
    engine = SemanticFusionEngine()
    return engine.verify_generation(generated, list(evidence))


def retrieve_relevant_media(
    query: str,
    *candidates: MediaObject,
    top_k: int = 5,
) -> List[Dict]:
    """Retrieve relevant media for a query."""
    engine = SemanticFusionEngine()
    return engine.cross_modal_retrieval(query, list(candidates), top_k=top_k)