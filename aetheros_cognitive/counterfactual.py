"""Counterfactual engine (Phase I, §22-23, §69): generate / simulate /
compare / rank / explain alternative scenarios from state snapshots.
All alternatives are PREDICTIONS compared against the chosen branch.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .models import SimulationBudget, WorldState
from .planner import score_branch
from .simulator import Simulator


class CounterfactualEngine:
    def __init__(self, simulator: Simulator):
        self.sim = simulator

    def generate(self, state: WorldState,
                 alternatives: List[List[Dict[str, Any]]]) -> List[Dict]:
        return [{"scenario_id": i, "actions": alt}
                for i, alt in enumerate(alternatives)]

    def simulate(self, state: WorldState, scenarios: List[Dict],
                 budget: Optional[SimulationBudget] = None) -> List[Dict]:
        out = []
        for sc in scenarios:
            branch = self.sim.rollout(state, sc["actions"],
                                      budget or SimulationBudget())
            out.append({**sc, "branch": branch,
                        "score": score_branch(branch)})
        return out

    def compare(self, chosen: Dict, alternatives: List[Dict]) -> Dict:
        ranked = sorted(alternatives,
                        key=lambda s: -s.get("score", 0.0))
        return {"chosen_score": chosen.get("score", 0.0),
                "best_alternative": (ranked[0]["scenario_id"]
                                     if ranked else None),
                "would_change": bool(ranked) and ranked[0].get(
                    "score", 0.0) > chosen.get("score", 0.0) + 0.1,
                "ranking": [s["scenario_id"] for s in ranked]}

    def explain_difference(self, chosen: Dict,
                           alternative: Dict) -> str:
        cb, ab = chosen["branch"], alternative["branch"]
        return (f"Chosen ends {cb.predicted_states[-1:] or 'unknown'} "
                f"(score {chosen.get('score', 0):.2f}, risk {cb.risk:.2f}); "
                f"alternative ends {ab.predicted_states[-1:] or 'unknown'} "
                f"(score {alternative.get('score', 0):.2f}, "
                f"risk {ab.risk:.2f}). Both are PREDICTIONS, not facts.")
