"""Cognitive router (Phase L, §99-104, §190-191): mode selection by
risk/uncertainty/horizon/complexity/cost; user override Fast/Balanced/
Deep/Max (Max stays budget-constrained, §104); safe degradation chain
Deep → Basic → Reactive, never total failure (§191).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .models import CognitiveMode, SimulationBudget


class CognitiveRouter:
    MODES = [m.value for m in CognitiveMode]

    def __init__(self, user_preference: str = "balanced"):
        assert user_preference in ("fast", "balanced", "deep", "max")
        self.user_preference = user_preference
        self.selections = 0

    def select(self, risk: float, uncertainty: float, horizon: int,
               complexity: float, reversible: bool = True,
               world_model_available: bool = True) -> Dict[str, Any]:
        self.selections += 1
        if not world_model_available:
            return {"mode": CognitiveMode.REACTIVE.value,
                    "reason": "world model unavailable — reactive "
                              "fallback (§190)", "degraded": True}
        if self.user_preference == "fast" and risk < 0.5:
            return {"mode": CognitiveMode.REACTIVE.value,
                    "reason": "user=fast, low risk"}
        if risk >= 0.8 or (uncertainty >= 0.6 and horizon >= 5):
            mode = CognitiveMode.DELIBERATIVE.value
        elif uncertainty >= 0.5 and horizon >= 3:
            mode = CognitiveMode.COUNTERFACTUAL.value
        elif horizon >= 3 or complexity >= 0.7:
            mode = CognitiveMode.SIMULATIVE.value
        elif uncertainty >= 0.4:
            mode = CognitiveMode.CAUSAL.value
        elif risk >= 0.3 or horizon >= 2:
            mode = CognitiveMode.FORESIGHT.value
        else:
            mode = CognitiveMode.REACTIVE.value
        if self.user_preference == "max":
            mode = CognitiveMode.DELIBERATIVE.value
        elif self.user_preference == "deep" and mode == \
                CognitiveMode.REACTIVE.value:
            mode = CognitiveMode.FORESIGHT.value
        depth = {"reactive": 0, "foresight": 2, "causal": 2,
                 "simulative": 4, "counterfactual": 4,
                 "deliberative": 6}[mode]
        return {"mode": mode, "depth": depth,
                "budget": SimulationBudget(
                    max_depth=depth,
                    max_branches=4 if mode in ("reactive", "foresight")
                    else 8). __dict__,
                "reason": f"risk={risk} unc={uncertainty} horizon={horizon}"}

    @staticmethod
    def degrade(mode: str) -> str:
        chain = {"deliberative": "simulative", "simulative": "foresight",
                 "counterfactual": "simulative", "causal": "foresight",
                 "foresight": "reactive", "reactive": "reactive"}
        return chain.get(mode, "reactive")
