"""World-model backends (Phases C-D, §11-14, §49-51, §93-94, §118-119).

Hybrid default: deterministic rules → state-transition table → graph
dynamics → (LLM/external only if wired). LLM/NEURAL backends without a
provider report SIMULATION_UNAVAILABLE — never fabricated futures
(§0.3, §124). Models carry versions + trust; repeated failure disables
foresight for that model (§49). Observations become knowledge only via
source/provenance/confidence/validation (§119).
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from .models import (BackendKind, PredictedState, PredictionConfidence,
                     WorldState)


class SimulationUnavailable(Exception):
    pass


class WorldModel:
    kind = BackendKind.RULE_BASED.value
    version = "v1"

    def predict_next(self, state: WorldState, action: Dict[str, Any],
                     horizon: int = 1) -> PredictedState:
        raise NotImplementedError

    def uncertainty(self, state: WorldState, horizon: int) -> float:
        return 0.5

    def update(self, observation: Dict[str, Any],
               error: Optional[Dict[str, Any]] = None) -> None:
        pass

    def describe(self) -> Dict[str, Any]:
        return {"kind": self.kind, "version": self.version}


TransitionFn = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


class RuleBasedWorldModel(WorldModel):
    """Deterministic (action_type -> transition fn) rules (§96 fast path)."""
    kind = BackendKind.RULE_BASED.value

    def __init__(self, version: str = "rules-v1"):
        self.version = version
        self.rules: Dict[str, TransitionFn] = {}
        self.fallback_confidence = 0.2

    def register(self, action_type: str, fn: TransitionFn) -> None:
        self.rules[action_type] = fn

    def predict_next(self, state: WorldState, action: Dict[str, Any],
                     horizon: int = 1) -> PredictedState:
        fn = self.rules.get(action.get("type", ""))
        cur = {k: dict(v.state) for k, v in state.entities.items()}
        conf = 0.9 if fn else self.fallback_confidence
        for _ in range(max(1, horizon)):
            if fn is None:
                break  # unknown action: explicit low-confidence, no fiction
            cur = fn(cur, action.get("parameters", {}))
        return PredictedState(
            state=cur,
            confidence=PredictionConfidence(
                model=conf, data=0.8, state=state.confidence,
                causal=0.6, env_similarity=0.8,
                horizon_penalty=min(0.9, 0.15 * (horizon - 1))),
            horizon=horizon, model_version=self.version,
            provenance={"backend": self.kind, "rule": fn is not None})

    def uncertainty(self, state: WorldState, horizon: int) -> float:
        return min(0.95, 0.1 + 0.15 * horizon)


class StateTransitionWorldModel(WorldModel):
    """Explicit (state_key, action_type) -> next_state_key table (§14)."""
    kind = BackendKind.STATE_TRANSITION.value

    def __init__(self, table: Optional[Dict[str, str]] = None,
                 version: str = "trans-v1"):
        self.version = version
        self.table = dict(table or {})

    def learn(self, state_key: str, action_type: str,
              next_key: str) -> None:
        self.table[f"{state_key}|{action_type}"] = next_key

    def predict_next(self, state: WorldState, action: Dict[str, Any],
                     horizon: int = 1) -> PredictedState:
        key = state.environment.get("mode", "default")
        nxt = self.table.get(f"{key}|{action.get('type', '')}")
        if nxt is None:
            conf = PredictionConfidence(model=0.15, data=0.5,
                                        state=state.confidence, causal=0.3,
                                        env_similarity=0.5,
                                        horizon_penalty=0.2 * horizon)
            return PredictedState(
                state={"mode": key, "unknown_transition": True},
                confidence=conf, horizon=horizon,
                model_version=self.version,
                provenance={"backend": self.kind, "known": False})
        cur = nxt
        for _ in range(horizon - 1):
            cur = self.table.get(f"{cur}|{action.get('type', '')}", cur)
        return PredictedState(
            state={"mode": cur}, confidence=PredictionConfidence(
                model=0.85, data=0.8, state=state.confidence, causal=0.6,
                env_similarity=0.85,
                horizon_penalty=min(0.9, 0.12 * (horizon - 1))),
            horizon=horizon, model_version=self.version,
            provenance={"backend": self.kind, "known": True})


class GraphDynamicsWorldModel(WorldModel):
    """Propagate state along depends_on/contains edges (§171)."""
    kind = BackendKind.GRAPH_DYNAMICS.value

    def predict_next(self, state: WorldState, action: Dict[str, Any],
                     horizon: int = 1) -> PredictedState:
        target = (action.get("parameters", {}) or {}).get("target")
        affected = {target} if target else set()
        for _ in range(horizon):
            grown = set(affected)
            for r in state.relationships:
                if r.rel in ("depends_on", "contains", "derived_from"):
                    if r.src in affected:
                        grown.add(r.dst)
                    if r.dst in affected:
                        grown.add(r.src)
            affected = grown
        return PredictedState(
            state={"affected": sorted(affected)},
            confidence=PredictionConfidence(
                model=0.6, data=0.7, state=state.confidence, causal=0.5,
                env_similarity=0.7,
                horizon_penalty=min(0.9, 0.2 * (horizon - 1))),
            horizon=horizon, model_version=self.version,
            provenance={"backend": self.kind})


class LLMWorldModel(WorldModel):
    """Honest seam: needs a provider; otherwise UNAVAILABLE (§0.3)."""
    kind = BackendKind.LLM_SIMULATOR.value

    def __init__(self, infer: Optional[Callable] = None,
                 version: str = "llm-v1"):
        self.version = version
        self._infer = infer

    def predict_next(self, state: WorldState, action: Dict[str, Any],
                     horizon: int = 1) -> PredictedState:
        if self._infer is None:
            raise SimulationUnavailable(
                "STATUS: NOT AVAILABLE — no LLM provider wired for "
                "simulation; use rule/state/graph backends.")
        return self._infer(state, action, horizon)


class HybridWorldModel(WorldModel):
    """Rules → transition table → graph → external, first-known wins."""
    kind = BackendKind.HYBRID.value

    def __init__(self, models: List[WorldModel],
                 version: str = "hybrid-v1"):
        self.version = version
        self.models = models
        self.consecutive_failures = 0
        self.disabled = False  # §49: broken model stops being used

    def predict_next(self, state: WorldState, action: Dict[str, Any],
                     horizon: int = 1) -> PredictedState:
        if self.disabled:
            raise SimulationUnavailable("hybrid model disabled after "
                                        "repeated failures (§49)")
        last: Optional[Exception] = None
        for m in self.models:
            try:
                pred = m.predict_next(state, action, horizon)
                if pred.provenance.get("known", True) is False and \
                        m is not self.models[-1]:
                    continue
                pred.model_version = f"{self.version}+{m.version}"
                return pred
            except SimulationUnavailable as exc:
                last = exc
        raise SimulationUnavailable(
            f"no backend could predict: {last}")

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= 5:
            self.disabled = True

    def record_success(self) -> None:
        self.consecutive_failures = 0

    def update(self, observation: Dict[str, Any],
               error: Optional[Dict[str, Any]] = None) -> None:
        for m in self.models:
            try:
                m.update(observation, error)
            except Exception:
                pass


class ModelEnsemble:
    """Compare predictions; disagreement triggers caution (§50-51)."""

    def __init__(self, models: List[WorldModel]):
        self.models = models

    def predict_all(self, state: WorldState, action: Dict[str, Any],
                    horizon: int = 1) -> List[Dict[str, Any]]:
        out = []
        for m in self.models:
            try:
                p = m.predict_next(state, action, horizon)
                out.append({"model": m.describe(), "state": p.state,
                            "confidence": p.confidence.combined()
                            if p.confidence else 0.0})
            except SimulationUnavailable as exc:
                out.append({"model": m.describe(), "unavailable": str(exc)})
        return out

    @staticmethod
    def disagrees(preds: List[Dict[str, Any]]) -> bool:
        states = [str(p.get("state")) for p in preds
                  if "state" in p]
        return len(set(states)) > 1
