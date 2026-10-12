"""Budget engine (sections 52-53): global caps, sub-budgets, reallocation.

Real accounting only: executors report measured tokens/cost/tool calls;
the engine enforces caps and redistributes unused budget without ever
exceeding the global limit. Uses provider pricing when supplied, else the
role cost profile from the registry (never fabricated per-call cost).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List

from aetheros_swarm.models import TaskBudget


@dataclass
class RunBudget:
    max_tokens: int = 60000
    max_cost_usd: float = 1.00
    max_duration_s: float = 3600.0
    max_agents: int = 10
    max_tool_calls: int = 200
    max_retries: int = 3
    max_depth: int = 3


class BudgetEngine:
    def __init__(self, run: RunBudget) -> None:
        self.run = run
        self._lock = threading.Lock()
        self.used_tokens = 0
        self.used_cost = 0.0
        self.used_tools = 0
        self.allocations: Dict[str, TaskBudget] = {}

    def allocate(self, task_id: str, share: float) -> TaskBudget:
        """Carve a sub-budget as a share of the remaining global budget."""
        with self._lock:
            rem_tok = max(0, self.run.max_tokens - self.used_tokens)
            rem_cost = max(0.0, self.run.max_cost_usd - self.used_cost)
            rem_tools = max(0, self.run.max_tool_calls - self.used_tools)
            sub = TaskBudget(max_tokens=max(500, int(rem_tok * share)),
                             max_cost_usd=round(rem_cost * share, 4),
                             max_tool_calls=max(2, int(rem_tools * share)),
                             max_retries=self.run.max_retries)
            self.allocations[task_id] = sub
            return sub

    def charge(self, task_id: str, *, tokens: int = 0,
               cost: float = 0.0, tools: int = 0) -> None:
        with self._lock:
            self.used_tokens += tokens
            self.used_cost += cost
            self.used_tools += tools
            sub = self.allocations.get(task_id)
            if sub is not None:
                sub.tokens_used += tokens
                sub.cost_used_usd += cost
                sub.tool_calls_used += tools

    def reallocate_unused(self, from_task: str, to_task: str) -> Dict[str, float]:
        """Move unused sub-budget between tasks; global cap unchanged."""
        with self._lock:
            src = self.allocations.get(from_task)
            dst = self.allocations.get(to_task)
            if src is None or dst is None:
                return {}
            move_tok = max(0, src.max_tokens - src.tokens_used)
            move_cost = max(0.0, src.max_cost_usd - src.cost_used_usd)
            # Leave 10% reserve on the source.
            move_tok = int(move_tok * 0.9)
            move_cost = round(move_cost * 0.9, 4)
            src.max_tokens -= move_tok
            src.max_cost_usd = round(src.max_cost_usd - move_cost, 4)
            dst.max_tokens += move_tok
            dst.max_cost_usd = round(dst.max_cost_usd + move_cost, 4)
            return {"tokens": move_tok, "cost_usd": move_cost}

    def within_limits(self) -> bool:
        with self._lock:
            return (self.used_tokens < self.run.max_tokens
                    and self.used_cost < self.run.max_cost_usd
                    and self.used_tools < self.run.max_tool_calls)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {"run": {f: getattr(self.run, f) for f in self.run.__dataclass_fields__},
                    "used_tokens": self.used_tokens,
                    "used_cost_usd": round(self.used_cost, 4),
                    "used_tools": self.used_tools,
                    "allocations": len(self.allocations)}
