"""Tests for aetheros_security.budget (resource budgets + recursion limits)."""

import threading
import time

import pytest

from aetheros_security.budget import (
    BudgetLimits,
    RecursionError,
    RecursionGuard,
    ResourceBudget,
    get_budget,
    get_or_create_budget,
    get_recursion_guard,
    register_budget,
)


class TestRecursionGuard:
    def test_depth_tracking(self):
        guard = RecursionGuard(max_depth=3)
        assert guard.depth == 0
        guard.push("agent")
        guard.push("tool")
        assert guard.depth == 2
        assert guard.pop() == "tool"
        assert guard.depth == 1

    def test_can_recurse_respects_soft_cap(self):
        guard = RecursionGuard(max_depth=2)
        assert guard.can_recurse()
        guard.push()
        guard.push()
        assert not guard.can_recurse()

    def test_remaining(self):
        guard = RecursionGuard(max_depth=5)
        guard.push()
        assert guard.remaining() == 4

    def test_absolute_cap(self):
        guard = RecursionGuard(max_depth=1)  # soft cap is low
        with pytest.raises(RecursionError):
            for _ in range(64):  # exceeds _ABSOLUTE_MAX_DEPTH
                guard.push()

    def test_thread_local_isolation(self):
        guard = RecursionGuard()
        guard.push("main")
        depths = []

        def worker():
            guard.push("worker")
            depths.append(guard.depth)

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        assert depths == [1]  # worker sees its own stack only
        assert guard.depth == 1  # main still at depth 1

    def test_reset(self):
        guard = RecursionGuard()
        guard.push()
        guard.reset()
        assert guard.depth == 0

    def test_singleton(self):
        assert get_recursion_guard() is get_recursion_guard()


class TestResourceBudget:
    def test_tool_call_ceiling(self):
        budget = ResourceBudget(limits=BudgetLimits(tool_calls=3))
        budget.spend_tool_call()
        budget.spend_tool_call()
        assert budget.can_tool_call()
        budget.spend_tool_call()
        assert not budget.can_tool_call()
        assert budget.exhausted()

    def test_cost_ceiling(self):
        budget = ResourceBudget(limits=BudgetLimits(cost_usd=1.0))
        budget.spend_cost(0.6)
        assert budget.can_cost(0.3)
        assert not budget.can_cost(0.5)

    def test_time_ceiling(self):
        budget = ResourceBudget(limits=BudgetLimits(time_seconds=0.05))
        time.sleep(0.08)
        assert budget.time_exceeded()
        assert budget.exhausted()

    def test_token_ceiling(self):
        budget = ResourceBudget(limits=BudgetLimits(token_budget=100))
        budget.spend_tokens(80)
        assert budget.can_tokens(19)
        assert not budget.can_tokens(20)

    def test_network_ceiling(self):
        budget = ResourceBudget(limits=BudgetLimits(network_requests=2))
        budget.spend_network_request()
        budget.spend_network_request()
        assert not budget.can_network_request()

    def test_storage_ceiling(self):
        budget = ResourceBudget(limits=BudgetLimits(storage_bytes=10))
        budget.spend_storage(6)
        assert budget.can_storage(3)
        assert not budget.can_storage(5)

    def test_compute_ceiling(self):
        budget = ResourceBudget(limits=BudgetLimits(compute_units=1))
        budget.spend_compute(1)
        assert not budget.can_compute()

    def test_unlimited_by_default(self):
        budget = ResourceBudget()
        for _ in range(1000):
            budget.spend_tool_call()
        assert budget.can_tool_call()
        assert not budget.exhausted()

    def test_remaining_report(self):
        budget = ResourceBudget(limits=BudgetLimits(tool_calls=10, cost_usd=5.0))
        budget.spend_tool_call()
        budget.spend_cost(1.0)
        remaining = budget.remaining()
        assert remaining["tool_calls_remaining"] == 9
        assert remaining["cost_remaining_usd"] == 4.0

    def test_reset(self):
        budget = ResourceBudget(limits=BudgetLimits(tool_calls=1))
        budget.spend_tool_call()
        assert budget.exhausted()
        budget.reset()
        assert not budget.exhausted()

    def test_registry(self):
        budget = register_budget("test-budget", ResourceBudget(name="test-budget"))
        assert get_budget("test-budget") is budget
        assert get_or_create_budget("test-budget") is budget

    def test_get_or_create(self):
        created = get_or_create_budget("unique-budget",
                                       limits=BudgetLimits(tool_calls=1))
        assert get_budget("unique-budget") is created