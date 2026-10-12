"""Seeded chaos harness (P94): deterministic fault injection into executors.

Faults are declared per (node_key, attempt) so runs are reproducible:
    ChaosHarness(fail_plan={
        ("research", 1): FailureType.NETWORK_ERROR,
        ("coding", 2): TimeoutError,
    })
The orchestrator's recovery path must still reach a safe terminal state.
"""

from __future__ import annotations

import random
from typing import Any, Callable, Dict, Optional, Tuple

from agent.orchestration.types import FailureType


class ChaosHarness:
    def __init__(
        self,
        base_executor: Callable[[Dict[str, Any]], Any],
        *,
        fail_plan: Optional[Dict[Tuple[str, int], Any]] = None,
        seed: int = 1234,
        random_failure_rate: float = 0.0,
        rng_faults: Optional[list] = None,
    ):
        self.base = base_executor
        self.fail_plan = dict(fail_plan or {})
        self.random_rate = random_failure_rate
        self.rng = random.Random(seed)
        self.rng_faults = rng_faults or [
            RuntimeError("chaos-random"),
            TimeoutError("chaos-timeout"),
            ConnectionError("chaos-network"),
        ]
        self.calls: Dict[str, int] = {}

    def __call__(self, ctx: Dict[str, Any]) -> Any:
        node = ctx.get("node")
        key = getattr(node, "node_key", "?")
        n = self.calls.get(key, 0) + 1
        self.calls[key] = n
        planned = self.fail_plan.get((key, n))
        if planned is not None:
            raise planned if isinstance(planned, BaseException) else \
                RuntimeError(str(planned))
        if self.random_rate > 0 and self.rng.random() < self.random_rate:
            raise self.rng.choice(self.rng_faults)
        return self.base(ctx)
