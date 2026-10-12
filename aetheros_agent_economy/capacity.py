"""Capacity awareness + load-aware routing (spec sections 11-12).

Capacity is tracked where available (advertised or observed); unknown
capacity is reported as unknown, never assumed infinite. Load-aware
routing may prefer an available peer ONLY when capability, trust,
security, policy, and quality remain acceptable — safety is never
sacrificed for latency.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_agent_market.store import JsonStore


@dataclass
class CapacitySnapshot:
    agent_id: str = ""
    concurrency_used: Optional[int] = None
    concurrency_max: Optional[int] = None
    queue_length: Optional[int] = None
    rate_limit_per_min: Optional[int] = None
    quota_remaining: Optional[int] = None
    availability: str = "unknown"  # available|limited|unavailable|unknown
    health: str = "unknown"        # online|degraded|offline|unknown
    observed_latency_ms: Optional[float] = None
    at: float = field(default_factory=time.time)
    provenance: str = "advertised"  # advertised|observed|registry

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapacitySnapshot":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})

    def load_ratio(self) -> Optional[float]:
        if self.concurrency_used is None or not self.concurrency_max:
            return None
        return max(0.0, self.concurrency_used / self.concurrency_max)

    def is_usable(self) -> bool:
        if self.availability == "unavailable" or self.health == "offline":
            return False
        if self.quota_remaining is not None and self.quota_remaining <= 0:
            return False
        ratio = self.load_ratio()
        if ratio is not None and ratio >= 1.0:
            return False
        return True


class CapacityRegistry:
    """Live capacity view. Snapshots expire (stale capacity is not trusted)."""

    def __init__(self, home: Path, max_age_s: float = 300.0) -> None:
        self._store = JsonStore(Path(home) / "capacity.json")
        self.max_age_s = max_age_s

    def report(self, snapshot: CapacitySnapshot) -> CapacitySnapshot:
        if not snapshot.agent_id:
            raise ValueError("agent_id required")
        snapshot.at = time.time()
        self._store.put(snapshot.agent_id, snapshot.to_dict())
        return snapshot

    def get(self, agent_id: str) -> Optional[CapacitySnapshot]:
        raw = self._store.get(agent_id)
        if raw is None:
            return None
        snap = CapacitySnapshot.from_dict(raw)
        if time.time() - snap.at > self.max_age_s:
            return None  # stale: treated as unknown, never as available
        return snap

    def overloaded(self, agent_id: str, threshold: float = 0.85) -> Optional[bool]:
        """True/False/None(unknown). Unknown is never treated as healthy."""
        snap = self.get(agent_id)
        if snap is None:
            return None
        if not snap.is_usable():
            return True
        ratio = snap.load_ratio()
        if ratio is None:
            return None
        return ratio >= threshold


def route_load_aware(primary_id: str, candidate_ids: List[str],
                     capacity: CapacityRegistry,
                     gate: Any,
                     min_trust_rank: int = 0) -> Dict[str, Any]:
    """Choose between a preferred agent and alternatives.

    `gate(candidate_id) -> (ok: bool, reason: str)` enforces capability,
    trust, security, policy, quality OUTSIDE this module (caller-owned).
    Returns {selected, rerouted, reasons}. Never reroutes on unknown data.
    """
    reasons = []
    primary_over = capacity.overloaded(primary_id)
    if primary_over is not True:
        state = "healthy" if primary_over is False else "unknown"
        return {"selected": primary_id, "rerouted": False,
                "reasons": [f"primary {primary_id} {state}; no reroute"]}
    reasons.append(f"primary {primary_id} overloaded/unusable")
    for cand in candidate_ids:
        if cand == primary_id:
            continue
        snap = capacity.get(cand)
        if snap is None:
            reasons.append(f"{cand}: capacity unknown — skipped (never assume)")
            continue
        if not snap.is_usable():
            reasons.append(f"{cand}: unusable ({snap.availability}/{snap.health})")
            continue
        ok, why = gate(cand)
        if not ok:
            reasons.append(f"{cand}: gate rejected ({why})")
            continue
        return {"selected": cand, "rerouted": True,
                "reasons": reasons + [f"{cand}: acceptable on all gates"]}
    return {"selected": primary_id, "rerouted": False,
            "reasons": reasons + ["no acceptable alternative; keep primary "
                                  "(safety over latency)"]}
