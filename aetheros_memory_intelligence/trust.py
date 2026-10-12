"""Trust model for memory entries.

Trust is a property of *provenance*, not content.  A fresh entry's trust
starts from its origin's baseline; verification (corroboration) raises it;
age decays it toward zero unless refreshed.  Confidence combines trust with
recency.  These numbers drive the write pipeline's grounding filter and the
context engine's ranking, so a poisoned low-trust web fact never outranks a
corroborated user fact.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Dict, Optional

from aetheros_memory_intelligence.schema import MemoryEntry
from aetheros_memory_intelligence.types import TrustLevel, VerificationLevel


@dataclass
class TrustModel:
    """Compute trust/confidence for entries."""

    # Verification -> additive trust bonus.
    verification_bonus: Dict[str, float] = None
    # Age decay half-life in days (trust halves after this long without refresh).
    decay_half_life_days: float = 90.0
    # Recency weight in confidence blend.
    recency_weight: float = 0.2

    def __post_init__(self) -> None:
        if self.verification_bonus is None:
            self.verification_bonus = {
                VerificationLevel.UNVERIFIED.value: 0.0,
                VerificationLevel.SINGLE_SOURCE.value: 0.05,
                VerificationLevel.CORROBORATED.value: 0.15,
                VerificationLevel.CONTRADICTED.value: -0.3,
            }

    def initial_trust(self, origin_trust: float) -> float:
        return max(0.0, min(1.0, origin_trust))

    def trust_for(self, entry: MemoryEntry) -> float:
        """Compute the entry's current trust from its provenance + age."""
        base = entry.trust if entry.trust > 0 else 0.5
        bonus = self.verification_bonus.get(entry.verification, 0.0)
        raw = base + bonus
        raw = self._apply_age_decay(raw, entry)
        return max(0.0, min(1.0, raw))

    def _apply_age_decay(self, trust: float, entry: MemoryEntry) -> float:
        if entry.memory_type and entry.memory_type.is_transient:
            return trust  # transient entries don't age-decay
        age_days = (time.time() - entry.updated_at) / 86400.0
        if age_days <= 0:
            return trust
        half_life = max(self.decay_half_life_days, 1.0)
        decay = math.pow(0.5, age_days / half_life)
        return trust * decay

    def confidence(self, entry: MemoryEntry) -> float:
        """Blend trust with recency to get a single [0,1] confidence."""
        trust = self.trust_for(entry)
        age_hours = (time.time() - entry.updated_at) / 3600.0
        recency = math.exp(-age_hours / (24.0 * 7.0))  # ~1-week decay
        w = self.recency_weight
        return max(0.0, min(1.0, (1.0 - w) * trust + w * recency))

    def trust_level(self, trust: float) -> TrustLevel:
        if trust >= 0.8:
            return TrustLevel.VERIFIED if trust >= 0.9 else TrustLevel.HIGH
        if trust >= 0.6:
            return TrustLevel.MEDIUM
        if trust >= 0.35:
            return TrustLevel.LOW
        return TrustLevel.UNTRUSTED