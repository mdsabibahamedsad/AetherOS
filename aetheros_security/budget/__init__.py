"""
Resource Budgets and Recursion Limits for AetherOS
==================================================

Enforce deterministic ceilings on agent missions, delegations, tool chains,
and resource consumption (master security spec steps 46-47).

Two cooperating components:

    - :class:`RecursionGuard` — prevents unbounded agent recursion, delegation
      depth, and tool chaining. A hard depth cap is always applied; a
      policy/context depth cap is optional.
    - :class:`ResourceBudget` — enforces time, token, cost, tool-call, network,
      storage, and compute budgets with configurable limits. Once a budget is
      exhausted the relevant ``can_*`` check returns ``False`` until reset.

Usage::

    from aetheros_security.budget import RecursionGuard, ResourceBudget

    guard = RecursionGuard(max_depth=3)
    guard.push()          # enter an agent/tool scope
    ok = guard.can_recurse()
    guard.pop()

    budget = ResourceBudget(tool_calls=50, cost_usd=5.0)
    budget.spend_tool_call()
    budget.spend_cost(0.10)
    budget.exhausted()     # False until ceilings are hit
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: Absolute hard cap on recursion depth — cannot be overridden by config.
_ABSOLUTE_MAX_DEPTH = 32


class RecursionError(Exception):
    """Raised when a recursion/delegation depth ceiling is exceeded."""


class RecursionGuard:
    """Track recursion / delegation / tool-chain depth.

    The guard is thread-local so nested agents running in parallel do not
    share depth state.

    Args:
        max_depth: Soft cap from policy/context (default 6). The absolute
            cap of ``_ABSOLUTE_MAX_DEPTH`` always applies.
    """

    def __init__(self, max_depth: int = 6) -> None:
        self._max_depth = max(max_depth, 1)
        self._local = threading.local()
        self._local.stack = []

    @property
    def depth(self) -> int:
        return len(getattr(self._local, "stack", []))

    def push(self, scope: str = "") -> int:
        """Enter a scope. Returns the new depth.

        Raises:
            RecursionError: When the absolute cap is exceeded.
        """
        stack = getattr(self._local, "stack", None)
        if stack is None:
            stack = self._local.stack = []
        depth = len(stack) + 1
        if depth > _ABSOLUTE_MAX_DEPTH:
            raise RecursionError(f"absolute recursion cap ({_ABSOLUTE_MAX_DEPTH}) exceeded")
        stack.append(scope)
        return depth

    def pop(self) -> Optional[str]:
        stack = getattr(self._local, "stack", None)
        if stack:
            return stack.pop()
        return None

    def can_recurse(self) -> bool:
        """Whether another recursion level is allowed by the soft cap."""
        return self.depth < self._max_depth

    def remaining(self) -> int:
        return max(0, self._max_depth - self.depth)

    def reset(self) -> None:
        self._local.stack = []


# ---------------------------------------------------------------------------
# Resource budgets
# ---------------------------------------------------------------------------

@dataclass
class BudgetLimits:
    """Configurable ceilings. ``None`` means unlimited for that dimension."""
    time_seconds: Optional[float] = None
    token_budget: Optional[int] = None
    cost_usd: Optional[float] = None
    tool_calls: Optional[int] = None
    network_requests: Optional[int] = None
    storage_bytes: Optional[int] = None
    compute_units: Optional[int] = None


@dataclass
class BudgetState:
    """Current usage counters."""
    start_time: float = 0.0
    tokens: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    network_requests: int = 0
    storage_bytes: int = 0
    compute_units: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time,
            "elapsed_seconds": round(time.time() - self.start_time, 3),
            "tokens": self.tokens,
            "cost_usd": round(self.cost_usd, 6),
            "tool_calls": self.tool_calls,
            "network_requests": self.network_requests,
            "storage_bytes": self.storage_bytes,
            "compute_units": self.compute_units,
        }


class ResourceBudget:
    """Deterministic resource budget enforcement (step 47).

    Usage::

        budget = ResourceBudget(limits=BudgetLimits(tool_calls=10, cost_usd=1.0))
        budget.spend_tool_call()
        budget.can_tool_call()   # False once 10 calls used
    """

    def __init__(self, limits: Optional[BudgetLimits] = None,
                 name: str = "") -> None:
        self._limits = limits or BudgetLimits()
        self._name = name
        self._state = BudgetState(start_time=time.time())

    @property
    def name(self) -> str:
        return self._name

    # -- spenders ----------------------------------------------------------

    def spend_tokens(self, amount: int) -> None:
        self._state.tokens += max(0, int(amount))

    def spend_cost(self, amount: float) -> None:
        self._state.cost_usd += max(0.0, float(amount))

    def spend_tool_call(self) -> None:
        self._state.tool_calls += 1

    def spend_network_request(self) -> None:
        self._state.network_requests += 1

    def spend_storage(self, amount: int) -> None:
        self._state.storage_bytes += max(0, int(amount))

    def spend_compute(self, amount: int = 1) -> None:
        self._state.compute_units += max(0, int(amount))

    # -- checkers ----------------------------------------------------------

    def _exceeded(self, value, limit) -> bool:
        return limit is not None and value is not None and value >= limit

    def time_exceeded(self) -> bool:
        if self._limits.time_seconds is None:
            return False
        return (time.time() - self._state.start_time) >= self._limits.time_seconds

    def can_tool_call(self) -> bool:
        return not self._exceeded(self._state.tool_calls, self._limits.tool_calls)

    def can_network_request(self) -> bool:
        return not self._exceeded(self._state.network_requests, self._limits.network_requests)

    def can_storage(self, additional: int = 0) -> bool:
        if self._limits.storage_bytes is None:
            return True
        return (self._state.storage_bytes + additional) < self._limits.storage_bytes

    def can_tokens(self, additional: int = 0) -> bool:
        if self._limits.token_budget is None:
            return True
        return (self._state.tokens + additional) < self._limits.token_budget

    def can_cost(self, additional: float = 0.0) -> bool:
        if self._limits.cost_usd is None:
            return True
        return (self._state.cost_usd + additional) < self._limits.cost_usd

    def can_compute(self, additional: int = 1) -> bool:
        if self._limits.compute_units is None:
            return True
        return (self._state.compute_units + additional) < self._limits.compute_units

    def exhausted(self) -> bool:
        """Whether ANY configured ceiling has been reached."""
        return (self.time_exceeded()
                or not self.can_tool_call()
                or not self.can_network_request()
                or not self.can_tokens()
                or not self.can_cost()
                or not self.can_compute()
                or not self.can_storage())

    def remaining(self) -> Dict[str, Any]:
        """Human-readable remaining budget per configured dimension."""
        result: Dict[str, Any] = {"elapsed_seconds": round(time.time() - self._state.start_time, 3)}
        if self._limits.time_seconds is not None:
            result["time_remaining_seconds"] = max(
                0, round(self._limits.time_seconds - (time.time() - self._state.start_time), 3))
        if self._limits.token_budget is not None:
            result["tokens_remaining"] = max(0, self._limits.token_budget - self._state.tokens)
        if self._limits.cost_usd is not None:
            result["cost_remaining_usd"] = max(0, round(self._limits.cost_usd - self._state.cost_usd, 6))
        if self._limits.tool_calls is not None:
            result["tool_calls_remaining"] = max(0, self._limits.tool_calls - self._state.tool_calls)
        if self._limits.network_requests is not None:
            result["network_remaining"] = max(0, self._limits.network_requests - self._state.network_requests)
        if self._limits.storage_bytes is not None:
            result["storage_remaining"] = max(0, self._limits.storage_bytes - self._state.storage_bytes)
        if self._limits.compute_units is not None:
            result["compute_remaining"] = max(0, self._limits.compute_units - self._state.compute_units)
        return result

    def state(self) -> Dict[str, Any]:
        return self._state.to_dict()

    def reset(self) -> None:
        self._state = BudgetState(start_time=time.time())


# Global budget registry — scoped budgets by name.
_budget_registry: Dict[str, ResourceBudget] = {}
_budget_lock = threading.Lock()


def register_budget(name: str, budget: ResourceBudget) -> ResourceBudget:
    """Register a named budget for reuse."""
    with _budget_lock:
        _budget_registry[name] = budget
    return budget


def get_budget(name: str) -> Optional[ResourceBudget]:
    with _budget_lock:
        return _budget_registry.get(name)


def get_or_create_budget(name: str, limits: Optional[BudgetLimits] = None) -> ResourceBudget:
    """Return an existing named budget or create and register one."""
    with _budget_lock:
        existing = _budget_registry.get(name)
        if existing is not None:
            return existing
        budget = ResourceBudget(limits=limits, name=name)
        _budget_registry[name] = budget
        return budget


def list_budgets() -> List[Dict[str, Any]]:
    with _budget_lock:
        return [{"name": b.name, **b.state()} for b in _budget_registry.values()]


# Global recursion guard
_recursion_guard: RecursionGuard | None = None


def get_recursion_guard() -> RecursionGuard:
    """Return the global RecursionGuard singleton."""
    global _recursion_guard
    if _recursion_guard is None:
        _recursion_guard = RecursionGuard()
    return _recursion_guard