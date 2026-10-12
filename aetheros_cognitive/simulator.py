"""Simulator (Phase E, §24-29, §32, §121-127): budget-enforced rollouts
over a WorldModel. Side-effect firewall: only tools declaring
simulationSafe run even in simulation; anything else returns
SIMULATION_UNAVAILABLE (§122-124). Simulated tool calls execute against
provided twin/sandbox hooks — never the real environment (§121).
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from .models import FutureBranch, SimulationBudget, WorldState
from .world_models import SimulationUnavailable, WorldModel


class SideEffectFirewall:
    """§122: simulated tools must declare simulationSafe."""

    def __init__(self):
        self.safe_tools: Dict[str, Callable] = {}
        self.attempts_blocked = 0

    def declare_safe(self, tool: str, fn: Callable) -> None:
        self.safe_tools[tool] = fn

    def call(self, tool: str, args: Dict[str, Any]) -> Any:
        fn = self.safe_tools.get(tool)
        if fn is None:
            self.attempts_blocked += 1
            raise SimulationUnavailable(
                f"SIMULATION_UNAVAILABLE: tool '{tool}' has no "
                "simulationSafe implementation (§124)")
        return fn(args)


class Simulator:
    def __init__(self, model: WorldModel,
                 firewall: Optional[SideEffectFirewall] = None):
        self.model = model
        self.firewall = firewall or SideEffectFirewall()
        self.runs = 0

    def rollout(self, state: WorldState, actions: List[Dict[str, Any]],
                budget: Optional[SimulationBudget] = None) -> FutureBranch:
        """Single deterministic rollout; returns branch with PREDICTIONS."""
        budget = budget or SimulationBudget()
        t0 = time.perf_counter()
        branch = FutureBranch(parent_state_id=state.state_id)
        cur = state
        for i, action in enumerate(actions):
            if budget.exceeded(i + 1, 1, self.runs + 1,
                               time.perf_counter() - t0, 0.0):
                branch.outcome = {"truncated": True,
                                  "reason": "budget exceeded"}
                break
            tool = action.get("tool")
            if tool:
                # simulated tool effect only — firewall enforced
                self.firewall.call(tool, action.get("parameters", {}))
            pred = self.model.predict_next(cur, action, horizon=1)
            branch.actions.append(action.get("type", action.get("tool",
                                                                "?")))
            branch.predicted_states.append(pred.state)
            branch.confidence = pred.confidence.combined() \
                if pred.confidence else 0.0
        self.runs += 1
        return branch

    def monte_carlo(self, state: WorldState,
                    action_sets: List[List[Dict[str, Any]]],
                    budget: Optional[SimulationBudget] = None,
                    rollouts_per_set: int = 4) -> List[FutureBranch]:
        """N rollouts per action set; frequency = simulation frequency,
        NOT real-world probability (§28)."""
        budget = budget or SimulationBudget()
        branches: List[FutureBranch] = []
        for actions in action_sets[:budget.max_branches]:
            outs: List[FutureBranch] = []
            for _ in range(min(rollouts_per_set, budget.max_rollouts)):
                outs.append(self.rollout(state, actions, budget))
            # aggregate identical predicted outcomes
            seen: Dict[str, int] = {}
            for b in outs:
                key = str(b.predicted_states[-1]) if b.predicted_states \
                    else "empty"
                seen[key] = seen.get(key, 0) + 1
            total = max(1, len(outs))
            for b in outs:
                key = str(b.predicted_states[-1]) if b.predicted_states \
                    else "empty"
                b.frequency = seen[key] / total
                branches.append(b)
        return branches
