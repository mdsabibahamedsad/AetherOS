"""Planner ( คน §25-27, §72-87): real search strategies over the
simulator — beam, best-first, A*, MCTS-lite, heuristic. Risk-constrained:
policy/budget violations pruned pre-execution (§73, §87). Reversibility
preferred on ties (§75). Weights documented in SCORE_WEIGHTS (§76).
"""

from __future__ import annotations

import heapq
import math
import random
from typing import Any, Callable, Dict, List, Optional

from .models import (ActionCandidate, FutureBranch, SimulationBudget,
                     WorldState)
from .simulator import Simulator
from .world_models import SimulationUnavailable

# Documented scoring weights (§76): goal progress, success likelihood,
# risk, cost, latency, reversibility, confidence.
SCORE_WEIGHTS = {"goal": 1.0, "success": 1.0, "risk": -1.5, "cost": -0.3,
                 "latency": -0.1, "reversibility": 0.5, "confidence": 0.7}


def score_branch(branch: FutureBranch,
                 weights: Optional[Dict[str, float]] = None) -> float:
    w = weights or SCORE_WEIGHTS
    goal = float(branch.outcome.get("goal_progress", 0.5))
    succ = branch.frequency or 0.5
    return (w["goal"] * goal + w["success"] * succ
            + w["risk"] * branch.risk + w["cost"] * branch.cost
            + w["confidence"] * branch.confidence)


class Planner:
    def __init__(self, simulator: Simulator,
                 goal_test: Optional[Callable[[Dict[str, Any]], float]]
                 = None):
        self.sim = simulator
        self.goal_test = goal_test or (lambda _s: 0.5)
        # policy hook: returns denial reason or None (wired to M50)
        self.policy_check: Optional[Callable[[Dict[str, Any]], Optional[str]]] \
            = None
        self.pruned = 0

    # -- candidate expansion ------------------------------------------------
    def expand(self, state: WorldState,
               generator: Callable[[WorldState], List[ActionCandidate]],
               budget: Optional[SimulationBudget] = None) -> List[Dict]:
        budget = budget or SimulationBudget()
        scored = []
        for cand in generator(state)[:budget.max_branches]:
            if not self._preconditions_ok(cand, state):
                self.pruned += 1
                continue
            if self.policy_check:
                denial = self.policy_check({"type": cand.type,
                                            "parameters": cand.parameters})
                if denial:  # §73: reject before execution
                    self.pruned += 1
                    continue
            branch = None
            try:
                branch = self.sim.rollout(state, [{"type": cand.type,
                                                   "parameters": cand.parameters,
                                                   "tool": cand.parameters.get(
                                                       "tool")}],
                                          budget)
            except SimulationUnavailable:
                # §190: reactive planning stays functional without a model.
                branch = FutureBranch(parent_state_id=state.state_id)
                branch.actions.append(cand.type)
                branch.confidence = 0.0
                branch.outcome["goal_progress"] = 0.0
                branch.outcome["model_unavailable"] = True
            branch.risk = cand.risk
            branch.cost = cand.cost
            if branch.predicted_states:
                branch.outcome["goal_progress"] = self.goal_test(
                    branch.predicted_states[-1])
            branch.score = score_branch(branch)
            # reversibility tie-break (§75)
            scored.append((branch.score + 0.01 * cand.reversibility,
                           cand, branch))
        scored.sort(key=lambda t: -t[0])
        return [{"candidate": c, "branch": b, "score": s}
                for s, c, b in scored]

    @staticmethod
    def _preconditions_ok(cand: ActionCandidate,
                          state: WorldState) -> bool:
        present = {e.id for e in state.entities.values()}
        present |= {e.kind for e in state.entities.values()}
        return all(p in present or p in state.available_actions
                   for p in cand.preconditions)

    # -- strategies -----------------------------------------------------------
    def beam_search(self, state: WorldState, generator, depth: int = 2,
                    width: int = 3,
                    budget: Optional[SimulationBudget] = None) -> List[Dict]:
        budget = budget or SimulationBudget()
        frontier = [{"state": state, "path": [], "score": 0.0}]
        for _ in range(min(depth, budget.max_depth)):
            nxt = []
            for node in frontier:
                for item in self.expand(node["state"], generator,
                                        budget)[:width]:
                    nxt.append({"item": item, "score": item["score"]})
            if not nxt:
                break
            nxt.sort(key=lambda n: -n["score"])
            frontier = [{"state": state,
                         "path": [n["item"]],
                         "score": n["score"]} for n in nxt[:width]]
            # adaptive: stop when clearly dominated (§86)
            if len(frontier) > 1 and (frontier[0]["score"]
                                      - frontier[1]["score"] > 2.0):
                break
        out = []
        for node in frontier:
            out.extend(node["path"])
        return out

    def best_first(self, state: WorldState, generator,
                   budget: Optional[SimulationBudget] = None) -> List[Dict]:
        items = self.expand(state, generator, budget)
        heap = [(-it["score"], i, it) for i, it in enumerate(items)]
        heapq.heapify(heap)
        return [heapq.heappop(heap)[2] for _ in range(len(heap))]

    def a_star(self, state: WorldState, generator,
               heuristic: Optional[Callable[[Dict], float]] = None,
               budget: Optional[SimulationBudget] = None) -> List[Dict]:
        h = heuristic or (lambda _it: 0.0)
        items = self.expand(state, generator, budget)
        ranked = sorted(items,
                        key=lambda it: -(it["score"] + h(it["branch"].__dict__)))
        return ranked

    def mcts(self, state: WorldState, generator, iterations: int = 12,
             budget: Optional[SimulationBudget] = None,
             seed: int = 0) -> List[Dict]:
        """MCTS-lite: UCB1 over candidate arms using simulator rollouts."""
        rng = random.Random(seed)
        arms = self.expand(state, generator, budget)
        if not arms:
            return []
        wins = [0.0] * len(arms)
        pulls = [0] * len(arms)
        total = 0
        for _ in range(min(iterations,
                           (budget or SimulationBudget()).max_rollouts)):
            best, best_ucb = 0, -1e9
            for i in range(len(arms)):
                if pulls[i] == 0:
                    best, best_ucb = i, 1e9
                    break
                ucb = (wins[i] / pulls[i] + math.sqrt(2 * math.log(total + 1)
                                                     / pulls[i]))
                if ucb > best_ucb:
                    best, best_ucb = i, ucb
            arm = arms[best]
            reward = max(0.0, min(1.0, arm["score"]))
            if rng.random() < 0.15:  # stochastic rollout noise
                reward = rng.random() * reward
            pulls[best] += 1
            wins[best] += reward
            total += 1
        order = sorted(range(len(arms)),
                       key=lambda i: -(wins[i] / max(1, pulls[i])))
        return [arms[i] for i in order]
