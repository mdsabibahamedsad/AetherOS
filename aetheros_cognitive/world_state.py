"""World state + entity/relationship graph (Phases A-B, §3-10, §89-92).

Temporal validity, staleness, observation conflicts resolved by source
authority + freshness + independence + direct observation. Snapshots
enable replay/simulation/rollback/counterfactuals.
"""

from __future__ import annotations

import copy
import time
from typing import Any, Dict, List, Optional

from .models import Entity, Provenance, Relationship, WorldState, new_id


class StateEstimator:
    """Perception layer: fold observations into a WorldState."""

    def __init__(self):
        self.state = WorldState()
        self.snapshots: Dict[str, WorldState] = {}
        # source -> authority rank (higher wins ties)
        self.authority: Dict[str, int] = {"direct": 3, "tool": 2,
                                          "memory": 1, "model": 0}

    # -- entities ----------------------------------------------------------
    def observe_entity(self, entity: Entity, source: str = "direct",
                       ttl_s: Optional[float] = None) -> None:
        entity.observed_at = time.time()
        entity.valid_until = (time.time() + ttl_s) if ttl_s else None
        self.state.sources[entity.id] = source
        prev = self.state.entities.get(entity.id)
        if prev is None:
            entity.provenance = Provenance.OBSERVED.value
            self.state.entities[entity.id] = entity
            return
        # conflict: prefer higher authority, then fresher
        old_auth = self.authority.get(self.state.sources.get(
            entity.id, "model"), 0)
        new_auth = self.authority.get(source, 0)
        if new_auth > old_auth or (
                new_auth == old_auth
                and entity.observed_at >= prev.observed_at):
            if (prev.state != entity.state
                    and self.state.sources.get(entity.id) != source):
                entity.provenance = Provenance.CONTRADICTED.value
            else:
                entity.provenance = Provenance.OBSERVED.value
            self.state.entities[entity.id] = entity
        else:
            prev.provenance = Provenance.CONTRADICTED.value

    def mark_unknown(self, entity_id: str, reason: str = "") -> None:
        ent = self.state.entities.get(entity_id)
        if ent:
            ent.provenance = Provenance.UNKNOWN.value
            ent.confidence = 0.0
        if reason and reason not in self.state.known_unknowns:
            self.state.known_unknowns.append(reason)

    def relate(self, src: str, rel: str, dst: str,
               confidence: float = 1.0,
               provenance: str = "observed") -> None:
        self.state.relationships.append(Relationship(
            src, rel, dst, confidence, provenance))

    def neighbors(self, entity_id: str) -> List[Relationship]:
        return [r for r in self.state.relationships
                if r.src == entity_id or r.dst == entity_id]

    # -- snapshots / temporal -----------------------------------------------
    def snapshot(self) -> str:
        snap = copy.deepcopy(self.state)
        snap.state_id = new_id("snap")
        self.snapshots[snap.state_id] = snap
        return snap.state_id

    def restore(self, snapshot_id: str) -> WorldState:
        snap = self.snapshots.get(snapshot_id)
        if snap is None:
            raise KeyError(f"unknown snapshot {snapshot_id}")
        self.state = copy.deepcopy(snap)
        self.state.version += 1
        return self.state

    def refresh_stale(self, entity_id: str) -> bool:
        """Returns True if entity was stale (§187 caller re-observes)."""
        ent = self.state.entities.get(entity_id)
        return bool(ent and ent.is_stale())

    def present(self) -> Dict[str, Any]:
        """Task-specific projection (never the whole state blindly)."""
        return {"state_id": self.state.state_id,
                "version": self.state.version,
                "entities": {k: {"kind": e.kind, "state": e.state,
                                 "confidence": e.confidence,
                                 "provenance": e.provenance,
                                 "stale": e.is_stale()}
                             for k, e in self.state.entities.items()},
                "goals": self.state.goals,
                "constraints": self.state.constraints,
                "known_unknowns": self.state.known_unknowns}
