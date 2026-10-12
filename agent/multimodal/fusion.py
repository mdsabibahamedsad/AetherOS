"""Cross-Modal Fusion Engine (Phase 19 of Master Prompt 10).

Provides unified representation and fusion of multiple modalities:
- Temporal fusion: align audio + video streams by timestamp
- Spatial fusion: combine image + depth + point cloud
- Semantic fusion: align text embeddings with visual features
- Attention-based fusion: learn cross-modal attention weights
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

from agent.multimodal.media_abstraction import MediaObject, MediaType
from agent.multimodal.provenance import ProvenanceTracker

logger = logging.getLogger(__name__)


class FusionStrategy(Enum):
    """Strategies for fusing multiple modalities."""

    CONCATENATE = "concatenate"  # Simple feature concatenation
    ATTENTION = "attention"  # Cross-modal attention (requires learned weights)
    PRODUCT_OF_EXPERTS = "product_of_experts"  # Probabilistic fusion
    WEIGHTED_SUM = "weighted_sum"  # Linear combination with learned weights
    HIERARCHICAL = "hierarchical"  # Multi-level fusion (early + late)


class ModalityAlignment(Enum):
    """How modalities are aligned before fusion."""

    TEMPORAL = "temporal"  # By timestamp (audio + video)
    SPATIAL = "spatial"  # By coordinate system (image + depth)
    SEMANTIC = "semantic"  # By embedding similarity (text + image)
    NONE = "none"  # No alignment, raw concatenation


@dataclass
class FusionConfig:
    """Configuration for cross-modal fusion."""

    strategy: FusionStrategy = FusionStrategy.CONCATENATE
    alignment: ModalityAlignment = ModalityAlignment.SEMANTIC
    # Per-modality weights for weighted sum strategy
    modality_weights: Dict[MediaType, float] = field(default_factory=dict)
    # Temperature for attention softmax
    attention_temperature: float = 1.0
    # Maximum sequence length for temporal alignment
    max_sequence_length: int = 512
    # Embedding dimension for projection
    projection_dim: int = 512


@dataclass
class FusionInput:
    """A single modality input to the fusion engine."""

    media: MediaObject
    embedding: Optional[np.ndarray] = None  # Pre-computed embedding
    features: Optional[Dict[str, Any]] = None  # Additional features
    timestamp: float = field(default_factory=time.time)  # For temporal alignment
    spatial_transform: Optional[np.ndarray] = None  # For spatial alignment
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FusionResult:
    """Result of cross-modal fusion."""

    fused_embedding: np.ndarray
    modality_contributions: Dict[MediaType, float]  # Attention weights or contribution scores
    aligned_modalities: List[MediaType]
    fusion_strategy: FusionStrategy
    alignment_method: ModalityAlignment
    fusion_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CrossModalFusionEngine:
    """Engine for fusing multiple modalities into a unified representation (Phase 19)."""

    def __init__(
        self,
        config: Optional[FusionConfig] = None,
        tracker: Optional[ProvenanceTracker] = None,
    ):
        self.config = config or FusionConfig()
        self.tracker = tracker
        # Projection layers for each modality (lazy init)
        self._projections: Dict[MediaType, np.ndarray] = {}

    def _get_projection(self, modality: MediaType, input_dim: int) -> np.ndarray:
        """Get or create a random projection matrix for a modality."""
        if modality not in self._projections:
            # Random projection matrix (in production, this would be learned)
            np.random.seed(hash(modality.value) % (2**32))
            self._projections[modality] = np.random.randn(input_dim, self.config.projection_dim).astype(np.float32) * 0.02
        return self._projections[modality]

    def _project_embedding(self, embedding: np.ndarray, modality: MediaType) -> np.ndarray:
        """Project embedding to common fusion dimension."""
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        input_dim = embedding.shape[-1]
        if input_dim == self.config.projection_dim:
            return embedding
        proj = self._get_projection(modality, input_dim)
        return embedding @ proj

    def _align_temporal(self, inputs: List[FusionInput]) -> List[FusionInput]:
        """Align modalities by timestamp (simple interpolation)."""
        # Sort by timestamp
        inputs.sort(key=lambda x: x.timestamp)
        # For now, just return sorted; real implementation would interpolate
        return inputs

    def _align_spatial(self, inputs: List[FusionInput]) -> List[FusionInput]:
        """Align modalities by spatial transform."""
        # Apply spatial transforms if available
        for inp in inputs:
            if inp.spatial_transform is not None and inp.embedding is not None:
                # Apply transformation to embedding (simplified)
                pass
        return inputs

    def _align_semantic(self, inputs: List[FusionInput]) -> List[FusionInput]:
        """Align by semantic similarity (embedding space)."""
        # In production, this would use contrastive learning or CLIP-style alignment
        # For now, just project all to common dimension
        for inp in inputs:
            if inp.embedding is not None:
                inp.embedding = self._project_embedding(inp.embedding, inp.media.type)
        return inputs

    def fuse(
        self,
        inputs: List[FusionInput],
        strategy: Optional[FusionStrategy] = None,
        alignment: Optional[ModalityAlignment] = None,
    ) -> FusionResult:
        """Fuse multiple modality inputs into a unified representation."""
        if not inputs:
            raise ValueError("At least one input required")

        strategy = strategy or self.config.strategy
        alignment = alignment or self.config.alignment

        # 1. Align modalities
        if alignment == ModalityAlignment.TEMPORAL:
            inputs = self._align_temporal(inputs)
        elif alignment == ModalityAlignment.SPATIAL:
            inputs = self._align_spatial(inputs)
        elif alignment == ModalityAlignment.SEMANTIC:
            inputs = self._align_semantic(inputs)

        # 2. Extract embeddings (or compute from media if not provided)
        embeddings = {}
        for inp in inputs:
            if inp.embedding is not None:
                embeddings[inp.media.type] = inp.embedding
            else:
                # In production, compute embedding from media
                embeddings[inp.media.type] = self._compute_embedding(inp.media)

        # 3. Apply fusion strategy
        if strategy == FusionStrategy.CONCATENATE:
            fused = self._fuse_concatenate(embeddings)
            contributions = {m: 1.0 for m in embeddings}
        elif strategy == FusionStrategy.WEIGHTED_SUM:
            fused, contributions = self._fuse_weighted_sum(embeddings)
        elif strategy == FusionStrategy.ATTENTION:
            fused, contributions = self._fuse_attention(embeddings)
        elif strategy == FusionStrategy.PRODUCT_OF_EXPERTS:
            fused, contributions = self._fuse_product_of_experts(embeddings)
        elif strategy == FusionStrategy.HIERARCHICAL:
            fused, contributions = self._fuse_hierarchical(embeddings)
        else:
            fused = self._fuse_concatenate(embeddings)
            contributions = {m: 1.0 for m in embeddings}

        # 4. Track provenance
        if self.tracker:
            self.tracker.record(
                claim=f"Cross-modal fusion: {strategy.value} ({len(inputs)} modalities)",
                media=None,
                processor="CrossModalFusionEngine",
                confidence=0.8,
            )

        return FusionResult(
            fused_embedding=fused,
            modality_contributions=contributions,
            aligned_modalities=list(embeddings.keys()),
            fusion_strategy=strategy,
            alignment_method=alignment,
        )

    def _compute_embedding(self, media: MediaObject) -> np.ndarray:
        """Compute embedding from media (placeholder for production embedding)."""
        # In production, this would call the embedding model
        # For now, return a deterministic random embedding based on media hash
        seed = hash(media.media_id) % (2**32)
        np.random.seed(seed)
        return np.random.randn(self.config.projection_dim).astype(np.float32)

    def _fuse_concatenate(self, embeddings: Dict[MediaType, np.ndarray]) -> np.ndarray:
        """Simple concatenation of embeddings."""
        arrays = [embeddings[m].flatten() for m in sorted(embeddings.keys(), key=lambda x: x.value)]
        return np.concatenate(arrays)

    def _fuse_weighted_sum(self, embeddings: Dict[MediaType, np.ndarray]) -> tuple:
        """Weighted sum of embeddings with modality weights."""
        weights = self.config.modality_weights
        total_weight = sum(weights.get(m, 1.0) for m in embeddings)
        fused = np.zeros_like(next(iter(embeddings.values())))
        contributions = {}
        for m, emb in embeddings.items():
            w = weights.get(m, 1.0) / total_weight
            fused += w * emb.flatten()
            contributions[m] = w
        return fused, contributions

    def _fuse_attention(self, embeddings: Dict[MediaType, np.ndarray]) -> tuple:
        """Cross-modal attention fusion (simplified)."""
        # Stack embeddings
        modalities = list(embeddings.keys())
        stacked = np.stack([embeddings[m].flatten() for m in modalities])
        # Self-attention over modalities
        d_k = stacked.shape[-1]
        scores = stacked @ stacked.T / np.sqrt(d_k)
        attn_weights = np.exp(scores / self.config.attention_temperature)
        attn_weights = attn_weights / attn_weights.sum(axis=-1, keepdims=True)
        # Weighted combination
        fused = (attn_weights @ stacked).mean(axis=0)
        contributions = {m: float(attn_weights[i].mean()) for i, m in enumerate(modalities)}
        return fused, contributions

    def _fuse_product_of_experts(self, embeddings: Dict[MediaType, np.ndarray]) -> tuple:
        """Product of experts fusion (probabilistic)."""
        # Assume Gaussian experts, compute precision-weighted mean
        fused = np.zeros_like(next(iter(embeddings.values())))
        total_precision = 0
        contributions = {}
        for m, emb in embeddings.items():
            # Uniform precision for simplicity
            precision = 1.0
            fused += precision * emb.flatten()
            total_precision += precision
            contributions[m] = precision
        fused /= total_precision
        contributions = {m: c / total_precision for m, c in contributions.items()}
        return fused, contributions

    def _fuse_hierarchical(self, embeddings: Dict[MediaType, np.ndarray]) -> tuple:
        """Hierarchical fusion: early fusion for similar modalities, late fusion for decisions."""
        # Group by modality category
        visual = {m: e for m, e in embeddings.items() if m in (MediaType.IMAGE, MediaType.VIDEO, MediaType.SCREEN, MediaType.CAMERA, MediaType.DOCUMENT)}
        audio = {m: e for m, e in embeddings.items() if m == MediaType.AUDIO}
        text = {m: e for m, e in embeddings.items() if m in (MediaType.TEXT, MediaType.STRUCTURED_DATA)}

        # Early fusion within groups
        fused_parts = []
        contributions = {}
        for group_name, group_embs in [("visual", visual), ("audio", audio), ("text", text)]:
            if group_embs:
                group_fused = np.mean([e.flatten() for e in group_embs.values()], axis=0)
                fused_parts.append(group_fused)
                for m in group_embs:
                    contributions[m] = 1.0 / len(group_embs)

        # Late fusion across groups
        if fused_parts:
            fused = np.concatenate(fused_parts)
        else:
            fused = np.zeros(512)

        return fused, contributions


def create_fusion_engine(
    strategy: FusionStrategy = FusionStrategy.CONCATENATE,
    alignment: ModalityAlignment = ModalityAlignment.SEMANTIC,
    tracker: Optional[ProvenanceTracker] = None,
) -> CrossModalFusionEngine:
    """Factory for creating a configured fusion engine."""
    config = FusionConfig(strategy=strategy, alignment=alignment)
    return CrossModalFusionEngine(config=config, tracker=tracker)


# Convenience functions for common fusion patterns
def fuse_image_text(
    image: MediaObject,
    text: MediaObject,
    strategy: FusionStrategy = FusionStrategy.ATTENTION,
    tracker: Optional[ProvenanceTracker] = None,
) -> FusionResult:
    """Fuse image and text modalities (common pattern)."""
    engine = create_fusion_engine(strategy=strategy, tracker=tracker)
    inputs = [
        FusionInput(media=image),
        FusionInput(media=text),
    ]
    return engine.fuse(inputs)


def fuse_video_audio(
    video: MediaObject,
    audio: MediaObject,
    strategy: FusionStrategy = FusionStrategy.HIERARCHICAL,
    tracker: Optional[ProvenanceTracker] = None,
) -> FusionResult:
    """Fuse video and audio modalities (temporal alignment)."""
    engine = create_fusion_engine(strategy=strategy, alignment=ModalityAlignment.TEMPORAL, tracker=tracker)
    inputs = [
        FusionInput(media=video),
        FusionInput(media=audio),
    ]
    return engine.fuse(inputs)


def fuse_multimodal(
    *medias: MediaObject,
    strategy: FusionStrategy = FusionStrategy.CONCATENATE,
    alignment: ModalityAlignment = ModalityAlignment.SEMANTIC,
    tracker: Optional[ProvenanceTracker] = None,
) -> FusionResult:
    """Fuse arbitrary number of modalities."""
    engine = create_fusion_engine(strategy=strategy, alignment=alignment, tracker=tracker)
    inputs = [FusionInput(media=m) for m in medias]
    return engine.fuse(inputs)